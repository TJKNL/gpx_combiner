import os
from sqlalchemy import create_engine, Column, Integer, String, DateTime, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv
import datetime
import hashlib

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

# --- one-off schema patch (adds ip_hash column if upgrading from v1 schema) ---
with engine.begin() as conn:
    conn.execute(text("""
        ALTER TABLE download_logs
        ADD COLUMN IF NOT EXISTS ip_hash VARCHAR;
    """))
# ---------------------------------------------------------------------------

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class DownloadLog(Base):
    __tablename__ = "download_logs"

    id = Column(Integer, primary_key=True, index=True)
    # Deprecated (kept null) – hashed variant below is used instead
    ip_address = Column(String, nullable=True)
    # New anonymised field
    ip_hash = Column(String, index=True)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)

def anonymise_ip(ip: str) -> str:
    """Return a truncated SHA-256 hash of the IP plus a salt.
    This preserves uniqueness while removing personal data."""
    salt = os.getenv("HASH_SALT", "gpxcombiner")
    return hashlib.sha256(f"{ip}{salt}".encode("utf-8")).hexdigest()[:16]

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close() 