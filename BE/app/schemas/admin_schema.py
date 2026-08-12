# admin_schema.py
from datetime import datetime

from pydantic import BaseModel, Field


class AdminLogin(BaseModel):
    username: str = Field(min_length=1, max_length=50, examples=["admin01"])
    password: str = Field(min_length=1, examples=["pwd1234"])


class AdminPublic(BaseModel):
    id: int
    username: str
    created_at: datetime
