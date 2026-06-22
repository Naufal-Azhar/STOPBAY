## Persiapan Jalur Daya (Power Rail) Breadboard

Sebelum mencolok komponen lain, mari buat "jalur listrik" utama di bagian pinggir breadboard (garis merah untuk positif, garis biru/hitam untuk negatif/GND).

1. Colok ESP32 Utama ke breadboard.
2. Hubungkan pin GND ESP32 ke jalur Minus (-) breadboard.
3. Hubungkan pin VIN / 5V ESP32 ke jalur Plus (+) breadboard (ini akan menjadi jalur 5V).
4. Hubungkan pin 3V3 ESP32 ke baris kosong lain di breadboard jika membutuhkan tegangan 3.3V (khusus untuk RFID).

## Panduan Wiring Komponen

Berikut adalah tabel pemetaan pin dari setiap modul ke ESP32 Utama. Hubungkan menggunakan kabel jumper melalui breadboard:

### 1. Wiring LCD I2C (Penanda Registrasi & Pembayaran)

Modul I2C pada LCD hanya membutuhkan 4 kabel. Kita menggunakan pin I2C standar pada ESP32.

| Pin LCD I2C | Hubungkan ke (ESP32 / Breadboard) | Keterangan |
|-------------|-----------------------------------|------------|
| GND | Jalur Minus (-) Breadboard | Ground bersama |
| VCC | Jalur Plus (+) Breadboard (5V) | LCD butuh 5V agar kontrasnya terang |
| SDA | GPIO 21 | Jalur Data I2C |
| SCL | GPIO 22 | Jalur Clock I2C |

### 2. Wiring RFID Reader RC522 (Alat Registrasi)

RFID menggunakan komunikasi SPI. Karena pin GPIO 22 sudah dipakai oleh LCD, maka pin RST pada RFID kita pindahkan ke GPIO 4.

| Pin RFID RC522 | Hubungkan ke (ESP32 / Breadboard) | Keterangan |
|----------------|-----------------------------------|------------|
| 3.3V | Pin 3V3 ESP32 | **Jangan ke 5V!** RFID bisa terbakar |
| RST | GPIO 4 | Reset Pin (Sudah disesuaikan) |
| GND | Jalur Minus (-) Breadboard | Ground bersama |
| MISO | GPIO 19 | SPI Master In Slave Out |
| MOSI | GPIO 23 | SPI Master Out Slave In |
| SCK | GPIO 18 | SPI Clock |
| SDA (SS) | GPIO 5 | SPI Chip Select |

### 3. Wiring ESP32-CAM (Kamera Pemindai Plat)

Untuk fase uji coba ini, ESP32-CAM akan mengirimkan data teks (simulasi hasil OCR) ke ESP32 Utama melalui komunikasi Serial2 (RX2/TX2).

| Pin ESP32-CAM | Hubungkan ke (ESP32 / Breadboard) | Keterangan |
|---------------|-----------------------------------|------------|
| 5V | Jalur Plus (+) Breadboard (5V) | ESP32-CAM sangat butuh daya stabil |
| GND | Jalur Minus (-) Breadboard | Ground bersama (**Wajib terhubung!**) |
| TX / U0T | GPIO 16 (RX2) ESP32 Utama | Data keluar dari CAM masuk ke RX ESP32 |
| RX / U0R | GPIO 17 (TX2) ESP32 Utama | Data keluar dari ESP32 masuk ke RX CAM |
