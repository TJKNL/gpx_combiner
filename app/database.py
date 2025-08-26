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

# Read pool sizing from env for flexibility, with conservative defaults
POOL_SIZE = int(os.getenv("DB_POOL_SIZE", "1"))
MAX_OVERFLOW = int(os.getenv("DB_MAX_OVERFLOW", "1"))
POOL_TIMEOUT = int(os.getenv("DB_POOL_TIMEOUT", "10"))
POOL_RECYCLE = int(os.getenv("DB_POOL_RECYCLE", "1800"))

engine = create_engine(
	DATABASE_URL,
	pool_size=POOL_SIZE,
	max_overflow=MAX_OVERFLOW,
	pool_timeout=POOL_TIMEOUT,
	pool_recycle=POOL_RECYCLE,
	pool_pre_ping=True,
)

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
	"""Return a truncated SHA-256 hash of the IP plus a required secret salt.
	Raises RuntimeError if HASH_SALT is missing to avoid insecure defaults."""
	salt = os.getenv("HASH_SALT")
	if not salt:
		raise RuntimeError(
			"HASH_SALT environment variable is not set.\n"
			"Set a strong random value in Railway variables (or .env locally) before starting the app."
		)
	return hashlib.sha256(f"{ip}{salt}".encode("utf-8")).hexdigest()[:16]

def get_db():
	db = SessionLocal()
	try:
		yield db
	finally:
		db.close() 