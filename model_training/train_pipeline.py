import os
import joblib
import pandas as pd
import numpy as np
import warnings
from supabase import create_client, Client

from sklearn.metrics import accuracy_score, classification_report, roc_auc_score
import lightgbm as lgb

warnings.filterwarnings("ignore")

# 1. CẤU HÌNH KẾT NỐI SUPABASE
SUPABASE_URL = os.getenv("SUPABASE_URL", "https://nyscfgkqwgpgifceiikp.supabase.co")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "sb_publishable_LVQZXX11x8tsfkg2rt0t-A_4r5_otpW")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)


def fetch_data_from_supabase():
    """Tải TOÀN BỘ dữ liệu lịch sử từ Supabase bằng cơ chế phân trang (Bỏ giới hạn 1000 dòng)."""
    print("[+] Đang tải toàn bộ dữ liệu lịch sử từ Supabase...")

    # 1. Kéo toàn bộ bảng market_prices
    all_mp = []
    start = 0
    step = 1000
    while True:
        res = supabase.table("market_prices").select("*").range(start, start + step - 1).execute()
        if not res.data:
            break
        all_mp.extend(res.data)
        if len(res.data) < step:
            break
        start += step

    df_mp = pd.DataFrame(all_mp)

    # 2. Kéo toàn bộ bảng technical_indicators
    all_tech = []
    start = 0
    while True:
        res = supabase.table("technical_indicators").select("*").range(start, start + step - 1).execute()
        if not res.data:
            break
        all_tech.extend(res.data)
        if len(res.data) < step:
            break
        start += step

    df_tech = pd.DataFrame(all_tech)

    # 3. Lấy tin tức news
    try:
        news_res = supabase.table("news").select("*").execute()
        df_news = pd.DataFrame(news_res.data) if news_res.data else pd.DataFrame()
    except Exception:
        df_news = pd.DataFrame()

    if df_mp.empty or df_tech.empty:
        print("[!] Bảng dữ liệu đang trống!")
        return pd.DataFrame(), df_news

    # JOIN 2 bảng
    df_combined = pd.merge(
        df_tech, 
        df_mp, 
        left_on="market_price_id", 
        right_on="id", 
        suffixes=("_tech", "_mp")
    )

    date_col = next((col for col in ["timestamp", "timestamp_mp", "created_at_mp", "created_at"] if col in df_combined.columns), None)
    if date_col:
        df_combined["date"] = pd.to_datetime(df_combined[date_col]).dt.strftime("%Y-%m-%d")

    print(f"   [✓] Đã nạp thành công {len(df_combined)} dòng dữ liệu thô từ Supabase!")
    return df_combined, df_news


def prepare_feature_matrix(df_combined: pd.DataFrame, df_news: pd.DataFrame):
    """Tạo Feature Matrix chuỗi thời gian chuẩn hóa (Stationary Features)."""
    print("[+] Đang xây dựng Feature Matrix tối ưu cho AI...")

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
        close_col = "close_gold"
    else:
        df_features = df_combined.sort_values("date").reset_index(drop=True)
        close_col = "close" if "close" in df_features.columns else [c for c in df_features.columns if "close" in c][0]

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

    # ----------------------------------------------------
    # 4. TẠO CÁC ĐẶC TRƯNG CHUẨN HÓA (STATIONARY FEATURES)
    # ----------------------------------------------------
    df_features["gold_return_1d"] = df_features["close_gold"].pct_change(1)
    df_features["gold_return_3d"] = df_features["close_gold"].pct_change(3)
    df_features["oil_return_1d"] = df_features["close_oil"].pct_change(1)
    
    df_features["gold_range"] = (df_features["high_gold"] - df_features["low_gold"]) / df_features["close_gold"]
    df_features["oil_range"] = (df_features["high_oil"] - df_features["low_oil"]) / df_features["close_oil"]
    
    df_features["gold_body"] = (df_features["close_gold"] - df_features["open_gold"]) / df_features["open_gold"]

    df_features["rsi_gold_lag1"] = df_features["rsi_gold"].shift(1)
    df_features["macd_hist_gold_lag1"] = df_features["macd_hist_gold"].shift(1)
    df_features["gold_return_lag1"] = df_features["gold_return_1d"].shift(1)

    # 5. Target Label: 1 nếu Phiên MAI > HÔM NAY
    df_features["next_close_gold"] = df_features["close_gold"].shift(-1)
    df_features["target"] = (df_features["next_close_gold"] > df_features["close_gold"]).astype(int)

    # Danh sách các cột đặc trưng quan trọng
    feature_cols = [
        "rsi_gold_lag1", "macd_gold", "macd_signal_gold", "macd_hist_gold_lag1", 
        "rsi_oil", "macd_oil", "macd_signal_oil", "macd_hist_oil",
        "gold_return_1d", "gold_return_3d", "oil_return_1d",
        "gold_range", "oil_range", "gold_body", "gold_return_lag1",
        "avg_gold_impact", "avg_oil_threat", "news_count"
    ]
    feature_cols = [c for c in feature_cols if c in df_features.columns]

    # Chỉ lọc bỏ NaN trên các cột đặc trưng chính & Target (không dropna toàn bộ bảng)
    cols_to_check = feature_cols + ["target"]
    df_features = df_features.dropna(subset=cols_to_check).reset_index(drop=True)

    print(f"   [✓] Tạo thành công Feature Matrix tối ưu với {len(df_features)} mẫu!")
    return df_features, feature_cols


def train_lightgbm_model(X_train, y_train, X_test, y_test):
    """Huấn luyện mô hình LightGBM Classifier tối ưu hóa cân bằng lớp."""
    print(f"\n==========================================")
    print(f"=== HUẤN LUYỆN MÔ HÌNH DỰ BÁO VÀNG ===")
    print(f"==========================================")

    if len(X_train) == 0 or len(X_test) == 0:
        print("[!] Lỗi: Tập dữ liệu huấn luyện hoặc kiểm thử đang trống (0 mẫu)!")
        return None

    model = lgb.LGBMClassifier(
        n_estimators=200,
        learning_rate=0.015,
        max_depth=3,
        num_leaves=7,
        min_child_samples=20,
        subsample=0.8,
        colsample_bytree=0.8,
        class_weight="balanced",
        random_state=42,
        verbosity=-1
    )

    model.fit(X_train, y_train)

    y_pred = model.predict(X_test)
    y_prob = model.predict_proba(X_test)[:, 1]

    acc = accuracy_score(y_test, y_pred)
    try:
        auc = roc_auc_score(y_test, y_prob)
    except Exception:
        auc = 0.5

    print(f"[✓] Đã huấn luyện xong model!")
    print(f"   - Độ chính xác (Accuracy): {acc * 100:.2f}%")
    print(f"   - Chỉ số ROC-AUC: {auc:.4f}")
    print("\nBáo cáo chi tiết trên tập Validation/Test:")
    print(classification_report(y_test, y_pred, target_names=["GIẢM (0)", "TĂNG (1)"], zero_division=0))

    return model


def main():
    df_combined, df_news = fetch_data_from_supabase()

    if df_combined.empty or len(df_combined) < 10:
        print("[!] Dữ liệu chưa đủ để huấn luyện.")
        return

    df_features, feature_cols = prepare_feature_matrix(df_combined, df_news)

    if len(df_features) == 0:
        print("[!] Lỗi: Feature Matrix bị trống sau khi xử lý dữ liệu!")
        return

    X = df_features[feature_cols]
    y = df_features["target"]

    split_idx = int(len(X) * 0.8)

    X_train, X_test = X.iloc[:split_idx], X.iloc[split_idx:]
    y_train, y_test = y.iloc[:split_idx], y.iloc[split_idx:]

    print(f"[+] Chia tập dữ liệu: Train ({len(X_train)} mẫu) | Test ({len(X_test)} mẫu)")

    model = train_lightgbm_model(X_train, y_train, X_test, y_test)
    if model is None:
        return

    os.makedirs("models", exist_ok=True)
    joblib.dump(model, "models/forecast_lightgbm.pkl")
    joblib.dump(feature_cols, "models/feature_columns.pkl")

    print("\n[✓] ĐÃ LƯU THÀNH CÔNG MÔ HÌNH VÀO THƯ MỤC `models/`!")


if __name__ == "__main__":
    main()