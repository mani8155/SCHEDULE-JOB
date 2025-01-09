from pydantic import BaseModel
from typing import Optional
from datetime import datetime, date, time


class CreateRecordSchema(BaseModel):
    created_by: str
    api_name: str
    uid: str
    api_type: str
    api_method: str
    # db_connection: int
    # db_connection_name: str
    document_url: Optional[str] = None
    core_api: str
    core_api_secrete_key: str
    timer_interval: int
    timer_options: str
    task_start: date
    task_end: date
    task_start_time: time
    # task_start_end: time


class UpdateRecordSchema(BaseModel):
    psk_id: int
    updated_by: str
    api_name: str
    document_url: Optional[str] = None
    core_api: str
    core_api_secrete_key: str
    timer_interval: int
    timer_options: str
    task_start: date
    task_end: date
    task_start_time: time
    # task_start_end: time


