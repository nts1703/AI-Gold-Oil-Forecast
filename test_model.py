import os
import joblib
import pandas as pd
import numpy as np
import warnings
from supabase import create_client, Client

warnings.filterwarnings("ignore")

SUPABASE_URL = os.getenv("SUPABASE_URL", "https://nyscfgkqwgpgifceiikp.supabase.co")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "sb_publishable_LVQZXX11x8tsfkg2rt0t-A_4r5_otpW")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def fetch_historical_data_for_backtest(target_date="2025-10-20"):
    """Tải dữ liệu quanh mốc ngày target_date từ Supabase."""
    print(f"[+] Đang tải dữ liệu để Backtest cho ngày {target_date}...")
    
    # 1. Kéo dữ liệu market_prices trước và tại ngày target_date
    mp_res = supabase.table("market_prices").select("*").lte("timestamp", f"{target_date}T23:59:59").order("timestamp", desc=True).limit(200).execute()
    df_mp = pd.DataFrame(mp_res.data) if mp_res.data else pd.DataFrame()

    if df_mp.empty:
        print(f"[!] Không tìm thấy dữ liệu market_prices trước ngày {target_date}!")
        return None, None, None

    # Lấy thêm vài phiên SAU ngày target_date để đối chiếu (dùng desc=False cho thứ tự tăng dần)
    future_mp_res = supabase.table("market_prices").select("*").gte("timestamp", target_date).order("timestamp", desc=False).limit(10).execute()
    df_future_mp = pd.DataFrame(future_mp_res.data) if future_mp_res.data else pd.DataFrame()

    # Ghép dữ liệu lại
    df_all_mp = pd.concat([df_mp, df_future_mp]).drop_duplicates(subset=["id"])

    # 2. Kéo bảng technical_indicators
    mp_ids = df_all_mp["id"].tolist()
    tech_res = supabase.table("technical_indicators").select("*").in_("market_price_id", mp_ids).execute()
    df_tech = pd.DataFrame(tech_res.data) if tech_res.data else pd.DataFrame()

    # 3. Kéo news
    try:
        news_res = supabase.table("news").select("*").lte("published_at", f"{target_date}T23:59:59").order("published_at", desc=True).limit(100).execute()
        df_news = pd.DataFrame(news_res.data) if news_res.data else pd.DataFrame()
    except Exception:
        df_news = pd.DataFrame()

    df_combined = pd.merge(df_tech, df_all_mp, left_on="market_price_id", right_on="id", suffixes=("_tech", "_mp"))
    date_col = next((col for col in ["timestamp", "timestamp_mp", "created_at_mp", "created_at"] if col in df_combined.columns), None)
    if date_col:
        df_combined["date"] = pd.to_datetime(df_combined[date_col]).dt.strftime("%Y-%m-%d")

    return df_combined, df_news, target_date

def prepare_backtest_features(df_combined: pd.DataFrame, df_news: pd.DataFrame, target_date: str, feature_cols: list):
    """Xây dựng đặc trưng cho ngày target_date và lấy kết quả thực tế ngày hôm sau."""
    
    # 1. Sentiment News
    if not df_news.empty and "published_at" in df_news.columns:
        df_news["date"] = pd.to_datetime(df_news["published_at"]).dt.strftime("%Y-%m-%d")
        daily_sentiment = df_news.groupby("date").agg(
            avg_gold_impact=("gold_impact_score", "mean"),
            avg_oil_threat=("oil_supply_threat_score", "mean"),
            news_count=("id", "count")
        ).reset_index()
    else:
        daily_sentiment = pd.DataFrame(columns=["date", "avg_gold_impact", "avg_oil_threat", "news_count"])

    # 2. Tách Vàng & Dầu
    symbols = df_combined["symbol"].unique() if "symbol" in df_combined.columns else []

    if "XAUUSD" in symbols and "WTIUSD" in symbols:
        df_gold = df_combined[df_combined["symbol"] == "XAUUSD"].copy().sort_values("date").reset_index(drop=True)
        df_oil = df_combined[df_combined["symbol"] == "WTIUSD"].copy().sort_values("date").reset_index(drop=True)

        gold_cols = {c: f"{c}_gold" for c in df_gold.columns if c != "date"}
        oil_cols = {c: f"{c}_oil" for c in df_oil.columns if c != "date"}
        
        df_gold = df_gold.rename(columns=gold_cols)
        df_oil = df_oil.rename(columns=oil_cols)

        df_features = pd.merge(df_gold, df_oil, on="date", how="inner")
    else:
        df_features = df_combined.sort_values("date").reset_index(drop=True)

    # 3. Merge Sentiment
    if not daily_sentiment.empty:
        df_features = pd.merge(df_features, daily_sentiment, on="date", how="left")
    else:
        df_features["avg_gold_impact"] = 0.0
        df_features["avg_oil_threat"] = 0.0
        df_features["news_count"] = 0

    df_features["avg_gold_impact"] = df_features["avg_gold_impact"].fillna(0.0)
    df_features["avg_oil_threat"] = df_features["avg_oil_threat"].fillna(0.0)
    df_features["news_count"] = df_features["news_count"].fillna(0)

    # 4. Tính toán các thuộc tính chuỗi thời gian
    df_features["gold_return_1d"] = df_features["close_gold"].pct_change(1)
    df_features["gold_return_3d"] = df_features["close_gold"].pct_change(3)
    df_features["oil_return_1d"] = df_features["close_oil"].pct_change(1)
    
    df_features["gold_range"] = (df_features["high_gold"] - df_features["low_gold"]) / df_features["close_gold"]
    df_features["oil_range"] = (df_features["high_oil"] - df_features["low_oil"]) / df_features["close_oil"]
    df_features["gold_body"] = (df_features["close_gold"] - df_features["open_gold"]) / df_features["open_gold"]

    df_features["rsi_gold_lag1"] = df_features["rsi_gold"].shift(1)
    df_features["macd_hist_gold_lag1"] = df_features["macd_hist_gold"].shift(1)
    df_features["gold_return_lag1"] = df_features["gold_return_1d"].shift(1)

    for col in feature_cols:
        if col not in df_features.columns:
            df_features[col] = 0.0

    df_features = df_features.sort_values("date").reset_index(drop=True)

    # Tìm dòng dữ liệu đúng ngày target_date hoặc ngày giao dịch gần nhất trước đó
    target_idx = df_features[df_features["date"] <= target_date].index
    if len(target_idx) == 0:
        print(f"[!] Không tìm thấy dòng dữ liệu phù hợp vào mốc ngày {target_date}")
        return None, None, None, None, None

    row_pos = target_idx[-1]
    target_row = df_features.iloc[[row_pos]]
    X_target = target_row[feature_cols]

    actual_date = target_row["date"].values[0]
    curr_price = target_row["close_gold"].values[0]

    # Lấy thực tế phiên kế tiếp (1-day) và 3 phiên sau (3-day)
    next_price_1d = df_features.iloc[row_pos + 1]["close_gold"] if row_pos + 1 < len(df_features) else None
    next_date_1d = df_features.iloc[row_pos + 1]["date"] if row_pos + 1 < len(df_features) else None

    next_price_3d = df_features.iloc[row_pos + 3]["close_gold"] if row_pos + 3 < len(df_features) else None
    next_date_3d = df_features.iloc[row_pos + 3]["date"] if row_pos + 3 < len(df_features) else None

    return X_target, actual_date, curr_price, (next_date_1d, next_price_1d), (next_date_3d, next_price_3d)


def backtest_prediction(target_date="2025-10-20"):
    model_path = "models/forecast_lightgbm.pkl"
    features_path = "models/feature_columns.pkl"

    if not os.path.exists(model_path) or not os.path.exists(features_path):
        print("[!] Không tìm thấy file model trong thư mục `models/`!")
        return

    model = joblib.load(model_path)
    feature_cols = joblib.load(features_path)

    df_combined, df_news, date_str = fetch_historical_data_for_backtest(target_date)
    if df_combined is None or len(df_combined) == 0:
        return

    res = prepare_backtest_features(df_combined, df_news, date_str, feature_cols)
    if res[0] is None:
        return

    X_target, actual_date, curr_price, (next_date_1d, next_price_1d), (next_date_3d, next_price_3d) = res

    # 1. AI Dự báo
    prediction = model.predict(X_target)[0]
    probabilities = model.predict_proba(X_target)[0]

    prob_down, prob_up = probabilities[0] * 100, probabilities[1] * 100
    pred_trend = "TĂNG 📈" if prediction == 1 else "GIẢM 📉"
    confidence = prob_up if prediction == 1 else prob_down

    print("\n==========================================")
    print(f"=== KẾT QUẢ BACKTEST DỰ BÁO TẠI NGÀY {actual_date} ===")
    print("==========================================")
    print(f"📌 Giá Vàng tại ngày test ({actual_date}): ${curr_price:.2f}")
    print(f"🔮 AI Dự báo cho phiên tiếp theo         : {pred_trend} (Độ tin cậy: {confidence:.2f}%)")
    print(f"📊 Xác suất chi tiết                     : GIẢM: {prob_down:.2f}% | TĂNG: {prob_up:.2f}%")
    print("------------------------------------------")

    # 2. Đối chiếu thực tế 1 ngày sau (21/10/2025)
    if next_price_1d is not None:
        actual_1d_trend_num = 1 if next_price_1d > curr_price else 0
        actual_1d_str = "TĂNG 📈" if actual_1d_trend_num == 1 else "GIẢM 📉"
        is_correct_1d = "✅ ĐÚNG" if prediction == actual_1d_trend_num else "❌ SAI"

        diff_1d = next_price_1d - curr_price
        print(f"🎯 ĐỐI CHIẾU THỰC TẾ NGÀY TIẾP THEO ({next_date_1d}):")
        print(f"   - Giá thực tế đóng cửa : ${next_price_1d:.2f} (Biến động: {diff_1d:+.2f}$)")
        print(f"   - Xu hướng thực tế    : {actual_1d_str}")
        print(f"   - Kết quả dự báo AI   : {is_correct_1d}")
    else:
        print("   [!] Chưa có dữ liệu phiên tiếp theo trong DB.")

    # 3. Đối chiếu thực tế 3 ngày sau
    if next_price_3d is not None:
        actual_3d_trend_num = 1 if next_price_3d > curr_price else 0
        actual_3d_str = "TĂNG 📈" if actual_3d_trend_num == 1 else "GIẢM 📉"
        diff_3d = next_price_3d - curr_price
        print("\n------------------------------------------")
        print(f"🎯 THỰC TẾ SAU 3 NGÀY ({next_date_3d}):")
        print(f"   - Giá thực tế đóng cửa : ${next_price_3d:.2f} (Biến động: {diff_3d:+.2f}$)")
        print(f"   - Xu hướng thực tế 3D  : {actual_3d_str}")

    print("==========================================\n")


if __name__ == "__main__":
    # Thay đổi ngày bạn muốn test ở đây (Mặc định: 2025-10-20)
    TARGET_TEST_DATE = "2025-10-20"
    backtest_prediction(TARGET_TEST_DATE)