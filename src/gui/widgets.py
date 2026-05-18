from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel
from PyQt6.QtCore import Qt

from constants import WAVELENGTHS

try:
    from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
    from matplotlib.figure import Figure
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False


if MATPLOTLIB_AVAILABLE:
    class SpectralCanvas(FigureCanvas):
        def __init__(self):
            self.fig = Figure(figsize=(6, 3.5), facecolor="#f8f8f8")
            super().__init__(self.fig)
            self.ax = self.fig.add_subplot(111)
            self._setup_axes()

        def _setup_axes(self):
            ax = self.ax
            ax.set_facecolor("#f8f8f8")
            for sp in ['top', 'right']:
                ax.spines[sp].set_visible(False)
            ax.tick_params(labelsize=7)
            ax.set_xlabel('Longitud de onda (nm)', fontsize=9)
            ax.set_ylabel('Intensidad', fontsize=9)
            ax.set_xticks(WAVELENGTHS)
            ax.set_xticklabels([str(w) for w in WAVELENGTHS], rotation=45, ha='right')
            ax.set_xlim(390, 960)
            ax.set_ylim(0, 1)
            self.fig.tight_layout(pad=1.5)

        def update_data(self, values: list):
            self.ax.clear()
            self._setup_axes()

            safe = []
            for v in values:
                try:
                    fv = float(v)
                    if fv != fv or fv in (float('inf'), float('-inf')):
                        fv = 0.0
                    safe.append(fv)
                except (TypeError, ValueError):
                    safe.append(0.0)

            if len(safe) != len(WAVELENGTHS):
                self.draw()
                return

            self.ax.bar(WAVELENGTHS, safe, width=18,
                        color='#3a7ebf', alpha=0.8, zorder=3)

            peak = max(safe) if safe else 0.0
            if peak <= 0:
                ymax = 1.0
            elif peak <= 1.5:
                ymax = max(peak * 1.15, 0.1)
            else:
                ymax = peak * 1.15
            self.ax.set_ylim(0, ymax)

            self.fig.tight_layout(pad=1.5)
            self.draw()

        def clear_plot(self):
            self.ax.clear()
            self._setup_axes()
            self.draw()

else:
    class SpectralCanvas(QWidget):
        def __init__(self):
            super().__init__()
            lay = QVBoxLayout(self)
            lbl = QLabel("matplotlib no disponible\npip install matplotlib")
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lay.addWidget(lbl)

        def update_data(self, values: list): pass
        def clear_plot(self):               pass
