# STOPBAY v3.0 — Capture Photo Dashboard + Card Discipline — Design

> Status: DRAFT — menunggu review
> Depends on: on-demand plate capture (`services/capture_detect.py`, endpoint `POST /api/parking/capture/{slot}`) — sudah diimplementasi di sesi sebelumnya.

## Ringkasan

Dua fitur independen yang dikerjakan bersamaan:

1. **Capture photo di dashboard admin** — foto hasil `capture_and_detect()` (dengan bounding box YOLO + teks plat) disimpan ke disk dan ditampilkan di tab Live (di bawah live stream tiap slot) dan tab History (via modal, klik tombol).
2. **Card discipline + grace period exit** — kartu RFID yang sudah ACTIVE di satu slot tidak bisa registrasi ulang di slot lain (atau slot yang sama). Saat keluar (RFID EXIT), sistem mengecek riwayat tap: kalau kartu belum pernah tap di slot manapun, keluar gratis; kalau sudah tap dan durasi kurang dari 5 menit, keluar gratis (tetap tercatat); kalau lebih dari 5 menit, kena charge tarif normal.

## Bagian 1: Capture Photo Dashboard

### Arsitektur

```
RFID tap → register-card (ACTIVE) → ESP32 trigger capture
                                            ↓
                            POST /api/parking/capture/{slot}
                                            ↓
                  capture_and_detect() ambil 3 foto dari CAM
                                            ↓
              voting plat terbaik dari 3 hasil OCR (logic existing)
                                            ↓
        gambar box YOLO + teks plat di foto terbaik (server-side, cv2)
     (kalau tidak ada plat terdeteksi di 3 foto → simpan foto polos, tanpa box)
                                            ↓
   simpan ke backend/captures/{space_id}_{timestamp}.jpg (timpa foto lama utk space_id itu)
                                            ↓
     update session.snapshot_url = "/captures/xx.jpg", plate_number = hasil vote
                                            ↓
    Dashboard Live (polling 5s existing) tampilkan foto di bawah live stream tiap slot
                                            ↓
         session exit → snapshot_url ikut pindah ke ParkingLog (sudah otomatis, existing)
                                            ↓
          Dashboard History → klik tombol → modal menampilkan foto tersimpan
```

Live stream MJPEG slot yang sedang di-capture akan terputus sesaat (ESP32-CAM HTTP server hanya menangani 1 koneksi bersamaan) — capture diprioritaskan, live stream reconnect otomatis setelah capture selesai.

### Komponen

**`backend/services/capture_detect.py`** (perluasan dari yang sudah ada)
- `_draw_annotations(frame, detections, winning_plate) -> np.ndarray` — gambar kotak hijau di deteksi yang platnya menang voting, kotak abu-abu di deteksi lain, teks plat di atas kotak (`cv2.rectangle` + `cv2.putText`)
- `_save_capture(frame, space_id) -> str` — simpan ke `backend/captures/{space_id}_{timestamp}.jpg`; sebelum simpan, hapus file lama yang match pattern `{space_id}_*.jpg` di folder itu (timpa); buat folder `captures/` otomatis kalau belum ada (`os.makedirs(exist_ok=True)`); return path relatif buat disimpan di `snapshot_url` (contoh: `/captures/SPACE-01_20260717153000.jpg`)
- `capture_and_detect()` — di akhir proses (setelah voting), panggil `_draw_annotations` pada frame shot yang menghasilkan plat pemenang (atau frame terakhir kalau tidak ada plat terdeteksi sama sekali), lalu `_save_capture`. Return dict ditambah key `"snapshot_url"`.

**`backend/main.py`**
- Endpoint `POST /api/parking/capture/{slot}` (sudah ada) — tambah: set `session.snapshot_url = result["snapshot_url"]` sebelum `db.commit()`.
- Tambah mount static files: `from fastapi.staticfiles import StaticFiles` lalu `app.mount("/captures", StaticFiles(directory="captures"), name="captures")`. Folder `captures/` dibuat relatif ke working directory backend (sejajar `main.py`).

**`admin_dashboard/src/components/LiveDashboard.jsx`**
- Di bawah tiap `<img>` live stream slot, tambah `<img src={API + session.snapshot_url}>` kalau ada sesi aktif dengan `snapshot_url` terisi di slot itu. Data `snapshot_url` sudah ikut di response `/api/parking/active` (field existing di `to_dict()`), tidak perlu endpoint atau polling baru.
- Ubah `onError` pada `<img>` live stream: alih-alih mematikan gambar permanen, retry otomatis tiap 3 detik dengan cache-bust query param (`?t=timestamp`), supaya stream reconnect sendiri setelah capture menang akses CAM.

**`admin_dashboard/src/components/HistoryDashboard.jsx`**
- Tambah kolom "Foto" di tabel — tombol kecil (misal ikon kamera), `onClick` buka `Modal` (Ant Design) menampilkan `<img src={API + record.snapshot_url}>`. Kalau `record.snapshot_url` null/kosong, tombol disabled.

### Error Handling

- CAM tidak reachable saat capture → `capture_and_detect` sudah retry per-shot (logic existing); kalau gagal total, `result["success"] = False`, tidak ada frame untuk disimpan, `snapshot_url` tetap null, session tetap ACTIVE tanpa plate_number.
- Gagal tulis file ke disk (disk penuh/permission) → catch exception, log ke console, endpoint tetap return hasil deteksi JSON ke ESP32 tanpa error 500, `snapshot_url` tidak terisi.
- Folder `captures/` belum ada saat startup → dibuat otomatis saat pertama kali `_save_capture` dipanggil.

### Testing

- Manual: panggil `capture_and_detect(cam_ip)` langsung dari Python REPL dengan CAM yang menyala, cek file muncul di `backend/captures/` dengan bounding box tergambar.
- Endpoint: `curl -X POST http://localhost:8000/api/parking/capture/1` saat ada session ACTIVE di slot 1, cek response mengandung `plate_number` dan `snapshot_url`; cek DB session ter-update.
- Dashboard Live: RFID tap → foto muncul di bawah live stream slot terkait dalam ~15 detik.
- Dashboard History: exit session yang punya foto, cek foto masih bisa dibuka di modal History setelah pindah ke `ParkingLog`.

## Bagian 2: Card Discipline + Grace Period Exit

### Alur Logic

**Check-in (RFID slot 1 atau slot 2, endpoint `PUT /api/parking/register-card`):**
1. Cek dulu: apakah `card_uid` ini punya session dengan `status == "ACTIVE"` di parking_space_id manapun (termasuk slot yang sama)?
   - **Ya** → tolak dengan HTTP 409, tidak ada perubahan DB. ESP32 tampilkan LCD "Kartu sudah parkir".
   - **Tidak** → lanjut proses existing (join session WAITING kalau ada, atau buat session ACTIVE baru).

**Exit (RFID EXIT, endpoint `POST /api/parking/exit`):**
1. Cek: apakah `card_uid` ini punya session `status == "ACTIVE"`?
   - **Tidak ada** → kartu belum pernah tap di slot manapun (skenario: batal parkir). Langsung sukses, `total_fare = 0`, tidak membuat `ParkingLog` (tidak ada apa pun untuk dicatat).
   - **Ada** → hitung `elapsed_minutes` dari `entry_time` sampai sekarang.
     - `elapsed_minutes < GRACE_MINUTES` (5 menit, constant existing) → `total_fare = 0`, `payment_method = "FREE_EXIT"`, tetap buat `ParkingLog` (tercatat di History dengan fare Rp 0), session dihapus dari `ActiveParking`.
     - `elapsed_minutes >= GRACE_MINUTES` → logic existing tidak berubah: hitung fare per jam, potong saldo user, buat `ParkingLog`, hapus session.

### Perubahan Backend (`backend/main.py`)

**`register_card()`** — tambah guard di awal fungsi, sebelum query session WAITING/ACTIVE untuk slot yang di-request:
```python
active_elsewhere = db.query(ActiveParking).filter(
    ActiveParking.card_uid == req.card_uid,
    ActiveParking.status == "ACTIVE",
).first()
if active_elsewhere:
    raise HTTPException(409, "Card already parked")
```

**`process_exit()`** — restrukturisasi urutan cek:
```python
session = db.query(ActiveParking).filter(
    ActiveParking.card_uid == req.card_uid, ActiveParking.status == "ACTIVE",
).first()

if not session:
    return ExitResponse(success=True, message="Exit — no active session", total_fare=0)

now = datetime.now(timezone.utc)
entry = session.entry_time.replace(tzinfo=timezone.utc) if session.entry_time.tzinfo is None else session.entry_time
elapsed_min = (now - entry).total_seconds() / 60.0

if elapsed_min < GRACE_MINUTES:
    fare = 0
    payment_method = "FREE_EXIT"
    bal_before = bal_after = (user.balance if user else 0)
else:
    dur_h = round((now - entry).total_seconds() / 3600.0, 2)
    fare = max(int(dur_h * FARE_PER_HOUR), FARE_PER_HOUR)
    payment_method = "DUMMY_BALANCE"
    bal_before = user.balance if user else 0
    bal_after = max(bal_before - fare, 0) if user else 0
    if user:
        user.balance = bal_after
        user.last_seen = now

log = ParkingLog(
    ..., total_fare=fare, payment_method=payment_method,
    balance_before=bal_before, balance_after=bal_after, forced_billing=False,
)
db.add(log)
db.delete(session)
db.commit()
```

Tidak ada constant baru — `GRACE_MINUTES` (=5) yang sudah ada dipakai ulang untuk threshold ini.

### Perubahan ESP32 (`ARDUINO_TEST.ino`)

**`checkSlotRFID()` / handler hasil `postRegisterCard`** — tambah penanganan HTTP 409:
```cpp
if (code == 409) {
  lcdShow("Kartu sudah", "parkir");
  delay(2000);
  state = STATE_IDLE;
  lcdShow("Tap kartu", "untuk parkir");
  return;
}
```
Ditempatkan sebelum/di samping pengecekan `code == 200` yang sudah ada di `postRegisterCard`.

**`postExit()`** — tampilan LCD dibedakan berdasarkan `total_fare` di response:
```cpp
int fare = r["total_fare"] | 0;
if (fare == 0) {
  lcdShow("Keluar gratis", "Terima kasih");
} else {
  // tampilan existing: "Tarif: Rp xxx,- — Selamat jalan!"
}
```

### Error Handling

- Kartu ditolak check-in (409) tidak mengubah state ESP32 selain balik ke IDLE — tidak ada session yang tersentuh di DB.
- Exit tanpa session aktif tidak membuat `ParkingLog` — tidak ada jejak di History untuk kejadian "batal parkir", sesuai perilaku sebelum fitur ini (tidak ada regresi).
- Race condition (dua RFID tap hampir bersamaan untuk kartu yang sama di slot berbeda) — ditangani oleh urutan commit DB SQLAlchemy per-request; kemungkinan kecil dan tidak butuh locking khusus untuk skala demo/skripsi ini.

### Testing

- Tap kartu di slot 1 → ACTIVE. Tap kartu yang sama di slot 2 → harus 409, LCD "Kartu sudah parkir", slot 2 tidak berubah.
- Tap kartu di slot 1 → ACTIVE. Tap kartu yang sama lagi di slot 1 → harus 409 juga (tidak bisa re-register di slot sendiri).
- Tap RFID EXIT dengan kartu yang belum pernah tap di slot manapun → sukses, `total_fare: 0`, cek tidak ada row baru di `ParkingLog`.
- Tap kartu di slot 1, langsung (< 5 menit) tap RFID EXIT → sukses, `total_fare: 0`, cek ada row baru di `ParkingLog` dengan `total_fare = 0` dan `payment_method = "FREE_EXIT"`.
- Tap kartu di slot 1, tunggu lebih dari 5 menit (atau ubah `entry_time` manual di DB untuk simulasi), tap RFID EXIT → fare dihitung normal seperti sebelumnya (regression check).
