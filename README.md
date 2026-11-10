# set100-# SET100 Top Gainers & Losers Alert

ระบบอัตโนมัติแจ้งเตือนหุ้น SET100 ที่ปรับตัวขึ้นแรง (Top 3 Gainers) และลงแรง (Top 3 Losers) ผ่านทางแอป **ntfy** ทุกวันจันทร์ถึงศุกร์ เวลา 12:50 น. และ 17:50 น.

## วิธีการตั้งค่า
1. ไปที่ Settings > Secrets and variables > Actions ของ Repository นี้
2. สร้าง Repository Secret ชื่อ `NTFY_TOPIC` โดยใส่ชื่อ Topic ของ ntfy ที่คุณใช้งานในมือถือ
3. ไปที่แท็บ **Actions** บน GitHub เพื่อกดรันปุ่ม Test (`workflow_dispatch`) ทดสอบการเชื่อมต่อได้ทันทีtop-gainers-losers
