import math
import random

import serial as _serial
import time
import csv
from typing import List, Optional


class SerialReader:
    """Interfaz con el puerto serie del Arduino."""

    """Función de inico que establece los parametros iniciales para la conexión con el Arduino"""
    def __init__(self, port: str, baudrate: int):
        self.port = port
        self.baudrate = baudrate
        self.serial_connection = None
        self.is_scanning = False
        self.leds_enabled = False

    """Función que realiza la conexión con el puerto serie del Arduino, devolviendo si ha sido exitosa o no"""
    def connect(self) -> bool:
        try:
            self.serial_connection = _serial.Serial(self.port, self.baudrate, timeout=1)
            print(f"Conectado al puerto {self.port} a {self.baudrate}")
            return True
        except _serial.SerialException as e:
            print(f"Error al conectar: {e}")
            return False
        
    """Función que desconecta el arduino del puerto serie cesando la conexión si esta existe"""
    def disconnect(self):
        if self.serial_connection and self.serial_connection.is_open:
            self.serial_connection.close()
            print("Conexión cerrada")

    """Función que envía comandos al Arduino para interactuar con eñ senor"""
    def send_command(self, command: str) -> Optional[str]:
        if not self.serial_connection or not self.serial_connection.is_open:
            print("No hay conexión serial activa.")
            return None
        try:
            self.serial_connection.write((command + "\n").encode("utf-8"))
            time.sleep(0.1)
            response = self.serial_connection.readline().decode("utf-8").strip()
            return response if response else None
        except _serial.SerialException as e:
            print(f"Error al enviar el comando: {e}")
            return None
        
    """Función que comienza el escaneo del sensor, enviando el comando pertinente"""
    def start_scanning(self) -> bool:
        response = self.send_command("s")
        if response == "Scanning ...":
            self.is_scanning = True
            time.sleep(0.5)
            self.serial_connection.reset_input_buffer()
            print("Escaneo iniciado")
            return True
        print("No se pudo iniciar el escaneo")
        return False

    """Función que detiene el escaneo del sensor, enviando el comando pertinente"""
    def stop_scanning(self) -> bool:
        response = self.send_command("x")
        if response == "Scan stopped":
            self.is_scanning = False
            print("Escaneo detenido")
            return True
        print("No se pudo detener el escaneo")
        return False

    """Función que cambia el estado de los LEDs, enviando el comando pertinente"""
    def change_leds(self) -> bool:
        response = self.send_command("l")
        if response is not None:
            self.leds_enabled = not self.leds_enabled
            print(f"LEDs en modo {'transmitancia' if self.leds_enabled else 'reflectancia'}")
            return True
        print("No se pudo cambiar el estado de los LEDs")
        return False

    """Función que lee los datos que recibe del sensor y los pasa a una lista"""
    def read_data(self) -> Optional[List[float]]:
        if not self.serial_connection or not self.serial_connection.is_open:
            print("No hay conexión serial activa.")
            return None
        try:
            line = self.serial_connection.readline().decode("utf-8").strip()
            if not line:
                return None
            first = line.split(",")[0].strip()
            try:
                float(first)
            except ValueError:
                return None
            return [float(val) for val in line.split(",")]
        except (_serial.SerialException, ValueError) as e:
            print(f"Error al leer datos: {e}")
            return None

    """Función que ejecuta el scaneo del sensor y almacena los datos en un CSV"""
    def run_scanning(self, output_file: Optional[str] = None, max_reads: int = 100):
        if not self.start_scanning():
            return
        try:
            with open(output_file, "w", newline="") as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow([
                    "A_410", "B_435", "C_460", "D_485", "E_510", "F_535", "G_560", "H_585",
                    "R_610", "I_645", "S_680", "J_705", "T_730", "U_760", "V_810", "W_860",
                    "K_900", "L_940",
                ])
                for i in range(max_reads):
                    data = self.read_data()
                    if data:
                        writer.writerow(data)
                        print(f"Lectura {i + 1}: {data}")
                    else:
                        print("No hay datos disponibles.")
                    time.sleep(0.5)
        except Exception as e:
            print(f"Error al escribir en el archivo: {e}")
        finally:
            self.stop_scanning()

if __name__ == "__main__":
    reader = SerialReader(port="COM4", baudrate=115200) # Creamos el serial reader con los datos por defecto, luego se elegiran desde la interfaz
    if not reader.connect():
        print("Error: No se pudo conectar al Arduino.")
        exit(1)
    try:
        reader.run_scanning(output_file="datos_sensor.csv", max_reads=50)
    finally:
        reader.disconnect()


class MockSerialReader:
    """Genera datos simulados para probar la interfaz sin hardware real. Son como los anteriores pero no necesitan un arduino conectado"""

    def __init__(self, port: str = "Modo Prueba", baudrate: int = 115200):
        self.port = port
        self.baudrate = baudrate
        self.is_scanning = False
        self.leds_enabled = False

    def connect(self) -> bool:
        return True

    def disconnect(self):
        pass

    def send_command(self, command: str) -> Optional[str]:
        if command == "s":
            return "Scanning ..."
        if command == "x":
            return "Scan stopped"
        if command == "l":
            self.leds_enabled = not self.leds_enabled
            return "OK"
        return None

    def start_scanning(self) -> bool:
        self.is_scanning = True
        return True

    def stop_scanning(self) -> bool:
        self.is_scanning = False
        return True

    def change_leds(self) -> bool:
        self.leds_enabled = not self.leds_enabled
        return True

    """Esta función genera datos aleatorios para poder ver el funcionamiento de la interfaz de forma correcta"""
    def read_data(self) -> Optional[List[float]]:
        if not self.is_scanning:
            return None
        base = [random.uniform(100, 300) for _ in range(18)]
        for i in range(18):
            base[i] += 2000 * math.exp(-((i - 9) ** 2) / 20)
        base = [v + random.gauss(0, 15) for v in base]
        return [round(max(v, 0.0), 1) for v in base]
