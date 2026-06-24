"""
STOPBAY v2.0 - Virtual ESP32 Simulator
Simulate Main ESP32 behavior for testing without hardware.

Commands:
  p          - Inject dummy plate (car detected)
  c          - Tap random card from existing users
  u <UID>    - Tap specific card UID
  f          - Trigger forced billing on current session
  e          - Simulate exit (tap active card)
  s          - Show current state + LCD display
  h          - Show this help
  q          - Quit

Usage:
  cd backend/mock
  pip install -r requirements.txt
  python virtual_esp32.py
"""

import requests, random, time, sys, os, json
from datetime import datetime
from colorama import init, Fore, Style

init(autoreset=True)

# ============================================================
# CONFIG
# ============================================================
API_BASE = os.getenv("STOPBAY_API", "http://localhost:8000")
PARKING_SPACE = "SPACE-01"
SPACE_LABEL = "SLOT_1"

PLATES = ["B 1234 ABC", "D 5678 XYZ", "L 9012 EFG", "F 3456 HIJ", "N 7890 KLM",
          "AE 1234 ABC", "AB 5678 XYZ", "H 9012 EFG", "T 3456 HIJ", "W 7890 KLM"]

# ============================================================
# STATE
# ============================================================
class VirtualESP32:
    def __init__(self):
        self.state = "IDLE"
        self.plate = ""
        self.card_uid = ""
        self.car_detected_time = 0
        self.session_start_time = 0

    def api(self, method, path, data=None):
        try:
            url = f"{API_BASE}{path}"
            if method == "POST":
                r = requests.post(url, json=data, timeout=5)
            elif method == "PUT":
                r = requests.put(url, json=data, timeout=5)
            else:
                r = requests.get(url, timeout=5)
            return r.status_code, r.json() if r.text else {}
        except Exception as e:
            return 0, {"error": str(e)}

    def plate_injected(self, plate):
        code, resp = self.api("POST", "/api/parking/space-occupied", {
            "plate_number": plate, "parking_space_id": PARKING_SPACE, "space_label": SPACE_LABEL
        })
        if code == 200:
            print(f"{Fore.GREEN}[HTTP] POST space-occupied -> {code} OK")
            print(f"       expiry: {resp.get('expiry_time', 'N/A')}")
            return True
        print(f"{Fore.RED}[HTTP] POST space-occupied -> {code} FAIL: {resp}")
        return False

    def card_tapped(self, uid):
        code, resp = self.api("PUT", "/api/parking/register-card", {
            "card_uid": uid, "parking_space_id": PARKING_SPACE,
            "plate_number": self.plate, "space_label": SPACE_LABEL
        })
        if code == 200:
            name = resp.get("user_name", "?")
            bal = resp.get("balance", 0)
            print(f"{Fore.GREEN}[HTTP] PUT register-card -> {code} OK")
            print(f"       user: {name} | balance: Rp {bal:,}")
            return True
        print(f"{Fore.RED}[HTTP] PUT register-card -> {code} FAIL: {resp}")
        return False

    def forced_billing(self):
        code, resp = self.api("POST", "/api/parking/forced-billing", {
            "plate_number": self.plate, "parking_space_id": PARKING_SPACE
        })
        if code == 200:
            fare = resp.get("total_fare", 2000)
            print(f"{Fore.YELLOW}[HTTP] POST forced-billing -> {code} OK (fare: Rp {fare:,})")
            return True
        print(f"{Fore.RED}[HTTP] POST forced-billing -> {code} FAIL: {resp}")
        return False

    def process_exit(self, uid):
        code, resp = self.api("POST", "/api/parking/exit", {"card_uid": uid})
        if code == 200:
            fare = resp.get("total_fare", 0)
            dur = resp.get("duration_hours", 0)
            print(f"{Fore.GREEN}[HTTP] POST exit -> {code} OK")
            print(f"       fare: Rp {fare:,} | duration: {dur}h")
            return True
        print(f"{Fore.RED}[HTTP] POST exit -> {code} FAIL: {resp}")
        return False

    def get_random_uid(self):
        try:
            r = requests.get(f"{API_BASE}/api/users", timeout=5)
            if r.status_code == 200:
                users = r.json().get("data", [])
                if users:
                    return random.choice(users)["card_uid"]
        except:
            pass
        return "".join(random.choices("0123456789ABCDEF", k=8))

    def lcd(self):
        if self.state == "IDLE":
            print(f"  {Fore.CYAN}LCD: [STOPBAY Ready] [Waiting car...] [Slot 1: Ready]")
        elif self.state == "WAITING_CARD":
            elapsed = int(time.time() - self.car_detected_time)
            print(f"  {Fore.CYAN}LCD: [Car Detected!] [Plate: {self.plate}] [Tap KTP/KTM...] [{elapsed}s / 300s]")
        elif self.state == "ACTIVE":
            elapsed = int(time.time() - self.session_start_time)
            h, m, s = elapsed // 3600, (elapsed % 3600) // 60, elapsed % 60
            fare = max(int((elapsed / 3600.0) * 2000), 2000)
            print(f"  {Fore.CYAN}LCD: [ACTIVE SESSION] [Plate: {self.plate}] [{h:02d}:{m:02d}:{s:02d} | Rp {fare}] [Card: {self.card_uid[:8]}]")
        elif self.state == "FORCED_BILLING":
            print(f"  {Fore.YELLOW}LCD: [TIME'S UP!] [No card tapped] [Forced billing] [Plate: {self.plate}]")

    def status(self):
        print(f"\n{Fore.YELLOW}{'='*50}")
        print(f"  State : {self.state}")
        print(f"  Plate : {self.plate or '---'}")
        print(f"  Card  : {self.card_uid or '---'}")
        self.lcd()
        print(f"{Fore.YELLOW}{'='*50}\n")


# ============================================================
# MAIN
# ============================================================
def main():
    print(f"{Fore.GREEN}{'='*50}")
    print(f"  Virtual ESP32 - Main Controller Sim")
    print(f"  STOPBAY v2.0")
    print(f"{'='*50}")
    print(f"  API: {API_BASE}")
    print(f"  Space: {PARKING_SPACE}")
    print(f"  Commands: p=detect c=tap u=<UID> f=force e=exit s=status h=help q=quit")
    print(f"{Fore.GREEN}{'='*50}\n")

    virt = VirtualESP32()

    while True:
        try:
            cmd = input(f"{Fore.WHITE}> ").strip()
        except (EOFError, KeyboardInterrupt):
            print(f"\n{Fore.YELLOW}[Virtual ESP32] Bye!")
            break

        if not cmd:
            continue

        parts = cmd.split()
        action = parts[0].lower()

        if action == "q":
            print(f"{Fore.YELLOW}[Virtual ESP32] Bye!")
            break

        elif action == "h":
            print(f"\n{Fore.WHITE}Commands:")
            print(f"  p          Inject dummy plate (car detected)")
            print(f"  c          Tap random card")
            print(f"  u <UID>    Tap specific card UID")
            print(f"  f          Trigger forced billing")
            print(f"  e          Simulate exit")
            print(f"  s          Show state + LCD")
            print(f"  h          Show this help")
            print(f"  q          Quit\n")

        elif action == "s":
            virt.status()

        elif action == "p":
            if virt.state == "IDLE" or virt.state == "FORCED_BILLING":
                plate = random.choice(PLATES)
                print(f"\n{CAM} Detected plate: {plate}")
                if virt.plate_injected(plate):
                    virt.plate = plate
                    virt.state = "WAITING_CARD"
                    virt.car_detected_time = time.time()
                    print(f"{Fore.CYAN}[STATE] IDLE -> WAITING_CARD (5 min timer)")
                virt.status()
            else:
                print(f"{Fore.RED}Cannot detect car - state is {virt.state}")

        elif action == "c":
            uid = virt.get_random_uid()
            print(f"\n{RFID} Random card: {uid}")
            if virt.state == "WAITING_CARD":
                if virt.card_tapped(uid):
                    virt.card_uid = uid
                    virt.state = "ACTIVE"
                    virt.session_start_time = time.time()
                    print(f"{Fore.CYAN}[STATE] WAITING_CARD -> ACTIVE")
                virt.status()
            elif virt.state == "ACTIVE" and uid == virt.card_uid:
                print(f"Exit requested...")
                if virt.process_exit(uid):
                    virt.state = "IDLE"
                    virt.plate = ""
                    virt.card_uid = ""
                    print(f"{Fore.CYAN}[STATE] ACTIVE -> IDLE (exit complete)")
                virt.status()
            else:
                print(f"{Fore.RED}Card tap ignored - invalid state or different card")

        elif action == "u" and len(parts) > 1:
            uid = parts[1].upper()
            print(f"\n{RFID} Card: {uid}")
            if virt.state == "WAITING_CARD":
                if virt.card_tapped(uid):
                    virt.card_uid = uid
                    virt.state = "ACTIVE"
                    virt.session_start_time = time.time()
                    print(f"{Fore.CYAN}[STATE] WAITING_CARD -> ACTIVE")
                virt.status()
            elif virt.state == "ACTIVE":
                if uid == virt.card_uid:
                    print(f"Exit requested...")
                    if virt.process_exit(uid):
                        virt.state = "IDLE"
                        virt.plate = ""
                        virt.card_uid = ""
                        print(f"{Fore.CYAN}[STATE] ACTIVE -> IDLE (exit complete)")
                    virt.status()
                else:
                    print(f"{Fore.RED}Card {uid} is not the active card ({virt.card_uid})")
            else:
                print(f"{Fore.RED}Card tap ignored - state is {virt.state}")

        elif action == "f":
            if virt.state == "WAITING_CARD":
                print(f"\n{Fore.YELLOW}Triggering forced billing...")
                if virt.forced_billing():
                    virt.state = "FORCED_BILLING"
                    print(f"{Fore.CYAN}[STATE] WAITING_CARD -> FORCED_BILLING")
                    print(f"{Fore.YELLOW}Waiting 3 seconds before reset...")
                    time.sleep(3)
                    virt.state = "IDLE"
                    virt.plate = ""
                    virt.card_uid = ""
                    print(f"{Fore.CYAN}[STATE] FORCED_BILLING -> IDLE")
                virt.status()
            else:
                print(f"{Fore.RED}Cannot force billing - state is {virt.state}")

        elif action == "e":
            if virt.state == "ACTIVE" and virt.card_uid:
                print(f"\n{Fore.YELLOW}Processing exit for {virt.card_uid}...")
                if virt.process_exit(virt.card_uid):
                    virt.state = "IDLE"
                    virt.plate = ""
                    virt.card_uid = ""
                    print(f"{Fore.CYAN}[STATE] ACTIVE -> IDLE (exit complete)")
                virt.status()
            else:
                print(f"{Fore.RED}No active session to exit")

        else:
            print(f"{Fore.RED}Unknown command: {action} (type 'h' for help)")

if __name__ == "__main__":
    main()
