from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.config import settings
from app.core.security import create_access_token, verify_password
from app.database import get_db
from app.models.db_models import Employee
from app.models.request import LoginRequest
from app.models.response import TokenResponse

router = APIRouter()


@router.post("/login", response_model=TokenResponse)
def login(request: LoginRequest, db: Session = Depends(get_db)):
    employee: Employee = (
        db.query(Employee)
        .filter(Employee.email == request.email, Employee.is_active == True)
        .first()
    )
    if not employee or not verify_password(request.password, employee.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    token = create_access_token(
        data={"sub": employee.employee_id},
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    )
    return TokenResponse(
        access_token=token,
        employee_id=employee.employee_id,
        name=employee.name,
        email=employee.email,
        department=employee.department,
        position=employee.position,
        is_admin=employee.is_admin,
    )
