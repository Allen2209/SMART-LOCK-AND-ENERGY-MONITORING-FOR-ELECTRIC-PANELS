int inputPin = 7;   // from Pico
int relayPin = 8;   // to relay

void setup() {
  pinMode(inputPin, INPUT);
  pinMode(relayPin, OUTPUT);
}

void loop() {
  int state = digitalRead(inputPin);

  if (state == HIGH) {
    digitalWrite(relayPin, HIGH); // unlock
  } else {
    digitalWrite(relayPin, LOW);  // lock
  }
}