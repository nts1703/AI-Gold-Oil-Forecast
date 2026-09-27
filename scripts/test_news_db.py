import sys
import os
from datetime import datetime

# Thêm thư mục gốc dự án vào PYTHONPATH
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.database.connection import SessionLocal
from backend.database.models import VNMarketNews

def test_vn_market_news():
    print("⏳ Đang test các thao tác trên bảng [vn_market_news]...")
    db = SessionLocal()
    
    try:
        # 1. Thêm 2 tin tức mẫu với các chuyên mục khác nhau
        news_items = [
            VNMarketNews(
                title="Ngân hàng Nhà nước đấu thầu vàng miếng SJC để ổn định thị trường",
                content="NHNN tiếp tục đưa ra các biện pháp can thiệp nhằm thu hẹp chênh lệch giá vàng trong nước và thế giới...",
                source="VnExpress",
                url="https://vnexpress.net/test-dau-thau-vang-sjc-100",
                published_at=datetime.utcnow(),
                category="GOLD",
                sentiment_score=0.65,
                summary="NHNN can thiệp thị trường vàng."
            ),
            VNMarketNews(
                title="Bộ Công Thương điều chỉnh giá xăng RON95 tăng nhẹ theo chu kỳ",
                content="Giá xăng trong nước biến động cùng chiều với đà tăng của giá dầu Brent thế giới...",
                source="Báo Công Thương",
                url="https://congthuong.vn/test-gia-xang-ron95-200",
                published_at=datetime.utcnow(),
                category="FUEL",
                sentiment_score=0.10,
                summary="Xăng RON95 tăng nhẹ."
            )
        ]

        # Tránh trùng URL nếu đã chạy test trước đó
        for item in news_items:
            existing = db.query(VNMarketNews).filter(VNMarketNews.url == item.url).first()
            if not existing:
                db.add(item)

        db.commit()
        print("✅ Đã chèn thành công dữ liệu tin tức mẫu!")

        # 2. Truy vấn tất cả tin tức hiện có
        all_news = db.query(VNMarketNews).order_by(VNMarketNews.id.desc()).all()
        print(f"\n📰 Tổng số bài viết đang lưu trong database: {len(all_news)}")

        # 3. Lọc bài viết theo chuyên mục 'GOLD'
        gold_news = db.query(VNMarketNews).filter(VNMarketNews.category == "GOLD").all()
        print(f"📌 Bài viết thuộc chuyên mục [GOLD]: {len(gold_news)} bài")
        for news in gold_news:
            print(f"   - [{news.source}] {news.title} (Sentiment: {news.sentiment_score})")

    except Exception as e:
        db.rollback()
        print(f"❌ Lỗi khi test bảng news: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    test_vn_market_news()