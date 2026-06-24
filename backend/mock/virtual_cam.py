"""
STOPBAY v2.0 - Virtual ESP32-CAM Simulator
Auto-send dummy plate to backend (simulate ESP32-CAM behavior).

Usage:
  python virtual_cam.py                    # sequential plates, 15s interval
  python virtual_cam.py --interval 5        # 5 second interval
  python virtual_cam.py --random            # random plates
  python virtual_cam.py --single "B 999 X"  # send one plate and exit

Target: POST /api/parking/space-occupied
"""

import requests, random, time, sys, os, argparse
from datetime import datetime
from colorama import init, Fore, Style

init(autoreset=True)

# ============================================================
# CONFIG
# ============================================================
API_BASE = os.getenv("STOPBAY_API", "http://localhost:8000")
PARKING_SPACE = "SPACE-01"

PLATES_SEQ = [
    "B 1234 ABC", "D 5678 XYZ", "L 9012 EFG", "F 3456 HIJ",
    "N 7890 KLM", "AE 1122 AB", "AB 3344 CD", "H 5566 EF",
    "T 7788 GH", "W 9900 IJ", "B 2468 LMN", "D 1357 OPQ",
]

PLATES_RANDOM = [
    "B 1111 AB", "B 2222 CD", "D 3333 EF", "D 4444 GH",
    "L 5555 IJ", "L 6666 KL", "F 7777 MN", "F 8888 OP",
    "N 9999 QR", "N 0000 ST", "H 1212 UV", "H 3434 WX",
    "T 5656 YZ", "T 7878 AA", "W 9090 BB", "W 1212 CC",
]


def send_plate(plate, space):
    """Send plate detection to backend."""
    try:
        r = requests.post(
            f"{API_BASE}/api/parking/space-occupied",
            json={"plate_number": plate, "parking_space_id": space, "space_label": "SLOT_1"},
            timeout=5,
        )
        ts = datetime.now().strftime("%H:%M:%S")
        if r.status_code == 200:
            print(f"{Fore.GREEN}[{ts}] [CAM] Sent: {plate} -> OK")
            return True
        else:
            print(f"{Fore.RED}[{ts}] [CAM] Sent: {plate} -> FAIL ({r.status_code})")
            return False
    except Exception as e:
        ts = datetime.now().strftime("%H:%M:%S")
        print(f"{Fore.RED}[{ts}] [CAM] Error: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description="STOPBAY Virtual ESP32-CAM")
    parser.add_argument("--interval", type=int, default=15, help="Seconds between sends (default: 15)")
    parser.add_argument("--random", action="store_true", help="Use random plates instead of sequential")
    parser.add_argument("--single", type=str, help="Send one plate and exit")
    parser.add_argument("--space", type=str, default=PARKING_SPACE, help="Parking space ID")
    args = parser.parse_args()

    # Single shot mode
    if args.single:
        print(f"{Fore.GREEN}Virtual ESP32-CAM - Single Shot")
        send_plate(args.single.upper(), args.space)
        return

    plates = PLATES_RANDOM if args.random else PLATES_SEQ
    idx = 0
    mode = "random" if args.random else "sequential"

    print(f"{Fore.GREEN}{'='*50}")
    print(f"  Virtual ESP32-CAM - Auto Plate Sender")
    print(f"  STOPBAY v2.0")
    print(f"{'='*50}")
    print(f"  API     : {API_BASE}")
    print(f"  Space   : {args.space}")
    print(f"  Interval: {args.interval}s")
    print(f"  Mode    : {mode}")
    print(f"  Plates  : {len(plates)} available")
    print(f"{Fore.GREEN}{'='*50}")
    print(f"  Press Ctrl+C to stop\n")

    sent_ok = 0
    sent_fail = 0
    start_time = time.time()

    try:
        while True:
            plate = random.choice(plates) if args.random else plates[idx % len(plates)]
            if send_plate(plate, args.space):
                sent_ok += 1
            else:
                sent_fail += 1
            idx += 1
            time.sleep(args.interval)
    except KeyboardInterrupt:
        elapsed = int(time.time() - start_time)
        m, s = divmod(elapsed, 60)
        print(f"\n{Fore.YELLOW}{'='*50}")
        print(f"  Virtual CAM stopped")
        print(f"  Runtime : {m}m {s}s")
        print(f"  Sent    : {sent_ok} OK, {sent_fail} FAIL")
        print(f"{'='*50}")


if __name__ == "__main__":
    main()
