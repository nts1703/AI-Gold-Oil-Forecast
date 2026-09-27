import os
import yfinance as yf
import pandas as pd
import numpy as np
from supabase import create_client, Client

# Khởi tạo Supabase Client
SUPABASE_URL = os.getenv("SUPABASE_URL", "https://nyscfgkqwgpgifceiikp.supabase.co")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "sb_publishable_LVQZXX11x8tsfkg2rt0t-A_4r5_otpW")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)


def calculate_technical_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """Tính toán RSI, MACD, MA20, MA50 cho chuỗi lịch sử và chuẩn hóa ngày."""
    df = df.copy()
    
    # Chuẩn hóa Timestamp về dạng YYYY-MM-DD
    df["timestamp"] = pd.to_datetime(df["timestamp"]).dt.strftime("%Y-%m-%d")

    # 1. RSI (14)
    delta = df["close"].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df["rsi"] = 100 - (100 / (1 + rs))

    # 2. MACD (12, 26, 9)
    exp1 = df["close"].ewm(span=12, adjust=False).mean()
    exp2 = df["close"].ewm(span=26, adjust=False).mean()
    df["macd"] = exp1 - exp2
    df["macd_signal"] = df["macd"].ewm(span=9, adjust=False).mean()
    df["macd_hist"] = df["macd"] - df["macd_signal"]

    # 3. Moving Averages
    df["ma20"] = df["close"].rolling(window=20).mean()
    df["ma50"] = df["close"].rolling(window=50).mean()

    # Loại bỏ các dòng NaN do rolling window (50 dòng đầu)
    return df.dropna().reset_index(drop=True)


def push_to_supabase(df: pd.DataFrame, asset_name: str, batch_size: int = 200):
    """
    Đẩy dữ liệu vào Supabase theo lô (Batching) giúp tăng tốc độ 
    và bắt lỗi minh bạch.
    """
    print(f"\n[+] Đang đẩy dữ liệu {asset_name} vào Supabase (Tổng: {len(df)} dòng)...")
    total_inserted = 0

    for i in range(0, len(df), batch_size):
        batch_df = df.iloc[i : i + batch_size]

        # 1. Chuẩn bị batch dữ liệu cho bảng market_prices
        mp_batch = []
        for _, row in batch_df.iterrows():
            mp_batch.append({
                "symbol": str(row["symbol"]),
                "timestamp": str(row["timestamp"]),
                "open": float(row["open"]),
                "high": float(row["high"]),
                "low": float(row["low"]),
                "close": float(row["close"]),
                "volume": float(row["volume"])
            })

        try:
            # Upsert theo lô vào bảng market_prices
            mp_res = supabase.table("market_prices").upsert(
                mp_batch, 
                on_conflict="symbol,timestamp"
            ).execute()

            if not mp_res.data:
                print(f"   [!] Lô {i//batch_size + 1}: Không nhận được dữ liệu phản hồi từ market_prices.")
                continue

            # 2. Tạo Map từ (symbol, timestamp) -> ID vừa được cấp trong market_prices
            id_map = { (item["symbol"], str(item["timestamp"])[:10]): item["id"] for item in mp_res.data }

            # 3. Chuẩn bị batch dữ liệu cho bảng technical_indicators
            tech_batch = []
            for _, row in batch_df.iterrows():
                key = (str(row["symbol"]), str(row["timestamp"])[:10])
                if key in id_map:
                    tech_batch.append({
                        "market_price_id": id_map[key],
                        "rsi": float(row["rsi"]),
                        "macd": float(row["macd"]),
                        "macd_signal": float(row["macd_signal"]),
                        "macd_hist": float(row["macd_hist"])
                    })

            if tech_batch:
                supabase.table("technical_indicators").upsert(
                    tech_batch, 
                    on_conflict="market_price_id"
                ).execute()

            total_inserted += len(tech_batch)
            print(f"   [✓] Đã lưu lô {i//batch_size + 1} ({len(tech_batch)} bản ghi)")

        except Exception as e:
            print(f"   [!] Lỗi tại lô {i//batch_size + 1}: {e}")

    print(f"   [🎉] HOÀN TẤT: Đã ghi thành công {total_inserted}/{len(df)} dòng cho {asset_name}!")


def load_5year_data():
    print("==================================================")
    print("[+] Bắt đầu tải 5 năm dữ liệu lịch sử cho Vàng (GC=F) & Dầu (CL=F) từ Yahoo Finance...")
    print("==================================================")

    # 1. Cào dữ liệu Vàng (XAUUSD)
    gold = yf.Ticker("GC=F").history(period="5y").reset_index()
    gold["symbol"] = "XAUUSD"
    gold = gold.rename(columns={
        "Date": "timestamp", "Open": "open", "High": "high", 
        "Low": "low", "Close": "close", "Volume": "volume"
    })
    gold = calculate_technical_indicators(gold)
    print(f"   [✓] Đã tính chỉ báo cho {len(gold)} phiên giao dịch Vàng.")

    # 2. Cào dữ liệu Dầu mỏ WTI (WTIUSD / CL=F)
    oil = yf.Ticker("CL=F").history(period="5y").reset_index()
    oil["symbol"] = "WTIUSD"
    oil = oil.rename(columns={
        "Date": "timestamp", "Open": "open", "High": "high", 
        "Low": "low", "Close": "close", "Volume": "volume"
    })
    oil = calculate_technical_indicators(oil)
    print(f"   [✓] Đã tính chỉ báo cho {len(oil)} phiên giao dịch Dầu mỏ.")

    # 3. Đẩy dữ liệu vào Supabase Database
    push_to_supabase(gold, "Vàng (XAUUSD)")
    push_to_supabase(oil, "Dầu mỏ (WTIUSD)")
    
    print("\n==================================================")
    print("[✓] BƠM HOÀN TẤT DỮ LIỆU LỊCH SỬ 5 NĂM CỦA CẢ VÀNG & DẦU VÀO DATABASE!")
    print("==================================================")


if __name__ == "__main__":
    load_5year_data()