import pytest
from serial import SerialException

# -------------------------------------------------------------------- #
#                        Conexión                                      #
# -------------------------------------------------------------------- #

def test_connect_success(mock_serial, mocker):
    from hives.core.sensor import SerialReader
    reader = SerialReader("COM3", 115200)
    assert reader.connect() is True
    assert reader.serial_connection is mock_serial


def test_connect_failure(mocker):
    mocker.patch("serial.Serial", side_effect=SerialException("no port"))
    from hives.core.sensor import SerialReader
    reader = SerialReader("COM3", 115200)
    assert reader.connect() is False
    assert reader.serial_connection is None


# -------------------------------------------------------------------- #
#                        Desconexión                                   #
# -------------------------------------------------------------------- #

def test_disconnect_closes_open_port(mock_reader, mock_serial):
    mock_serial.is_open = True
    mock_reader.disconnect()
    mock_serial.close.assert_called_once()


def test_disconnect_noop_when_not_open(mock_reader, mock_serial):
    mock_serial.is_open = False
    mock_reader.disconnect()
    mock_serial.close.assert_not_called()


def test_disconnect_noop_when_no_connection(mocker):
    mocker.patch("serial.Serial")
    from hives.core.sensor import SerialReader
    reader = SerialReader("COM3", 115200)
    reader.serial_connection = None
    reader.disconnect()  # No debe saltar excecpción


# -------------------------------------------------------------------- #
#                              Enviar comando                          #
# -------------------------------------------------------------------- #

def test_send_command_returns_response(mock_reader, mock_serial, mocker):
    mocker.patch("hives.core.sensor.time.sleep")
    mock_serial.readline.return_value = b"OK\n"
    result = mock_reader.send_command("s")
    mock_serial.write.assert_called_once_with(b"s\n")
    assert result == "OK"


def test_send_command_no_connection(mocker):
    mocker.patch("serial.Serial")
    from hives.core.sensor import SerialReader
    reader = SerialReader("COM3", 115200)
    reader.serial_connection = None
    assert reader.send_command("s") is None


def test_send_command_no_connection_closed(mock_reader, mock_serial, mocker):
    mock_serial.is_open = False
    assert mock_reader.send_command("s") is None


def test_send_command_serial_exception(mock_reader, mock_serial, mocker):
    mocker.patch("hives.core.sensor.time.sleep")
    mock_serial.readline.side_effect = SerialException("read error")
    assert mock_reader.send_command("s") is None


# -------------------------------------------------------------------- #
#                              Comenzar escaneo                        #
# -------------------------------------------------------------------- #

def test_start_scanning_success(mock_reader, mock_serial, mocker):
    mocker.patch("hives.core.sensor.time.sleep")
    mock_serial.readline.return_value = b"Scanning ...\n"
    assert mock_reader.start_scanning() is True
    assert mock_reader.is_scanning is True


def test_start_scanning_failure(mock_reader, mock_serial, mocker):
    mocker.patch("hives.core.sensor.time.sleep")
    mock_serial.readline.return_value = b"Error\n"
    assert mock_reader.start_scanning() is False
    assert mock_reader.is_scanning is False


# -------------------------------------------------------------------- #
#                        Parar escaneo                                 #
# -------------------------------------------------------------------- #

def test_stop_scanning_success(mock_reader, mock_serial, mocker):
    mocker.patch("hives.core.sensor.time.sleep")
    mock_reader.is_scanning = True
    mock_serial.readline.return_value = b"Scan stopped\n"
    assert mock_reader.stop_scanning() is True
    assert mock_reader.is_scanning is False


def test_stop_scanning_failure(mock_reader, mock_serial, mocker):
    mocker.patch("hives.core.sensor.time.sleep")
    mock_serial.readline.return_value = b"???\n"
    assert mock_reader.stop_scanning() is False

# -------------------------------------------------------------------- #
#                  Cambiar modo -> cambiar leds                        #
# -------------------------------------------------------------------- #

def test_change_leds_toggles_on(mock_reader, mock_serial, mocker):
    mocker.patch("hives.core.sensor.time.sleep")
    mock_serial.readline.return_value = b"LEDs on\n"
    mock_reader.leds_enabled = False
    assert mock_reader.change_leds() is True
    assert mock_reader.leds_enabled is True


def test_change_leds_toggles_off(mock_reader, mock_serial, mocker):
    mocker.patch("hives.core.sensor.time.sleep")
    mock_serial.readline.return_value = b"LEDs off\n"
    mock_reader.leds_enabled = True
    assert mock_reader.change_leds() is True
    assert mock_reader.leds_enabled is False


def test_change_leds_failure(mock_reader, mock_serial, mocker):
    mocker.patch("hives.core.sensor.time.sleep")
    mock_serial.readline.return_value = b""  # send_command returns None for empty response
    initial_state = mock_reader.leds_enabled
    assert mock_reader.change_leds() is False
    assert mock_reader.leds_enabled == initial_state

# -------------------------------------------------------------------- #
#                              Leer datos                            #
# -------------------------------------------------------------------- #

def test_read_data_returns_18_floats(mock_reader, mock_serial):
    line = ",".join([f"{i+1}.0" for i in range(18)]) + "\n"
    mock_serial.readline.return_value = line.encode("utf-8")
    result = mock_reader.read_data()
    assert result is not None
    assert len(result) == 18
    assert result[0] == pytest.approx(1.0)
    assert result[17] == pytest.approx(18.0)


def test_read_data_empty_line(mock_reader, mock_serial):
    mock_serial.readline.return_value = b""
    assert mock_reader.read_data() is None


def test_read_data_non_numeric_first(mock_reader, mock_serial):
    mock_serial.readline.return_value = b"A_410,B_435,C_460\n"
    assert mock_reader.read_data() is None


def test_read_data_no_connection(mocker):
    mocker.patch("serial.Serial")
    from hives.core.sensor import SerialReader
    reader = SerialReader("COM3", 115200)
    reader.serial_connection = None
    assert reader.read_data() is None


def test_read_data_serial_exception_handled(mock_reader, mock_serial):
    from serial import SerialException
    mock_serial.readline.side_effect = SerialException("read error")
    assert mock_reader.read_data() is None


def test_read_data_value_error_handled(mock_reader, mock_serial):
    mock_serial.readline.return_value = b"1.0,2.0,not_a_number\n"
    result = mock_reader.read_data()
    assert result is None

# -------------------------------------------------------------------- #
#              Enviar comando y obtener respuesta vacía                #
# -------------------------------------------------------------------- #

def test_send_command_empty_response(mock_reader, mock_serial, mocker):
    mocker.patch("hives.core.sensor.time.sleep")
    mock_serial.readline.return_value = b"\n"
    assert mock_reader.send_command("s") is None
