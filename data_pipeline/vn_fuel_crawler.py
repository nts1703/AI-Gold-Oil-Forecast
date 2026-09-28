import os
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timezone
from supabase import create_client, Client
from dotenv import load_dotenv
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("Thiếu SUPABASE_URL hoặc SUPABASE_KEY trong biến môi trường.")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}

def crawl_vn_fuel():
    print("==========================================")
    print("=== BẮT ĐẦU CÀO GIÁ XĂNG DẦU PETROLIMEX ===")
    print("==========================================")
    url = "https://webgia.com/gia-xang-dau/petrolimex/"
    
    try:
        res = requests.get(url, headers=HEADERS, timeout=10, verify=False)
        soup = BeautifulSoup(res.text, "html.parser")
        rows = soup.find_all("tr")
        
        fuel_items = []
        for row in rows:
            cols = [c.get_text().strip() for c in row.find_all(["td", "th"])]
            if len(cols) >= 2:
                name = cols[0]
                price_str = cols[1].replace(".", "").replace(",", "").replace("đ", "").strip()
                
                if price_str.isdigit():
                    price = int(price_str)
                    category_code = None
                    
                    # Chuẩn hóa tên mã category cho khớp DB lịch sử
                    if "RON 95" in name.upper():
                        category_code = "GAS_RON95"
                    elif "E5" in name.upper() or "RON 92" in name.upper():
                        category_code = "GAS_E5RON92"
                    elif "DO 0,05S" in name.upper() or "DO 0.05S" in name.upper() or "DẦU DO" in name.upper():
                        category_code = "DIESEL"
                        
                    if category_code:
                        fuel_items.append({
                            "category": category_code,
                            "buy_price": 0,
                            "sell_price": price,
                            "unit": "Lít",
                            "currency": "VND",
                            "region": "VN",
                            "source": "Petrolimex",
                            "source_url": url,
                            "recorded_at": datetime.now(timezone.utc).isoformat()
                        })

        if not fuel_items:
            print("   [⚠️] Không tìm thấy dữ liệu giá xăng dầu.")
            return

        # --- LƯU VÀO SUPABASE (Thêm mới bản ghi để lưu chuỗi thời gian) ---
        seen = set()
        for item in fuel_items:
            cat = item["category"]
            if cat not in seen:
                seen.add(cat)
                supabase.table("vn_commodity_prices").insert(item).execute()
                print(f"   [✓] Đã lưu bản ghi mới DB: {cat} -> Bán: {item['sell_price']:,} VNĐ/lít")

    except Exception as e:
        print(f"   [!] Lỗi cào giá xăng dầu: {e}")

if __name__ == "__main__":
    crawl_vn_fuel()