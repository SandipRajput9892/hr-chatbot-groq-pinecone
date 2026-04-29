from datetime import date, datetime
from typing import Any, Dict, List, Optional
from uuid import UUID
from pydantic import BaseModel


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    employee_id: str
    name: str
    email: str
    department: str
    position: str
    is_admin: bool


class EmployeeResponse(BaseModel):
    id: UUID
    employee_id: str
    name: str
    email: str
    department: str
    position: str
    is_admin: bool
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class LeaveBalanceResponse(BaseModel):
    employee_id: UUID
    annual_leave: int
    sick_leave: int
    casual_leave: int
    updated_at: datetime

    model_config = {"from_attributes": True}


class LeaveRequestResponse(BaseModel):
    id: UUID
    employee_id: UUID
    leave_type: str
    start_date: date
    end_date: date
    days_requested: int
    reason: str
    status: str
    admin_comment: Optional[str]
    created_at: datetime
    updated_at: datetime
    employee_name: Optional[str] = None

    model_config = {"from_attributes": True}


class DocumentResponse(BaseModel):
    id: UUID
    filename: str
    chunks: int
    uploaded_at: datetime
    uploader_name: Optional[str] = None


class ChatResponse(BaseModel):
    message: str
    sources: Optional[List[str]] = None


class HealthResponse(BaseModel):
    status: str
    version: str
    services: Dict[str, str]


class MessageResponse(BaseModel):
    message: str
    data: Optional[Any] = None
