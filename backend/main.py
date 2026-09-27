import os
import joblib
import pandas as pd
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from supabase import create_client, Client
from dotenv import load_dotenv

# Nạp biến môi trường từ .env
load_dotenv()

# 1. KHỞI TẠO FASTAPI APP
app = FastAPI(
    title="AI Gold & Oil Forecast API",
    description="API dự báo xu hướng giá Vàng và Dầu mỏ (Thế giới & Việt Nam) dựa trên Kỹ thuật & Sentiment AI",
    version="1.1.0"
)

# Cho phép Frontend (React / Streamlit / HTML) truy cập API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 2. CẤU HÌNH SUPABASE
SUPABASE_URL = os.getenv("SUPABASE_URL", "https://nyscfgkqwgpgifceiikp.supabase.co")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_KEY", "sb_publishable_LVQZXX11x8tsfkg2rt0t-A_4r5_otpW")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# 3. LOAD MÔ HÌNH MACHINE LEARNING (THẾ GIỚI)
MODEL_PATH = "models/forecast_lightgbm.pkl"
FEATURES_PATH = "models/feature_columns.pkl"

model = None
feature_cols = []

if os.path.exists(MODEL_PATH) and os.path.exists(FEATURES_PATH):
    model = joblib.load(MODEL_PATH)
    feature_cols = joblib.load(FEATURES_PATH)
    print("[✓] Đã load mô hình LightGBM Quốc tế thành công!")
else:
    print("[!] Cảnh báo: Chưa tìm thấy tệp mô hình Quốc tế trong `models/`.")

# 4. LOAD MÔ HÌNH MACHINE LEARNING (VIỆT NAM) - BỔ SUNG MỚI
VN_MODEL_PATH = "models/forecast_vn_lightgbm.pkl"
VN_FEATURES_PATH = "models/vn_feature_columns.pkl"

vn_model = None
vn_feature_cols = []

if os.path.exists(VN_MODEL_PATH) and os.path.exists(VN_FEATURES_PATH):
    vn_model = joblib.load(VN_MODEL_PATH)
    vn_feature_cols = joblib.load(VN_FEATURES_PATH)
    print("[✓] Đã load mô hình LightGBM Việt Nam (Vàng SJC) thành công!")
else:
    print("[!] Cảnh báo: Chưa tìm thấy tệp mô hình Việt Nam trong `models/`.")


# ==============================================================================
# ROUTE DÙNG CHUNG
# ==============================================================================

@app.get("/")
def root():
    return {
        "status": "online",
        "message": "AI Gold & Oil Forecast API (Quốc tế & Việt Nam) đang hoạt động bình thường!"
    }


# ==============================================================================
# ENDPOINTS THỊ TRƯỜNG QUỐC TẾ (GIỮ NGUYÊN CODE CŨ)
# ==============================================================================

@app.get("/api/predict")
def predict_next_trend():
    """API Dự báo xu hướng giá tiếp theo (TĂNG / GIẢM) cho Thị trường Quốc tế."""
    if not model or not feature_cols:
        raise HTTPException(status_code=500, detail="Mô hình ML Quốc tế chưa được tải.")

    try:
        # Lấy bản ghi kỹ thuật mới nhất
        mp_res = supabase.table("market_prices").select("*").execute()
        tech_res = supabase.table("technical_indicators").select("*").execute()
        news_res = supabase.table("news").select("*").eq("status", "completed").execute()

        df_mp = pd.DataFrame(mp_res.data)
        df_tech = pd.DataFrame(tech_res.data)
        df_news = pd.DataFrame(news_res.data)

        if df_mp.empty or df_tech.empty:
            raise HTTPException(status_code=400, detail="Chưa có đủ dữ liệu trong Database.")

        # JOIN 2 bảng
        df_combined = pd.merge(df_tech, df_mp, left_on="market_price_id", right_on="id")

        # Sentiment gần nhất
        avg_gold_impact = 0.0
        avg_oil_threat = 0.0
        news_count = 0

        if not df_news.empty:
            avg_gold_impact = df_news["gold_impact_score"].mean()
            avg_oil_threat = df_news["oil_supply_threat_score"].mean()
            news_count = len(df_news)

        df_combined["avg_gold_impact"] = avg_gold_impact
        df_combined["avg_oil_threat"] = avg_oil_threat
        df_combined["news_count"] = news_count

        # Lấy dòng mới nhất
        latest_row = df_combined.iloc[-1:]

        # Chuẩn bị input đúng các cột đã dùng khi train
        X_input = pd.DataFrame()
        for col in feature_cols:
            X_input[col] = latest_row[col] if col in latest_row.columns else [0.0]

        # Dự báo
        prediction = model.predict(X_input)[0]
        probability = model.predict_proba(X_input)[0]

        trend = "TĂNG" if prediction == 1 else "GIẢM"
        confidence = float(probability[1] if prediction == 1 else probability[0])

        return {
            "latest_price": float(latest_row["close"].values[0]) if "close" in latest_row.columns else None,
            "forecast_trend": trend,
            "confidence_score": round(confidence * 100, 2),
            "sentiment_summary": {
                "gold_impact": round(avg_gold_impact, 2),
                "oil_threat": round(avg_oil_threat, 2),
                "analyzed_news_count": news_count
            }
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi dự báo: {str(e)}")


@app.get("/api/news")
def get_latest_news(limit: int = 10):
    """API lấy danh sách tin tức Quốc tế mới nhất kèm điểm Sentiment AI."""
    try:
        res = supabase.table("news").select("*").order("created_at", desc=True).limit(limit).execute()
        return {"data": res.data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi truy vấn tin tức: {str(e)}")


@app.get("/api/market-history")
def get_market_history(limit: int = 30):
    """API lấy lịch sử giá và chỉ báo kỹ thuật Quốc tế phục vụ vẽ biểu đồ."""
    try:
        mp_res = supabase.table("market_prices").select("*").execute()
        tech_res = supabase.table("technical_indicators").select("*").execute()

        df_mp = pd.DataFrame(mp_res.data)
        df_tech = pd.DataFrame(tech_res.data)

        if df_mp.empty or df_tech.empty:
            return {"data": []}

        df_combined = pd.merge(df_tech, df_mp, left_on="market_price_id", right_on="id")
        df_combined = df_combined.tail(limit)

        return {"data": df_combined.to_dict(orient="records")}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi lấy lịch sử giá: {str(e)}")


# ==============================================================================
# BỔ SUNG MỚI: ENDPOINTS CHO THỊ TRƯỜNG VIỆT NAM (VÀNG SJC & XĂNG DẦU)
# ==============================================================================

@app.get("/api/predict/vn-gold")
def predict_vn_gold():
    """API Dự báo xu hướng giá Vàng SJC Việt Nam phiên tới (TĂNG / GIẢM)."""
    if not vn_model or not vn_feature_cols:
        raise HTTPException(status_code=500, detail="Mô hình ML Việt Nam chưa được tải (models/forecast_vn_lightgbm.pkl).")

    try:
        # 1. Lấy 5 bản ghi giá SJC gần nhất
        res_price = supabase.table("vn_commodity_prices") \
            .select("*") \
            .eq("category", "GOLD_SJC") \
            .order("recorded_at", desc=True) \
            .limit(5) \
            .execute()

        if not res_price.data or len(res_price.data) < 4:
            raise HTTPException(status_code=400, detail="Chưa đủ dữ liệu giá SJC trong bảng `vn_commodity_prices`.")

        df_price = pd.DataFrame(res_price.data).sort_values("recorded_at").reset_index(drop=True)

        # 2. Lấy Sentiment tin tức VN trong 24h qua
        res_news = supabase.table("vn_market_news") \
            .select("sentiment_score") \
            .order("published_at", desc=True) \
            .limit(10) \
            .execute()

        avg_sentiment = 0.0
        news_count = 0
        if res_news.data:
            avg_sentiment = float(pd.DataFrame(res_news.data)["sentiment_score"].mean())
            news_count = len(res_news.data)

        # 3. Tính toán Features
        latest_sell = float(df_price["sell_price"].iloc[-1])
        latest_buy = float(df_price["buy_price"].iloc[-1])
        prev_sell_1d = float(df_price["sell_price"].iloc[-2])
        prev_sell_3d = float(df_price["sell_price"].iloc[-4]) if len(df_price) >= 4 else prev_sell_1d

        sjc_return_1d = (latest_sell - prev_sell_1d) / prev_sell_1d if prev_sell_1d != 0 else 0.0
        sjc_return_3d = (latest_sell - prev_sell_3d) / prev_sell_3d if prev_sell_3d != 0 else 0.0
        sjc_spread = latest_sell - latest_buy

        feature_dict = {
            "sjc_return_1d": sjc_return_1d,
            "sjc_return_3d": sjc_return_3d,
            "sjc_spread": sjc_spread,
            "avg_vn_sentiment": avg_sentiment,
            "vn_news_count": news_count
        }

        # Đưa vào DataFrame theo đúng thứ tự các cột khi huấn luyện
        X_input = pd.DataFrame([{col: feature_dict.get(col, 0.0) for col in vn_feature_cols}])

        # 4. Dự báo từ Model VN
        prediction = vn_model.predict(X_input)[0]
        probabilities = vn_model.predict_proba(X_input)[0]

        signal = "TĂNG" if prediction == 1 else "GIẢM / ĐI NGANG"
        confidence = float(probabilities[1] if prediction == 1 else probabilities[0])

        return {
            "target_asset": "VÀNG SJC VIỆT NAM",
            "latest_price": latest_sell,
            "forecast_trend": signal,
            "confidence_score": round(confidence * 100, 2),
            "sentiment_summary": {
                "avg_sentiment": round(avg_sentiment, 2),
                "analyzed_news_count": news_count
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi dự báo Vàng VN: {str(e)}")


@app.get("/api/vn/prices")
def get_latest_vn_prices(limit: int = 20):
    """API lấy danh sách giá Vàng & Xăng dầu Việt Nam mới nhất từ Supabase."""
    try:
        res = supabase.table("vn_commodity_prices") \
            .select("*") \
            .order("recorded_at", desc=True) \
            .limit(limit) \
            .execute()
        return {"data": res.data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi lấy giá VN: {str(e)}")


@app.get("/api/vn/news")
def get_latest_vn_news(limit: int = 10):
    """API lấy tin tức Việt Nam mới nhất kèm điểm Sentiment AI."""
    try:
        res = supabase.table("vn_market_news") \
            .select("*") \
            .order("published_at", desc=True) \
            .limit(limit) \
            .execute()
        return {"data": res.data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi lấy tin tức VN: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)