/*
 * Modified MFRC522 DumpInfo for Arduino UNO R4 WiFi
 * This version uses the correct pins for UNO R4
 */

#include <SPI.h>
#include <MFRC522.h>

// UNO R4 pin configuration
#define SS_PIN 10     // SDA/SS pin
#define RST_PIN 9     // Reset pin
#define MOSI_PIN 11   // MOSI pin
#define MISO_PIN 12   // MISO pin
#define SCK_PIN 13    // SCK pin

MFRC522 mfrc522(SS_PIN, RST_PIN);  // Create MFRC522 instance

void setup() {
  Serial.begin(115200);  // Match your Serial Monitor setting
  while (!Serial);        // Wait for Serial Monitor to open (important for UNO R4)
  
  Serial.println("Initializing RFID Reader for UNO R4 WiFi...");
  
  SPI.begin();           // Initialize SPI bus
  mfrc522.PCD_Init();    // Initialize MFRC522
  
  // Show reader version to verify connection
  byte version = mfrc522.PCD_ReadRegister(MFRC522::VersionReg);
  Serial.print("Reader Version: 0x");
  Serial.println(version, HEX);
  
  if (version == 0x00 || version == 0xFF) {
    Serial.println("WARNING: RFID reader not detected! Check wiring.");
  } else {
    Serial.println("RFID reader detected successfully!");
  }
  
  Serial.println("Ready to scan RFID cards/tags...");
  Serial.println("Place card near reader");
}

void loop() {
  // Look for new cards
  if (!mfrc522.PICC_IsNewCardPresent() || !mfrc522.PICC_ReadCardSerial()) {
    delay(50);
    return;
  }

  // Show UID on serial monitor
  Serial.print("Card UID: ");
  for (byte i = 0; i < mfrc522.uid.size; i++) {
    if (mfrc522.uid.uidByte[i] < 0x10) {
      Serial.print("0");  // Add leading zero
    }
    Serial.print(mfrc522.uid.uidByte[i], HEX);
    Serial.print(" ");
  }
  Serial.println();

  // Halt PICC
  mfrc522.PICC_HaltA();
}