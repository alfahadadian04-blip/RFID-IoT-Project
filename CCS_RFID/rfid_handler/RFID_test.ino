#include <SPI.h>
#include <MFRC522.h>

#define SS_PIN 10
#define RST_PIN 9

MFRC522 rfid(SS_PIN, RST_PIN);

String lastCardUID = "";
bool cardProcessed = false;

void setup() {
  Serial.begin(9600);
  delay(1000);
  
  Serial.println("\n=== RFID Reader Ready ===");
  Serial.println("Tap a card to read it once");
  Serial.println("");
  
  SPI.begin();
  rfid.PCD_Init();
  
  // Verify RFID module is working
  byte version = rfid.PCD_ReadRegister(MFRC522::VersionReg);
  if (version == 0x00 || version == 0xFF) {
    Serial.println("ERROR: RFID module not detected!");
  } else {
    Serial.println("RFID module ready!");
  }
}

void loop() {
  // Check for card present
  if (rfid.PICC_IsNewCardPresent()) {
    
    // Try to read the card
    if (rfid.PICC_ReadCardSerial()) {
      
      // Get current card UID
      String currentCardUID = "";
      for (byte i = 0; i < rfid.uid.size; i++) {
        if (rfid.uid.uidByte[i] < 0x10) {
          currentCardUID += "0";
        }
        currentCardUID += String(rfid.uid.uidByte[i], HEX);
        if (i < rfid.uid.size - 1) {
          currentCardUID += " ";
        }
      }
      currentCardUID.toUpperCase();
      
      // Only print if it's a different card
      if (currentCardUID != lastCardUID) {
        Serial.println("=========================");
        Serial.print("Card UID: ");
        Serial.println(currentCardUID);
        
        // Get card type
        MFRC522::PICC_Type piccType = rfid.PICC_GetType(rfid.uid.sak);
        Serial.print("Card Type: ");
        Serial.println(rfid.PICC_GetTypeName(piccType));
        Serial.println("=========================");
        
        lastCardUID = currentCardUID;
      }
      
      // Halt the card
      rfid.PICC_HaltA();
      rfid.PCD_StopCrypto1();
      
      // Wait for card to be removed
      delay(500);
    }
  }
  
  // Reset after card is removed (optional - uncomment if you want to read same card again)
  // if (!rfid.PICC_IsNewCardPresent() && cardProcessed) {
  //   cardProcessed = false;
  //   lastCardUID = "";
  // }
  
  delay(50); // Small delay to prevent overwhelming the reader
}
