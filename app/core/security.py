import base64
import hashlib
from datetime import datetime, timedelta
from typing import Optional

import bcrypt as _bcrypt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db

bearer_scheme = HTTPBearer()

# ── Password hashing ──────────────────────────────────────────────────────────
# passlib 1.7.4 is incompatible with bcrypt 5.x: passlib's detect_wrap_bug()
# tests with a 73-byte password, but bcrypt 5.x raises ValueError for any
# password > 72 bytes. We therefore call bcrypt directly.
#
# SHA-256 pre-hash: any-length password → 32 bytes → base64 → 44 ASCII bytes.
# bcrypt 5.x limit is 72 bytes, so 44 bytes always passes.


def _prehash(password: str) -> bytes:
    digest = hashlib.sha256(password.encode("utf-8")).digest()
    return base64.b64encode(digest)          # 44 ASCII bytes, always < 72


def hash_password(plain: str) -> str:
    return _bcrypt.hashpw(_prehash(plain), _bcrypt.gensalt(12)).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return _bcrypt.checkpw(_prehash(plain), hashed.encode("utf-8"))
    except Exception:
        return False


# ── JWT ───────────────────────────────────────────────────────────────────────

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    payload = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))
    payload["exp"] = expire
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def _decode_token(token: str) -> dict:
    try:
        return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")


# ── Dependencies ──────────────────────────────────────────────────────────────

def get_current_employee(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: Session = Depends(get_db),
):
    from app.models.db_models import Employee

    payload = _decode_token(credentials.credentials)
    employee_id: Optional[str] = payload.get("sub")
    if not employee_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token payload")

    employee = (
        db.query(Employee)
        .filter(Employee.employee_id == employee_id, Employee.is_active == True)
        .first()
    )
    if not employee:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Employee not found or inactive")
    return employee


def get_current_admin(employee=Depends(get_current_employee)):
    if not employee.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    return employee
