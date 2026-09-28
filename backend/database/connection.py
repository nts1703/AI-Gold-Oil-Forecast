import os
import re
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent.parent
env_path = BASE_DIR / ".env"

if env_path.exists():
    load_dotenv(dotenv_path=env_path)
else:
    load_dotenv()

# 1. Lấy giá trị biến môi trường và làm sạch khoảng trắng / dấu ngoặc kép dư thừa
raw_db_url = os.getenv("DATABASE_URL") or ""
raw_db_url = raw_db_url.strip().strip("'").strip('"')

# 2. Xử lý trường hợp bị dán nhầm URL https:// hoặc để trống
if not raw_db_url or raw_db_url.startswith("https://") or raw_db_url.startswith("http://"):
    raise ValueError(
        "\n" + "="*70 + "\n"
        "❌ LỖI CẤU HÌNH DATABASE_URL:\n"
        f"Giá trị DATABASE_URL hiện tại đang là: '{raw_db_url}'\n\n"
        "DATABASE_URL KHÔNG ĐƯỢC bắt đầu bằng 'https://'!\n"
        "Bạn cần sửa Secret 'DATABASE_URL' trên GitHub thành dạng PostgreSQL URI:\n"
        "postgresql://postgres.[PROJECT_REF]:[PASSWORD]@aws-0-ap-southeast-2.pooler.supabase.com:6543/postgres\n"
        "======================================================================\n"
    )

# 3. Chuẩn hóa prefix dialect cho SQLAlchemy
if raw_db_url.startswith("postgres://"):
    raw_db_url = raw_db_url.replace("postgres://", "postgresql://", 1)

engine = create_engine(raw_db_url, echo=False)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()