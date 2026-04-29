import os
import warnings
from contextlib import asynccontextmanager

# passlib 1.7.4 tries to read bcrypt.__about__.__version__ which was removed in
# bcrypt 4.x — suppress the harmless AttributeError it logs on startup.
warnings.filterwarnings("ignore", message=".*error reading bcrypt version.*")

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api.routes import admin, auth, chat, health, webhooks
from app.config import settings
from app.core.pinecone_client import init_pinecone_index
from app.database import SessionLocal, create_tables
from app.utils.logger import get_logger

logger = get_logger(__name__)


def _create_initial_admin() -> None:
    if not settings.INITIAL_ADMIN_EMAIL or not settings.INITIAL_ADMIN_PASSWORD:
        logger.warning("INITIAL_ADMIN_EMAIL or INITIAL_ADMIN_PASSWORD not set — skipping admin bootstrap")
        return

    from app.core.security import hash_password
    from app.models.db_models import Employee, LeaveBalance

    db = SessionLocal()
    try:
        existing = db.query(Employee).filter(Employee.email == settings.INITIAL_ADMIN_EMAIL).first()
        if existing:
            logger.info(f"Admin already exists: {settings.INITIAL_ADMIN_EMAIL}")
            return

        admin_emp = Employee(
            employee_id=settings.INITIAL_ADMIN_EMPLOYEE_ID,
            name=settings.INITIAL_ADMIN_NAME,
            email=settings.INITIAL_ADMIN_EMAIL,
            password_hash=hash_password(settings.INITIAL_ADMIN_PASSWORD),
            department="Administration",
            position="System Administrator",
            is_admin=True,
        )
        db.add(admin_emp)
        db.flush()
        db.add(LeaveBalance(employee_id=admin_emp.id))
        db.commit()
        logger.info(f"Initial admin created: {settings.INITIAL_ADMIN_EMAIL}")
    except Exception as exc:
        db.rollback()
        logger.error(f"Failed to create initial admin: {exc}")
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting HR Chatbot API …")
    create_tables()
    _create_initial_admin()
    init_pinecone_index()
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    logger.info("Startup complete. API is ready.")
    yield
    logger.info("Shutting down.")


app = FastAPI(
    title="HR Chatbot API",
    version="1.0.0",
    description="AI-powered HR Assistant — Groq LLM + Pinecone vector search + PostgreSQL",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="frontend/static"), name="static")

app.include_router(health.router, prefix="/api/v1", tags=["Health"])
app.include_router(auth.router, prefix="/api/v1/auth", tags=["Auth"])
app.include_router(chat.router, prefix="/api/v1", tags=["Chat"])
app.include_router(admin.router,    prefix="/api/v1/admin",    tags=["Admin"])
app.include_router(webhooks.router, prefix="/api/v1/webhooks", tags=["Webhooks"])


@app.get("/", include_in_schema=False)
def serve_frontend():
    return FileResponse("frontend/templates/index.html")
