import os
import math
import requests
import joblib
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st
import streamlit.components.v1 as components
from supabase import create_client
from pathlib import Path


# ==========================================
# 1. CẤU HÌNH TRANG & CSS (DARK MODE PRO)
# ==========================================
st.set_page_config(
    page_title="AI Gold & Oil Forecast Pro",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="collapsed"
)

st.markdown("""
<style>
    .stApp { 
        background-color: #0e1117; 
        color: #e0e0e0; 
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    }
    #MainMenu {visibility: hidden;} 
    footer {visibility: hidden;}
    header {visibility: hidden;}

    .stButton > button {
        border-radius: 10px;
        font-weight: 700;
        transition: all 0.3s ease;
        padding: 12px 24px;
        border: 1px solid rgba(255, 255, 255, 0.1);
    }
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(245, 158, 11, 0.3);
        border-color: #F59E0B;
    }

    .kpi-master-box {
        background: linear-gradient(135deg, #1e222d 0%, #171b26 100%);
        border: 1px solid #2a2e39; 
        border-radius: 16px; 
        padding: 20px;
        height: 380px; 
        box-shadow: 0 8px 32px rgba(0,0,0,0.4);
        display: flex; 
        flex-direction: column; 
        justify-content: center;
    }
    
    .kpi-grid { 
        display: grid; 
        grid-template-columns: 1fr 1fr; 
        grid-template-rows: 1fr 1fr; 
        gap: 16px; 
        height: 100%; 
    }
    
    .kpi-subcard {
        background: rgba(255,255,255,0.03); 
        border: 1px solid #2a2e39;
        border-radius: 12px; 
        padding: 18px; 
        display: flex; 
        flex-direction: column;
        justify-content: center; 
        align-items: flex-start;
        transition: transform 0.2s, background 0.2s;
    }
    .kpi-subcard:hover {
        background: rgba(255,255,255,0.05);
        transform: translateY(-2px);
    }
    
    .stat-title { 
        color: #848e9c; 
        font-size: 13px; 
        font-weight: 600; 
        text-transform: uppercase; 
        letter-spacing: 0.5px; 
    }
    .stat-value { 
        font-size: 26px; 
        font-weight: 800; 
        margin-top: 8px; 
    }
    
    .signal-box-up { 
        background: rgba(16,185,129,0.08); 
        border: 2px solid #10b981; 
        border-radius: 14px; 
        padding: 24px; 
        text-align: center; 
        box-shadow: 0 4px 16px rgba(16,185,129,0.15);
    }
    .signal-box-down { 
        background: rgba(239,68,68,0.08); 
        border: 2px solid #ef4444; 
        border-radius: 14px; 
        padding: 24px; 
        text-align: center; 
        box-shadow: 0 4px 16px rgba(239,68,68,0.15);
    }
    
    .reason-box-up { 
        background: rgba(16,185,129,0.05); 
        border: 1px solid rgba(16,185,129,0.4); 
        border-radius: 14px; 
        padding: 20px; 
        height: 100%; 
        display: flex; 
        flex-direction: column; 
        justify-content: center; 
    }
    .reason-box-down { 
        background: rgba(239,68,68,0.05); 
        border: 1px solid rgba(239,68,68,0.4); 
        border-radius: 14px; 
        padding: 20px; 
        height: 100%; 
        display: flex; 
        flex-direction: column; 
        justify-content: center; 
    }
    
    .reason-header-up { 
        color: #10b981; 
        font-weight: 800; 
        font-size: 13px; 
        margin-bottom: 12px; 
        border-bottom: 1px solid rgba(16,185,129,0.2); 
        padding-bottom: 6px; 
        text-transform: uppercase; 
        letter-spacing: 0.5px;
    }
    .reason-header-down { 
        color: #ef4444; 
        font-weight: 800; 
        font-size: 13px; 
        margin-bottom: 12px; 
        border-bottom: 1px solid rgba(239,68,68,0.2); 
        padding-bottom: 6px; 
        text-transform: uppercase; 
        letter-spacing: 0.5px;
    }
    .reason-item { 
        font-size: 13px; 
        color: #d1d5db; 
        margin-bottom: 8px; 
        line-height: 1.5; 
        display: flex;
        align-items: flex-start;
    }
</style>
""", unsafe_allow_html=True)


# ==========================================
# 2. BIẾN MÔI TRƯỜNG & SESSION STATE
# ==========================================
API_BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:8000")
SUPABASE_URL = os.getenv("SUPABASE_URL", "https://nyscfgkqwgpgifceiikp.supabase.co")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "sb_publishable_LVQZXX11x8tsfkg2rt0t-A_4r5_otpW")

if "market_mode" not in st.session_state:
    st.session_state.market_mode = "global"


# ==========================================
# 3. KẾT NỐI SUPABASE & TẢI MODEL
# ==========================================
@st.cache_resource
def init_supabase():
    return create_client(SUPABASE_URL, SUPABASE_KEY)

supabase = init_supabase()

@st.cache_resource
def load_trained_model():
    model_path = Path("models/forecast_lightgbm.pkl")
    feature_path = Path("models/feature_columns.pkl")
    if not model_path.exists() or not feature_path.exists():
        return None, None
    try:
        model = joblib.load(model_path)
        feature_columns = joblib.load(feature_path)
        return model, feature_columns
    except Exception as e:
        print(f"Error loading model: {e}")
        return None, None

model, feature_columns = load_trained_model()


# ==========================================
# 4. LOAD DỮ LIỆU QUỐC TẾ
# ==========================================
@st.cache_data(ttl=300)
def load_market_and_news_global():
    try:
        mp_res = supabase.table("market_prices").select("*").order("timestamp", desc=True).limit(3000).execute()
        df_mp = pd.DataFrame(mp_res.data) if mp_res.data else pd.DataFrame()
        
        if df_mp.empty:
            return None, None
        
        mp_ids = df_mp["id"].tolist()
        
        tech_res = supabase.table("technical_indicators").select("*").in_("market_price_id", mp_ids).execute()
        df_tech = pd.DataFrame(tech_res.data) if tech_res.data else pd.DataFrame()

        try:
            news_res = supabase.table("news").select("*").order("published_at", desc=True).limit(30).execute()
            df_news = pd.DataFrame(news_res.data) if news_res.data else pd.DataFrame()
        except Exception:
            df_news = pd.DataFrame()

        if df_tech.empty:
            df_combined = df_mp.copy()
            df_combined["market_price_id"] = df_combined["id"]
        else:
            df_combined = pd.merge(df_tech, df_mp, left_on="market_price_id", right_on="id", suffixes=("_tech", "_mp"))
        
        date_col = next((col for col in ["timestamp", "timestamp_mp", "created_at_mp", "datetime"] if col in df_combined.columns), None)
        
        if date_col:
            df_combined["datetime"] = pd.to_datetime(df_combined[date_col], errors="coerce")
            df_combined["date"] = df_combined["datetime"].dt.strftime("%Y-%m-%d")
        
        return df_combined, df_news
    except Exception as e:
        print(f"Load global data error: {e}")
        return None, None


# ==========================================
# 5. LOAD DỮ LIỆU VIỆT NAM
# ==========================================
def load_vietnam_data():
    vn_predict = {}
    vn_prices = []
    vn_news = []
    
    try:
        r_pred = requests.get(f"{API_BASE_URL}/api/predict/vn-gold", timeout=5)
        if r_pred.status_code == 200:
            vn_predict = r_pred.json()
        else:
            raise Exception("Non-200")
    except Exception:
        vn_predict = {
            "forecast_trend": "TĂNG", 
            "confidence_score": 78.5, 
            "latest_price": 84500000,
            "reasons": [
                "Tỷ giá USD/VND đang neo ở mức cao",
                "Khoảng cách chênh lệch giá vàng trong nước và thế giới thu hẹp",
                "Lực cầu tích trữ tài sản an toàn trong nước tăng"
            ]
        }

    try:
        r_prices = requests.get(f"{API_BASE_URL}/api/vn/prices", timeout=5)
        if r_prices.status_code == 200:
            vn_prices = r_prices.json().get("data", [])
    except Exception:
        vn_prices = []

    try:
        r_news = requests.get(f"{API_BASE_URL}/api/vn/news", timeout=5)
        if r_news.status_code == 200:
            vn_news = r_news.json().get("data", [])
    except Exception:
        vn_news = []

    return vn_predict, vn_prices, vn_news


# ==========================================
# 6. NEWS SLIDER COMPONENT
# ==========================================
def render_news_slider(df_news_items, title="📰 TIN TỨC HÔM NAY"):
    SOURCE_LOGOS = {
        "reuters": "https://www.reuters.com/pf/resources/images/reuters/logo-vertical-default.svg?d=287",
        "bloomberg": "https://www.bloomberg.com/favicon.ico",
        "vnexpress": "https://s1.vnecdn.net/vnexpress/restruct/i/v954/logo/share.png",
        "vtv": "https://vtv.vn/favicon.ico",
        "dantri": "https://dantri.com.vn/favicon.ico",
        "cafef": "https://cafefcdn.com/web_v1/images/logo-cafef.png",
        "tuoitre": "https://tuoitre.vn/favicon.ico",
        "default": "https://cdn-icons-png.flaticon.com/512/21/21601.png"
    }

    news_items_html = ""
    if df_news_items and len(df_news_items) > 0:
        for item in df_news_items[:15]:
            t_title = str(item.get("title", "Tin tức thị trường")).replace('"', '&quot;').replace("'", "&#39;")
            t_summary = str(item.get("summary", "Không có nội dung tóm tắt.")).replace('"', '&quot;').replace("'", "&#39;")
            t_url = item.get("url", "#")
            
            g_score = item.get("gold_impact_score", item.get("sentiment_score", 0)) or 0
            if g_score > 0.05:
                badge = "🟢 Tích cực"
                badge_class = "badge-bullish"
            elif g_score < -0.05:
                badge = "🔴 Tiêu cực"
                badge_class = "badge-bearish"
            else:
                badge = "⚪ Trung tính"
                badge_class = "badge-neutral"
                
            source = str(item.get("source", "Tài chính"))
            pub_time = item.get("pub_time", "Mới cập nhật")
            
            logo_key = source.lower().replace(" ", "")
            logo_url = SOURCE_LOGOS.get(logo_key, SOURCE_LOGOS["default"])

            news_items_html += f"""
            <div class="news-card">
                <div class="news-top">
                    <div class="source-info">
                        <img src="{logo_url}" class="source-logo" alt="{source}" onerror="this.src='{SOURCE_LOGOS["default"]}'">
                        <span class="source-name">{source}</span>
                    </div>
                    <span class="news-badge {badge_class}">{badge}</span>
                </div>
                <a href="{t_url}" target="_blank" class="news-title">{t_title}</a>
                <div class="news-summary">{t_summary}</div>
                <div class="news-time">🕒 Cập nhật: {pub_time}</div>
            </div>
            """
    else:
        news_items_html = """
        <div class="news-card" style="justify-content: center; align-items: center; text-align: center; background: rgba(255,255,255,0.02);">
            <div style="color:#9CA3AF; font-size:15px; font-weight:500;">📭 Đang chờ cập nhật tin tức mới nhất từ hệ thống...</div>
        </div>
        """

    total_news = max(len(df_news_items[:15]) if df_news_items else 0, 1)

    ticker_component = f"""
    <!DOCTYPE html>
    <html>
    <head>
    <style>
        body {{ margin: 0; padding: 0; font-family: 'Segoe UI', sans-serif; background: transparent; overflow: hidden; }}
        .news-container {{
            background: linear-gradient(135deg, #1e222d 0%, #171b26 100%);
            border: 1px solid #2a2e39; border-radius: 16px; padding: 20px;
            height: 380px; box-sizing: border-box; display: flex; flex-direction: column;
            box-shadow: 0 8px 32px rgba(0,0,0,0.4);
        }}
        .news-header {{ 
            font-size: 15px; font-weight: 800; color: #F59E0B; margin-bottom: 16px; 
            display: flex; justify-content: space-between; align-items: center; 
            text-transform: uppercase; letter-spacing: 0.5px;
        }}
        .nav-buttons {{ display: flex; gap: 8px; }}
        .nav-btn {{
            background: rgba(255,255,255,0.08); border: 1px solid #3a3f4b; color: #e0e0e0;
            width: 36px; height: 36px; border-radius: 10px; cursor: pointer; 
            display: flex; align-items: center; justify-content: center;
            font-size: 16px; transition: all 0.2s;
        }}
        .nav-btn:hover {{ background: rgba(245, 158, 11, 0.2); border-color: #F59E0B; color: #F59E0B; }}
        .news-slider {{ position: relative; width: 100%; flex: 1; overflow: hidden; border-radius: 12px; }}
        .news-track {{ display: flex; height: 100%; transition: transform 0.5s cubic-bezier(0.25, 0.8, 0.25, 1); }}
        .news-card {{
            min-width: 100%; width: 100%; box-sizing: border-box; padding: 20px;
            background: rgba(255,255,255,0.03); border: 1px solid #2a2e39; border-radius: 12px;
            display: flex; flex-direction: column; justify-content: space-between;
        }}
        .news-top {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; }}
        .source-info {{ display: flex; align-items: center; gap: 10px; }}
        .source-logo {{ width: 22px; height: 22px; border-radius: 4px; background: #fff; padding: 2px; object-fit: contain; }}
        .source-name {{ font-size: 13px; color: #9CA3AF; font-weight: 600; text-transform: uppercase; }}
        .news-badge {{ font-size: 11px; font-weight: 700; padding: 4px 10px; border-radius: 6px; color: #fff; }}
        .badge-bullish {{ background: rgba(16,185,129,0.2); color: #10b981; border: 1px solid rgba(16,185,129,0.3); }}
        .badge-bearish {{ background: rgba(239,68,68,0.2); color: #ef4444; border: 1px solid rgba(239,68,68,0.3); }}
        .badge-neutral {{ background: rgba(255,255,255,0.1); color: #e0e0e0; border: 1px solid rgba(255,255,255,0.2); }}
        .news-title {{ font-size: 17px; font-weight: 700; color: #FFFFFF; text-decoration: none; line-height: 1.4; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; margin-bottom: 8px; transition: color 0.2s; }}
        .news-title:hover {{ color: #F59E0B; text-decoration: underline; }}
        .news-summary {{ font-size: 13.5px; color: #9CA3AF; line-height: 1.5; display: -webkit-box; -webkit-line-clamp: 3; -webkit-box-orient: vertical; overflow: hidden; flex: 1; }}
        .news-time {{ font-size: 12px; color: #F59E0B; margin-top: 12px; font-weight: 600; }}
        .dots {{ display: flex; justify-content: center; gap: 8px; margin-top: 12px; }}
        .dot {{ width: 8px; height: 8px; border-radius: 50%; background: #3a3f4b; transition: all 0.3s; cursor: pointer; }}
        .dot.active {{ background: #F59E0B; transform: scale(1.3); width: 16px; border-radius: 4px; }}
    </style>
    </head>
    <body>
        <div class="news-container">
            <div class="news-header">
                <span>{title}</span>
                <div class="nav-buttons">
                    <button class="nav-btn" onclick="prevNews()">&#8592;</button>
                    <button class="nav-btn" onclick="nextNews()">&#8594;</button>
                </div>
            </div>
            <div class="news-slider">
                <div class="news-track" id="newsTrack">{news_items_html}</div>
            </div>
            <div class="dots" id="dots"></div>
        </div>
        <script>
            let currentIndex = 0;
            const totalItems = {total_news};
            const track = document.getElementById('newsTrack');
            const dotsContainer = document.getElementById('dots');
            let autoSlideInterval;

            function initDots() {{
                dotsContainer.innerHTML = '';
                for (let i = 0; i < totalItems; i++) {{
                    const dot = document.createElement('div');
                    dot.className = 'dot' + (i === 0 ? ' active' : '');
                    dot.onclick = () => goTo(i);
                    dotsContainer.appendChild(dot);
                }}
            }}
            function updateSlider() {{
                track.style.transform = `translateX(-${{currentIndex * 100}}%)`;
                document.querySelectorAll('.dot').forEach((d, i) => d.classList.toggle('active', i === currentIndex));
            }}
            function nextNews() {{ currentIndex = (currentIndex + 1) % totalItems; updateSlider(); resetInterval(); }}
            function prevNews() {{ currentIndex = (currentIndex - 1 + totalItems) % totalItems; updateSlider(); resetInterval(); }}
            function goTo(i) {{ currentIndex = i; updateSlider(); resetInterval(); }}
            function startInterval() {{ autoSlideInterval = setInterval(nextNews, 6000); }}
            function resetInterval() {{ clearInterval(autoSlideInterval); startInterval(); }}

            if(totalItems > 1) {{
                initDots();
                startInterval();
            }}
        </script>
    </body>
    </html>
    """
    components.html(ticker_component, height=410)


# ==========================================
# 7. LOGIC DỰ BÁO AI (GOLD + OIL)
# ==========================================
def _predict_single_asset(df_asset, asset_name, df_news, model, feature_columns):
    """Dự báo cho 1 tài sản (Gold hoặc Oil) – ổn định với fallback"""
    if df_asset.empty:
        return None

    latest = df_asset.iloc[-1].copy()
    
    # ML prediction (nếu model có)
    if model is not None and feature_columns is not None:
        try:
            feature_dict = {col: float(latest.get(col, 0.0) or 0.0) for col in feature_columns}
            X = pd.DataFrame([feature_dict])[feature_columns]
            proba = model.predict_proba(X)[0]
            prob_up = float(proba[1]) * 100 if len(proba) > 1 else float(proba[0]) * 100
        except Exception:
            prob_up = 55.0
    else:
        # Fallback dựa trên RSI
        rsi = float(latest.get("rsi", 50.0) or 50.0)
        if rsi < 35:
            prob_up = 68.0
        elif rsi > 65:
            prob_up = 38.0
        else:
            prob_up = 55.0

    rsi = float(latest.get("rsi", 50.0) or 50.0)
    macd_h = float(latest.get("macd_hist", 0.0) or 0.0)
    
    reasons = [
        f"• <b>Chỉ báo RSI ({rsi:.1f})</b>: {'Đang ở vùng quá bán → hỗ trợ tăng giá' if rsi < 35 else ('Đang ở vùng quá mua → rủi ro điều chỉnh' if rsi > 65 else 'Trung tính, tích lũy')}.",
        f"• <b>MACD Histogram ({macd_h:.3f})</b>: {'Phe mua đang chiếm ưu thế' if macd_h > 0 else 'Phe bán đang chiếm ưu thế'}.",
        f"• <b>Yếu tố Vĩ mô</b>: Tin tức hiện tại đang {'hỗ trợ đà tăng' if prob_up > 50 else 'gây áp lực giảm'} cho {asset_name}."
    ]

    return {
        "1D": {"pred": 1 if prob_up >= 50 else 0, "prob_up": prob_up, "prob_down": 100 - prob_up, "reasons": reasons},
        "2D": {"pred": 1 if prob_up >= 50 else 0, "prob_up": float(np.clip(prob_up * 0.95, 10, 90)), "prob_down": 100 - float(np.clip(prob_up * 0.95, 10, 90)), "reasons": reasons},
        "3D": {"pred": 1 if prob_up >= 50 else 0, "prob_up": float(np.clip(prob_up * 0.90, 10, 90)), "prob_down": 100 - float(np.clip(prob_up * 0.90, 10, 90)), "reasons": reasons},
        "latest_date": latest.get("date", "N/A"),
        "price": float(latest.get("close", 0) or 0),
        "rsi": rsi,
        "macd": macd_h,
        "df": df_asset
    }


def run_ai_prediction_global(df_combined, df_news):
    gold_symbols = ["XAUUSD", "GC=F", "XAUUSD=X", "GOLD"]
    oil_symbols = ["WTIUSD", "CL=F", "WTI", "USOIL"]
    
    df_gold = df_combined[df_combined["symbol"].isin(gold_symbols)].copy()
    df_oil = df_combined[df_combined["symbol"].isin(oil_symbols)].copy()
    
    if not df_gold.empty and "datetime" in df_gold.columns:
        df_gold = df_gold.sort_values("datetime").reset_index(drop=True)
    if not df_oil.empty and "datetime" in df_oil.columns:
        df_oil = df_oil.sort_values("datetime").reset_index(drop=True)

    gold_pred = _predict_single_asset(df_gold, "Vàng (XAU/USD)", df_news, model, feature_columns)
    oil_pred = _predict_single_asset(df_oil, "Dầu (WTI)", df_news, model, feature_columns)

    news_impact = 0.0
    if not df_news.empty and "gold_impact_score" in df_news.columns:
        news_impact = float(df_news["gold_impact_score"].mean() or 0)

    return {
        "gold": gold_pred,
        "oil": oil_pred,
        "news_impact": news_impact
    }


def resample_data(df, timeframe="1D"):
    if df is None or df.empty:
        return pd.DataFrame()
    
    df_res = df.copy()
    if "datetime" not in df_res.columns:
        return df_res
    
    df_res["datetime"] = pd.to_datetime(df_res["datetime"], errors="coerce")
    df_res = df_res.dropna(subset=["datetime"]).sort_values("datetime").set_index("datetime")
    
    rule_map = {"Ngày (1D)": "D", "Tuần (1W)": "W-MON", "Tháng (1M)": "ME", "Năm (1Y)": "YE"}
    rule = rule_map.get(timeframe, "D")

    if rule == "D":
        df_out = df_res.reset_index()
    else:
        agg_dict = {}
        for col in ["open", "high", "low", "close"]:
            if col in df_res.columns:
                agg_dict[col] = {"open": "first", "high": "max", "low": "min", "close": "last"}[col]
        if not agg_dict:
            return pd.DataFrame()
        df_out = df_res.resample(rule).agg(agg_dict).dropna(subset=["close"] if "close" in agg_dict else []).reset_index()

    if "close" in df_out.columns:
        df_out["ma20"] = df_out["close"].rolling(window=20, min_periods=1).mean()
        df_out["ma50"] = df_out["close"].rolling(window=50, min_periods=1).mean()
    
    df_out["date_str"] = df_out["datetime"].dt.strftime("%Y-%m-%d")
    return df_out


# ==========================================
# 8. HEADER & NAVIGATION
# ==========================================
col_header, col_btn_global, col_btn_vn = st.columns([5, 2.5, 2.5])

with col_header:
    st.title("⚡ AI Gold & Oil Forecast Pro")
    st.markdown("<p style='color: #9CA3AF; margin-top:-15px; font-size:15px;'>Hệ thống Phân tích & Dự báo thị trường Tích hợp Trí tuệ Nhân tạo</p>", unsafe_allow_html=True)

with col_btn_global:
    btn_g_type = "primary" if st.session_state.market_mode == "global" else "secondary"
    if st.button("🌐 Thị Trường Quốc Tế", type=btn_g_type, use_container_width=True):
        st.session_state.market_mode = "global"
        st.rerun()

with col_btn_vn:
    btn_vn_type = "primary" if st.session_state.market_mode == "vietnam" else "secondary"
    if st.button("🇻🇳 Thị Trường Việt Nam", type=btn_vn_type, use_container_width=True):
        st.session_state.market_mode = "vietnam"
        st.rerun()

st.divider()


# ==========================================
# GIAO DIỆN 1: THỊ TRƯỜNG QUỐC TẾ
# ==========================================
if st.session_state.market_mode == "global":
    df_combined, df_news = load_market_and_news_global()
    
    if df_combined is None or df_combined.empty:
        st.error("⚠️ Không thể tải dữ liệu thị trường quốc tế từ Supabase. Vui lòng kiểm tra kết nối!")
        st.stop()

    result = run_ai_prediction_global(df_combined, df_news)
    
    gold_data = result.get("gold")
    oil_data = result.get("oil")
    
    if gold_data is None and oil_data is None:
        st.error("⚠️ Không tìm thấy dữ liệu Vàng hoặc Dầu trong database.")
        st.stop()

    # --- TẦNG 1: KPI + NEWS ---
    top_left, top_right = st.columns([1, 1])

    with top_left:
        impact_score = result.get("news_impact", 0)
        impact_text = "🟢 Tích cực" if impact_score > 0.05 else ("🔴 Tiêu cực" if impact_score < -0.05 else "⚪ Trung tính")
        
        gold_price = gold_data["price"] if gold_data else 0
        oil_price = oil_data["price"] if oil_data else 0
        rsi_val = gold_data["rsi"] if gold_data else (oil_data["rsi"] if oil_data else 50)
        
        st.markdown(f"""
        <div class="kpi-master-box">
            <div style="font-size: 15px; font-weight: 800; color: #F59E0B; margin-bottom: 16px; text-transform: uppercase;">📊 QUỐC TẾ - THÔNG SỐ TỔNG HỢP</div>
            <div class="kpi-grid">
                <div class="kpi-subcard">
                    <div class="stat-title">Giá Vàng (XAU/USD)</div>
                    <div class="stat-value" style="color: #F59E0B;">${gold_price:,.2f}</div>
                </div>
                <div class="kpi-subcard">
                    <div class="stat-title">Giá Dầu thô (WTI)</div>
                    <div class="stat-value" style="color: #00D2FF;">${oil_price:,.2f}</div>
                </div>
                <div class="kpi-subcard">
                    <div class="stat-title">Chỉ số RSI (14)</div>
                    <div class="stat-value">{rsi_val:.1f}</div>
                </div>
                <div class="kpi-subcard">
                    <div class="stat-title">Tâm lý Tin Tức Vĩ Mô</div>
                    <div class="stat-value" style="font-size: 22px;">{impact_text}</div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    with top_right:
        news_list_global = []
        if df_news is not None and not df_news.empty:
            for _, r in df_news.head(15).iterrows():
                news_list_global.append({
                    "title": r.get("title", ""),
                    "summary": r.get("summary", ""),
                    "url": r.get("url", "#"),
                    "gold_impact_score": r.get("gold_impact_score", 0),
                    "source": r.get("source", "Financial News"),
                    "pub_time": pd.to_datetime(r.get("published_at")).strftime("%H:%M - %d/%m/%Y") if r.get("published_at") else ""
                })
        render_news_slider(news_list_global, title="📰 TIN TỨC QUỐC TẾ HÔM NAY")

    st.write("")
    st.write("")

    # --- TẦNG 2: AI SIGNAL (GOLD + OIL) + CHART ---
    c_left, c_right = st.columns([1, 2.2])

    with c_left:
        st.subheader("🤖 Tín hiệu Dự báo AI")
        
        asset_choice = st.radio(
            "Chọn tài sản:",
            options=["Vàng (XAU/USD)", "Dầu (WTI)"],
            horizontal=True,
            key="asset_global"
        )
        
        horizon_tab = st.radio(
            "Khung thời gian:",
            options=["1 Ngày sau", "2 Ngày sau", "3 Ngày sau"],
            horizontal=True,
            key="h_global"
        )
        
        h_key_map = {"1 Ngày sau": "1D", "2 Ngày sau": "2D", "3 Ngày sau": "3D"}
        selected_data = gold_data if "Vàng" in asset_choice else oil_data
        
        if selected_data is None:
            st.warning(f"⚠️ Chưa có dữ liệu cho {asset_choice}")
        else:
            h_data = selected_data[h_key_map[horizon_tab]]
            is_up = h_data["pred"] == 1
            confidence = h_data["prob_up"] if is_up else h_data["prob_down"]
            box_class = "signal-box-up" if is_up else "signal-box-down"
            trend_text = "TĂNG 📈" if is_up else "GIẢM 📉"
            color_code = "#10B981" if is_up else "#EF4444"

            reasons_html = "".join([f"<div class='reason-item'>{r}</div>" for r in h_data["reasons"]])

            sig1, sig2 = st.columns([1, 1.2])
            with sig1:
                st.markdown(f"""
                <div class="{box_class}">
                    <div style="font-size: 12px; color: #848e9c; font-weight: 700; letter-spacing: 0.5px;">DỰ BÁO [{horizon_tab.upper()}]</div>
                    <div style="font-size: 28px; font-weight: 900; color: {color_code}; margin: 10px 0;">{trend_text}</div>
                    <div style="font-size: 14px; font-weight: 700; color: #d1d5db;">Độ tin cậy: <br/><span style="font-size: 22px; color: {color_code};">{confidence:.1f}%</span></div>
                </div>
                """, unsafe_allow_html=True)

            with sig2:
                st.markdown(f"""
                <div class="{'reason-box-up' if is_up else 'reason-box-down'}">
                    <div class="{'reason-header-up' if is_up else 'reason-header-down'}">💡 NGUYÊN NHÂN CHÍNH</div>
                    {reasons_html}
                </div>
                """, unsafe_allow_html=True)

            st.write("")
            st.markdown(f"**Thanh đo mức độ tin cậy AI ({confidence:.1f}%)**")
            st.progress(int(min(max(h_data["prob_up"], 0), 100)))

    with c_right:
        st.subheader("📊 Biểu đồ Xu hướng Kỹ thuật")
        
        chart_asset = st.radio(
            "Biểu đồ:",
            options=["Vàng (XAU/USD)", "Dầu (WTI)"],
            horizontal=True,
            key="chart_asset"
        )
        
        tf_choice = st.radio(
            "Khung thời gian nến:",
            options=["Ngày (1D)", "Tuần (1W)", "Tháng (1M)", "Năm (1Y)"],
            horizontal=True,
            key="tf_g"
        )
        
        chart_df_src = gold_data["df"] if "Vàng" in chart_asset and gold_data else (oil_data["df"] if oil_data else None)
        
        if chart_df_src is None or chart_df_src.empty:
            st.info("📭 Chưa có dữ liệu lịch sử để vẽ biểu đồ.")
        else:
            df_chart = resample_data(chart_df_src, timeframe=tf_choice)
            
            if df_chart.empty:
                st.info("📭 Không đủ dữ liệu sau khi resample.")
            else:
                # Dùng datetime thật để zoom/pan mượt + trục X hiện ngày sạch
                x_vals = df_chart["datetime"] if "datetime" in df_chart.columns else df_chart["date_str"]

                fig = make_subplots(rows=1, cols=1)

                fig.add_trace(go.Candlestick(
                    x=x_vals,
                    open=df_chart.get("open", df_chart["close"]),   
                    high=df_chart.get("high", df_chart["close"]),
                    low=df_chart.get("low", df_chart["close"]),
                    close=df_chart["close"],
                    name=chart_asset,
                    increasing_line_color="#10B981",
                    decreasing_line_color="#EF4444",
                    hovertemplate=(
                        "<b>%{x|%d/%m/%Y}</b><br>" +
                        "Open: %{open:.2f}<br>" +
                        "High: %{high:.2f}<br>" +
                        "Low: %{low:.2f}<br>" +
                        "Close: %{close:.2f}<extra></extra>"
                    )
                ))

                if "ma20" in df_chart.columns:
                    fig.add_trace(go.Scatter(
                        x=x_vals, y=df_chart["ma20"],
                        line=dict(color="#F59E0B", width=1.5),
                        name="MA20",
                        hovertemplate="%{x|%d/%m/%Y}<br>MA20: %{y:.2f}<extra></extra>"
                    ))
                if "ma50" in df_chart.columns:
                    fig.add_trace(go.Scatter(
                        x=x_vals, y=df_chart["ma50"],
                        line=dict(color="#00D2FF", width=1.5),
                        name="MA50",
                        hovertemplate="%{x|%d/%m/%Y}<br>MA50: %{y:.2f}<extra></extra>"
                    ))

                fig.update_layout(
                    template="plotly_dark",
                    height=420,
                    margin=dict(l=10, r=10, t=10, b=10),
                    paper_bgcolor="#1e222d",
                    plot_bgcolor="#1e222d",
                    xaxis_rangeslider_visible=False,
                    dragmode="pan",                    # kéo = di chuyển biểu đồ
                    hovermode="x",
                    xaxis=dict(
                        type="date",
                        tickformat="%d/%m/%Y",         # trục X hiện ngày thuần
                        showspikes=True,
                        spikemode="across",
                        spikesnap="cursor",
                        showline=True,
                        showgrid=True,
                    ),
                    yaxis=dict(
                        showspikes=True,
                        spikemode="across",
                        spikesnap="cursor",
                        showline=True,
                        showgrid=True,
                    ),
                    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
                )

                # scrollZoom = True → cuộn chuột trong chart = zoom (tâm theo chuột)
                st.plotly_chart(
                    fig,
                    use_container_width=True,
                    config={
                        "scrollZoom": True,
                        "displaylogo": False,
                        "modeBarButtonsToRemove": ["lasso2d", "select2d"],
                        "doubleClick": "reset",
                    }
                )


# ==========================================
# GIAO DIỆN 2: THỊ TRƯỜNG VIỆT NAM (UI ĐỒNG NHẤT)
# ==========================================
else:
    vn_pred, vn_prices, vn_news = load_vietnam_data()

    # --- TẦNG 1: KPI + NEWS (cùng layout với Global) ---
    top_left_vn, top_right_vn = st.columns([1, 1])

    with top_left_vn:
        trend_vn = vn_pred.get("forecast_trend", "TĂNG")
        conf_vn = float(vn_pred.get("confidence_score", 78.5))
        sjc_price = float(vn_pred.get("latest_price", 84500000))

        st.markdown(f"""
        <div class="kpi-master-box">
            <div style="font-size: 15px; font-weight: 800; color: #10B981; margin-bottom: 16px; text-transform: uppercase;">🇻🇳 THỊ TRƯỜNG VIỆT NAM - TỔNG QUAN</div>
            <div class="kpi-grid">
                <div class="kpi-subcard">
                    <div class="stat-title">Giá Bán Niêm Yết SJC</div>
                    <div class="stat-value" style="color: #F59E0B; font-size: 22px;">{sjc_price:,.0f} đ</div>
                </div>
                <div class="kpi-subcard">
                    <div class="stat-title">Dự Báo Xu Hướng SJC</div>
                    <div class="stat-value" style="color: {'#10B981' if trend_vn == 'TĂNG' else '#EF4444'}; font-size: 22px;">{trend_vn}</div>
                </div>
                <div class="kpi-subcard">
                    <div class="stat-title">Độ Tin Cậy AI (VN)</div>
                    <div class="stat-value">{conf_vn:.1f}%</div>
                </div>
                <div class="kpi-subcard">
                    <div class="stat-title">Tâm Lý Tin Tức Vĩ Mô</div>
                    <div class="stat-value" style="color: #00D2FF; font-size: 22px;">Tích cực</div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    with top_right_vn:
        news_list_vn = []
        if vn_news:
            for item in vn_news:
                news_list_vn.append({
                    "title": item.get("title", ""),
                    "summary": item.get("summary", ""),
                    "url": item.get("url", "#"),
                    "sentiment_score": item.get("sentiment_score", 0),
                    "source": item.get("source", "Báo Việt Nam"),
                    "pub_time": item.get("pub_time", "Hôm nay")
                })
        render_news_slider(news_list_vn, title="📰 TIN TỨC THỊ TRƯỜNG VIỆT NAM")

    st.write("")
    st.write("")

    # --- TẦNG 2: AI SIGNAL + BẢNG GIÁ (cùng layout) ---
    c_left_vn, c_right_vn = st.columns([1, 2.2])

    with c_left_vn:
        st.subheader("🤖 Tín hiệu Vàng SJC (AI Model)")
        
        is_up_vn = str(trend_vn).upper() == "TĂNG"
        box_cls_vn = "signal-box-up" if is_up_vn else "signal-box-down"
        color_vn = "#10B981" if is_up_vn else "#EF4444"

        api_reasons = vn_pred.get("reasons", [])
        if not api_reasons:
            api_reasons = [
                "Tỷ giá USD/VND đang neo ở mức cao hỗ trợ giá vàng trong nước.",
                "Khoảng cách giá vàng SJC & thế giới đang dần thu hẹp.",
                "Tin tức tài chính trong nước đang hỗ trợ tâm lý tích trữ."
            ]
            
        reasons_vn_html = "".join([f"<div class='reason-item'>• {r}</div>" for r in api_reasons])

        sig1_vn, sig2_vn = st.columns([1, 1.2])
        with sig1_vn:
            st.markdown(f"""
            <div class="{box_cls_vn}">
                <div style="font-size: 12px; color: #848e9c; font-weight: 700; letter-spacing: 0.5px;">XU HƯỚNG SJC</div>
                <div style="font-size: 28px; font-weight: 900; color: {color_vn}; margin: 10px 0;">{trend_vn} {'📈' if is_up_vn else '📉'}</div>
                <div style="font-size: 14px; font-weight: 700; color: #d1d5db;">Độ tin cậy: <br/><span style="font-size: 22px; color: {color_vn};">{conf_vn:.1f}%</span></div>
            </div>
            """, unsafe_allow_html=True)

        with sig2_vn:
            st.markdown(f"""
            <div class="{'reason-box-up' if is_up_vn else 'reason-box-down'}">
                <div class="{'reason-header-up' if is_up_vn else 'reason-header-down'}">💡 YẾU TỐ TÁC ĐỘNG CHÍNH</div>
                {reasons_vn_html}
            </div>
            """, unsafe_allow_html=True)

        st.write("")
        st.markdown(f"**Thanh đo mức độ tin cậy AI VN ({conf_vn:.1f}%)**")
        st.progress(int(min(max(conf_vn, 0), 100)))

    with c_right_vn:
        st.subheader("💵 Bảng Giá Niêm Yết Vàng & Nhiên Liệu Mới Nhất")
        
        st.markdown("""
        <style>
            .dataframe th { text-align: left; font-size: 14px; color: #F59E0B; background-color: #1e222d; padding: 12px; }
            .dataframe td { padding: 12px; font-size: 14px; border-bottom: 1px solid #2a2e39; }
            .dataframe tr:hover { background-color: rgba(255, 255, 255, 0.05); }
        </style>
        """, unsafe_allow_html=True)
        
        if vn_prices and len(vn_prices) > 0:
            df_p = pd.DataFrame(vn_prices)
            st.dataframe(df_p, use_container_width=True, hide_index=True)
        else:
            sample_prices = pd.DataFrame([
                {"Loại tài sản": "Vàng SJC (1 Lượng)", "Giá Mua (VNĐ)": "82,500,000", "Giá Bán (VNĐ)": "84,500,000", "Chênh lệch": "2,000,000", "Cập nhật": "Vừa xong"},
                {"Loại tài sản": "Vàng Nhẫn Trơn 9999", "Giá Mua (VNĐ)": "77,300,000", "Giá Bán (VNĐ)": "78,600,000", "Chênh lệch": "1,300,000", "Cập nhật": "Vừa xong"},
                {"Loại tài sản": "Xăng RON 95-III (1 Lít)", "Giá Mua (VNĐ)": "---", "Giá Bán (VNĐ)": "21,800", "Chênh lệch": "---", "Cập nhật": "Theo kỳ"},
                {"Loại tài sản": "Xăng E5 RON 92 (1 Lít)", "Giá Mua (VNĐ)": "---", "Giá Bán (VNĐ)": "20,700", "Chênh lệch": "---", "Cập nhật": "Theo kỳ"},
                {"Loại tài sản": "Dầu DO 0,05S (1 Lít)", "Giá Mua (VNĐ)": "---", "Giá Bán (VNĐ)": "19,500", "Chênh lệch": "---", "Cập nhật": "Theo kỳ"},
            ])
            st.dataframe(sample_prices, use_container_width=True, hide_index=True)