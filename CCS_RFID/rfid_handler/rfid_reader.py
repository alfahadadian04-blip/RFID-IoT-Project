import serial
import requests
import time
import re

# CONFIGURATION
ARDUINO_PORT = 'COM21'
BAUD_RATE = 9600
DJANGO_URL = 'http://127.0.0.1:8000'

def main():
    print("=" * 50)
    print("SIMPLE RFID ATTENDANCE READER")
    print("=" * 50)
    
    # Connect to Arduino
    try:
        ser = serial.Serial(ARDUINO_PORT, BAUD_RATE, timeout=1)
        time.sleep(2)
        print(f"Connected to Arduino on {ARDUINO_PORT}")
    except Exception as e:
        print(f"ERROR: Cannot open {ARDUINO_PORT}: {e}")
        return
    
    # Get active session
    print("Checking for active session...")
    try:
        resp = requests.get(f'{DJANGO_URL}/api/get-active-session/', timeout=2)
        data = resp.json()
        if not data.get('has_active_session'):
            print("No active session. Teacher must start a class first.")
            return
        session_id = data.get('session_id')
        print(f"Active session found! ID: {session_id}")
    except Exception as e:
        print(f"Cannot connect to Django: {e}")
        return
    
    print("\nReady! Tap RFID cards to record attendance.\n")
    
    # Main loop
    while True:
        if ser.in_waiting:
            line = ser.readline().decode('utf-8').strip()
            print(f"RAW: {line}")
            
            # Look for UID pattern (hex numbers with spaces)
            match = re.search(r'([0-9A-F]{2} [0-9A-F]{2} [0-9A-F]{2} [0-9A-F]{2})', line)
            if match:
                rfid_tag = match.group(1)
                print(f"TAG FOUND: {rfid_tag}")
                
                # Send to Django
                try:
                    response = requests.post(
                        f'{DJANGO_URL}/record-attendance/',
                        json={
                            'rfid_tag': rfid_tag,
                            'session_id': session_id
                        },
                        timeout=2
                    )
                    
                    if response.status_code == 200:
                        result = response.json()
                        print(f"✅ {result.get('message', 'Attendance recorded!')}")
                    else:
                        error = response.json()
                        print(f"❌ {error.get('error', 'Unknown error')}")
                except Exception as e:
                    print(f"❌ Error sending: {e}")
        
        time.sleep(0.05)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nShutting down...")