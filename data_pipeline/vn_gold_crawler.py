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
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

def crawl_vn_gold():
    print("==========================================")
    print("=== BẮT ĐẦU CÀO GIÁ VÀNG SJC (OFFICIAL) ===")
    print("==========================================")
    
    gold_items = []
    
    # --- NGUỒN 1: SJC OFFICIAL XML ---
    url_sjc = "https://sjc.com.vn/xml/tygiavang.xml"
    try:
        res = requests.get(url_sjc, headers=HEADERS, timeout=10, verify=False)
        if res.status_code == 200:
            soup = BeautifulSoup(res.content, "xml")
            items = soup.find_all("item")
            print(f"   [*] Đã kết nối SJC XML. Tìm thấy {len(items)} mục dữ liệu.")
            
            for item in items:
                name = item.get("type", "")
                buy_raw = item.get("buy", "0").replace(".", "").replace(",", "").strip()
                sell_raw = item.get("sell", "0").replace(".", "").replace(",", "").strip()
                
                try:
                    buy_val = float(buy_raw) if buy_raw else 0
                    sell_val = float(sell_raw) if sell_raw else 0
                    if buy_val == 0 or sell_val == 0:
                        continue
                    
                    buy_price = int(buy_val * 1000) if buy_val < 1000000 else int(buy_val)
                    sell_price = int(sell_val * 1000) if sell_val < 1000000 else int(sell_val)
                    
                    category_name = None
                    if any(k in name.upper() for k in ["1L", "10L", "SJC"]):
                        category_name = "Vàng SJC (1 Lượng)"
                    elif "NHẪN" in name.upper():
                        category_name = "Vàng Nhẫn Trơn 9999"
                        
                    if category_name:
                        gold_items.append({
                            "category": category_name,
                            "buy_price": buy_price,
                            "sell_price": sell_price,
                            "unit": "Lượng",
                            "currency": "VND",
                            "region": "VN",
                            "source": "SJC",
                            "source_url": url_sjc,
                            "recorded_at": datetime.now(timezone.utc).isoformat()
                        })
                except ValueError:
                    continue
    except Exception as e:
        print(f"   [!] Nguồn SJC XML gặp lỗi: {e}")

    # --- NGUỒN 2: DỰ PHÒNG WEBGIA (Nếu SJC lỗi hoặc không có dữ liệu) ---
    if not gold_items:
        print("   [*] Chuyển sang cào nguồn dự phòng Webgia.com...")
        url_webgia = "https://webgia.com/gia-vang/sjc/"
        try:
            res = requests.get(url_webgia, headers=HEADERS, timeout=10, verify=False)
            soup = BeautifulSoup(res.text, "html.parser")
            rows = soup.find_all("tr")
            
            for row in rows:
                cols = [c.get_text().strip() for c in row.find_all(["td", "th"])]
                if len(cols) >= 3:
                    name = cols[0]
                    buy_str = cols[1].replace(".", "").replace(",", "").replace("đ", "").strip()
                    sell_str = cols[2].replace(".", "").replace(",", "").replace("đ", "").strip()
                    
                    if buy_str.isdigit() and sell_str.isdigit():
                        buy_price = int(buy_str)
                        sell_price = int(sell_str)
                        
                        if buy_price < 1000000:
                            buy_price *= 1000
                        if sell_price < 1000000:
                            sell_price *= 1000
                            
                        category_name = None
                        if any(k in name.upper() for k in ["SJC", "1L"]):
                            category_name = "Vàng SJC (1 Lượng)"
                        elif "NHẪN" in name.upper():
                            category_name = "Vàng Nhẫn Trơn 9999"
                            
                        if category_name:
                            gold_items.append({
                                "category": category_name,
                                "buy_price": buy_price,
                                "sell_price": sell_price,
                                "unit": "Lượng",
                                "currency": "VND",
                                "region": "VN",
                                "source": "Webgia",
                                "source_url": url_webgia,
                                "recorded_at": datetime.now(timezone.utc).isoformat()
                            })
        except Exception as e:
            print(f"   [!] Nguồn Webgia gặp lỗi: {e}")

    # --- LƯU VÀO SUPABASE ---
    if not gold_items:
        print("   [⚠️] Không tìm thấy dữ liệu giá vàng từ các nguồn.")
        return

    seen = set()
    for item in gold_items:
        cat = item["category"]
        if cat not in seen:
            seen.add(cat)
            check_res = supabase.table("vn_commodity_prices").select("id").eq("category", cat).execute()
            if check_res.data and len(check_res.data) > 0:
                row_id = check_res.data[0]["id"]
                supabase.table("vn_commodity_prices").update(item).eq("id", row_id).execute()
            else:
                supabase.table("vn_commodity_prices").insert(item).execute()
                
            print(f"   [✓] Cập nhật DB: {cat} -> Mua: {item['buy_price']:,} đ | Bán: {item['sell_price']:,} đ")

if __name__ == "__main__":
    crawl_vn_gold()