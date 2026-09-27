import os
import joblib
import pandas as pd
import numpy as np
import warnings
from supabase import create_client, Client
from sklearn.metrics import accuracy_score
import lightgbm as lgb
from dotenv import load_dotenv

# Nạp biến môi trường từ file .env
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("[!] Thiếu SUPABASE_URL hoặc SUPABASE_KEY trong file .env!")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

warnings.filterwarnings("ignore")

def fetch_vn_data():
    print("[+] Đang lấy dữ liệu giá Việt Nam từ Supabase...")
    
    # 1. Kéo dữ liệu giá Việt Nam
    res_price = supabase.table("vn_commodity_prices").select("*").execute()
    df_price = pd.DataFrame(res_price.data)

    if df_price.empty:
        print("[!] Không có dữ liệu giá Việt Nam trong bảng `vn_commodity_prices`!")
        return pd.DataFrame(), pd.DataFrame()

    df_price['date'] = pd.to_datetime(df_price['recorded_at']).dt.strftime('%Y-%m-%d')

    # 2. Kéo dữ liệu tin tức Việt Nam
    try:
        res_news = supabase.table("vn_market_news").select("*").execute()
        df_news = pd.DataFrame(res_news.data)
    except Exception as e:
        print(f"   [!] Không đọc được tin tức: {e}")
        df_news = pd.DataFrame()

    return df_price, df_news

def prepare_vn_features(df_price: pd.DataFrame, df_news: pd.DataFrame):
    print("[+] Đang tạo Feature Matrix dự báo Vàng SJC...")

    df_sjc = df_price[df_price['category'] == 'GOLD_SJC'].sort_values('date').reset_index(drop=True)

    if df_sjc.empty:
        raise ValueError("[!] Bảng `vn_commodity_prices` không chứa bản ghi category GOLD_SJC!")

    # Tính biến động giá SJC
    df_sjc['sjc_return_1d'] = df_sjc['sell_price'].pct_change(1)
    df_sjc['sjc_return_3d'] = df_sjc['sell_price'].pct_change(3)
    df_sjc['sjc_spread'] = df_sjc['sell_price'] - df_sjc['buy_price']

    # Tích hợp Sentiment tin tức VN
    if not df_news.empty and 'published_at' in df_news.columns:
        df_news['date'] = pd.to_datetime(df_news['published_at']).dt.strftime('%Y-%m-%d')
        daily_sentiment = df_news.groupby('date').agg(
            avg_vn_sentiment=('sentiment_score', 'mean'),
            vn_news_count=('id', 'count')
        ).reset_index()
        df_sjc = pd.merge(df_sjc, daily_sentiment, on='date', how='left')
    else:
        df_sjc['avg_vn_sentiment'] = 0.0
        df_sjc['vn_news_count'] = 0

    df_sjc['avg_vn_sentiment'] = df_sjc['avg_vn_sentiment'].fillna(0.0)
    df_sjc['vn_news_count'] = df_sjc['vn_news_count'].fillna(0)

    # Target: 1 nếu ngày mai giá SJC TĂNG, 0 nếu GIẢM/ĐI NGANG
    df_sjc['next_price'] = df_sjc['sell_price'].shift(-1)
    df_sjc['target'] = (df_sjc['next_price'] > df_sjc['sell_price']).astype(int)

    feature_cols = ['sjc_return_1d', 'sjc_return_3d', 'sjc_spread', 'avg_vn_sentiment', 'vn_news_count']
    df_features = df_sjc.dropna(subset=feature_cols + ['target']).reset_index(drop=True)

    return df_features, feature_cols

def main():
    df_price, df_news = fetch_vn_data()
    if df_price.empty:
        return

    df_features, feature_cols = prepare_vn_features(df_price, df_news)

    X = df_features[feature_cols]
    y = df_features['target']

    split_idx = int(len(X) * 0.8)
    X_train, X_test = X.iloc[:split_idx], X.iloc[split_idx:]
    y_train, y_test = y.iloc[:split_idx], y.iloc[split_idx:]

    print(f"[+] Chia Dataset VN: Train ({len(X_train)} mẫu) | Test ({len(X_test)} mẫu)")

    # Huấn luyện LightGBM cho Việt Nam
    model = lgb.LGBMClassifier(
        n_estimators=150,
        learning_rate=0.02,
        max_depth=3,
        class_weight="balanced",
        random_state=42,
        verbosity=-1
    )
    model.fit(X_train, y_train)

    y_pred = model.predict(X_test)
    print(f"   [✓] Đã train xong Model VN! Accuracy: {accuracy_score(y_test, y_pred) * 100:.2f}%")

    os.makedirs("models", exist_ok=True)
    joblib.dump(model, "models/forecast_vn_lightgbm.pkl")
    joblib.dump(feature_cols, "models/vn_feature_columns.pkl")
    print("[✔] ĐÃ LƯU MODEL DỰ BÁO VIỆT NAM VÀO `models/forecast_vn_lightgbm.pkl`!")

if __name__ == "__main__":
    main()