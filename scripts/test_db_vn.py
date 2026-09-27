import sys
import os
from datetime import datetime

# Thêm thư mục gốc dự án vào PYTHONPATH
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.database.connection import SessionLocal
from backend.database.models import VNCommodityPrice, VNSectorImpactForecast, VNMarketNews

def test_vn_database():
    print("⏳ Đang kết nối Supabase và chèn dữ liệu mẫu...")
    db = SessionLocal()
    
    try:
        # 1. Thêm bản ghi mẫu vào vn_commodity_prices
        sample_price = VNCommodityPrice(
            category="GOLD_SJC",
            buy_price=82000000.0,
            sell_price=84000000.0,
            recorded_at=datetime.utcnow()
        )
        db.add(sample_price)

        # 2. Thêm bản ghi mẫu vào vn_sector_impact_forecast
        sample_forecast = VNSectorImpactForecast(
            sector_name="GOLD_JEWELRY_RETAIL",
            sentiment_score=0.75,
            forecast_horizon="1_WEEK",
            summary="Nhu cầu vàng nhẫn PNJ tăng theo đà bứt phá của giá vàng thế giới.",
            created_at=datetime.utcnow()
        )
        db.add(sample_forecast)

        # 3. Thêm bản ghi mẫu vào vn_market_news
        sample_news = VNMarketNews(
            title="Bộ Công Thương công bố điều chỉnh giá xăng RON95 hôm nay",
            content="Liên Bộ Công Thương - Tài chính vừa điều chỉnh chu kỳ giá xăng dầu mới...",
            source="Báo Công Thương",
            url="https://test-link.vn/tin-xang-dau-1",
            published_at=datetime.utcnow(),
            category="FUEL",
            sentiment_score=0.15,
            summary="Giá xăng tăng nhẹ trong kỳ điều hành."
        )
        db.add(sample_news)

        # Lưu thay đổi vào Supabase
        db.commit()
        print("✅ Đã Insert dữ liệu mẫu thành công!")

        # 4. Kiểm tra Query truy vấn dữ liệu từ Supabase
        price_count = db.query(VNCommodityPrice).count()
        forecast_count = db.query(VNSectorImpactForecast).count()
        news_count = db.query(VNMarketNews).count()

        print("\n📊 Kiểm tra số lượng bản ghi hiện có trên Database:")
        print(f" • [vn_commodity_prices]: {price_count} bản ghi")
        print(f" • [vn_sector_impact_forecast]: {forecast_count} bản ghi")
        print(f" • [vn_market_news]: {news_count} bản ghi")

    except Exception as e:
        db.rollback()
        print(f"❌ Lỗi khi làm việc với Database: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    test_vn_database()