import os
import requests
from datetime import datetime
import pytz
import pandas as pd

def get_set100_data():
    # URL อ้างอิงตามที่คุณต้องการ
    url = "https://www.settrade.com/th/equities/market-data/overview?category=Index&index=SET100"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    try:
        # ดึงข้อมูลตาราง HTML จากหน้า Settrade
        dfs = pd.read_html(url, header=0)
        if not dfs:
            raise ValueError("ไม่พบตารางข้อมูลในหน้าเว็บ")
        
        # ค้นหาตารางที่มีข้อมูลหุ้น SET100
        df = None
        for table in dfs:
            # ตรวจสอบคอลัมน์ที่เกี่ยวข้องกับชื่อหลักทรัพย์และการเปลี่ยนแปลง
            cols = [str(c) for c in table.columns]
            if any('หลักทรัพย์' in c or 'Symbol' in c or 'ราคา' in c for c in cols):
                df = table
                break
                
        if df is None:
            df = dfs[0] # ใช้ตารางแรกเป็นค่าสำรอง
            
        # ทำความสะอาดข้อมูลคอลัมน์ (ชื่อหุ้น และ % เปลี่ยนแปลง)
        # หมายเหตุ: โครงสร้างคอลัมน์มักประกอบด้วย ชื่อย่อหลักทรัพย์, ราคาล่าสุด, เปลี่ยนแปลง (%) ฯลฯ
        print("ดึงข้อมูลสำเร็จ จำนวนแถว:", len(df))
        return df
    except Exception as e:
        print(f"เกิดข้อผิดพลาดในการดึงข้อมูล: {e}")
        return None

def process_and_send_notification(is_test=False):
    tz = pytz.timezone('Asia/Bangkok')
    now = datetime.now(tz)
    date_str = now.strftime('%d/%m/%Y')
    time_str = now.strftime('%H:%M:%S')
    
    ntfy_topic = os.getenv("NTFY_TOPIC")
    if not ntfy_topic:
        print("Error: ยังไม่ได้ตั้งค่า NTFY_TOPIC ใน GitHub Secrets")
        return

    if is_test:
        message = f"🟢 ทดสอบระบบ\nntfy เชื่อมต่อ github สำเร็จ\n📅 วันที่: {date_str}\n⏰ เวลา: {time_str}"
        title = "GitHub Connection Test"
    else:
        # ดึงข้อมูลจริงจาก Settrade
        df = get_set100_data()
        
        if df is not None and not df.empty:
            # สมมติโครงสร้างคอลัมน์ (ปรับให้ตรงกับชื่อคอลัมน์จริงบนหน้าเว็บ)
            # ค้นหาคอลัมน์ชื่อหลักทรัพย์และ % เปลี่ยนแปลง
            symbol_col = next((c for c in df.columns if 'ชื่อย่อ' in str(c) or 'Symbol' in str(c)), df.columns[0])
            change_pct_col = next((c for c in df.columns if '%' in str(c) or 'เปลี่ยนแปลง (%)' in str(c)), df.columns[-1])
            
            # แปลงค่า % เปลี่ยนแปลงให้เป็นตัวเลข
            df[change_pct_col] = pd.to_numeric(df[change_pct_col].astype(str).str.replace('+', '').str.replace(',', ''), errors='coerce')
            df = df.dropna(subset=[change_pct_col])
            
            #จัดอันดับ Top 3 Gainers และ Top 3 Losers
            top_gainers = df.nlargest(3, change_pct_col)
            top_losers = df.nsmallest(3, change_pct_col)
            
            msg_lines = [
                f"📊 แจ้งเตือนความเคลื่อนไหว SET100",
                f"📅 วันที่: {date_str} | ⏰ เวลา: {time_str} น.\n",
                "📈 Top 3 Gainers (ขึ้นแรง):"
            ]
            for _, row in top_gainers.iterrows():
                msg_lines.append(f"• {row[symbol_col]}: +{row[change_pct_col]}%")
                
            msg_lines.append("\n📉 Top 3 Losers (ลงแรง):")
            for _, row in top_losers.iterrows():
                msg_lines.append(f"• {row[symbol_col]}: {row[change_pct_col]}%")
                
            message = "\n".join(msg_lines)
            title = f"SET100 Report ({time_str})"
        else:
            # Fallback กรณีดึงเว็บไม่ได้ชั่วคราว
            message = f"⚠️ แจ้งเตือน SET100\n📅 วันที่: {date_str} ⏰ {time_str}\nไม่สามารถดึงข้อมูลจาก Settrade ได้ในรอบนี้ กรุณาตรวจสอบเว็บหลัก"
            title = "SET100 Alert Error"

    # ส่งเข้า ntfy.sh
    ntfy_url = f"https://ntfy.sh/{ntfy_topic}"
    try:
        response = requests.post(
            ntfy_url,
            data=message.encode('utf-8'),
            headers={
                "Title": title.encode('utf-8'),
                "Priority": "default",
                "Tags": "chart_with_upwards_trend,stock"
            }
        )
        if response.status_code == 200:
            print("ส่งการแจ้งเตือนไปยัง ntfy สำเร็จครับ")
        else:
            print(f"ส่งไม่สำเร็จ Status Code: {response.status_code}")
    except Exception as e:
        print(f"เกิดข้อผิดพลาดในการส่ง ntfy: {e}")

if __name__ == "__main__":
    # ตรวจสอบว่าเป็นโหมด Test หรือไม่จาก Environment Variable
    test_mode = os.getenv("TEST_MODE", "false").lower() == "true"
    process_and_send_notification(is_test=test_mode)
