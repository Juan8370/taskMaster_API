from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from app.config import DATABASE_URL

# Only apply sqlite-specific connect_args when using sqlite
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

# Enable pool_pre_ping to avoid stale connections (useful for cloud DBs like Neon)
engine = create_engine(
    DATABASE_URL,
    connect_args=connect_args,
    pool_pre_ping=True,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
