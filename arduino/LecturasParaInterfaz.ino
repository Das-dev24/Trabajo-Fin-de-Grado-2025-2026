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
  Serial.println("AS7265x Spectral Triad Example");

  if (sensor.begin() == false) {
    Serial.println("Sensor does not appear to be connected. Please check wiring. Freezing...");
    while (1);
  }

  Wire.setClock(400000);

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
      sensor.enableBulb(AS7265x_LED_WHITE);
      sensor.enableBulb(AS7265x_LED_IR);
      sensor.enableBulb(AS7265x_LED_UV);
      encendidos = true;
    } else {
      sensor.disableBulb(AS7265x_LED_WHITE);
      sensor.disableBulb(AS7265x_LED_IR);
      sensor.disableBulb(AS7265x_LED_UV);
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