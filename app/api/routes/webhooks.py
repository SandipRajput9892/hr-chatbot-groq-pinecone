import re
import secrets
import string

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.config import settings
from app.core.security import hash_password
from app.database import get_db
from app.models.db_models import Employee, LeaveBalance
from app.utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter()


def _generate_password(length: int = 12) -> str:
    alphabet = string.ascii_letters + string.digits + "!@#$"
    return "".join(secrets.choice(alphabet) for _ in range(length))


def _normalize_employee_id(raw: str) -> str | None:
    """Convert any Zoho employee ID string into our EMP\d+ pattern, or return None."""
    raw = raw.strip().upper()
    if re.match(r"^[A-Z]{1,10}\d{1,6}$", raw):
        return raw
    digits = re.sub(r"\D", "", raw)
    return f"EMP{digits.zfill(3)}" if digits else None


def _pick(payload: dict, *keys: str, default: str = "") -> str:
    """Return the first non-empty value from payload matching any of the keys."""
    for k in keys:
        v = payload.get(k) or payload.get(k.lower()) or payload.get(k.upper())
        if v:
            return str(v).strip()
    return default


def _verify_token(request: Request) -> None:
    """Reject the request if ZOHO_WEBHOOK_TOKEN is set and the caller didn't send it."""
    expected = settings.ZOHO_WEBHOOK_TOKEN
    if not expected:
        return
    sent = (
        request.headers.get("X-Zoho-Webhook-Token")
        or request.headers.get("Authorization", "").removeprefix("Bearer ").strip()
        or request.query_params.get("token", "")
    )
    if sent != expected:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid webhook token")


@router.post("/zoho", status_code=status.HTTP_200_OK)
async def zoho_employee_webhook(
    request: Request,
    db: Session = Depends(get_db),
):
    """
    Zoho People calls this endpoint whenever a new employee is added.
    Configure the Zoho webhook URL as:
        https://<your-domain>/api/v1/webhooks/zoho
    Set the secret token in ZOHO_WEBHOOK_TOKEN and pass it as the
    X-Zoho-Webhook-Token header (or ?token=... query param) in Zoho.
    """
    _verify_token(request)

    # Parse JSON or form-encoded body (Zoho sends either depending on config)
    content_type = request.headers.get("content-type", "")
    if "application/json" in content_type:
        payload: dict = await request.json()
    else:
        form = await request.form()
        payload = dict(form)

    logger.info(f"Zoho webhook payload: {payload}")

    # ── Extract fields (Zoho field names differ per org/configuration) ──────
    email = _pick(
        payload,
        "EmailID", "email", "Email", "official_email", "workEmail",
    )
    if not email:
        logger.warning("Zoho webhook: no email in payload — skipped")
        return {"status": "skipped", "reason": "missing email"}

    first     = _pick(payload, "First_Name", "firstName", "first_name", "givenName")
    last      = _pick(payload, "Last_Name",  "lastName",  "last_name",  "familyName")
    full_name = (
        _pick(payload, "Full_Name", "fullName", "displayName")
        or f"{first} {last}".strip()
        or email.split("@")[0]
    )
    dept      = _pick(payload, "Department", "department", "dept") or "General"
    position  = _pick(payload, "Designation", "designation", "jobTitle", "position") or "Employee"
    raw_id    = _pick(payload, "Employee_ID", "employee_id", "EmployeeID", "staffId")

    # ── Idempotency: skip if this email already exists ───────────────────────
    if db.query(Employee).filter(Employee.email == email).first():
        logger.info(f"Zoho webhook: {email} already exists — skipped")
        return {"status": "skipped", "reason": "employee already exists"}

    # ── Resolve employee ID ──────────────────────────────────────────────────
    emp_id = _normalize_employee_id(raw_id) if raw_id else None

    # If normalised ID already taken, fall back to auto-increment
    if emp_id and db.query(Employee).filter(Employee.employee_id == emp_id).first():
        emp_id = None

    if not emp_id:
        count = db.query(Employee).count() + 1
        emp_id = f"EMP{count:03d}"
        while db.query(Employee).filter(Employee.employee_id == emp_id).first():
            count += 1
            emp_id = f"EMP{count:03d}"

    # ── Create employee ──────────────────────────────────────────────────────
    temp_password = _generate_password()

    employee = Employee(
        employee_id=   emp_id,
        name=          full_name,
        email=         email,
        password_hash= hash_password(temp_password),
        department=    dept,
        position=      position,
        is_admin=      False,
    )
    db.add(employee)
    db.flush()
    db.add(LeaveBalance(employee_id=employee.id))
    db.commit()

    logger.info(
        f"Zoho webhook: created employee | id={emp_id} | name={full_name} "
        f"| email={email} | temp_password={temp_password}"
    )

    return {
        "status":       "created",
        "employee_id":  emp_id,
        "name":         full_name,
        "email":        email,
        "temp_password": temp_password,
    }
