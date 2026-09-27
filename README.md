# ⚡ AI Gold & Oil Forecast Pro

**AI Gold & Oil Forecast Pro** là một hệ thống bảng điều khiển (Dashboard) phân tích và dự báo thị trường tài chính toàn diện. Hệ thống ứng dụng Trí tuệ Nhân tạo (Machine Learning) để phân tích xu hướng giá Vàng (Quốc tế & Việt Nam), giá Dầu và tổng hợp đánh giá tâm lý tin tức (News Sentiment) theo thời gian thực.

---

## 🌟 Bảng Mục Lục
- [Tổng quan Tính năng](#-tổng-quan-tính-năng)
- [Kiến trúc & Công nghệ](#-kiến-trúc--công-nghệ)
- [Cấu trúc Thư mục](#-cấu-trúc-thư-mục)
- [Cấu trúc Cơ sở dữ liệu (Supabase)](#-cấu-trúc-cơ-sở-dữ-liệu-supabase)
- [Hướng dẫn Cài đặt & Chạy dự án](#-hướng-dẫn-cài-đặt--chạy-dự-án)
- [Quy trình Hoạt động (Data Flow)](#-quy-trình-hoạt-động-data-flow)

---

## 🚀 Tổng quan Tính năng

Hệ thống cung cấp góc nhìn đa chiều song song giữa 2 thị trường:

### 🌐 Thị trường Quốc tế (Global Market)
- **Theo dõi Giá trị:** Cập nhật giá Vàng (XAU/USD) và Dầu thô (WTI).
- **Dự báo AI Đa khung thời gian:** Dự báo xu hướng giá (Tăng/Giảm) trong 1 Ngày, 2 Ngày, 3 Ngày tới kèm mức độ tin cậy (%) và lý do dựa trên chỉ báo kỹ thuật (RSI, MACD...).
- **Biểu đồ Kỹ thuật:** Biểu đồ Nến Nhật đa khung thời gian (1D, 1W, 1M, 1Y) tích hợp các đường trung bình động MA20, MA50.

### 🇻🇳 Thị trường Việt Nam (Vietnam Market)
- **Theo dõi Giá trị:** Cập nhật bảng giá Vàng SJC, Vàng Nhẫn 9999 và giá các loại nhiên liệu (Xăng RON 95, E5, Dầu DO).
- **Dự báo Vàng SJC:** AI đưa ra nhận định xu hướng giá SJC trong nước dựa trên tỷ giá, độ chênh lệch thế giới và tin tức vĩ mô.

### 📰 Phân tích Tâm lý Tin tức (News Sentiment)
- Tự động thu thập (crawling) tin bài từ các báo chí tài chính trong nước và quốc tế.
- Chấm điểm tác động (Impact Score) lên Vàng và Dầu để phân loại: 🟢 Tích cực, 🔴 Tiêu cực, ⚪ Trung tính.
- Hiển thị qua thanh Slider tin tức tự động cuộn.

---

## 🛠 Kiến trúc & Công nghệ

Dự án được xây dựng theo kiến trúc Modular, tách biệt các thành phần:
* **Frontend (Giao diện):** `Streamlit` (Python), `Plotly` (Vẽ biểu đồ), Custom HTML/CSS/JS.
* **Backend (API):** `FastAPI` (Cung cấp dữ liệu từ DB lên giao diện).
* **Database (Lưu trữ):** `Supabase` (PostgreSQL) hoạt động trên Cloud.
* **Data Pipeline (Cào & Xử lý dữ liệu):** `Python`, `BeautifulSoup4`, `Requests`.
* **Machine Learning (AI):** `Scikit-learn`, `LightGBM`/`XGBoost` (Phân loại xu hướng).

---

## 📂 Cấu trúc Thư mục

```text
AI_GOLD_OIL_FORECAST/
│
├── app.py                      # (1) Frontend: File chạy chính của giao diện Streamlit
├── backend/
│   └── main.py                 # (2) Backend: Chứa API FastAPI (/api/predict, /api/vn/prices...)
│
├── data_pipeline/              # (3) Scripts cào và xử lý dữ liệu
│   ├── vn_fuel_crawler.py      # Crawler giá xăng dầu VN và đẩy lên Supabase
│   ├── vn_gold_crawler.py      # Crawler giá vàng VN
│   └── news_crawler.py         # Crawler tin tức và đánh giá sentiment
│
├── models/                     # (4) Nơi chứa các model AI đã huấn luyện
│   ├── forecast_lightgbm.pkl   # File model dự báo
│   └── feature_columns.pkl     # Cấu trúc feature cho model
│
├── .env                        # Biến môi trường (API keys, Supabase credentials) - KHÔNG ĐƯA LÊN GITHUB
├── requirements.txt            # Danh sách thư viện Python cần cài đặt
└── README.md                   # File tài liệu dự án (bạn đang đọc)
🗄 Cấu trúc Cơ sở dữ liệu (Supabase)
Dự án sử dụng cơ sở dữ liệu quan hệ (PostgreSQL) trên Supabase với các bảng chính:

1. Bảng news (Lưu trữ tin tức & Sentiment)
id (uuid, PK): ID tự tăng.

title (text): Tiêu đề bản tin.

summary (text): Nội dung tóm tắt.

url (text): Link bài viết gốc.

source (text): Nguồn báo (VD: VnExpress, Reuters).

topic (varchar): Chủ đề (VD: Lãi suất, Vĩ mô).

gold_impact_score (float): Điểm tác động lên giá vàng (Âm: Giảm, Dương: Tăng).

oil_supply_threat_score (float): Điểm đe dọa nguồn cung dầu mỏ.

confidence_score (float): Độ tin cậy của AI khi phân tích tin tức này.

published_at (timestamp): Thời gian báo đăng.

created_at (timestamp): Thời gian dữ liệu được lưu vào DB (Cài đặt mặc định là now()).

status (varchar): Trạng thái xử lý của AI.

2. Bảng market_prices (Giá tài sản quốc tế)
id (uuid, PK)

symbol (varchar): Tên mã (XAUUSD, WTIUSD).

open, high, low, close (float): Thông số nến giá.

timestamp (timestamp): Thời điểm đóng nến.

3. Bảng technical_indicators (Chỉ báo kỹ thuật)
id (uuid, PK)

market_price_id (uuid, FK): Trỏ tới bảng market_prices.

rsi (float): Chỉ số sức mạnh tương đối.

macd_hist (float): Histogram của MACD.

4. Bảng vn_commodity_prices (Giá tài sản Việt Nam)
id (uuid, PK)

category (varchar): Phân loại (VD: Gold, Fuel).

asset_name (varchar): Tên tài sản (SJC, RON 95...).

buy_price, sell_price (float): Giá mua, Giá bán.

updated_at (timestamp): Thời gian cập nhật giá.

💻 Hướng dẫn Cài đặt & Chạy dự án
Bước 1: Chuẩn bị môi trường
Clone dự án về máy.

Tạo môi trường ảo (Virtual Environment):

Bash
python -m venv venv
# Kích hoạt trên Windows:
venv\Scripts\activate
# Kích hoạt trên Mac/Linux:
source venv/bin/activate
Cài đặt thư viện:

Bash
pip install -r requirements.txt
(Lưu ý: Nếu chưa có file requirements.txt, hãy chạy pip install streamlit pandas numpy plotly supabase requests joblib bs4 python-dotenv)

Bước 2: Cấu hình biến môi trường (.env)
Tạo file .env ở thư mục gốc của dự án và điền thông tin:

Đoạn mã
SUPABASE_URL=https://[PROJECT-ID].supabase.co
SUPABASE_KEY=ey...[YOUR-ANON-KEY]
API_BASE_URL=[http://127.0.0.1:8000](http://127.0.0.1:8000)
Bước 3: Chạy Backend (FastAPI)
Mở một terminal mới, kích hoạt môi trường ảo và chạy:

Bash
uvicorn backend.main:app --reload
API sẽ chạy tại: http://127.0.0.1:8000

Bước 4: Chạy Frontend (Streamlit Dashboard)
Mở một terminal khác, kích hoạt môi trường ảo và chạy:

Bash
streamlit run app.py
Giao diện sẽ tự động mở trên trình duyệt tại: http://localhost:8501

Bước 5: Chạy các Data Crawler (Thu thập dữ liệu)
Để cập nhật dữ liệu mới nhất lên Supabase, bạn chạy các script trong thư mục data_pipeline:

Bash
python data_pipeline/vn_fuel_crawler.py
python data_pipeline/news_crawler.py
(Trong môi trường thực tế (Production), các script này nên được cài đặt chạy tự động bằng Cronjob, Windows Task Scheduler hoặc Apache Airflow).

🔄 Quy trình Hoạt động (Data Flow)
Thu thập (Crawler): Các file .py trong data_pipeline cào dữ liệu web, làm sạch và lưu lên Supabase.

Lưu trữ: Supabase nhận dữ liệu. Bảng news tự động gán ngày giờ qua cột created_at.

Phân phối (Backend): FastAPI Server truy vấn dữ liệu từ Supabase, đóng gói thành các API JSON (/api/predict/vn-gold, /api/vn/prices...).

Hiển thị & Dự báo (Frontend): File app.py gọi API, load mô hình AI .pkl để dự báo, tính toán UI và hiển thị trực quan hóa qua biểu đồ Plotly và Streamlit.

Tác giả: [Ngô Trường Sơn]

Phiên bản: 1.0.0

License: MIT