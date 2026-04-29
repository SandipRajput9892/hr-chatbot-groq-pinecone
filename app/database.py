from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from app.config import settings

# make_url correctly handles percent-encoded characters in the password
# (e.g. %40 for @) and is required for PgBouncer / Supabase pooler URLs.
_db_url = make_url(settings.DATABASE_URL)

engine = create_engine(
    _db_url,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_tables():
    # Import models so SQLAlchemy registers them with Base.metadata before create_all
    from app.models.db_models import Employee, LeaveBalance, LeaveRequest, ChatHistory  # noqa: F401
    Base.metadata.create_all(bind=engine)
