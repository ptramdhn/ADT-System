import pymysql
from sqlalchemy import create_engine, text
from sqlalchemy.orm import declarative_base, sessionmaker
from app.core.config import settings

def ensure_database_exists():
    """Create MySQL database if it does not already exist."""
    if "sqlite" in settings.DATABASE_URL.lower():
        return
    try:
        connection = pymysql.connect(
            host=settings.DB_HOST,
            port=settings.DB_PORT,
            user=settings.DB_USER,
            password=settings.DB_PASSWORD,
            charset='utf8mb4'
        )
        with connection.cursor() as cursor:
            cursor.execute(f"CREATE DATABASE IF NOT EXISTS {settings.DB_NAME} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;")
        connection.commit()
        connection.close()
        print(f"Database '{settings.DB_NAME}' is ready.")
    except Exception as e:
        print(f"Warning: Could not automatically create MySQL database: {e}")

# Ensure DB exists before engine creation
ensure_database_exists()

connect_args = {"check_same_thread": False} if "sqlite" in settings.DATABASE_URL.lower() else {}
engine_kwargs = {"pool_pre_ping": True}
if "sqlite" not in settings.DATABASE_URL.lower():
    engine_kwargs["pool_recycle"] = 3600

engine = create_engine(
    settings.DATABASE_URL,
    connect_args=connect_args,
    **engine_kwargs
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    from app.db import models
    Base.metadata.create_all(bind=engine)
