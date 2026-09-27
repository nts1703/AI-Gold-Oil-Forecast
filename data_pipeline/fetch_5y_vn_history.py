import os
import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def fetch_and_seed_5y_vn_data():
    print("[+] Đang tải 5 năm dữ liệu lịch sử cho thị trường Việt Nam...")

    # 1. Tải dữ liệu 5 năm từ Yahoo Finance: Vàng thế giới (GC=F), Tỷ giá USD/VND (VND=X), Dầu (CL=F)
    tickers = yf.download(["GC=F", "VND=X", "CL=F"], period="5y", interval="1d")['Close'].reset_index()
    tickers.columns = ['date', 'oil_world', 'gold_world', 'usdvnd']
    
    tickers['date'] = pd.to_datetime(tickers['date']).dt.strftime('%Y-%m-%d')
    tickers = tickers.dropna().sort_values('date').reset_index(drop=True)

    # 2. Quy đổi ra giá Vàng SJC ước tính (1 cây = 1.20565 oz * Tỷ giá + Thuế phí & Chênh lệch SJC)
    # Công thức quy đổi chuẩn: (Giá thế giới * 1.20565 * USDVND) + Chênh lệch SJC lịch sử (~5 - 18 triệu)
    tickers['sjc_buy'] = (tickers['gold_world'] * 1.20565 * tickers['usdvnd']) + 5000000
    tickers['sjc_sell'] = tickers['sjc_buy'] + 2000000  # Spread mua-bán khoảng 2 triệu

    # 3. Quy đổi ra giá Xăng RON95 VNĐ/lít ước tính từ giá Dầu mỏ thế giới
    tickers['ron95_price'] = (tickers['oil_world'] * tickers['usdvnd'] / 159) * 1.3 + 8000

    print(f"   [✓] Đã tạo thành công {len(tickers)} dòng dữ liệu 5 năm Việt Nam!")

    # 4. Push dữ liệu vào Supabase bảng `vn_commodity_prices` theo batch
    records = []
    for _, row in tickers.iterrows():
        # Thêm bản ghi Vàng SJC
        records.append({
            "category": "GOLD_SJC",
            "buy_price": round(float(row['sjc_buy']), 2),
            "sell_price": round(float(row['sjc_sell']), 2),
            "recorded_at": f"{row['date']}T08:00:00+00:00"
        })
        # Thêm bản ghi Xăng RON95
        records.append({
            "category": "GAS_RON95",
            "buy_price": round(float(row['ron95_price']), 2),
            "sell_price": round(float(row['ron95_price']), 2),
            "recorded_at": f"{row['date']}T08:00:00+00:00"
        })

    # Đẩy lên Supabase theo từng block 500 dòng
    step = 500
    for i in range(0, len(records), step):
        batch = records[i:i + step]
        try:
            supabase.table("vn_commodity_prices").insert(batch).execute()
            print(f"   [+] Đã lưu batch {i // step + 1}/{(len(records) // step) + 1} vào Supabase")
        except Exception as e:
            print(f"   [!] Lỗi chèn dữ liệu batch {i}: {e}")

    print("[✔] ĐÃ NẠP XONG 5 NĂM DỮ LIỆU GIÁ VIỆT NAM VÀO SUPABASE!")

if __name__ == "__main__":
    fetch_and_seed_5y_vn_data()