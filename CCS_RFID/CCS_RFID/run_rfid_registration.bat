@echo off
cd /d C:\Users\ADMIN\Documents\GitHub\RFID-IoT-Project\CCS_RFID
call env\Scripts\activate
python rfid_handler/rfid_reader.py %1
pause