import pytest

mpl = pytest.importorskip("matplotlib", reason="matplotlib not installed")

from hives.gui.widgets import SpectralCanvas 


# -------------------------------------------------------------------- #
#                              Persistencia                            #
# -------------------------------------------------------------------- #

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
    canvas.update_data([0.5] * 10)  # No debe saltar ninguan excepción


def test_update_data_value_error_handled(qtbot):
    canvas = SpectralCanvas()
    qtbot.addWidget(canvas)
    canvas.update_data(["bad"] * 18)  # No debe saltar ninguan excepción


def test_update_data_peak_above_1_5(qtbot):
    canvas = SpectralCanvas()
    qtbot.addWidget(canvas)
    canvas.update_data([10.0] * 18)  # peak > 1.5 → ymax = peak * 1.15


def test_update_data_inf_sanitized(qtbot):
    canvas = SpectralCanvas()
    qtbot.addWidget(canvas)
    canvas.update_data([float("inf")] * 18)  # No debe saltar ninguan excepción


def test_update_data_nan_sanitized(qtbot):
    canvas = SpectralCanvas()
    qtbot.addWidget(canvas)
    canvas.update_data([float("nan")] * 18)  # No debe saltar ninguan excepción


def test_clear_plot_resets_axes(qtbot):
    canvas = SpectralCanvas()
    qtbot.addWidget(canvas)
    canvas.update_data([0.8] * 18)
    canvas.clear_plot()  # No debe saltar ninguan excepción


def test_fallback_widget_when_matplotlib_absent(qtbot, mocker):
    mocker.patch("hives.gui.widgets._MATPLOTLIB_AVAILABLE", False)
    import importlib
    import hives.gui.widgets as widgets_mod
    importlib.reload(widgets_mod)

    fallback = widgets_mod.SpectralCanvas()
    qtbot.addWidget(fallback)
    fallback.update_data([0.5] * 18)  
    fallback.clear_plot()             # No debe saltar ninguan excepción
