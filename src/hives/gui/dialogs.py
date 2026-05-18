from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QLineEdit,
    QDialogButtonBox, QLabel, QComboBox,
)

from hives.constants import CAL_BLANCO, CAL_OSCURO


class NombreAnalisisDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Nuevo análisis")
        self.setFixedSize(340, 130)
        self.setStyleSheet("QDialog { background: #f0f0f0; } QLabel { color: #333; }")

        lay = QVBoxLayout(self)
        lay.setContentsMargins(20, 16, 20, 12)
        lay.setSpacing(10)

        form = QFormLayout()
        form.setSpacing(8)
        self.input_nombre = QLineEdit()
        self.input_nombre.setPlaceholderText("Ej: Muestra miel 001")
        self.input_nombre.setStyleSheet(
            "QLineEdit { background: white; border: 1px solid #ccc; "
            "border-radius: 3px; padding: 5px 8px; font-size: 13px; }"
        )
        form.addRow("Nombre del análisis:", self.input_nombre)
        lay.addLayout(form)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText("Iniciar escaneo")
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText("Cancelar")
        lay.addWidget(buttons)

    def _on_accept(self):
        if not self.input_nombre.text().strip():
            self.input_nombre.setPlaceholderText("Introduce un nombre")
            self.input_nombre.setStyleSheet(
                "QLineEdit { background: white; border: 1px solid #c0392b; "
                "border-radius: 3px; padding: 5px 8px; font-size: 13px; }"
            )
            return
        self.accept()

    def nombre(self) -> str:
        return self.input_nombre.text().strip()


class CalibracionDialog(QDialog):
    def __init__(self, parent=None, duracion_default: str = "5"):
        super().__init__(parent)
        self.setWindowTitle("Nueva calibración")
        self.setFixedSize(360, 170)
        self.setStyleSheet("QDialog { background: #f0f0f0; } QLabel { color: #333; }")

        lay = QVBoxLayout(self)
        lay.setContentsMargins(20, 16, 20, 12)
        lay.setSpacing(10)

        info = QLabel("Las calibraciones se usan para corregir las lecturas:\n"
                      "• Blanco: referencia 100% (estándar reflectante)\n"
                      "• Oscuro: referencia 0% (sensor tapado)")
        info.setStyleSheet("color: #555; font-size: 11px;")
        lay.addWidget(info)

        form = QFormLayout()
        form.setSpacing(8)
        self.combo_tipo = QComboBox()
        self.combo_tipo.addItems(["Blanco (referencia 100%)", "Oscuro (referencia 0%)"])
        self.combo_tipo.setStyleSheet(
            "QComboBox { background: white; border: 1px solid #ccc; "
            "border-radius: 3px; padding: 4px 6px; font-size: 12px; }"
        )
        form.addRow("Tipo:", self.combo_tipo)

        self.input_dur = QLineEdit(duracion_default)
        self.input_dur.setStyleSheet(
            "QLineEdit { background: white; border: 1px solid #ccc; "
            "border-radius: 3px; padding: 5px 8px; font-size: 12px; }"
        )
        form.addRow("Duración (s):", self.input_dur)
        lay.addLayout(form)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText("Iniciar calibración")
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText("Cancelar")
        lay.addWidget(buttons)

    def tipo(self) -> str:
        return CAL_BLANCO if self.combo_tipo.currentIndex() == 0 else CAL_OSCURO

    def duracion(self) -> int:
        t = self.input_dur.text().strip()
        return int(t) if t.isdigit() else 5
