import os
import re
import json
import time
from datetime import datetime, timezone
import feedparser
from google import genai
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
client = genai.Client(api_key=GEMINI_API_KEY) if GEMINI_API_KEY else None

PRIMARY_MODEL = "gemini-3.8-flash"

VN_RSS_FEEDS = [
    "https://cafef.vn/tai-chinh-ngan-hang.rss",
    "https://cafef.vn/thi-truong.rss",
    "https://vnexpress.net/rss/kinh-doanh.rss",
    "https://news.google.com/rss/search?q=gi%C3%A1+v%C3%A0ng+SJC+OR+gi%C3%A1+x%C4%83ng+petrolimex&hl=vi&gl=VN&ceid=VN:vi"
]

VN_KEYWORDS = ["vàng", "sjc", "pnj", "xăng", "dầu", "petrolimex", "lạm phát", "ngân hàng nhà nước", "tỷ giá"]

# ==============================================================================
# BỘ TỪ ĐIỂN TÀI CHÍNH MỞ RỘNG (Dùng cho Fallback Rule-Based)
# ==============================================================================

# Từ khóa phân loại nhóm sản phẩm
GOLD_KEYWORDS = ["vàng", "sjc", "pnj", "doji", "bảo tín minh châu", "vàng nhẫn", "vàng miếng", "chỉ vàng", "kitco", "xauusd"]
FUEL_KEYWORDS = ["xăng", "dầu", "petrolimex", "ron95", "e5", "ron92", "dầu do", "dầu mazut", "dầu thô", "brent", "wti", "opec", "chiết khấu", "cây xăng", "nhiên liệu"]
POLICY_KEYWORDS = ["ngân hàng nhà nước", "nhnn", "fed", "lãi suất", "tỷ giá", "usd/vnd", "chính sách tiền tệ", "dự trữ ngoại hối"]

# Từ khóa mang chỉ báo TĂNG GIÁ (+1.0 -> Tích cực cho đà tăng)
POS_KEYWORDS = [
    # Động từ / Danh từ tăng
    "tăng", "bứt phá", "vọt", "leo dốc", "lên đỉnh", "lập đỉnh", "kỷ lục", "sốt", "vượt mốc",
    "phục hồi", "trồi lên", "bùng nổ", "phi mã", "tăng vọt", "tăng mạnh", "nhích tăng", "đắt đỏ",
    "hưởng lợi", "đà tăng", "xanh sàn", "vượt ngưỡng", "đẩy giá", "thiết lập đỉnh", "leo cao",
    "nóng lên", "ngược dòng", "bật tăng", "tiếp đà", "nâng giá", "vàng vọt", "đạt mốc",
    # Thị trường / Nguồn cung kích tăng giá
    "sức mua tăng", "khan hiếm", "thiếu hụt", "căng thẳng nguồn cung", "sinh lời", "lãi đậm",
    "lãi khủng", "leo thang", "sức ép tăng", "áp lực tăng", "cầu vượt cung"
]

# Từ khóa mang chỉ báo GIẢM GIÁ (-1.0 -> Tiêu cực cho giá)
NEG_KEYWORDS = [
    # Động từ / Danh từ giảm
    "giảm", "lao dốc", "sụt", "sụt giảm", "bốc hơi", "rớt", "rớt giá", "chìm sâu", "ảm đạm",
    "rớt đài", "giảm mạnh", "đáy", "tụt dốc", "giảm sâu", "quay đầu", "xả hàng", "đỏ sàn",
    "chốt lời", "xả bán", "suy yếu", "hạ nhiệt", "bay màu", "bán tháo", "lao đao", "chững lại",
    "mất mốc", "mất ngưỡng", "thủng đáy", "tuột dốc", "chiết khấu sâu", "rủi ro", "thua lỗ",
    # Thị trường / Nguồn cung kích giảm giá
    "thừa mứa", "dư cung", "dưới kỳ vọng", "đình trệ", "bị ép giá", "sức mua yếu", "ảm đạm"
]

def rule_based_sentiment(title: str, summary: str):
    full_text = f"{title} {summary}".lower()

    # 1. Nhận diện Category
    category = "MACRO"
    if any(k in full_text for k in GOLD_KEYWORDS):
        category = "GOLD"
    elif any(k in full_text for k in FUEL_KEYWORDS):
        category = "FUEL"
    elif any(k in full_text for k in POLICY_KEYWORDS):
        category = "POLICY"

    # 2. Đếm từ khóa tính điểm
    pos_score = sum(1 for kw in POS_KEYWORDS if kw in full_text)
    neg_score = sum(1 for kw in NEG_KEYWORDS if kw in full_text)
    
    total = pos_score + neg_score
    if total == 0:
        sentiment_score = 0.0
    else:
        # Chuẩn hóa về khoảng -1.0 đến 1.0
        sentiment_score = round((pos_score - neg_score) / total, 2)

    return {
        "category": category,
        "sentiment_score": sentiment_score,
        "summary": summary[:200]
    }

def analyze_vn_sentiment(title: str, summary: str):
    if not client:
        return rule_based_sentiment(title, summary)

    prompt = f"""
Bạn là chuyên gia phân tích kinh tế Việt Nam. 
Hãy phân tích tin tức sau và trả về DUY NHẤT 1 chuỗi JSON:
Tiêu đề: {title}
Tóm tắt: {summary}

Cấu trúc JSON bắt buộc:
{{
  "category": "GOLD / FUEL / POLICY / MACRO",
  "sentiment_score": <float từ -1.0 đến 1.0>,
  "summary": "<Tóm tắt ngắn gọn 1 câu bằng tiếng Việt>"
}}
"""
    try:
        time.sleep(4)  # Chờ 4s giảm tải API
        response = client.models.generate_content(
            model=PRIMARY_MODEL,
            contents=prompt
        )
        text = response.text.strip()
        text = re.sub(r"^```json\s*", "", text, flags=re.MULTILINE)
        text = re.sub(r"^```\s*", "", text, flags=re.MULTILINE)
        text = re.sub(r"\s*```$", "", text, flags=re.MULTILINE)
        return json.loads(text)

    except Exception as e:
        err_msg = str(e)
        print(f"   [!] Gemini bị nghẽn ({err_msg[:60]}...) -> Tự động dùng Rule-Based Từ Điển")
        return rule_based_sentiment(title, summary)

def crawl_vn_news():
    print("==========================================")
    print("=== BẮT ĐẦU CÀO TIN TỨC VIỆT NAM (HYBRID) ===")
    print("==========================================")

    for feed_url in VN_RSS_FEEDS:
        feed = feedparser.parse(feed_url)
        print(f"\n[+] Đang cào: {feed.feed.get('title', feed_url)}")

        for entry in feed.entries[:5]:
            title = entry.title
            url = entry.link
            raw_summary = getattr(entry, "summary", "") or title
            summary = re.sub(r'<[^>]+>', '', raw_summary).strip()

            if not any(kw in f"{title} {summary}".lower() for kw in VN_KEYWORDS):
                continue

            # Kiểm tra trùng URL
            try:
                check = supabase.table("vn_market_news").select("id").eq("url", url).execute()
                if check.data:
                    print(f"   [⏩] Bỏ qua (Đã tồn tại): {title[:50]}...")
                    continue
            except Exception as check_err:
                print(f"   [!] Lỗi check DB: {check_err}")

            print(f"   [->] Đang phân tích: {title[:50]}...")
            analysis = analyze_vn_sentiment(title, summary)

            news_data = {
                "title": title,
                "content": summary,
                "source": feed.feed.get("title", "VN News"),
                "url": url,
                "published_at": datetime.now(timezone.utc).isoformat(),
                "category": analysis.get("category", "MACRO"),
                "sentiment_score": analysis.get("sentiment_score", 0.0),
                "summary": analysis.get("summary", "")
            }

            try:
                supabase.table("vn_market_news").upsert(news_data, on_conflict="url").execute()
                print(f"   [✓] Lưu tin tức thành công! Score: {news_data['sentiment_score']} | Cat: {news_data['category']}")
            except Exception as db_err:
                print(f"   [!] Lỗi lưu DB: {db_err}")

if __name__ == "__main__":
    crawl_vn_news()