import sys
import os

# Thêm thư mục gốc dự án vào PYTHONPATH
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.database.connection import engine, Base
# Import đầy đủ cả 4 model cũ và 3 model Việt Nam mới
from backend.database.models import (
    MarketPrice, 
    TechnicalIndicator, 
    News, 
    Prediction,
    VNCommodityPrice,
    VNSectorImpactForecast,
    VNMarketNews
)

def main():
    print("[+] Đang kết nối tới Supabase Database và tạo các bảng...")
    try:
        # SQLAlchemy sẽ kiểm tra và chỉ tạo thêm các bảng chưa có
        Base.metadata.create_all(bind=engine)
        print("[✔] Khởi tạo thành công toàn bộ các bảng trong Database (Thế giới + Việt Nam)!")
    except Exception as e:
        print(f"[✘] Lỗi khởi tạo Database: {e}")

if __name__ == "__main__":
    main()