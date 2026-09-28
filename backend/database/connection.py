import os
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from dotenv import load_dotenv

# Tìm đường dẫn tuyệt đối tới file .env ở thư mục gốc dự án
BASE_DIR = Path(__file__).resolve().parent.parent.parent
env_path = BASE_DIR / ".env"

# Load file .env nếu tồn tại (môi trường Local), không bắt buộc phải có khi chạy CI/CD
if env_path.exists():
    load_dotenv(dotenv_path=env_path)
else:
    load_dotenv()

# Ưu tiên lấy DATABASE_URL, nếu không có sẽ tự chuyển sang lấy SUPABASE_URL
DATABASE_URL = os.getenv("DATABASE_URL") or os.getenv("SUPABASE_URL")

if not DATABASE_URL:
    raise ValueError(
        "Chưa tìm thấy biến môi trường DATABASE_URL hoặc SUPABASE_URL. "
        "Vui lòng cấu hình trong file .env (Local) hoặc GitHub Secrets."
    )

# Chuẩn hóa prefix cho SQLAlchemy nếu dùng URI postgres:// cũ
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

engine = create_engine(DATABASE_URL, echo=False)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()