#include "SparkFun_AS7265X.h"
AS7265X sensor;
#include <Wire.h>

bool isScanning = false;
bool encendidos = false;

String readLineNonBlocking() {
  static String buf = "";

  while (Serial.available()) {
    char c = Serial.read();
    if (c == '\r') continue;

    if (c == '\n') {
      String line = buf;
      buf = "";
      line.trim();
      return line;
    } else {
      buf += c;
    }
  }

  return "";
}

void setup() {
  Serial.begin(115200);

  if (sensor.begin() == false) {
    Serial.println("Sensor does not appear to be connected. Please check wiring. Freezing...");
    while (1);
  }

  Wire.setClock(400000);

  //Pines de las plcas de leds
  pinMode(2,OUTPUT);
  pinMode(3,OUTPUT);
  pinMode(4,OUTPUT);
  pinMode(5,OUTPUT);
  pinMode(6,OUTPUT);
  pinMode(7,OUTPUT);
  pinMode(8,OUTPUT);
  pinMode(9,OUTPUT);
  pinMode(10,OUTPUT);
  pinMode(11,OUTPUT);
  pinMode(12,OUTPUT);
  pinMode(13,OUTPUT);

  digitalWrite(2,LOW);
  digitalWrite(3,LOW);
  digitalWrite(4,LOW);
  digitalWrite(5,LOW);
  digitalWrite(6,LOW);
  digitalWrite(7,LOW);
  digitalWrite(8,HIGH);
  digitalWrite(9,HIGH);
  digitalWrite(10,HIGH);
  digitalWrite(11,HIGH);
  digitalWrite(12,HIGH);

  sensor.setMeasurementMode(AS7265X_MEASUREMENT_MODE_6CHAN_CONTINUOUS);
  //Parametros para cambiar cuanto tarda en hacer las mediciones y la precisión de las medidas
    //Para cambiar la sensibilidad hay que subir los ciclos, por defecto 1, máximo recomendado 150 -> tarda más en las medidas
    sensor.setIntegrationCycles(100); 
    //Cambbiar el grano, por defecto es 1x y se puede poner: 1x, 3.7x, 16x, 64x -> a más número más calidad, pero más ruiodo -> tiene que haber poca luz
    sensor.setGain(AS7265X_GAIN_16X);
  sensor.disableIndicator();

  sensor.disableBulb(AS7265x_LED_WHITE);
  sensor.disableBulb(AS7265x_LED_IR);
  sensor.disableBulb(AS7265x_LED_UV);
}

void handleLineCommand(const String &line) {
  if (line.length() == 0) return;

  if (line.equalsIgnoreCase("s")) {
    if (!isScanning) {
      isScanning = true;
      Serial.println("Scanning ...");
      sendCsvHeader();
    }
  } else if (line.equalsIgnoreCase("x")) {
    if (isScanning) {
      isScanning = false;
      Serial.println("Scan stopped");
    }
  } else if (line.equalsIgnoreCase("l")) {
    if (!encendidos){
      digitalWrite(2,HIGH);
      digitalWrite(3,HIGH);
      digitalWrite(4,HIGH);
      digitalWrite(5,HIGH);
      digitalWrite(6,HIGH);
      digitalWrite(7,HIGH);
      digitalWrite(8,LOW);
      digitalWrite(9,LOW);
      digitalWrite(10,LOW);
      digitalWrite(11,LOW);
      digitalWrite(12,LOW);
      digitalWrite(13,LOW);
      Serial.println("Encendidos");
      encendidos = true;
    } else {
      digitalWrite(2,LOW);
      digitalWrite(3,LOW);
      digitalWrite(4,LOW);
      digitalWrite(5,LOW);
      digitalWrite(6,LOW);
      digitalWrite(7,LOW);
      digitalWrite(8,HIGH);
      digitalWrite(9,HIGH);
      digitalWrite(10,HIGH);
      digitalWrite(11,HIGH);
      digitalWrite(12,HIGH);
      Serial.println("Apagados");
      encendidos = false;
    }
    
  } else {
    Serial.println("Comando no valido");
  }
}

void loop() {
  String line = readLineNonBlocking();
  if (line.length() > 0) {
    handleLineCommand(line);
  }

  if (isScanning) {
    if (sensor.dataAvailable()) {
      sendCsvRow();
    }
  }
}

void sendCsvHeader() {
  Serial.println("A_410,B_435,C_460,D_485,E_510,F_535,G_560,H_585,R_610,I_645,S_680,J_705,T_730,U_760,V_810,W_860,K_900,L_940");
}

void sendCsvRow() {
  Serial.print(sensor.getCalibratedA()); Serial.print(",");
  Serial.print(sensor.getCalibratedB()); Serial.print(",");
  Serial.print(sensor.getCalibratedC()); Serial.print(",");
  Serial.print(sensor.getCalibratedD()); Serial.print(",");
  Serial.print(sensor.getCalibratedE()); Serial.print(",");
  Serial.print(sensor.getCalibratedF()); Serial.print(",");
  Serial.print(sensor.getCalibratedG()); Serial.print(",");
  Serial.print(sensor.getCalibratedH()); Serial.print(",");
  Serial.print(sensor.getCalibratedR()); Serial.print(",");
  Serial.print(sensor.getCalibratedI()); Serial.print(",");
  Serial.print(sensor.getCalibratedS()); Serial.print(",");
  Serial.print(sensor.getCalibratedJ()); Serial.print(",");
  Serial.print(sensor.getCalibratedT()); Serial.print(",");
  Serial.print(sensor.getCalibratedU()); Serial.print(",");
  Serial.print(sensor.getCalibratedV()); Serial.print(",");
  Serial.print(sensor.getCalibratedW()); Serial.print(",");
  Serial.print(sensor.getCalibratedK()); Serial.print(",");
  Serial.println(sensor.getCalibratedL());
}