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
                    category_name = None
                    
                    if "RON 95" in name.upper():
                        category_name = "Xăng RON 95-III (1 Lít)"
                    elif "E5" in name.upper() or "RON 92" in name.upper():
                        category_name = "Xăng E5 RON 92 (1 Lít)"
                    elif "DO 0,05S" in name.upper() or "DO 0.05S" in name.upper() or "DẦU DO" in name.upper():
                        category_name = "Dầu DO 0,05S (1 Lít)"
                        
                    if category_name:
                        fuel_items.append({
                            "category": category_name,
                            "buy_price": 0,
                            "sell_price": price,
                            "unit": "Lít",
                            "currency": "VND",
                            "region": "VN",
                            "source": "Petrolimex",
                            "source_url": url,
                            "recorded_at": datetime.now(timezone.utc).isoformat()
                        })

        seen = set()
        for item in fuel_items:
            cat = item["category"]
            if cat not in seen:
                seen.add(cat)
                
                # Logic ghi DB an toàn: Tìm bản ghi cũ theo category
                check_res = supabase.table("vn_commodity_prices").select("id").eq("category", cat).execute()
                if check_res.data and len(check_res.data) > 0:
                    row_id = check_res.data[0]["id"]
                    supabase.table("vn_commodity_prices").update(item).eq("id", row_id).execute()
                else:
                    supabase.table("vn_commodity_prices").insert(item).execute()
                    
                print(f"   [✓] Cập nhật DB: {cat} -> Bán: {item['sell_price']:,} VNĐ/lít")

    except Exception as e:
        print(f"   [!] Lỗi cào giá xăng dầu: {e}")

if __name__ == "__main__":
    crawl_vn_fuel()