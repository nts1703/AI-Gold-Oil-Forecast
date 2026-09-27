import os
import joblib
import pandas as pd
from typing import Dict, Any, Optional
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from supabase import create_client, Client

# 1. KHỞI TẠO FASTAPI APP
app = FastAPI(
    title="AI Gold & Oil Forecast API",
    description="API cung cấp dự báo xu hướng Vàng (XAU/USD) & Dầu mỏ (WTI/USD) bằng Machine Learning (LightGBM)",
    version="1.0.0"
)

# Cho phép ứng dụng di động / web khác kết nối (CORS)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 2. CẤU HÌNH SUPABASE
SUPABASE_URL = os.getenv("SUPABASE_URL", "https://nyscfgkqwgpgifceiikp.supabase.co")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "sb_publishable_LVQZXX11x8tsfkg2rt0t-A_4r5_otpW")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# 3. LOAD MODEL & FEATURE COLUMNS
MODEL_PATH = "models/forecast_lightgbm.pkl"
FEATURE_PATH = "models/feature_columns.pkl"

def load_ai_model():
    if os.path.exists(MODEL_PATH) and os.path.exists(FEATURE_PATH):
        model = joblib.load(MODEL_PATH)
        features = joblib.load(FEATURE_PATH)
        return model, features
    return None, None

model, feature_cols = load_ai_model()

# 4. ENDPOINTS

@app.get("/", tags=["Health Check"])
def root():
    """Kiểm tra trạng thái hoạt động của API."""
    return {
        "status": "online",
        "service": "AI Gold & Oil Forecast Backend",
        "version": "1.0.0"
    }

@app.get("/api/v1/forecast", tags=["Dự Báo AI"])
def get_forecast(symbol: str = Query("XAUUSD", description="Mã tài sản: XAUUSD (Vàng) hoặc WTIUSD (Dầu)")):
    """
    Trả về dự báo TĂNG/GIẢM cho phiên tiếp theo kèm tỷ lệ phần trăm độ tin cậy.
    """
    symbol = symbol.upper()
    if symbol not in ["XAUUSD", "WTIUSD"]:
        raise HTTPException(status_code=400, detail="Mã symbol không hợp lệ. Vui lòng chọn 'XAUUSD' hoặc 'WTIUSD'")

    # Tải lại model nếu chưa nạp
    global model, feature_cols
    if not model or not feature_cols:
        model, feature_cols = load_ai_model()
        if not model:
            raise HTTPException(status_code=500, detail="Mô hình AI chưa được khởi tạo trên Server.")

    # Truy vấn dữ liệu mới nhất từ Supabase
    res = supabase.table("market_prices").select("*").eq("symbol", symbol).order("timestamp", desc=True).limit(1).execute()
    if not res.data:
        raise HTTPException(status_code=404, detail=f"Không tìm thấy dữ liệu thị trường cho symbol {symbol}")

    latest_data = res.data[0]
    current_price = float(latest_data.get("close", 0.0))
    timestamp = str(latest_data.get("timestamp", ""))

    # Lấy chỉ báo kỹ thuật tương ứng
    tech_res = supabase.table("technical_indicators").select("*").eq("market_price_id", latest_data["id"]).execute()
    tech_data = tech_res.data[0] if tech_res.data else {}

    # Lấy tin tức mới nhất
    news_res = supabase.table("news").select("*").order("published_at", desc=True).limit(5).execute()
    news_list = news_res.data if news_res.data else []

    # Tính trung bình Sentiment
    avg_gold_impact = sum(n.get("gold_impact_score", 0) for n in news_list) / max(len(news_list), 1)
    avg_oil_threat = sum(n.get("oil_supply_threat_score", 0) for n in news_list) / max(len(news_list), 1)

    # Đóng gói vector đặc trưng
    input_dict = {
        **latest_data,
        **tech_data,
        "avg_gold_impact": avg_gold_impact,
        "avg_oil_threat": avg_oil_threat,
        "news_count": len(news_list)
    }

    df_input = pd.DataFrame([input_dict])
    for col in feature_cols:
        if col not in df_input.columns:
            df_input[col] = 0.0

    X_predict = df_input[feature_cols]

    # Thực hiện dự báo
    prob_up = float(model.predict_proba(X_predict)[0][1])
    pred_direction = 1 if prob_up > 0.5 else 0
    prediction_label = "TĂNG" if pred_direction == 1 else "GIẢM"
    confidence = prob_up * 100 if pred_direction == 1 else (1 - prob_up) * 100

    return {
        "symbol": symbol,
        "asset_name": "Vàng (XAU/USD)" if symbol == "XAUUSD" else "Dầu Mỏ (WTI/USD)",
        "current_price": current_price,
        "forecast": {
            "prediction": prediction_label,
            "direction": pred_direction,
            "confidence_percentage": round(confidence, 2),
            "probability_up": round(prob_up, 4),
            "probability_down": round(1 - prob_up, 4)
        },
        "last_updated": timestamp
    }

@app.get("/api/v1/market-history", tags=["Dữ Liệu Thị Trường"])
def get_market_history(symbol: str = "XAUUSD", limit: int = 30):
    """Lấy danh sách lịch sử giá và chỉ báo kỹ thuật."""
    res = supabase.table("market_prices").select("*, technical_indicators(*)").eq("symbol", symbol.upper()).order("timestamp", desc=True).limit(limit).execute()
    return {"symbol": symbol, "count": len(res.data), "data": res.data}

@app.get("/api/v1/news", tags=["Tin Tức"])
def get_latest_news(limit: int = 10):
    """Lấy danh sách tin tức vĩ mô kèm điểm số Sentiment."""
    res = supabase.table("news").select("*").order("published_at", desc=True).limit(limit).execute()
    return {"total": len(res.data), "data": res.data}