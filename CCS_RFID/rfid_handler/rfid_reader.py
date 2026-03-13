#!/usr/bin/env python
"""
RFID Reader - Connects Arduino to Django
Now automatically checks for pending registrations!
"""

import serial
import requests
import time
import sys

ARDUINO_PORT = 'COM21'
BAUD_RATE = 9600
DJANGO_URL = 'http://127.0.0.1:8000'

def main():
    print("=" * 50)
    print("🤖 RFID Reader Starting...")
    print(f"Arduino Port: {ARDUINO_PORT}")
    print("Mode: Automatic (checks for pending registrations)")
    print("=" * 50)
    
    try:
        ser = serial.Serial(ARDUINO_PORT, BAUD_RATE, timeout=1)
        time.sleep(2)
        print(f"✅ Connected to Arduino on {ARDUINO_PORT}")
        print("📇 Waiting for RFID cards...")
        
        while True:
            if ser.in_waiting > 0:
                rfid_data = ser.readline().decode('utf-8').strip()
                
                if rfid_data:
                    print(f"\n📇 RFID Detected: {rfid_data}")
                    
                    # First, check if anyone is waiting for RFID
                    try:
                        pending_response = requests.get(
                            f'{DJANGO_URL}/api/pending-rfid/check/',
                            timeout=2
                        )
                        pending = pending_response.json()
                        
                        if pending.get('waiting'):
                            # Someone is waiting! Send with student_id
                            student_id = pending['student_id']
                            print(f"   Found pending registration for: {pending['student_name']} (ID: {student_id})")
                            
                            response = requests.post(
                                f'{DJANGO_URL}/api/rfid/',
                                json={
                                    'rfid_tag': rfid_data,
                                    'student_id': student_id
                                },
                                timeout=2
                            )
                            
                            if response.status_code == 200:
                                result = response.json()
                                print(f"✅ RFID registered for {result['name']}!")
                                print(f"🎉 Registration complete!")
                            else:
                                print(f"❌ Error: {response.json()}")
                        else:
                            # No one waiting - normal attendance mode
                            response = requests.post(
                                f'{DJANGO_URL}/api/rfid/',
                                json={'rfid_tag': rfid_data},
                                timeout=2
                            )
                            
                            if response.status_code == 200:
                                result = response.json()
                                print(f"✅ Attendance recorded for {result['name']}")
                            else:
                                print(f"❌ Unknown card: {rfid_data}")
                                
                    except requests.exceptions.ConnectionError:
                        print(f"❌ Cannot connect to Django - is server running?")
                    except Exception as e:
                        print(f"❌ Error: {e}")
            
            time.sleep(0.1)
            
    except serial.SerialException as e:
        print(f"❌ Cannot open serial port {ARDUINO_PORT}")
        print(f"   Error: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n👋 Shutting down...")
        ser.close()
        sys.exit(0)

if __name__ == "__main__":
    main()