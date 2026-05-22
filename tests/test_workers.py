import pytest
from hives.gui.workers import SerialWorker


def _csv18(value: float = 1.0) -> bytes:
    return (",".join([str(value)] * 18) + "\n").encode("utf-8")


# ── Emission ──────────────────────────────────────────────────────────────────

def test_worker_emits_data_received_on_18_values(qtbot, mock_reader, mock_serial):
    call_count = {"n": 0}

    def readline_side():
        call_count["n"] += 1
        return _csv18(1.0) if call_count["n"] == 1 else b""

    mock_serial.readline.side_effect = readline_side

    worker = SerialWorker(mock_reader)
    try:
        with qtbot.waitSignal(worker.data_received, timeout=2000) as blocker:
            worker.start()
        assert blocker.args == [[1.0] * 18]
    finally:
        worker.stop()


def test_worker_does_not_emit_for_wrong_length(qtbot, mock_reader, mock_serial):
    mock_serial.readline.return_value = (",".join(["1.0"] * 17) + "\n").encode("utf-8")
    worker = SerialWorker(mock_reader)
    worker.start()
    with qtbot.waitSignal(worker.data_received, timeout=300, raising=False) as blocker:
        pass
    worker.stop()
    assert not blocker.signal_triggered


def test_worker_does_not_emit_for_none(qtbot, mock_reader, mock_serial):
    mock_serial.readline.return_value = b""  # read_data → None
    worker = SerialWorker(mock_reader)
    worker.start()
    with qtbot.waitSignal(worker.data_received, timeout=300, raising=False) as blocker:
        pass
    worker.stop()
    assert not blocker.signal_triggered


# ── Stop behaviour ────────────────────────────────────────────────────────────

def test_worker_stop_sets_running_false(qtbot, mock_reader, mock_serial):
    mock_serial.readline.return_value = b""
    worker = SerialWorker(mock_reader)
    worker.start()
    qtbot.wait(60)
    worker.stop()
    assert worker._running is False


def test_worker_stop_waits_for_thread(qtbot, mock_reader, mock_serial):
    mock_serial.readline.return_value = b""
    worker = SerialWorker(mock_reader)
    worker.start()
    qtbot.wait(100)   # ensure run() has entered its loop before we stop
    worker.stop()     # sets _running=False then self.wait(2000)
    assert not worker.isRunning()


# ── Error signal ──────────────────────────────────────────────────────────────

def test_worker_error_not_emitted_normally(qtbot, mock_reader, mock_serial):
    """Documents current behaviour: SerialWorker.run() does not emit error_occurred."""
    mock_serial.readline.return_value = b""
    worker = SerialWorker(mock_reader)
    worker.start()
    with qtbot.waitSignal(worker.error_occurred, timeout=300, raising=False) as blocker:
        pass
    worker.stop()
    assert not blocker.signal_triggered
