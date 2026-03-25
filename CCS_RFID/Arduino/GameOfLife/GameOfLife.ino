#include "Arduino_LED_Matrix.h"

ArduinoLEDMatrix matrix;

// Your animation frames
const uint32_t animation[][4] = {
  {
    0x80080080,
    0xe000000,
    0x0,
    66
  },
  {
    0x88088088,
    0xe800000,
    0x0,
    66
  },
  {
    0x8a28b68a,
    0xaea20000,
    0x0,
    66
  }
};

void setup() {
  Serial.begin(9600);
  matrix.begin();
}

void loop() {
  // Manually control each frame with delay
  for(int i = 0; i < 3; i++) {
    matrix.loadFrame(animation[i]);
    delay(500); // Change this number to adjust speed (milliseconds)
    // Higher number = slower animation
    // 500 = half second per frame
    // 1000 = one second per frame
    // 2000 = two seconds per frame
  }
}