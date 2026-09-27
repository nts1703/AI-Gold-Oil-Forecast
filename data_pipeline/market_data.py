import sys
import os
from pathlib import Path
from datetime import datetime
import yfinance as yf
import pandas as pd
import numpy as np

# Thêm thư mục gốc vào PYTHONPATH
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))

from backend.database.connection import SessionLocal
from backend.database.models import MarketPrice, TechnicalIndicator

def fetch_market_data(ticker_symbol: str, period: str = "6mo", interval: str = "1d") -> pd.DataFrame:
    """Tải dữ liệu giá OHLCV từ yfinance."""
    print(f"[+] Đang tải dữ liệu thị trường cho {ticker_symbol}...")
    ticker = yf.Ticker(ticker_symbol)
    df = ticker.history(period=period, interval=interval)
    
    if df.empty:
        raise ValueError(f"Không thể tải dữ liệu cho mã {ticker_symbol}")
    
    df = df[['Open', 'High', 'Low', 'Close', 'Volume']].copy()
    df.columns = [col.lower() for col in df.columns]
    df.index.name = 'timestamp'
    return df

def add_technical_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """Tính toán toàn bộ các chỉ báo kỹ thuật: EMA, RSI, MACD, Bollinger Bands, ATR."""
    df = df.copy()
    
    # 1. Đường trung bình động lũy thừa (EMA)
    df['ema20'] = df['close'].ewm(span=20, adjust=False).mean()
    df['ema50'] = df['close'].ewm(span=50, adjust=False).mean()
    df['ema200'] = df['close'].ewm(span=200, adjust=False).mean()
    
    # 2. Chỉ số sức mạnh tương đối (RSI 14)
    delta = df['close'].diff()
    gain = delta.where(delta > 0, 0.0)
    loss = -delta.where(delta < 0, 0.0)
    avg_gain = gain.ewm(alpha=1/14, min_periods=14, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1/14, min_periods=14, adjust=False).mean()
    rs = avg_gain / avg_loss
    df['rsi'] = 100 - (100 / (1 + rs))
    
    # 3. Phân kỳ hội tụ đường trung bình động (MACD 12, 26, 9)
    ema12 = df['close'].ewm(span=12, adjust=False).mean()
    ema26 = df['close'].ewm(span=26, adjust=False).mean()
    df['macd'] = ema12 - ema26
    df['macd_signal'] = df['macd'].ewm(span=9, adjust=False).mean()
    df['macd_hist'] = df['macd'] - df['macd_signal']
    
    # 4. Dải Bollinger Bands (20, 2)
    sma20 = df['close'].rolling(window=20).mean()
    std20 = df['close'].rolling(window=20).std()
    df['bb_upper'] = sma20 + (std20 * 2)
    df['bb_middle'] = sma20
    df['bb_lower'] = sma20 - (std20 * 2)
    
    # 5. Khoảng dao động thực tế trung bình (ATR 14)
    high_low = df['high'] - df['low']
    high_close = (df['high'] - df['close'].shift()).abs()
    low_close = (df['low'] - df['close'].shift()).abs()
    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    df['atr'] = tr.ewm(alpha=1/14, min_periods=14, adjust=False).mean()
    
    return df.dropna().copy()

def save_to_database(df: pd.DataFrame, symbol: str, timeframe: str = "1d"):
    """Lưu giá thị trường và chỉ báo kỹ thuật vào Supabase Database, lọc trùng lặp timestamp."""
    db = SessionLocal()
    saved_count = 0
    
    try:
        for timestamp, row in df.iterrows():
            ts_dt = pd.to_datetime(timestamp).to_pydatetime()
            
            # Kiểm tra bản ghi đã tồn tại chưa
            existing = db.query(MarketPrice).filter(
                MarketPrice.symbol == symbol,
                MarketPrice.timestamp == ts_dt,
                MarketPrice.timeframe == timeframe
            ).first()
            
            if not existing:
                # Bản ghi thông tin giá OHLCV
                market_record = MarketPrice(
                    symbol=symbol,
                    timeframe=timeframe,
                    timestamp=ts_dt,
                    open=float(row['open']),
                    high=float(row['high']),
                    low=float(row['low']),
                    close=float(row['close']),
                    volume=float(row['volume'])
                )
                
                # Bản ghi các chỉ báo kỹ thuật
                indicator_record = TechnicalIndicator(
                    rsi=float(row['rsi']),
                    macd=float(row['macd']),
                    macd_signal=float(row['macd_signal']),
                    macd_hist=float(row['macd_hist']),
                    ema20=float(row['ema20']),
                    ema50=float(row['ema50']),
                    ema200=float(row['ema200']),
                    atr=float(row['atr']),
                    bb_upper=float(row['bb_upper']),
                    bb_middle=float(row['bb_middle']),
                    bb_lower=float(row['bb_lower'])
                )
                
                market_record.indicators = indicator_record
                db.add(market_record)
                saved_count += 1
                
        db.commit()
        print(f"[✔] Đã lưu thành công {saved_count} dòng dữ liệu mới cho {symbol} vào Database!")
    except Exception as e:
        db.rollback()
        print(f"[✘] Lỗi khi lưu Database cho {symbol}: {e}")
    finally:
        db.close()

def run_market_pipeline():
    """Chạy quy trình cào dữ liệu cho Vàng (GC=F) và Dầu WTI (CL=F)."""
    assets = {
        "GC=F": "Gold (Vàng)",
        "CL=F": "WTI Oil (Dầu WTI)"
    }
    
    for symbol, name in assets.items():
        print(f"\n--- Bắt đầu xử lý {name} ({symbol}) ---")
        df_raw = fetch_market_data(symbol, period="6mo", interval="1d")
        df_featured = add_technical_indicators(df_raw)
        save_to_database(df_featured, symbol=symbol, timeframe="1d")

if __name__ == "__main__":
    run_market_pipeline()