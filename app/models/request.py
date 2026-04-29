from datetime import date
from typing import Optional
from pydantic import BaseModel, EmailStr, Field


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000)
    source: Optional[str] = None   # filename to filter Pinecone query; None = all docs


class CreateEmployeeRequest(BaseModel):
    employee_id: str = Field(..., min_length=3, max_length=20, pattern=r"^[A-Z]{1,10}\d{1,6}$")
    name: str = Field(..., min_length=2, max_length=100)
    email: EmailStr
    password: str = Field(..., min_length=8)
    department: str = Field(..., min_length=2, max_length=100)
    position: str = Field(..., min_length=2, max_length=100)
    is_admin: bool = False


class UpdateLeaveBalanceRequest(BaseModel):
    annual_leave: Optional[int] = Field(None, ge=0, le=365)
    sick_leave: Optional[int] = Field(None, ge=0, le=365)
    casual_leave: Optional[int] = Field(None, ge=0, le=365)


class UpdateLeaveRequestStatus(BaseModel):
    status: str = Field(..., pattern=r"^(approved|rejected)$")
    admin_comment: Optional[str] = Field(None, max_length=500)
