import os
import sys
import subprocess
from datetime import datetime

def run_step(step_name, command):
    print(f"\n[+] Executing: {step_name}...")
    try:
        result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
        print(f"   [✓] Hoàn tất: {step_name}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"   [!] Lỗi tại bước '{step_name}': {e.stderr}")
        return False

def main():
    print("==================================================")
    print(f"🚀 BẮT ĐẦU PIPELINE TỰ ĐỘNG [Thời gian: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}]")
    print("==================================================")
    
    python_bin = sys.executable

    # Bước 1: Bơm/Cập nhật dữ liệu giá & chỉ báo kỹ thuật mới nhất từ Yahoo Finance vào Supabase
    step1 = run_step(
        "Cập nhật Giá & Chỉ báo kỹ thuật",
        f'"{python_bin}" data_pipeline/fetch_5y_history.py'
    )

    # Bước 2: Cào tin tức mới nhất từ RSS + Phân tích Sentiment Gemini AI
    step2 = run_step(
        "Cào tin tức & Phân tích Sentiment",
        f'"{python_bin}" data_pipeline/news_crawler.py'  # Thay đổi đường dẫn tới file crawler tin tức của bạn nếu cần
    )

    # Bước 3: Huấn luyện lại Model LightGBM & Tạo dự báo mới
    step3 = run_step(
        "Huấn luyện AI Model & Tạo dự báo",
        f'"{python_bin}" model_training/train_pipeline.py'
    )

    print("\n==================================================")
    if step1 and step2 and step3:
        print("✨ HOÀN THÀNH TẤT CẢ CÁC BƯỚC PIPELINE TỰ ĐỘNG HÀNG NGÀY!")
    else:
        print("⚠️ PIPELINE HOÀN THÀNH VỚI MỘT SỐ CẢNH BÁO/LỖI.")
    print("==================================================")

if __name__ == "__main__":
    main()