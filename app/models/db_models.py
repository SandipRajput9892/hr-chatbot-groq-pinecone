import uuid
from datetime import datetime
from sqlalchemy import Boolean, Column, Date, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import relationship
from app.database import Base


class Document(Base):
    __tablename__ = "documents"

    id          = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    filename    = Column(String(255), nullable=False, unique=True)   # original name == Pinecone source
    file_path   = Column(String(500), nullable=False)
    chunks      = Column(Integer, default=0, nullable=False)
    uploaded_by = Column(UUID(as_uuid=True), ForeignKey("employees.id", ondelete="SET NULL"), nullable=True)
    uploaded_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    uploader = relationship("Employee", foreign_keys=[uploaded_by])


class Employee(Base):
    __tablename__ = "employees"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    employee_id = Column(String(20), unique=True, nullable=False, index=True)
    name = Column(String(100), nullable=False)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    department = Column(String(100), nullable=False)
    position = Column(String(100), nullable=False)
    is_admin = Column(Boolean, default=False, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    leave_balance = relationship(
        "LeaveBalance", back_populates="employee", uselist=False, cascade="all, delete-orphan"
    )
    leave_requests = relationship(
        "LeaveRequest", back_populates="employee", cascade="all, delete-orphan"
    )
    chat_history = relationship(
        "ChatHistory", back_populates="employee", cascade="all, delete-orphan"
    )


class LeaveBalance(Base):
    __tablename__ = "leave_balances"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    employee_id = Column(
        UUID(as_uuid=True), ForeignKey("employees.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    annual_leave = Column(Integer, default=20, nullable=False)
    sick_leave = Column(Integer, default=10, nullable=False)
    casual_leave = Column(Integer, default=5, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    employee = relationship("Employee", back_populates="leave_balance")


class LeaveRequest(Base):
    __tablename__ = "leave_requests"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    employee_id = Column(
        UUID(as_uuid=True), ForeignKey("employees.id", ondelete="CASCADE"), nullable=False
    )
    leave_type = Column(String(20), nullable=False)   # annual | sick | casual
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    days_requested = Column(Integer, nullable=False)
    reason = Column(Text, nullable=False)
    status = Column(String(20), default="pending", nullable=False)  # pending | approved | rejected
    admin_comment = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    employee = relationship("Employee", back_populates="leave_requests")


class ChatHistory(Base):
    __tablename__ = "chat_history"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    employee_id = Column(
        UUID(as_uuid=True), ForeignKey("employees.id", ondelete="CASCADE"), nullable=False
    )
    message = Column(Text, nullable=False)
    response = Column(Text, nullable=False)
    sources = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    employee = relationship("Employee", back_populates="chat_history")
