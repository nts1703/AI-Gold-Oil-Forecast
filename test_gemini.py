import os
import json
import time
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not GEMINI_API_KEY:
    print("❌ Không tìm thấy GEMINI_API_KEY trong file .env")
    exit()

client = genai.Client(api_key=GEMINI_API_KEY)

news_text = """
Tensions in the Middle East escalated further on Tuesday as Iran-backed militias launched drone attacks on oil facilities in Saudi Arabia. 
Crude oil prices jumped more than 3% in early trading, while gold also rose as investors sought safe-haven assets. 
Analysts warn that prolonged conflict could disrupt global energy supplies.
"""

prompt = f"""
Phân tích đoạn tin tức sau và trả về kết quả ở định dạng JSON.
Yêu cầu các trường:
- "sentiment": cảm xúc tổng thể (positive / negative / neutral)
- "sentiment_score": điểm từ -1 (rất tiêu cực) đến 1 (rất tích cực)
- "main_topics": danh sách các chủ đề chính (list string)
- "geopolitical_risk": mức độ rủi ro địa chính trị (low / medium / high)
- "affected_assets": các tài sản bị ảnh hưởng (ví dụ: gold, oil, usd...)
- "summary": tóm tắt ngắn gọn bằng tiếng Việt (1-2 câu)

Tin tức:
\"\"\"
{news_text}
\"\"\"
"""

def generate_content_with_retry(prompt, max_retries=3, delay=3):
    """Gửi request với cơ chế tự thử lại nếu server Google báo bận (503)"""
    for attempt in range(1, max_retries + 1):
        try:
            print(f"Đang gửi request đến Gemini (Lần {attempt}/{max_retries})...")
            response = client.models.generate_content(
                model="gemini-3.8-flash",
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                ),
            )
            return response
        except Exception as e:
            err_msg = str(e)
            if "503" in err_msg or "UNAVAILABLE" in err_msg:
                print(f"⚠️ Server Google đang bận (503). Chờ {delay}s rồi thử lại...")
                time.sleep(delay)
            else:
                raise e
    raise Exception("Không thể kết nối đến API sau nhiều lần thử.")

try:
    response = generate_content_with_retry(prompt)
    result_json = json.loads(response.text)
    
    print("\n✅ Phân tích thành công!\n")
    print(json.dumps(result_json, indent=2, ensure_ascii=False))

except Exception as e:
    print(f"\n❌ Có lỗi xảy ra: {e}")