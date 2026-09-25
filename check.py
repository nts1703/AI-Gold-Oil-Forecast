import os
from dotenv import load_dotenv
from google import genai

load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not GEMINI_API_KEY:
    print("❌ Không tìm thấy GEMINI_API_KEY trong file .env")
    exit()

client = genai.Client(api_key=GEMINI_API_KEY)

print("🔍 Đang kiểm tra danh sách model khả dụng...\n")

try:
    # Lấy toàn bộ danh sách model từ Google API
    models_list = client.models.list()
    
    print("=== CÁC MODEL BẠN CÓ THỂ SỬ DỤNG ===")
    for model in models_list:
        # Lọc hiển thị tên model
        model_id = model.name.replace("models/", "")
        print(f"• {model_id}")

except Exception as e:
    print(f"❌ Lỗi kết nối: {e}")