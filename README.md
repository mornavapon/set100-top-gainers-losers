# SET100 Top Gainers & Losers Alert

<img width="400" height="446" alt="set100- top gainer   loser" src="https://github.com/user-attachments/assets/41ca4b1d-86a9-4550-ae3d-e9714e6bc75f" />

ลิ้งค์ไปยังเอไอที่ช่วยสร้าง
https://chatgpt.com/g/g-p-6ae01a981d208191b90116a6a767d75e-github-daanhunaelakaarlngthun/c/6afd688f-a60c-83ec-826c-08480e673af1

ระบบแจ้งเตือนหุ้น SET100 ที่มีเปอร์เซ็นต์การเปลี่ยนแปลงราคาสูงสุด 3 อันดับแรก (Gainers) และต่ำสุด 3 อันดับแรก (Losers) ผ่าน ntfy

ไม่มีหน้าเวปแอป !!

## กำหนดการ

- วันจันทร์–ศุกร์ เวลา 12:50 น. และ 17:50 น. ตามเวลาไทย
- GitHub Actions ใช้เวลา UTC จึงตั้ง cron เป็น 05:50 และ 10:50 UTC


## การสั่งงานผ่าน cron-job.org

เพิ่ม cron-job.org เพื่อเป็นตัวกระตุ้น GitHub Actions ผ่าน GitHub REST API แทนการพึ่งพา GitHub schedule เพียงอย่างเดียว ช่วยให้กำหนดเวลาสั่งเริ่ม Workflow ได้จาก cron-job.org

การทำงาน:
1. cron-job.org เรียก GitHub API ด้วย HTTP method `POST` ไปยัง Workflow dispatch endpoint
2. GitHub Actions รับคำสั่ง `workflow_dispatch` และรันโหมด `alert`
3. สคริปต์ดึงข้อมูล SET100 จัดอันดับ และส่งผลผ่าน ntfy ตามปกติ

การตั้งค่าปัจจุบัน:
- ชื่อ Cronjob: `SET100 Alert เช้า-เย็น`
- เวลาที่ตั้งใน cron-job.org: วันจันทร์–ศุกร์ เวลา 17:50 น. ตามเวลาไทย
- Request method: `POST`
- Workflow: `stock_alert.yml` บน branch `main`
- Request body: `{"ref":"main","inputs":{"mode":"alert"}}`
- ใช้ Fine-grained Personal Access Token ชื่อ `SET100-Cron-Trigger`
- Token จำกัด Repository access เฉพาะ `set100-top-gainers-losers` และให้สิทธิ์ Repository permission: `Actions: Read and write`
- **วันหมดอายุ Token: 17 พฤศจิกายน 2027 (พ.ศ. 2570)**

### ข้อควรจำเรื่อง Token
- เมื่อ Token หมดอายุ cron-job.org จะไม่สามารถสั่ง GitHub Actions ได้ ต้องสร้าง Token ใหม่และแก้ค่า Authorization header ใน cron-job.org
- ห้ามนำ Token ไปใส่ในไฟล์ของ Repository, README, source code หรือ commit ลง GitHub
- เก็บ Token ไว้ใน Authorization header ของ cron-job.org เท่านั้น และอย่าเปิดเผย Token ในภาพหน้าจอหรือแชต

### หมายเหตุเรื่องตารางเวลา
- GitHub Actions schedule เดิมยังตั้งไว้ที่ 12:50 และ 17:50 น. ตามเวลาไทย
- cron-job.org เพิ่มการสั่งงานที่ 17:50 น. ในช่วงทดสอบ ควรตรวจสอบการทำงานจริงก่อนปิด GitHub schedule เดิม เพื่อหลีกเลี่ยงการแจ้งเตือนซ้ำในเวลา 17:50 น.
- หลังยืนยันว่า cron-job.org ทำงานสม่ำเสมอแล้ว จึงค่อยพิจารณาปรับ GitHub schedule ให้เหลือเฉพาะเวลาที่ต้องการใช้เป็นระบบสำรอง หรือปิด schedule เดิมตามรูปแบบการใช้งาน
- HTTP 204 จาก cron-job.org หมายถึง GitHub รับคำสั่ง dispatch แล้ว แต่ยังควรตรวจสอบ Workflow run และการแจ้งเตือน ntfy เพื่อยืนยันว่าทำงานจนครบ

## แหล่งข้อมูล

ใช้ SET Index Composition API:

`https://www.set.or.th/api/set/index/SET100/composition?language=en`

ข้อมูลจาก endpoint นี้ประกอบด้วยรายชื่อหลักทรัพย์ใน SET100 และข้อมูล quote ของแต่ละหลักทรัพย์ในคำขอเดียว โดยใช้ไลบรารี `settfex` รุ่นที่ pin ไว้เพื่อจัดการ session, headers และตรวจสอบโครงสร้างข้อมูล

หมายเหตุ: `settfex` เป็นไลบรารีบุคคลที่สาม ไม่ใช่ผลิตภัณฑ์ API ที่ SET รับประกันอย่างเป็นทางการ และ endpoint สาธารณะอาจเปลี่ยนแปลงหรือมีมาตรการป้องกันการเรียกใช้งานอัตโนมัติได้

## ตั้งค่า ntfy

1. เปิด Repository > Settings > Secrets and variables > Actions
2. เพิ่ม Repository secret ชื่อ `NTFY_TOPIC` โดยใส่ชื่อ topic ที่ใช้ในแอป ntfy
3. ถ้า topic ต้องใช้การยืนยันตัวตน ให้เพิ่ม secret `NTFY_TOKEN` ด้วย (ไม่บังคับ)

## ทดสอบ

เปิดแท็บ **Actions** > **SET100 Top Gainers & Losers** > **Run workflow**

เลือกโหมด:
- `test-ntfy` — ทดสอบส่งข้อความ `ntfy เชื่อมต่อ GitHub สำเร็จ` โดยไม่เรียกข้อมูลตลาด
- `check-data` — เรียกข้อมูลและตรวจสอบจำนวนหุ้น/วันที่/ราคา แต่ไม่ส่งแจ้งเตือน
- `alert` — ทำงานจริง เรียกข้อมูลและส่ง Top Gainers/Losers

## ระบบป้องกันข้อมูลผิดพลาด

ก่อนจัดอันดับ ระบบตรวจว่า:
- API ตอบกลับเป็นดัชนี SET100
- มีสมาชิกครบ 100 หลักทรัพย์ และไม่มี ticker ซ้ำ
- มีค่า % เปลี่ยนแปลงที่ใช้ได้อย่างน้อย 90 หลักทรัพย์
- มี timestamp ที่ระบุเขตเวลา และเป็นวันที่ปัจจุบันตามเวลาไทย

หากไม่ผ่านการตรวจสอบ ระบบจะไม่สร้างอันดับจากข้อมูลที่ไม่สมบูรณ์ ในรอบแจ้งเตือนจริงจะส่งข้อความเตือนแทน

## หมายเหตุ

ข้อมูล % เปลี่ยนแปลงเป็นการเปลี่ยนแปลงจากราคาปิดก่อนหน้า ตามข้อมูลที่ API ส่งให้ ณ เวลาที่ดึงข้อมูล ไม่ใช่การคาดการณ์ราคา
