import os
import joblib
import pandas as pd
import numpy as np
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

MODEL_PATH = "models/forecast_vn_lightgbm.pkl"
FEATURES_PATH = "models/vn_feature_columns.pkl"

def predict_vn_gold_trend():
    """Lấy dữ liệu mới nhất từ Supabase và dự báo xu hướng giá Vàng SJC phiên tới."""
    if not os.path.exists(MODEL_PATH) or not os.path.exists(FEATURES_PATH):
        return {"error": "Chưa huấn luyện Model. Vui lòng chạy train_vn_pipeline.py trước!"}

    # 1. Load model & danh sách features
    model = joblib.load(MODEL_PATH)
    feature_cols = joblib.load(FEATURES_PATH)

    # 2. Lấy 5 bản ghi giá SJC gần nhất từ Supabase
    res_price = supabase.table("vn_commodity_prices") \
        .select("*") \
        .eq("category", "GOLD_SJC") \
        .order("recorded_at", desc=True) \
        .limit(5) \
        .execute()

    if not res_price.data or len(res_price.data) < 4:
        return {"error": "Chưa đủ dữ liệu giá SJC mới nhất để đưa ra dự báo."}

    df_price = pd.DataFrame(res_price.data).sort_values("recorded_at").reset_index(drop=True)

    # 3. Lấy tin tức sentiment trong 24h qua
    res_news = supabase.table("vn_market_news") \
        .select("sentiment_score") \
        .order("published_at", desc=True) \
        .limit(10) \
        .execute()

    if res_news.data:
        avg_sentiment = np.mean([item["sentiment_score"] for item in res_news.data])
        news_count = len(res_news.data)
    else:
        avg_sentiment = 0.0
        news_count = 0

    # 4. Tính toán Feature cho phiên hiện tại
    latest_sell = df_price["sell_price"].iloc[-1]
    prev_sell_1d = df_price["sell_price"].iloc[-2]
    prev_sell_3d = df_price["sell_price"].iloc[-4] if len(df_price) >= 4 else prev_sell_1d

    sjc_return_1d = (latest_sell - prev_sell_1d) / prev_sell_1d
    sjc_return_3d = (latest_sell - prev_sell_3d) / prev_sell_3d
    sjc_spread = latest_sell - df_price["buy_price"].iloc[-1]

    input_data = pd.DataFrame([{
        "sjc_return_1d": sjc_return_1d,
        "sjc_return_3d": sjc_return_3d,
        "sjc_spread": sjc_spread,
        "avg_vn_sentiment": avg_sentiment,
        "vn_news_count": news_count
    }])[feature_cols]

    # 5. Dự báo từ Model
    prediction = model.predict(input_data)[0]
    probabilities = model.predict_proba(input_data)[0]

    up_prob = float(probabilities[1]) * 100
    down_prob = float(probabilities[0]) * 100

    signal = "TĂNG" if prediction == 1 else "GIẢM / ĐI NGANG"

    return {
        "target_asset": "VÀNG SJC VIỆT NAM",
        "current_price": float(latest_sell),
        "predicted_signal": signal,
        "confidence_up": round(up_prob, 2),
        "confidence_down": round(down_prob, 2),
        "market_sentiment_score": round(float(avg_sentiment), 2),
        "news_analyzed_count": news_count
    }

if __name__ == "__main__":
    result = predict_vn_gold_trend()
    print("=== KẾT QUẢ DỰ BÁO XU HƯỚNG VÀNG SJC ===")
    print(result)