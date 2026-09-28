import requests
from bs4 import BeautifulSoup
import re
import urllib3

# Tắt cảnh báo SSL certificate
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

def test_gold_sjc():
    print("==================================================")
    print("🔍 TEST CÀO GIÁ VÀNG THỰC TẾ (SJC XML OFFICIAL)")
    print("==================================================")
    url = "https://sjc.com.vn/xml/tygia.xml"
    
    try:
        res = requests.get(url, headers=HEADERS, timeout=10, verify=False)
        # Dùng BeautifulSoup với html.parser để bỏ qua mọi ký tự lỗi XML
        soup = BeautifulSoup(res.content, "html.parser")
        
        found = False
        items = soup.find_all("item")
        
        for item in items:
            name = item.get("type", "")
            buy_raw = item.get("buy", "0")
            sell_raw = item.get("sell", "0")
            
            if any(k in name.upper() for k in ["1L", "SJC", "NHẪN"]):
                try:
                    buy_val = float(buy_raw)
                    sell_val = float(sell_raw)
                    
                    buy_price = int(buy_val * 1000) if buy_val < 1000000 else int(buy_val)
                    sell_price = int(sell_val * 1000) if sell_val < 1000000 else int(sell_val)
                    
                    print(f"📌 Loại vàng: {name}")
                    print(f"   -> Mua vào: {buy_price:,} VNĐ")
                    print(f"   -> Bán ra : {sell_price:,} VNĐ")
                    print("-" * 40)
                    found = True
                except ValueError:
                    continue
                    
        if not found:
            print("⚠️ Không đọc được các thẻ vàng SJC.")
            
    except Exception as e:
        print(f"❌ Lỗi kết nối nguồn SJC: {e}")

def test_fuel_webgia():
    print("\n==================================================")
    print("🔍 TEST CÀO GIÁ XĂNG DẦU THỰC TẾ (WEBGIA.COM)")
    print("==================================================")
    url = "https://webgia.com/gia-xang-dau/petrolimex/"
    
    try:
        res = requests.get(url, headers=HEADERS, timeout=10, verify=False)
        soup = BeautifulSoup(res.text, "html.parser")
        
        rows = soup.find_all("tr")
        found = False
        
        for row in rows:
            cols = [c.get_text().strip() for c in row.find_all(["td", "th"])]
            if len(cols) >= 2:
                name = cols[0].lower()
                if any(k in name for k in ["ron 95", "e5", "ron 92", "dầu do", "0,05s", "0.05s"]):
                    price_str = cols[1].replace(".", "").replace(",", "").replace("đ", "").strip()
                    if price_str.isdigit():
                        price = int(price_str)
                        print(f"⛽ Nhiên liệu: {cols[0]}")
                        print(f"   -> Giá niêm yết: {price:,} VNĐ/lít")
                        print("-" * 40)
                        found = True
                        
        if not found:
            print("⚠️ Không tìm thấy bảng giá xăng trên Webgia.com")
            
    except Exception as e:
        print(f"❌ Lỗi cào giá xăng dầu: {e}")

if __name__ == "__main__":
    test_gold_sjc()
    test_fuel_webgia()