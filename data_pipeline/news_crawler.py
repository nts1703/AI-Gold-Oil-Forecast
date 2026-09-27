import os
import re
import json
import time
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
import dateutil.parser
import feedparser
from google import genai
from supabase import create_client, Client
from dotenv import load_dotenv

# Load biến môi trường từ file .env
load_dotenv()

# ==========================================
# 1. CẤU HÌNH KẾT NỐI
# ==========================================
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
client = genai.Client(api_key=GEMINI_API_KEY) if GEMINI_API_KEY else None

print(f"[DEBUG] Supabase Key loaded: {SUPABASE_KEY[:20]}..." if SUPABASE_KEY else "[DEBUG] Supabase Key: None")
print(f"[DEBUG] Gemini Key loaded: {GEMINI_API_KEY[:15]}..." if GEMINI_API_KEY else "[DEBUG] Gemini Key: None")

# Chỉ dùng 1 model duy nhất (ổn định nhất hiện tại)
MODELS_TO_TRY = ["gemini-3.8-flash"]

# ==========================================
# 2. DANH SÁCH NGUỒN RSS
# ==========================================
RSS_FEEDS = [
    "https://oilprice.com/rss/main",
    "https://www.fxstreet.com/rss/news",
    "https://www.kitco.com/rss/KitcoNews.xml",
    "https://cafef.vn/home.rss",
    "https://cafef.vn/doanh-nghiep.rss",
    "https://cafef.vn/thi-truong.rss",
    "https://news.google.com/rss/search?q=gi%C3%A1+v%C3%A0ng+OR+gi%C3%A1+d%E1%BA%A7u+OR+x%C4%83ng&hl=vi&gl=VN&ceid=VN:vi",
    "https://news.google.com/rss/search?q=gold+price+OR+crude+oil+OR+OPEC&hl=en-US&gl=US&ceid=US:en",
]

# ==========================================
# 3. DANH SÁCH TỪ KHÓA LỌC TIN
# ==========================================
KEYWORDS = [
    # Tiếng Việt
    "vàng", "sjc", "dầu", "dầu thô", "xăng", "xăng dầu", "opec", "địa chính trị",
    "fed", "lãi suất", "lạm phát",
    # Tiếng Anh
    "gold", "xauusd", "oil", "crude", "wti", "brent", "opec", "geopolitics",
    "petroleum", "energy", "fed", "inflation"
]

# ==========================================
# 4. PHÂN TÍCH SENTIMENT BẰNG GEMINI
# ==========================================
def analyze_sentiment_with_fallback(title: str, summary: str, retries_per_model=2):
    default_data = {
        "topic": "Macroeconomics",
        "gold_impact_score": 0.0,
        "oil_supply_threat_score": 0.0,
        "confidence_score": 0.5
    }

    if not client:
        return default_data, "failed"

    prompt = f"""
Bạn là chuyên gia phân tích kinh tế địa chính trị, thị trường Vàng và Dầu mỏ.
Hãy phân tích tin tức sau và trả về duy nhất chuỗi JSON chuẩn:
Tiêu đề: {title}
Tóm tắt: {summary}

Cấu trúc JSON bắt buộc:
{{
  "topic": "Military Action / Sanctions / OPEC / Diplomacy / Macroeconomics / Other",
  "gold_impact_score": <float từ -1.0 đến 1.0>,
  "oil_supply_threat_score": <float từ -1.0 đến 1.0>,
  "confidence_score": <float từ 0.0 đến 1.0>
}}
"""

    for model_name in MODELS_TO_TRY:
        for attempt in range(retries_per_model):
            try:
                # Nghỉ lâu hơn để tránh vượt free tier (5 req/phút)
                time.sleep(12)

                response = client.models.generate_content(
                    model=model_name,
                    contents=prompt
                )
                text = response.text.strip()

                # Làm sạch markdown nếu có
                text = re.sub(r"^```json\s*", "", text, flags=re.MULTILINE)
                text = re.sub(r"^```\s*", "", text, flags=re.MULTILINE)
                text = re.sub(r"\s*```$", "", text, flags=re.MULTILINE)

                parsed_result = json.loads(text)
                print(f"   [✓] Chấm điểm thành công bằng model: {model_name}")
                return parsed_result, "completed"

            except Exception as e:
                print(f"   [!] Lỗi model {model_name} (Lần {attempt + 1}/{retries_per_model}): {e}")
                time.sleep(15)  # nghỉ lâu hơn khi bị lỗi

    return default_data, "failed"


# ==========================================
# 5. CÀO TIN TỨC
# ==========================================
def crawl_and_process_news():
    print("==========================================")
    print("=== BẮT ĐẦU CÀO TIN TỨC VÀ PHÂN TÍCH AI ===")
    print("==========================================")

    for feed_url in RSS_FEEDS:
        feed = feedparser.parse(feed_url)
        print(f"\n[+] Đang cào nguồn: {feed.feed.get('title', feed_url)}")

        for entry in feed.entries[:6]:  # giảm xuống 6 bài để tiết kiệm quota
            title = entry.title
            url = entry.link
            raw_summary = getattr(entry, "summary", "") or title

            # Làm sạch HTML + link
            summary = re.sub(r'<[^>]+>', '', raw_summary)
            summary = re.sub(r'https?://\S+', '', summary)
            summary = summary.strip()

            # Lọc từ khóa
            combined_text = f"{title} {summary}".lower()
            if not any(kw in combined_text for kw in KEYWORDS):
                print(f"   [⏩] Bỏ qua (Không liên quan): {title[:55]}...")
                continue

            # Xử lý ngày tháng
            pub_date = None
            try:
                if hasattr(entry, "published_parsed") and entry.published_parsed:
                    pub_date = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)
                elif hasattr(entry, "published") and entry.published:
                    try:
                        pub_date = parsedate_to_datetime(entry.published)
                    except Exception:
                        pub_date = dateutil.parser.parse(entry.published)
                if pub_date and pub_date.tzinfo is None:
                    pub_date = pub_date.replace(tzinfo=timezone.utc)
            except Exception as date_err:
                print(f"   [!] Lỗi parse ngày: {date_err}")
                pub_date = datetime.now(timezone.utc)

            published_at_str = pub_date.isoformat() if pub_date else datetime.now(timezone.utc).isoformat()

            print(f"\n--> Đang xử lý: {title[:65]}...")

            # Kiểm tra trùng
            try:
                check_exist = supabase.table("news").select("id").eq("url", url).execute()
                if check_exist.data and len(check_exist.data) > 0:
                    print("   [⏩] Bỏ qua: Đã tồn tại trong Database.")
                    continue
            except Exception as check_err:
                print(f"   [!] Lỗi kiểm tra trùng: {check_err}")

            # Gọi Gemini
            analysis, status = analyze_sentiment_with_fallback(title, summary)

            news_data = {
                "title": title,
                "content": summary,
                "source": feed.feed.get("title", "Unknown"),
                "url": url,
                "published_at": published_at_str,
                "topic": analysis.get("topic", "Macroeconomics"),
                "gold_impact_score": analysis.get("gold_impact_score", 0.0),
                "oil_supply_threat_score": analysis.get("oil_supply_threat_score", 0.0),
                "confidence_score": analysis.get("confidence_score", 0.5),
                "status": status
            }

            # Lưu DB
            try:
                supabase.table("news").upsert(news_data, on_conflict="url").execute()
                print(f"   [+] Lưu DB thành công! Trạng thái: {status}")
            except Exception as db_err:
                print(f"   [!] Lỗi lưu Database: {db_err}")


# ==========================================
# 6. CHẤM BÙ (tạm thời tắt để tránh cháy quota)
# ==========================================
def reprocess_failed_news():
    print("\n==================================================")
    print("=== QUÉT VÀ CHẤM ĐIỂM BÙ (ĐANG TẠM TẮT) ===")
    print("==================================================")
    print("[!] Chức năng chấm bù đang tạm tắt để tránh vượt free tier.")
    print("    Khi cần chấm lại, hãy bỏ comment dòng gọi hàm này.")


if __name__ == "__main__":
    crawl_and_process_news()
    # reprocess_failed_news()   # ← tạm tắt