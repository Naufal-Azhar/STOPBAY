# STOPBAY v2.0 — Summary Dokumentasi

**Ticketless Smart Parking System**  
_Created: 22 June 2026 | Status: Under Development_

---

## Tech Stack Final

| Layer | Technology | Storage |
|---|---|---|
| Firmware | Arduino C++ (ESP32 board 2.0.14) + library version lock | ~2 GB |
| Backend | Python 3.10+ / FastAPI / SQLAlchemy / PostgreSQL | ~1 GB |
| User App | PWA (HTML + Tailwind CDN + Vanilla JS + Service Worker) | ~5 MB |
| Admin Dashboard | React 18 + Vite + Tailwind CSS | ~500 MB |
| Database | PostgreSQL (or SQLite for dev) | ~500 MB |
| **Total** | | **~4 GB** |

---

## Hardware

| Component | Qty | Status | Connection |
|---|---|---|---|
| ESP32 DevKit | 1 | ✅ Active | Main controller |
| ESP32-CAM | 1 | ✅ Active | Serial2 (RX2=16, TX2=17) |
| I2C LCD 20x4 | 1 | ✅ Active | I2C (SDA=21, SCL=22, addr=0x27) |
| RFID RC522 | 1 | ✅ Active (Slot 1) | SPI (SS=5, RST=4) |
| RFID RC522 | 1 | ⏳ Defer (Slot 2) | File stub ready |
| RFID RC522 | 1 | ⏳ Defer (Exit Gate) | File stub ready |
| Servo | 1 | ⏳ Defer | Kode `#ifdef USE_SERVO` ready |
| ESP32-CAM #2 | 1 | ⏳ Defer | File stub ready |
| LCD #2 | 1 | ⏳ Defer | File stub ready |

---

## File Structure (25 files)

```
ARDUINO-TEST/
├── BAHAN.md                           # Original wiring reference
├── SUMMARY.md                         # This file
│
├── STOPBAY_CAM/
│   └── STOPBAY_CAM.ino                # ESP32-CAM dummy plate sender
│
├── ARDUINO_TEST/
│   ├── libraries.txt                  # Library version lock
│   ├── config.h                       # WiFi, API URL, hardware switches
│   └── ARDUINO_TEST.ino              # Main ESP32 firmware (v2.0)
│
├── backend/
│   ├── .env                           # PostgreSQL connection
│   ├── requirements.txt               # Python dependencies
│   ├── database.py                    # SQLAlchemy engine + session
│   ├── models.py                      # Tables: active_parking, parking_logs, users, hardware_status
│   ├── schemas.py                     # Pydantic schemas (v2.0)
│   └── main.py                        # FastAPI: 14 endpoints (v2.0)
│
├── pwa/                               # User Mobile App (replaces Flutter)
│   ├── index.html                     # UI: bilingual, hijau theme, responsive
│   ├── styles.css                     # Animations, themes
│   ├── app.js                         # Auto-refresh, i18n toggle, API fetcher
│   ├── manifest.json                  # PWA config
│   └── sw.js                          # Service Worker + Web Push ready
│
└── admin_dashboard/
    ├── package.json / index.html
    ├── vite.config.js / tailwind.config.js / postcss.config.js
    └── src/
        ├── main.jsx / index.css
        └── App.jsx                     # 4 tabs: Live, History, Users, Hardware
```

---

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/parking/space-occupied` | CAM detects car → creates WAITING session |
| `PUT` | `/api/parking/register-card` | RFID tap → auto-register user, activate session |
| `POST` | `/api/parking/forced-billing` | 5-min timeout → forced Rp 2,000 billing |
| `GET` | `/api/parking/status/{card_uid}` | PWA user: live duration + fare + balance |
| `POST` | `/api/parking/exit` | Exit gate: calculate fare, deduct balance, move to logs |
| `GET` | `/api/parking/active` | Admin: live parking sessions |
| `GET` | `/api/parking/logs` | Admin: history with pagination + date filter |
| `GET` | `/api/parking/stats` | Admin: aggregate statistics |
| `POST` | `/api/hardware/heartbeat` | ESP32 30-sec heartbeat |
| `GET` | `/api/hardware/status` | Admin: online/offline status |
| `GET` | `/api/users` | Admin: all users |
| `GET` | `/api/users/{card_uid}` | PWA: user balance |
| `POST` | `/api/users/{card_uid}/topup` | Admin: top-up balance |

---

## Database Schema

### `active_parking`
id, parking_space_id, plate_number, card_uid, entry_time, status, space_label, snapshot_url, user_name, nik, last_update, expiry_time

### `parking_logs`
id, plate_number, card_uid, start_time, end_time, total_fare, parking_space_id, space_label, user_name, nik, snapshot_url, payment_method, balance_before, balance_after, forced_billing

### `users`
card_uid (PK), full_name, nik, email, phone, balance, created_at, last_seen

### `hardware_status`
id, device_id, device_type, location, is_online, last_heartbeat, extra_info

---

## UI/UX Design Decisions

| Feature | Decision |
|---|---|
| Language | Bilingual (ID/EN) with toggle |
| Brand Color | Hijau Emerald (#059669) |
| Layout | Equal responsive (breakpoint 768px) |
| Animations | Full (CSS only: fadeIn, slideUp, popIn, pulse — no heavy parallax/blur) |
| PWA User Info | Plate + Duration + Fare + Balance |
| Admin Tabs | Live / History / Users / Hardware |

---

## System Workflow

```
1. CAM DETECT: ESP32-CAM sends plate → Main ESP32 → POST space-occupied
   Backend sets expiry_time = now + 5 minutes (grace period)
   LCD: "Car Detected! Tap KTP/KTM..."

2. CARD TAP (within 5 min): User taps RFID
   → Backend auto-registers user (random name, NIK, saldo Rp 50K-200K)
   → Session becomes ACTIVE, fare starts at Rp 2,000/hour
   → LCD: "Regis Success! Active Session"
   → PWA user can check status with UID

3. FORCED BILLING (if no tap in 5 min):
   → ESP32 timer expires → POST forced-billing
   → Backend charges Rp 2,000 automatically
   → Session moved to parking_logs, space freed
   → LCD: "TIME'S UP! Forced billing Rp 2,000"

4. EXIT (future): User taps card at exit gate
   → POST exit → backend calculates fare, deducts balance
   → Moves to parking_logs, deletes from active_parking
   → Servo gate opens (hardware pending)
```

---

## Library Version Lock

```
LiquidCrystal_I2C@1.1.2     (I2C LCD 20x4)
MFRC522@1.4.11               (RFID RC522 SPI)
ArduinoJson@7.3.1            (JSON HTTP payload)
ESP32Servo@1.2.2             (Servo motor)
esp32@2.0.14                 (Board package)
```

---

## How to Run

### 1. Firmware
```bash
# Install Arduino IDE > Boards Manager > esp32@2.0.14
# Library Manager > install exact versions from libraries.txt
# Edit config.h with WiFi SSID, password, API IP
# Upload ARDUINO_TEST.ino to ESP32 DevKit
# Upload STOPBAY_CAM.ino to ESP32-CAM (power via 5V rail, NOT USB)
```

### 2. Backend
```bash
cd backend
pip install -r requirements.txt --no-cache-dir
createdb stopbay           # PostgreSQL required
python main.py             # http://localhost:8000
```

### 3. PWA (User App)
```bash
# Option A: Open directly
open pwa/index.html

# Option B: Serve via HTTP for PWA features
npx serve pwa/             # http://localhost:3000
# Or deploy to Vercel/Netlify for HTTPS (required for Web Push)
```

### 4. Admin Dashboard
```bash
cd admin_dashboard
pnpm install               # or: npm install && npm cache clean --force
npm run dev                # http://localhost:3000
```

---

## Todo / Pending

- [ ] Purchase & connect RFID Slot 2
- [ ] Purchase & connect RFID Exit Gate
- [ ] Purchase & connect Servo gate
- [ ] Purchase & connect ESP32-CAM #2
- [ ] Purchase & connect LCD #2 (exit gate)
- [ ] Deploy PWA to HTTPS host (Vercel/Netlify) for Web Push
- [ ] Add real OCR instead of dummy plate
- [ ] Add real camera snapshot instead of placeholder
- [ ] Add JWT/auth security
- [ ] Migrate from SQLite to PostgreSQL for production
- [ ] Real payment gateway integration
- [ ] Physical wiring test with all hardware
- [ ] End-to-end workflow test

---

_Session: 21-22 June 2026 — Full architecture design, code generation, UI/UX design.  
v2.0 — PWA migration, bilingual UI, hijau theme, users + hardware tables, forced billing._
