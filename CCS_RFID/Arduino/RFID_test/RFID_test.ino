#include <SPI.h>
#include <MFRC522.h>

#define SS_PIN 10
#define RST_PIN 9

MFRC522 rfid(SS_PIN, RST_PIN);

void setup() {
  Serial.begin(9600);
  SPI.begin();
  rfid.PCD_Init();
  Serial.println("RFID Reader Ready");
}

void loop() {
  // Check if a new card is present
  if (!rfid.PICC_IsNewCardPresent()) {
    return;
  }
  
  // Try to read the card
  if (!rfid.PICC_ReadCardSerial()) {
    return;
  }
  
  // Read the UID
  String rfidTag = "";
  for (byte i = 0; i < rfid.uid.size; i++) {
    rfidTag += String(rfid.uid.uidByte[i] < 0x10 ? "0" : "");
    rfidTag += String(rfid.uid.uidByte[i], HEX);
    if (i < rfid.uid.size - 1) {
      rfidTag += " ";
    }
  }
  rfidTag.toUpperCase();
  
  // Send to serial
  Serial.println(rfidTag);
  
  // Halt PICC
  rfid.PICC_HaltA();
  rfid.PCD_StopCrypto1();
  
  delay(1000); // Prevent multiple reads
}