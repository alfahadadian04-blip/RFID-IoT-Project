import serial
import serial.tools.list_ports
import requests
import time
import re
import threading

# CONFIGURATION
BAUD_RATE = 9600
DJANGO_URL = 'http://127.0.0.1:8000'
PENDING_TIMEOUT = 300  # 5 minutes timeout for pending registration

# Auto-detect Arduino port
def find_arduino_port():
    """Automatically find and return the Arduino port"""
    print("Scanning for Arduino...")
    ports = serial.tools.list_ports.comports()
    
    for port in ports:
        print(f"  Checking: {port.device} - {port.description}")
        if 'Arduino' in port.description or 'USB Serial' in port.description:
            print(f"✓ Found Arduino on {port.device}")
            return port.device
    
    # If no Arduino found, try common ports
    common_ports = ['COM3', 'COM4', 'COM5', 'COM6', 'COM7', 'COM8', 'COM9', 'COM10']
    print("Trying common ports...")
    for port in common_ports:
        try:
            test_serial = serial.Serial(port, BAUD_RATE, timeout=1)
            test_serial.close()
            print(f"✓ Found Arduino on {port}")
            return port
        except:
            continue
    
    print("❌ Could not find Arduino. Please check connection.")
    return None

# Get Arduino port automatically
ARDUINO_PORT = find_arduino_port()
if ARDUINO_PORT is None:
    print("Please connect your Arduino and try again.")
    exit(1)

print(f"Using port: {ARDUINO_PORT}")

def get_active_session():
    """Check if there's an active class session"""
    try:
        response = requests.get(f'{DJANGO_URL}/api/get-active-session/', timeout=2)
        if response.status_code == 200:
            data = response.json()
            if data.get('has_active_session'):
                return data.get('session_id')
    except Exception:
        pass
    return None

def check_pending_registration():
    """Check if there's a student waiting for RFID registration"""
    try:
        response = requests.get(f'{DJANGO_URL}/api/pending-rfid/check/', timeout=2)
        if response.status_code == 200:
            data = response.json()
            if data.get('waiting'):
                return data.get('student_id'), data.get('student_name'), data.get('expires_at')
    except Exception:
        pass
    return None, None, None

def send_rfid_to_receive_endpoint(rfid_tag):
    """Send RFID tag to receive endpoint for claiming existing accounts"""
    try:
        requests.post(
            f'{DJANGO_URL}/api/receive-rfid/',
            json={'rfid_tag': rfid_tag},
            timeout=1
        )
    except:
        pass

def clear_pending_registration(student_id=None):
    """Clear pending registration"""
    try:
        data = {'student_id': student_id} if student_id else {}
        requests.post(
            f'{DJANGO_URL}/api/clear-pending-rfid/',
            json=data,
            timeout=2
        )
    except:
        pass

def main():
    print("=" * 60)
    print("RFID READER - Registration & Attendance (Auto-switching)")
    print("=" * 60)
    
    # Connect to Arduino
    try:
        ser = serial.Serial(ARDUINO_PORT, BAUD_RATE, timeout=1)
        print(f"Connected to Arduino on {ARDUINO_PORT}")
    except Exception as e:
        print(f"ERROR: Cannot open {ARDUINO_PORT}: {e}")
        return
    
    current_session_id = None
    last_session_check = 0
    pending_start_time = None
    current_pending_student = None
    
    print("\n✓ Ready for BOTH student registration AND attendance")
    print("✓ Will automatically detect which mode to use\n")
    
    while True:
        # Check for active session every 2 seconds
        now = time.time()
        if now - last_session_check > 2:
            last_session_check = now
            new_session = get_active_session()
            if new_session != current_session_id:
                if new_session:
                    print(f"✅ ACTIVE SESSION DETECTED! ID: {new_session}")
                    print("   → Attendance mode ACTIVE")
                    current_session_id = new_session
                elif current_session_id:
                    print(f"⚠️ Session {current_session_id} ended.")
                    print("   → Back to waiting for registration or new session")
                    current_session_id = None
        
        # Check for pending registration timeout
        if pending_start_time and (time.time() - pending_start_time) > PENDING_TIMEOUT:
            print(f"⏰ Pending registration timed out after {PENDING_TIMEOUT} seconds")
            if current_pending_student:
                clear_pending_registration(current_pending_student)
            pending_start_time = None
            current_pending_student = None
        
        # Read line from Arduino
        line = ser.readline().decode('utf-8').strip()
        
        if not line:
            continue
        
        # Look for UID pattern
        match = re.search(r'([0-9A-F]{2} [0-9A-F]{2} [0-9A-F]{2} [0-9A-F]{2})', line)
        if not match:
            continue
        
        rfid_tag = match.group(1)
        print(f"\n📇 Card tapped: {rfid_tag}")
        
        # Send RFID to receive endpoint for claiming existing accounts
        send_rfid_to_receive_endpoint(rfid_tag)
        
        # ALWAYS check for pending registration FIRST (new user registration)
        student_id, student_name, expires_at = check_pending_registration()
        
        if student_id:
            if not pending_start_time:
                pending_start_time = time.time()
                current_pending_student = student_id
                print(f"   📝 PENDING REGISTRATION detected for: {student_name}")
                print(f"   ⏰ This will timeout in {PENDING_TIMEOUT} seconds")
            
            try:
                response = requests.post(
                    f'{DJANGO_URL}/api/rfid/',
                    json={'rfid_tag': rfid_tag, 'student_id': student_id},
                    timeout=2
                )
                if response.status_code == 200:
                    print(f"   ✅ RFID REGISTERED for {student_name}!")
                    print(f"   → Account created! You can now login.")
                    # Clear the pending registration after successful registration
                    clear_pending_registration(student_id)
                    pending_start_time = None
                    current_pending_student = None
                else:
                    error_msg = response.json().get('error', 'Unknown error')
                    print(f"   ❌ Registration error: {error_msg}")
                    # If error, still clear pending to allow retry
                    if "already registered" in error_msg:
                        clear_pending_registration(student_id)
                        pending_start_time = None
                        current_pending_student = None
            except Exception as e:
                print(f"   ❌ Error: {e}")
            continue  # Skip attendance - this was registration
        
        # Reset pending timeout if no pending registration
        if pending_start_time:
            pending_start_time = None
            current_pending_student = None
        
        # If no pending registration, check for attendance (active session)
        if current_session_id:
            print(f"   → Attendance mode: Recording to session {current_session_id}")
            try:
                response = requests.post(
                    f'{DJANGO_URL}/record-attendance/',
                    json={'rfid_tag': rfid_tag, 'session_id': current_session_id},
                    timeout=2
                )
                if response.status_code == 200:
                    result = response.json()
                    print(f"   ✅ {result.get('message')}")
                else:
                    error = response.json().get('error')
                    print(f"   ❌ {error}")
            except Exception as e:
                print(f"   ❌ Error: {e}")
            continue
        
        # No pending registration and no active session
        # Check if card is registered (info only)
        try:
            check_user_response = requests.get(
                f'{DJANGO_URL}/api/check-user-by-rfid/',
                params={'rfid_tag': rfid_tag},
                timeout=2
            )
            if check_user_response.status_code == 200:
                user_data = check_user_response.json()
                if user_data.get('exists'):
                    print(f"   ℹ️ Card belongs to: {user_data.get('name')}")
                    print(f"   ⏳ No active session. Teacher must start a class for attendance.")
                else:
                    print(f"   ❌ Card not registered.")
                    print(f"   → To register: Fill out the registration form first, then tap your card.")
        except:
            print(f"   ⏳ No active session and no pending registration.")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n👋 Shutting down...")