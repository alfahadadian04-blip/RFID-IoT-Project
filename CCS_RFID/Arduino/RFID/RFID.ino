#include <SPI.h>
#include <MFRC522.h>
 
#define SS_PIN 10
#define RST_PIN 9
MFRC522 myRFID(SS_PIN, RST_PIN);   // Create MFRC522 instance.

int pinLED=2;
int pinLED2=7;
 
void setup() 
{
  Serial.begin(9600);   // Initiate a serial communication
  SPI.begin();      // Initiate  SPI bus
  myRFID.PCD_Init();   // Initiate MFRC522
  Serial.println("Please scan your RFID card...");
  Serial.println();
  pinMode(pinLED, OUTPUT);
  pinMode(pinLED2, OUTPUT);
}
void loop() 
{
  // Wait for RFID cards to be scanned
  if ( ! myRFID.PICC_IsNewCardPresent()) 
  {

    return;
  }
  // an RFID card has been scanned but no UID 
  if ( ! myRFID.PICC_ReadCardSerial()) 
  {
    
    return;
  }
  //Show UID on serial monitor
  digitalWrite(pinLED,HIGH);
  Serial.print("USER ID tag :");
  String content= "";
  for (byte i = 0; i < myRFID.uid.size; i++) 
  {
     Serial.print(myRFID.uid.uidByte[i] < 0x10 ? " 0" : " ");
     Serial.print(myRFID.uid.uidByte[i], HEX);
     content.concat(String(myRFID.uid.uidByte[i] < 0x10 ? " 0" : " "));
     content.concat(String(myRFID.uid.uidByte[i], HEX));
  }
  delay(500);
  digitalWrite(pinLED,LOW);
  Serial.println();
 // Serial.print("Message : ");
  content.toUpperCase();
  if (content.substring(1) == "7B C0 AD 21") //change here the UID of the card/cards that you want to give access
  {
    Serial.println("Access Granted!");
    digitalWrite(pinLED2,HIGH);
    Serial.println();
    delay(2000);
    digitalWrite(pinLED2,LOW);
  }
 
 else   {
    Serial.println("Access Succussful!");
    delay(2000);
  }
}