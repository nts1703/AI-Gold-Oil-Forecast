import yfinance as yf
from datetime import datetime, timedelta

print("=== Bắt đầu lấy dữ liệu giá Vàng & Dầu ===\n")

# Lấy dữ liệu 10 ngày gần nhất
end_date = datetime.now()
start_date = end_date - timedelta(days=10)

# ======================
# 1. Giá Vàng (GC=F - Gold Futures)
# ======================
print("1. Đang lấy giá Vàng (GC=F)...")
try:
    gold = yf.download(
        "GC=F",
        start=start_date,
        end=end_date,
        progress=False,
        multi_level_index=False   # Làm phẳng cột
    )

    if not gold.empty:
        latest_close = float(gold['Close'].iloc[-1])
        print("✅ Lấy giá Vàng thành công!")
        print(gold[['Open', 'High', 'Low', 'Close']].tail(5))
        print(f"\nGiá đóng cửa gần nhất: {latest_close:.2f} USD/oz\n")
    else:
        print("❌ Không lấy được dữ liệu Vàng\n")
except Exception as e:
    print(f"❌ Lỗi khi lấy giá Vàng: {e}\n")

# ======================
# 2. Giá Dầu WTI (CL=F)
# ======================
print("2. Đang lấy giá Dầu WTI (CL=F)...")
try:
    oil = yf.download(
        "CL=F",
        start=start_date,
        end=end_date,
        progress=False,
        multi_level_index=False
    )

    if not oil.empty:
        latest_close = float(oil['Close'].iloc[-1])
        print("✅ Lấy giá Dầu thành công!")
        print(oil[['Open', 'High', 'Low', 'Close']].tail(5))
        print(f"\nGiá đóng cửa gần nhất: {latest_close:.2f} USD/thùng\n")
    else:
        print("❌ Không lấy được dữ liệu Dầu\n")
except Exception as e:
    print(f"❌ Lỗi khi lấy giá Dầu: {e}\n")

print("=== Kết thúc ===")