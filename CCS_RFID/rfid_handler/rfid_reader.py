import serial
import serial.tools.list_ports
import requests
import time
import re
import threading

# CONFIGURATION
BAUD_RATE = 9600
DJANGO_URL = 'https://CCS.pythonanywhere.com'  # Your live website
PENDING_TIMEOUT = 300

# Auto-detect Arduino port
def find_arduino_port():
    print("Scanning for Arduino...")
    ports = serial.tools.list_ports.comports()
    
    for port in ports:
        print(f"  Checking: {port.device} - {port.description}")
        if 'Arduino' in port.description or 'USB Serial' in port.description:
            print(f"✓ Found Arduino on {port.device}")
            return port.device
    
    print("❌ Could not find Arduino.")
    return None

# Get Arduino port automatically
ARDUINO_PORT = find_arduino_port()
if ARDUINO_PORT is None:
    print("Please connect your Arduino and try again.")
    exit(1)

print(f"Using port: {ARDUINO_PORT}")
ser = None

# Global variables for state
current_pending_student_id = None
current_pending_student_name = None
pending_start_time = None
current_session_id = None
last_session_check = 0

def send_command(cmd):
    """Send command to Arduino"""
    global ser
    if ser:
        try:
            ser.write(f'{cmd}\n'.encode())
        except Exception as e:
            print(f"   ⚠️ Could not send command {cmd}: {e}")

def beep_success():
    """Send command to Arduino to play success beep"""
    send_command("BEEP")

def led_green():
    """Turn on Green LED (success)"""
    send_command("GREEN")

def led_yellow():
    """Turn on Yellow LED (warning - late or 4 absences)"""
    send_command("YELLOW")

def led_red():
    """Turn on Red LED (error)"""
    send_command("RED")

def led_off():
    """Turn off all LEDs"""
    send_command("LEDOFF")

def get_active_session():
    try:
        print("[DEBUG] Checking for active session...")
        response = requests.get(f'{DJANGO_URL}/api/get-active-session/', timeout=3)
        print(f"[DEBUG] Response status: {response.status_code}")
        print(f"[DEBUG] Response text: {response.text}") # This will print the raw response from the server
        
        if response.status_code == 200:
            data = response.json()
            if data.get('has_active_session'):
                print(f"[DEBUG] Session found! ID: {data.get('session_id')}")
                return data.get('session_id')
            else:
                print("[DEBUG] No active session found by the server.")
    except Exception as e:
        print(f"[ERROR] Error checking session: {e}")
    return None

def check_pending_registration():
    """Check if there's a student waiting for RFID registration"""
    global current_pending_student_id, current_pending_student_name, pending_start_time
    
    try:
        response = requests.get(f'{DJANGO_URL}/api/pending-rfid/check/', timeout=10)
        if response.status_code == 200:
            data = response.json()
            if data.get('waiting'):
                student_id = data.get('student_id')
                student_name = data.get('student_name')
                
                # New pending registration detected
                if student_id != current_pending_student_id:
                    current_pending_student_id = student_id
                    current_pending_student_name = student_name
                    pending_start_time = time.time()
                    print(f"\n📝 PENDING REGISTRATION detected for: {student_name}")
                    print(f"   Student ID: {student_id}")
                    print(f"   Please tap the RFID card now!\n")
                return student_id, student_name, data.get('expires_at')
            else:
                # No pending registration
                if current_pending_student_id is not None:
                    print(f"\n⏰ Pending registration cleared or expired.\n")
                    current_pending_student_id = None
                    current_pending_student_name = None
                    pending_start_time = None
    except Exception as e:
        print(f"Error checking pending: {e}")
    return None, None, None

def clear_pending_registration(student_id=None):
    try:
        data = {'student_id': student_id} if student_id else {}
        requests.post(f'{DJANGO_URL}/api/clear-pending-rfid/', json=data, timeout=2)
    except:
        pass

def main():
    global ser, current_session_id, last_session_check
    global current_pending_student_id, current_pending_student_name, pending_start_time
    
    print("=" * 60)
    print("RFID READER - Registration & Attendance (Auto-switching)")
    print(f"Connected to: {DJANGO_URL}")
    print("=" * 60)
    
    try:
        ser = serial.Serial(ARDUINO_PORT, BAUD_RATE, timeout=1)
        print(f"Connected to Arduino on {ARDUINO_PORT}")
    except Exception as e:
        print(f"ERROR: Cannot open {ARDUINO_PORT}: {e}")
        return
    
    print("\n✓ Ready for BOTH student registration AND attendance")
    print("✓ Auto-detects mode based on website state\n")
    
    # Start background thread to check for pending registrations
    def background_check():
        global current_session_id, last_session_check
        while True:
            try:
                # Check for active session every 3 seconds
                now = time.time()
                if now - last_session_check > 3:
                    last_session_check = now
                    new_session = get_active_session()
                    if new_session != current_session_id:
                        if new_session:
                            print(f"\n✅ ACTIVE SESSION DETECTED! ID: {new_session}")
                            print("   → Attendance mode ACTIVE\n")
                        elif current_session_id:
                            print(f"\n⚠️ Session {current_session_id} ended.\n")
                        current_session_id = new_session
                
                # Check for pending registration every 2 seconds
                check_pending_registration()
                
            except Exception as e:
                print(f"Background error: {e}")
            time.sleep(1)
    
    # Start background thread
    bg_thread = threading.Thread(target=background_check, daemon=True)
    bg_thread.start()
    
    while True:
        # Read line from Arduino
        line = ser.readline().decode('utf-8').strip()
        
        # DEBUG: Show raw data received from Arduino
        if line:
            print(f"[DEBUG] Raw from Arduino: '{line}'")
        
        if not line:
            continue
        
        # Look for UID pattern
        match = re.search(r'([0-9A-F]{2} [0-9A-F]{2} [0-9A-F]{2} [0-9A-F]{2})', line, re.IGNORECASE)
        if not match:
            print(f"[DEBUG] No UID pattern found in: '{line}'")
            continue
        
        rfid_tag = match.group(1)
        print(f"\n📇 Card tapped: {rfid_tag}")

        # For Superadmin Add/Change RFID feature
        try:
            receive_response = requests.post(
                f'{DJANGO_URL}/api/receive-rfid/',
                json={'rfid_tag': rfid_tag},
                timeout=2
            )
            if receive_response.status_code == 200:
                print(f"   → Sent to receive-rfid endpoint for manual assignment")
            else:
                print(f"   → receive-rfid response: {receive_response.status_code}")
        except Exception as e:
            print(f"   → Error sending to receive-rfid: {e}")
        
        # PRIORITY 1: Pending registration
        if current_pending_student_id is not None:
            print(f"   → Processing REGISTRATION for student: {current_pending_student_name}")
            try:
                response = requests.post(
                    f'{DJANGO_URL}/api/rfid/',
                    json={'rfid_tag': rfid_tag, 'student_id': current_pending_student_id},
                    timeout=10
                )
                if response.status_code == 200:
                    result = response.json()
                    if result.get('status') == 'success':
                        print(f"   ✅ RFID REGISTERED for {current_pending_student_name}!")
                        beep_success()
                        led_green()  # Green LED for success
                        # Clear pending
                        clear_pending_registration(current_pending_student_id)
                        current_pending_student_id = None
                        current_pending_student_name = None
                        pending_start_time = None
                        # Turn off LED after 2 seconds
                        time.sleep(2)
                        led_off()
                    else:
                        print(f"   ❌ Registration error: {result.get('message')}")
                        led_red()  # Red LED for error
                        time.sleep(2)
                        led_off()
                else:
                    print(f"   ❌ HTTP Error: {response.status_code}")
                    led_red()
                    time.sleep(2)
                    led_off()
            except Exception as e:
                print(f"   ❌ Error: {e}")
                led_red()
                time.sleep(2)
                led_off()
            continue
        
        # PRIORITY 2: Attendance (active session)
        if current_session_id:
            print(f"   → Processing ATTENDANCE for session {current_session_id}")
            try:
                response = requests.post(
                    f'{DJANGO_URL}/record-attendance/',
                    json={'rfid_tag': rfid_tag, 'session_id': current_session_id},
                    timeout=10
                )
                if response.status_code == 200:
                    result = response.json()
                    status = result.get('status')
                    message = result.get('message')
                    print(f"   ✅ {message}")
                    
                    # Check if it's late (based on message or status)
                    if 'late' in message.lower() or status == 'late':
                        led_yellow()  # Yellow LED for late
                    else:
                        led_green()  # Green LED for present on time
                    
                    beep_success()
                    time.sleep(2)
                    led_off()
                else:
                    error = response.json().get('error', 'Unknown error')
                    print(f"   ❌ {error}")
                    led_red()
                    time.sleep(2)
                    led_off()
            except Exception as e:
                print(f"   ❌ Error: {e}")
                led_red()
                time.sleep(2)
                led_off()
            continue
        
        # No pending, no active session
        print(f"   ⏳ No active session and no pending registration.")
        print(f"   → Start a class session OR open registration modal.")
        print(f"   → For Add/Change RFID, click the button on User Management page.\n")
        led_off()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n👋 Shutting down...")
        if ser:
            ser.close()