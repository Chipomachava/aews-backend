import os
import time
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

CONNECT_ATTEMPTS = 4
CONNECT_BACKOFF_SECONDS = 1.5


def _connect_with_retry():
    import psycopg2

    last_error = None
    for attempt in range(CONNECT_ATTEMPTS):
        try:
            return psycopg2.connect(DATABASE_URL)
        except psycopg2.OperationalError as error:
            last_error = error
            if attempt < CONNECT_ATTEMPTS - 1:
                time.sleep(CONNECT_BACKOFF_SECONDS * (attempt + 1))
    raise last_error


engine_options = {"pool_pre_ping": True}
if DATABASE_URL and DATABASE_URL.startswith("postgres"):
    engine_options["creator"] = _connect_with_retry
    engine_options["pool_recycle"] = 300

engine = create_engine(DATABASE_URL, **engine_options)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()