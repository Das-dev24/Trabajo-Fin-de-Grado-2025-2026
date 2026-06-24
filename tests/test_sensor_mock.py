import pytest

# -------------------------------------------------------------------- #
#         Pruebas del serial sin sensor                                #
# -------------------------------------------------------------------- #
def test_mock_serial_reader_connect():
    from hives.core.sensor import MockSerialReader
    reader = MockSerialReader()
    assert reader.port == "Modo Prueba"
    assert reader.baudrate == 115200
    assert reader.connect() is True
    assert reader.is_scanning is False


def test_mock_serial_reader_disconnect():
    from hives.core.sensor import MockSerialReader
    reader = MockSerialReader()
    reader.disconnect()  # NO debe saltar la excepción


def test_mock_serial_reader_send_command_s():
    from hives.core.sensor import MockSerialReader
    reader = MockSerialReader()
    assert reader.send_command("s") == "Scanning ..."


def test_mock_serial_reader_send_command_x():
    from hives.core.sensor import MockSerialReader
    reader = MockSerialReader()
    assert reader.send_command("x") == "Scan stopped"


def test_mock_serial_reader_send_command_l_toggles():
    from hives.core.sensor import MockSerialReader
    reader = MockSerialReader()
    assert reader.leds_enabled is False
    assert reader.send_command("l") == "OK"
    assert reader.leds_enabled is True
    assert reader.send_command("l") == "OK"
    assert reader.leds_enabled is False


def test_mock_serial_reader_send_command_unknown():
    from hives.core.sensor import MockSerialReader
    reader = MockSerialReader()
    assert reader.send_command("z") is None


def test_mock_serial_reader_start_scanning():
    from hives.core.sensor import MockSerialReader
    reader = MockSerialReader()
    assert reader.start_scanning() is True
    assert reader.is_scanning is True


def test_mock_serial_reader_stop_scanning():
    from hives.core.sensor import MockSerialReader
    reader = MockSerialReader()
    reader.is_scanning = True
    assert reader.stop_scanning() is True
    assert reader.is_scanning is False


def test_mock_serial_reader_change_leds():
    from hives.core.sensor import MockSerialReader
    reader = MockSerialReader()
    assert reader.leds_enabled is False
    assert reader.change_leds() is True
    assert reader.leds_enabled is True
    assert reader.change_leds() is True
    assert reader.leds_enabled is False


def test_mock_serial_reader_read_data_when_not_scanning():
    from hives.core.sensor import MockSerialReader
    reader = MockSerialReader()
    reader.is_scanning = False
    assert reader.read_data() is None


def test_mock_serial_reader_read_data_returns_18_values():
    from hives.core.sensor import MockSerialReader
    reader = MockSerialReader()
    reader.is_scanning = True
    result = reader.read_data()
    assert result is not None
    assert len(result) == 18
    for v in result:
        assert isinstance(v, float)
        assert v >= 0.0
