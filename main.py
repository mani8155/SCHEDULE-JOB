import time
from urllib.parse import quote_plus
import threading
import schedule
from sqlalchemy import create_engine, inspect, select, and_
from sqlalchemy.exc import OperationalError, SQLAlchemyError
from sqlalchemy.orm import declarative_base, sessionmaker, Session
import json
import asyncio
import logging
import requests as req
from fastapi import FastAPI, Depends, HTTPException
import schemas
from models import *
from database import get_db
from pytz import timezone

app = FastAPI(docs_url='/api_jobs', openapi_url='/api_jobs/openapi.json', title="Schedule Jobs")

IST = timezone("Asia/Kolkata")


@app.get('/api_jobs/get_records')
async def get_records(db: Session = Depends(get_db)):
    obj = db.query(ApiJobs).all()
    return obj


@app.get('/api_jobs/get_record/{psk_id}')
async def get_record(psk_id: int, db: Session = Depends(get_db)):
    obj = db.query(ApiJobs).filter_by(psk_id=psk_id).first()
    return obj


@app.post('/api_jobs/create_record')
async def create_record(request: schemas.CreateRecordSchema, db: Session = Depends(get_db)):
    obj = ApiJobs(
        created_by=request.created_by,
        api_name=request.api_name,
        uid=request.uid,
        api_type=request.api_type,
        api_method=request.api_method,
        # db_connection=request.db_connection,
        # db_connection_name=request.db_connection_name,
        document_url=request.document_url,
        core_api=request.core_api,
        # api_base_url=request.api_base_url,
        core_api_secrete_key=request.core_api_secrete_key,
        timer_interval=request.timer_interval,
        timer_options=request.timer_options,
        task_start=request.task_start,
        task_end=request.task_end,
        task_start_time=request.task_start_time,
        # task_start_end=request.task_start_end
    )
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


@app.put('/api_jobs/update_record')
async def update_record(request: schemas.UpdateRecordSchema, db: Session = Depends(get_db)):
    obj = db.query(ApiJobs).filter_by(psk_id=request.psk_id).first()

    obj.updated_by = request.updated_by
    obj.api_name = request.api_name
    obj.document_url = request.document_url
    obj.core_api = request.core_api
    obj.core_api_secrete_key = request.core_api_secrete_key
    obj.timer_interval = request.timer_interval
    obj.timer_options = request.timer_options
    obj.task_start = request.task_start
    obj.task_end = request.task_end
    obj.task_start_time = request.task_start_time
    # obj.task_end_time = request.task_start_end
    obj.updated_on = datetime.datetime.now(IST)

    db.commit()
    db.refresh(obj)

    return {"message": "Record updated successfully", "data": obj}


@app.delete('/api_jobs/delete_record/{psk_id}/')
async def delete_record(psk_id: int, db: Session = Depends(get_db)):
    obj = db.query(ApiJobs).filter_by(psk_id=psk_id).first()
    if not obj:
        raise HTTPException(
            status_code=404,
            detail=f"Record with psk_id {psk_id} not found."
        )

    try:
        db.delete(obj)
        db.commit()
        return {"message": "Record deleted successfully."}
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"An error occurred while deleting the record: {str(e)}"
        )


# Store scheduled jobs
jobs = {}


def run_scheduler():
    while True:
        schedule.run_pending()
        time.sleep(1)


def get_token(secret_key):

    url = f"http://127.0.0.1:8011/auth/token?secret_key={secret_key}"
    headers = {'Content-Type': 'application/json'}
    response = req.post(url, headers=headers, data={})

    if response.status_code != 200:
        url = f"http://127.0.0.1:8011/auth/token"
        payload = json.dumps({"secret_key": secret_key})
        response = req.post(url, headers=headers, data=payload)

    return response.json()


def job(db, psk_id):
    obj = db.query(ApiJobs).filter_by(psk_id=psk_id).first()

    start_job_date = obj.task_start.date() if isinstance(obj.task_start, datetime.datetime) else obj.task_start
    end_job_date = obj.task_end.date() if isinstance(obj.task_end, datetime.datetime) else obj.task_end
    start_job_time = obj.task_start_time
    current_time = datetime.datetime.now().time()
    current_date = datetime.datetime.now().date()

    # Check if the job is within the correct date and time range
    if start_job_date <= current_date <= end_job_date:
        if current_time >= start_job_time:

            try:
                token_data = get_token(obj.core_api_secrete_key)
                token_type = token_data['token_type']
                access_token = token_data['access_token']

                url = "http://127.0.0.1:8007/coreapi/api/etl0401"
                # url = f"{api_base_url}/coreapi/api/{obj.core_api}/"

                payload = json.dumps({
                    "data": {}
                })
                headers = {
                    'Content-Type': 'application/json',
                    'Authorization': f'{token_type} {access_token}'
                }

                response = req.request("POST", url, headers=headers, data=payload)
                print(f"{obj.uid} : ", response.text)

                if response.status_code != 200:
                    job_instance = jobs.get(psk_id)

                    if job_instance:
                        schedule.cancel_job(job_instance)
                        del jobs[psk_id]

                        if obj:
                            obj.active = False
                            db.commit()
                            raise HTTPException(status_code=400, detail=response.text)

            except Exception as e:
                print(f"Error: {e}")


scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
scheduler_thread.start()


@app.post('/api_jobs/start_job/{psk_id}/')
async def start_job(psk_id: int, db: Session = Depends(get_db)):
    # Check if the job is already scheduled
    obj = db.query(ApiJobs).filter_by(psk_id=psk_id).first()
    if psk_id in jobs:
        raise HTTPException(status_code=400, detail=f"Job with psk_id {obj.uid} is already scheduled.")

    # Query the database for the job (replace with actual database query)
    if not obj:
        raise HTTPException(status_code=404, detail="Job not found")

    # Mark the job as active and save changes
    obj.active = True
    db.commit()


    timer_interval = obj.timer_interval
    time_unit = obj.timer_options

    # # Get current time and date

    if time_unit == 'seconds':
        job_instance = schedule.every(timer_interval).seconds.do(job, db, psk_id=psk_id)
    elif time_unit == 'minutes':
        job_instance = schedule.every(timer_interval).minutes.do(job, db, psk_id=psk_id)
    elif time_unit == 'hours':
        job_instance = schedule.every(timer_interval).hours.do(job, db, psk_id=psk_id)
    elif time_unit == 'days':
        job_instance = schedule.every(timer_interval).days.do(job, db, psk_id=psk_id)
    else:
        raise HTTPException(status_code=400, detail="Invalid time unit specified.")

    # Store the job in the jobs dictionary
    jobs[psk_id] = job_instance
    return {"message": "Job scheduled successfully"}


@app.post('/api_jobs/stop_job/{psk_id}/')
async def stop_job(psk_id: int, db: Session = Depends(get_db)):
    job_instance = jobs.get(psk_id)

    if job_instance:
        schedule.cancel_job(job_instance)
        del jobs[psk_id]

        obj = db.query(ApiJobs).filter_by(psk_id=psk_id).first()
        if obj:
            obj.active = False
            db.commit()

        return {"message": f"Job with psk_id '{psk_id}' stopped successfully."}
    else:
        raise HTTPException(status_code=400, detail="Job not found or already stopped")


@app.get('/api_jobs/check_core_api/{psk_id}')
async def check_core_api(psk_id: int, db: Session = Depends(get_db)):
    obj = db.query(ApiJobs).filter_by(psk_id=psk_id).first()
    if not obj.active:
        return HTTPException(status_code=400, detail=f"Check the Core API {obj.core_api} in Postman first, as it's "
                                                     f"not working")

    return {"message": f"core api '{obj.core_api}' working successfully."}
