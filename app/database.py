import os
from sqlalchemy import create_engine, Column, Integer, String, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv
import datetime

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

# On Railway, DATABASE_URL might not be available, but component parts are.
if not DATABASE_URL:
    user = os.getenv("POSTGRES_USER")
    password = os.getenv("POSTGRES_PASSWORD")
    host = os.getenv("PGHOST")
    port = os.getenv("PGPORT")
    db = os.getenv("POSTGRES_DB")

    if all([user, password, host, port, db]):
        DATABASE_URL = f"postgresql://{user}:{password}@{host}:{port}/{db}"

if not DATABASE_URL:
    raise Exception("Could not configure database connection. Please set DATABASE_URL or Railway's PG* environment variables.")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class DownloadLog(Base):
    __tablename__ = "download_logs"

    id = Column(Integer, primary_key=True, index=True)
    ip_address = Column(String, index=True)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close() 