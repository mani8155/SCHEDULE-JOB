import uuid
from sqlalchemy import Column, Integer, String, DateTime, Boolean, Time, Text, Date
from database import Base
import datetime


class ApiJobs(Base):
    __tablename__ = 'api_jobs'

    psk_id = Column(Integer, primary_key=True, autoincrement=True)
    psk_uid = Column(String, default=uuid.uuid4)
    created_by = Column(String(255))
    updated_by = Column(String(255))
    created_on = Column(DateTime, default=datetime.datetime.utcnow)
    updated_on = Column(DateTime, default=datetime.datetime.utcnow)
    user_id = Column(Integer)
    uid = Column(String(255))
    api_name = Column(String(255))
    api_type = Column(String(255))
    api_method = Column(String(10))
    api_source = Column(String(255))
    active = Column(Boolean, default=False)
    document_url = Column(String(255))
    core_api = Column(String(255))
    core_api_secrete_key = Column(String(255))
    timer_interval = Column(Integer)
    timer_options = Column(String(255))
    task_start = Column(Date)
    task_end = Column(Date)
    task_start_time = Column(Time)
    last_executed_on = Column(DateTime)

