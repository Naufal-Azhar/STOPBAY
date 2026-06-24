# STOPBAY Software Testing Guide (No Hardware)

Test full STOPBAY system without physical hardware.
This guide covers: Backend + Admin Dashboard + PWA + Virtual ESP32/CAM.

---

## Prerequisites

### Software Requirements
- **Python 3.10+** (backend, mock scripts)
- **PostgreSQL 14+** (database) — or skip and use SQLite
- **Node.js 18+** + **pnpm** (admin dashboard)
- **Web browser** (Chrome/Edge recommended)

### Install
```bash
# Python dependencies
cd backend
pip install -r requirements.txt --no-cache-dir
cd mock
pip install -r requirements.txt --no-cache-dir

# Node.js dependencies
cd ../../admin_dashboard
pnpm install
```

---

## 1. Database Setup

```bash
# PostgreSQL
createdb stopbay
# or via SQL: CREATE DATABASE stopbay;

# Edit backend/.env
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/stopbay

# Alternative: SQLite (quick test, no install needed)
# Edit backend/database.py: DATABASE_URL = "sqlite:///stopbay.db"
```

---

## 2. Seed Database

```bash
cd backend
python seed_data.py
```

**Expected output:**
```
==================================================
  STOPBAY Database Seeder v2.0
==================================================

[SEED] Generating 50 users... ✓ 50 created (was: 0)
[SEED] Generating 20 active parking... ✓ 20 created (10 WAITING + 10 ACTIVE) (was: 0)
[SEED] Generating 100 parking logs... ✓ 100 logs (15 forced, total revenue: Rp 1,234,000) (was: 0)
[SEED] Generating hardware devices... ✓ 5 devices (was: 0)

==================================================
  ✓ Database ready for demo!
==================================================
```

**Additional commands:**
```bash
python seed_data.py --clean              # Clear all data first
python seed_data.py --users 100          # Generate 100 users
python seed_data.py --logs 200           # Generate 200 log entries
```

---

## 3. Start Backend

```bash
cd backend
python main.py
```

**Expected:**
```
INFO:     Started server process
INFO:     Uvicorn running on http://0.0.0.0:8000
[DB] All tables created successfully.
[STOPBAY] Backend API is running...
```

**Verify:**
- Open http://localhost:8000 → `{"service":"STOPBAY v2.0","status":"running"}`
- Open http://localhost:8000/docs → Swagger UI (all 14 endpoints)
- Open http://localhost:8000/parking/stats → stats with seed data
- Open http://localhost:8000/parking/active → active sessions
- Open http://localhost:8000/users → 50 users with balances

---

## 4. Start Admin Dashboard

```bash
cd admin_dashboard
npm run dev
```

**Expected:** Open http://localhost:3000

**What you should see:**
- **Tab Live:** Stats cards (Active, Waiting, Revenue, Sessions) with data
- **Tab Live:** Table of active parking sessions (10 ACTIVE, 10 WAITING)
- **Tab History:** 100 parking logs with pagination
- **Tab Users:** 50 users with name, NIK, email, balance
- **Tab Hardware:** 5 devices (all online — green dots)

**Test interactions:**
- Refresh button updates data
- Date filter on History tab
- Top-up button on Users tab (increase balance)
- Language toggle EN/ID works

---

## 5. Open PWA User App

```bash
# Edit pwa/app.js → change API_BASE to http://localhost:8000
# Open in browser:
open pwa/index.html
# or: cd pwa && npx serve .
```

**What you should see:**
- Card UID input field
- Language toggle EN/ID
- Green theme (brand-emerald)

**Test:**
1. Pick a UID from http://localhost:8000/users (e.g., first user UID)
2. Enter UID in PWA input
3. Click "Cek Status"
4. If user has active session → fare card + duration + details
5. If no active session → error message
6. Auto-refresh every 5 seconds (fare incrementing)

---

## 6. Virtual ESP32 (Interactive Testing)

```bash
cd backend/mock
python virtual_esp32.py
```

**Test Scenario A: Happy Path (Car → Card → Active)**

```
> p                          # Inject plate
[CAM] Detected plate: B 1234 ABC
[HTTP] POST space-occupied -> 200 OK
[STATE] IDLE -> WAITING_CARD

> c                          # Tap random card
[RFID] Random card: A1B2C3D4
[HTTP] PUT register-card -> 200 OK
[STATE] WAITING_CARD -> ACTIVE

> s                          # Show status
ACTIVE | Plate: B 1234 ABC | 00:05:32 | Rp 2000
```

**Verify in Admin Dashboard:**
- Live tab → entry moved from WAITING to ACTIVE
- Users tab → new user A1B2C3D4 created

**Verify in PWA:**
- Enter UID A1B2C3D4 → live fare + balance displayed

---

**Test Scenario B: Forced Billing**

```
> p                          # Inject new plate
> f                          # Trigger forced billing (5 min skip)
[STATE] WAITING_CARD -> FORCED_BILLING
[STATE] FORCED_BILLING -> IDLE  (after 3 sec auto-reset)
```

**Verify in Admin Dashboard:**
- History tab → new entry with forced_billing=true, fare Rp 2.000

---

**Test Scenario C: Exit (Tap Active Card)**

```
> s                          # Make sure ACTIVE state
> e                          # Process exit
[HTTP] POST exit -> 200 OK
      fare: Rp 4,000 | duration: 1.5h
[STATE] ACTIVE -> IDLE
```

**Verify:**
- Admin Dashboard History → new entry with payment_method=DUMMY_BALANCE
- Live tab → session removed
- User balance reduced (check Users tab)

---

**Test Scenario D: Top-up via Admin**

```
Admin Dashboard → Users tab → Find user → Click "Top Up"
→ Input amount: 50000 → Confirm
```

**Verify:**
- User balance increased by 50,000
- PWA user refreshes → balance updated

---

## 7. Virtual ESP32-CAM (Auto Mode)

```bash
cd backend/mock
python virtual_cam.py       # Sequential, 15s interval
python virtual_cam.py --random --interval 5  # Random, 5s interval
```

**Behavior:**
- Sends a dummy plate to backend every N seconds
- Backend creates WAITING sessions (auto)
- Admin Dashboard Live tab updates

**Stop:** `Ctrl+C` — shows summary (how many sent, OK/FAIL count)

---

## 8. Full Test: 4 Terminals

```
Terminal 1: Backend
  cd backend && python main.py

Terminal 2: Admin Dashboard
  cd admin_dashboard && npm run dev

Terminal 3: Virtual CAM (auto plates)
  cd backend/mock && python virtual_cam.py --interval 10

Terminal 4: Virtual ESP32 (interactive)
  cd backend/mock && python virtual_esp32.py
```

**Workflow:**
1. CAM sends plate → Admin Dashboard Live → new WAITING session
2. Virtual ESP32 type `c` → Admin Dashboard Live → becomes ACTIVE
3. PWA enter UID → sees live fare
4. Virtual ESP32 type `e` → Admin Dashboard History → new log entry
5. Refresh stats → revenue increased

---

## 9. Hardware Status Monitoring

**Without hardware (mock status):**
- Admin Dashboard → Hardware tab shows 5 devices (all online)
- Heartbeats are timestamps from seed data

**With Virtual ESP32 running:**
- If you stop Virtual ESP32 and wait 2 minutes:
  - Admin Dashboard → refresh → all devices remain as in seed data
  - Real ESP32 heartbeat feature requires physical hardware

---

## 10. Troubleshooting

| Problem | Solution |
|---|---|
| **Backend won't start** | Check PostgreSQL running: `pg_isready` |
| **Seed data error** | Make sure tables exist: `python main.py` first |
| **Admin dashboard shows no data** | Check proxy in vite.config.js (must point to :8000) |
| **PWA can't reach API** | Edit `API_BASE` in pwa/app.js to `http://localhost:8000` |
| **Virtual ESP32 connection refused** | Backend not running on port 8000 |
| **CORS error in browser** | Already `allow_origins=["*"]`, should be fine |
| **Virtual CAM fails all requests** | Backend not running OR wrong space ID |
| **PostgreSQL: FATAL ident authentication** | Edit pg_hba.conf: change to md5 |

---

## 11. When Hardware Arrives

```
1. Edit ARDUINO_TEST/config.h:
   - WIFI_SSID = your WiFi name
   - WIFI_PASSWORD = your WiFi password
   - API_BASE_URL = http://192.168.x.x:8000 (your laptop IP)

2. Upload firmware:
   - ARDUINO_TEST.ino → ESP32 DevKit
   - STOPBAY_CAM.ino → ESP32-CAM

3. Wire hardware (follow BAHAN.md)

4. ESP32 auto-connects to backend

5. Virtual scripts no longer needed
```

**Software is already 100% tested — just connect hardware.**

---

## Support

- Backend API docs: http://localhost:8000/docs
- Summary: ARDUINO-TEST/SUMMARY.md
- Wiring guide: ARDUINO-TEST/BAHAN.md
