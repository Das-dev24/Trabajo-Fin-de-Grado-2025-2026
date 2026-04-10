import serial
import time
import csv
from typing import List, Optional, Tuple

class SerialReader:
    """
    Clase para interactuar con el puerto serie del Arduino
    """
    def __init__(self, port: str, baudrate: int):
        """
        Dejamos los parámetros para pasar desde la interfaz gráfica
        """
        self.port = port
        self.baudrate = baudrate
        self.serial_connection = None
        self.is_scanning = False
        self.leds_enabled = False
    
    def connect(self) -> bool:
        """
        Establece la connexión con el arduino

        Returns:
            bool: True si la conexión fue exitosa, False si no
        """
        try: 
            self.serial_connection = serial.Serial(self.port, self.baudrate, timeout=1)
            print(f"Conectado al puerto {self.port} a {self.baudrate}")
            return True
        except serial.SerialException as e:
            print(f"Error al conectar: {e}")
            return False

    def disconnect(self):
        """
        Cierra la conexión serial con el Arduino
        """
        if self.serial_connection and self.serial_connection.is_open:
            self.serial_connection.close()
            print("Conexión cerrada")

    def send_command(self, command: str) -> Optional[str]:
        """
        Envía un comando al arduino y espera una respuesta

        Args:
            command (str): Comando a enviar (ej. "s", "x", "l")
        
        Returns:
            Optional[str]: Respuesta del arduino si hay, None de lo contrario
        """
        if not self.serial_connection or not self.serial_connection.is_open:
            print("No hay conexión serial activa.")
            return None
        try:
        
            self.serial_connection.write((command + "\n").encode("utf-8"))
            time.sleep(0.1)
            response = self.serial_connection.readline().decode("utf-8").strip()
            return response if response else None
        
        except serial.SerialException as e:
            print(f"Error al enviar el comando: {e}")
            return None
        
    def start_scanning(self) -> bool:
        """
        Inicia el escaneo de los datos del sensor
        
        returns:
            bool: True si el escane ha empezdo de forma correcta, False de lo contrario
        """
        response = self.send_command("s")
        if response == "Scanning ...":
            self.is_scanning = True
            print("Escaneo iniciado")
            return True
        else:
            print("No se pudo iniciar el escaneo")
            return False
        
    def stop_scanning(self) -> bool:
        """
        Detiene el escaneo de datos del sensor

        Returns:
            bool: True si el escaneo se detubo de forma correcta, False de lo contrario
        """
        response = self.send_command("x")
        if response == "Scan stopped":
            self.is_scanning = False
            print("Escaneo detenido")
            return True
        else:
            print("No se pudo detener el escaneo")
            return False
        
    def change_leds(self) -> bool:
        """
        Cambia entre lecturas de transmitacia y refractancia
        
        Returns:
            bool: True si los leds cambiaron de forma correcta, False si no
        """
        response = self.send_command("l")
        if response is not None:
            self.leds_enabled = not self.leds_enabled
            print(f"Los LEDS están en modo {'transmitancia' if self.leds_enabled else 'refractancia'}")
            return True
        else:
            print ("No se puedo cambiar el estado de los leds")
            return False
    def read_data(self) -> Optional[List[float]]:
        """
        Lee una fila de datos del sensor (formato CSV).

        Returns:
            Optional[List[float]]: Lista de valores de las longitudes de onda, o None si no hay datos.
        """
        if not self.serial_connection or not self.serial_connection.is_open:
            print("No hay conexión serial activa.")
            return None

        try:
            line = self.serial_connection.readline().decode("utf-8").strip()
            if line:
                values = [float(val) for val in line.split(",")]
                return values
        except (serial.SerialException, ValueError) as e:
            print(f"Error al leer datos: {e}")
            return None
        return None

    def run_scanning(self, output_file: Optional[str] = None, max_reads: int = 100):
        """
        Inicia el escaneo y guarda los datos en un archivo CSV.

        Args:
            output_file (str, optional): Ruta del archivo CSV donde se guardarán los datos. Si es None, no se guarda.
            max_reads (int): Número máximo de lecturas a realizar (por defecto 100).
        """
        if not self.start_scanning():
            return

        try:
            with open(output_file, "w", newline="") as csvfile:
                writer = csv.writer(csvfile)
                header = [
                    "A_410", "B_435", "C_460", "D_485", "E_510", "F_535", "G_560", "H_585",
                    "R_610", "I_645", "S_680", "J_705", "T_730", "U_760", "V_810", "W_860",
                    "K_900", "L_940"
                ]
                writer.writerow(header)

                for i in range(max_reads):
                    data = self.read_data()
                    if data:
                        writer.writerow(data)
                        print(f"Lectura {i+1}: {data}")
                    else:
                        print("No hay datos disponibles.")
                    time.sleep(0.5)  # Pequeña espera entre lecturas
        except Exception as e:
            print(f"Error al escribir en el archivo: {e}")
        finally:
            self.stop_scanning()
    
    #Este main es para probar si funciona, luego al usarlo hay que quitarlo:
if __name__ == "__main__":
    reader = SerialReader(port="COM4", baudrate=115200)  

    if not reader.connect():
        print("Error: No se pudo conectar al Arduino.")
        exit(1)

    try:
        reader.run_scanning(output_file="datos_sensor.csv", max_reads=50)
    finally:
        reader.disconnect()