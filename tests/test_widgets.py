import pytest

mpl = pytest.importorskip("matplotlib", reason="matplotlib not installed")

from hives.gui.widgets import SpectralCanvas  # noqa: E402  (import after importorskip)


def test_canvas_instantiates(qtbot):
    canvas = SpectralCanvas()
    qtbot.addWidget(canvas)


def test_update_data_18_values(qtbot, mocker):
    canvas = SpectralCanvas()
    qtbot.addWidget(canvas)
    spy = mocker.spy(canvas, "draw")
    canvas.update_data([0.5] * 18)
    assert spy.call_count >= 1


def test_update_data_wrong_length_does_not_raise(qtbot):
    canvas = SpectralCanvas()
    qtbot.addWidget(canvas)
    canvas.update_data([0.5] * 10)  # must not raise


def test_update_data_inf_sanitized(qtbot):
    canvas = SpectralCanvas()
    qtbot.addWidget(canvas)
    canvas.update_data([float("inf")] * 18)  # must not raise


def test_update_data_nan_sanitized(qtbot):
    canvas = SpectralCanvas()
    qtbot.addWidget(canvas)
    canvas.update_data([float("nan")] * 18)  # must not raise


def test_clear_plot_resets_axes(qtbot):
    canvas = SpectralCanvas()
    qtbot.addWidget(canvas)
    canvas.update_data([0.8] * 18)
    canvas.clear_plot()  # must not raise


def test_fallback_widget_when_matplotlib_absent(qtbot, mocker):
    mocker.patch("hives.gui.widgets._MATPLOTLIB_AVAILABLE", False)
    import importlib
    import hives.gui.widgets as widgets_mod
    importlib.reload(widgets_mod)

    fallback = widgets_mod.SpectralCanvas()
    qtbot.addWidget(fallback)
    fallback.update_data([0.5] * 18)  # no-op, must not raise
    fallback.clear_plot()             # no-op, must not raise
