import serial as _serial
import time
import csv
from typing import List, Optional


class SerialReader:
    """Interfaz con el puerto serie del Arduino."""

    def __init__(self, port: str, baudrate: int):
        self.port = port
        self.baudrate = baudrate
        self.serial_connection = None
        self.is_scanning = False
        self.leds_enabled = False

    def connect(self) -> bool:
        try:
            self.serial_connection = _serial.Serial(self.port, self.baudrate, timeout=1)
            print(f"Conectado al puerto {self.port} a {self.baudrate}")
            return True
        except _serial.SerialException as e:
            print(f"Error al conectar: {e}")
            return False

    def disconnect(self):
        if self.serial_connection and self.serial_connection.is_open:
            self.serial_connection.close()
            print("Conexión cerrada")

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

    def stop_scanning(self) -> bool:
        response = self.send_command("x")
        if response == "Scan stopped":
            self.is_scanning = False
            print("Escaneo detenido")
            return True
        print("No se pudo detener el escaneo")
        return False

    def change_leds(self) -> bool:
        response = self.send_command("l")
        if response is not None:
            self.leds_enabled = not self.leds_enabled
            print(f"LEDs en modo {'transmitancia' if self.leds_enabled else 'reflectancia'}")
            return True
        print("No se pudo cambiar el estado de los LEDs")
        return False

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
    reader = SerialReader(port="COM4", baudrate=115200)
    if not reader.connect():
        print("Error: No se pudo conectar al Arduino.")
        exit(1)
    try:
        reader.run_scanning(output_file="datos_sensor.csv", max_reads=50)
    finally:
        reader.disconnect()
