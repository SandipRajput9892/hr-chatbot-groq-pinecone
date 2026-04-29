from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from app.core.security import get_current_admin, hash_password
from app.database import get_db
from app.models.db_models import Employee, LeaveBalance, LeaveRequest
from app.models.request import CreateEmployeeRequest, UpdateLeaveBalanceRequest, UpdateLeaveRequestStatus
from app.models.response import (
    EmployeeResponse,
    LeaveBalanceResponse,
    LeaveRequestResponse,
    MessageResponse,
)

router = APIRouter()


# ─── Employees ────────────────────────────────────────────────────────────────

@router.get("/employees", response_model=List[EmployeeResponse])
def list_employees(
    admin=Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    return db.query(Employee).filter(Employee.is_active == True).all()


@router.post("/employees", response_model=EmployeeResponse, status_code=status.HTTP_201_CREATED)
def create_employee(
    request: CreateEmployeeRequest,
    admin=Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    if db.query(Employee).filter(Employee.email == request.email).first():
        raise HTTPException(status_code=400, detail="Email already registered")
    if db.query(Employee).filter(Employee.employee_id == request.employee_id).first():
        raise HTTPException(status_code=400, detail="Employee ID already exists")

    employee = Employee(
        employee_id=request.employee_id,
        name=request.name,
        email=request.email,
        password_hash=hash_password(request.password),
        department=request.department,
        position=request.position,
        is_admin=request.is_admin,
    )
    db.add(employee)
    db.flush()
    db.add(LeaveBalance(employee_id=employee.id))
    db.commit()
    db.refresh(employee)
    return employee


@router.delete("/employees/{employee_id}", response_model=MessageResponse)
def delete_employee(
    employee_id: str,
    admin=Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    employee = db.query(Employee).filter(Employee.employee_id == employee_id).first()
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    if employee.id == admin.id:
        raise HTTPException(status_code=400, detail="You cannot deactivate your own account")

    employee.is_active = False
    db.commit()
    return MessageResponse(message=f"Employee {employee_id} deactivated successfully")


# ─── Leave Balances ───────────────────────────────────────────────────────────

@router.get("/employees/{employee_id}/leave-balance", response_model=LeaveBalanceResponse)
def get_leave_balance(
    employee_id: str,
    admin=Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    employee = db.query(Employee).filter(Employee.employee_id == employee_id).first()
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    if not employee.leave_balance:
        raise HTTPException(status_code=404, detail="Leave balance record not found")
    return employee.leave_balance


@router.put("/employees/{employee_id}/leave-balance", response_model=LeaveBalanceResponse)
def update_leave_balance(
    employee_id: str,
    request: UpdateLeaveBalanceRequest,
    admin=Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    employee = db.query(Employee).filter(Employee.employee_id == employee_id).first()
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")

    balance = employee.leave_balance
    if not balance:
        balance = LeaveBalance(employee_id=employee.id)
        db.add(balance)

    if request.annual_leave is not None:
        balance.annual_leave = request.annual_leave
    if request.sick_leave is not None:
        balance.sick_leave = request.sick_leave
    if request.casual_leave is not None:
        balance.casual_leave = request.casual_leave
    balance.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(balance)
    return balance


# ─── Leave Requests ───────────────────────────────────────────────────────────

@router.get("/leave-requests", response_model=List[LeaveRequestResponse])
def list_leave_requests(
    status_filter: Optional[str] = Query(None, alias="status"),
    admin=Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    q = db.query(LeaveRequest)
    if status_filter:
        q = q.filter(LeaveRequest.status == status_filter)
    requests = q.order_by(LeaveRequest.created_at.desc()).all()

    return [
        LeaveRequestResponse(
            id=r.id,
            employee_id=r.employee_id,
            leave_type=r.leave_type,
            start_date=r.start_date,
            end_date=r.end_date,
            days_requested=r.days_requested,
            reason=r.reason,
            status=r.status,
            admin_comment=r.admin_comment,
            created_at=r.created_at,
            updated_at=r.updated_at,
            employee_name=r.employee.name if r.employee else None,
        )
        for r in requests
    ]


@router.put("/leave-requests/{request_id}", response_model=LeaveRequestResponse)
def update_leave_request(
    request_id: str,
    request: UpdateLeaveRequestStatus,
    admin=Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    leave_req = db.query(LeaveRequest).filter(LeaveRequest.id == request_id).first()
    if not leave_req:
        raise HTTPException(status_code=404, detail="Leave request not found")
    if leave_req.status != "pending":
        raise HTTPException(status_code=400, detail=f"Leave request already {leave_req.status}")

    leave_req.status = request.status
    leave_req.admin_comment = request.admin_comment
    leave_req.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(leave_req)

    return LeaveRequestResponse(
        id=leave_req.id,
        employee_id=leave_req.employee_id,
        leave_type=leave_req.leave_type,
        start_date=leave_req.start_date,
        end_date=leave_req.end_date,
        days_requested=leave_req.days_requested,
        reason=leave_req.reason,
        status=leave_req.status,
        admin_comment=leave_req.admin_comment,
        created_at=leave_req.created_at,
        updated_at=leave_req.updated_at,
        employee_name=leave_req.employee.name if leave_req.employee else None,
    )


# ─── Seed ─────────────────────────────────────────────────────────────────────

@router.post("/seed", response_model=MessageResponse)
def seed_database(
    admin=Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    if db.query(Employee).filter(Employee.is_admin == False).count() > 0:
        raise HTTPException(status_code=400, detail="Database already seeded with employees")

    seed_data = [
        {
            "employee_id": "EMP001",
            "name": "Alice Johnson",
            "email": "alice.johnson@company.com",
            "password": "Employee@123",
            "department": "Engineering",
            "position": "Senior Software Engineer",
        },
        {
            "employee_id": "EMP002",
            "name": "Bob Smith",
            "email": "bob.smith@company.com",
            "password": "Employee@123",
            "department": "Human Resources",
            "position": "HR Specialist",
        },
        {
            "employee_id": "EMP003",
            "name": "Carol White",
            "email": "carol.white@company.com",
            "password": "Employee@123",
            "department": "Finance",
            "position": "Financial Analyst",
        },
        {
            "employee_id": "EMP004",
            "name": "David Brown",
            "email": "david.brown@company.com",
            "password": "Employee@123",
            "department": "Marketing",
            "position": "Marketing Manager",
        },
        {
            "employee_id": "EMP005",
            "name": "Eva Martinez",
            "email": "eva.martinez@company.com",
            "password": "Employee@123",
            "department": "Engineering",
            "position": "QA Engineer",
        },
    ]

    created = []
    for data in seed_data:
        employee = Employee(
            employee_id=data["employee_id"],
            name=data["name"],
            email=data["email"],
            password_hash=hash_password(data["password"]),
            department=data["department"],
            position=data["position"],
            is_admin=False,
        )
        db.add(employee)
        db.flush()
        db.add(LeaveBalance(employee_id=employee.id))
        created.append(data["employee_id"])

    db.commit()
    return MessageResponse(
        message=f"Successfully seeded {len(created)} employees",
        data={"employees": created, "default_password": "Employee@123"},
    )
