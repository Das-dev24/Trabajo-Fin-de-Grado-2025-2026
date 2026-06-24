from __future__ import annotations

import io
import os
from datetime import datetime
from typing import Optional

from fpdf import FPDF, XPos, YPos

from hives.constants import WAVELENGTHS

try:
    import matplotlib
    import matplotlib.pyplot as plt
    _MPL_OK = True
except ImportError:
    _MPL_OK = False

HONEY_CLASSES = [
    "BorageField", "Clover", "Kamahi", "Manuka",
    "ManukaBlend", "ManukaUMF10", "ManukaUMF15", "ManukaUMF20",
    "ManukaUMF5", "MultiFloral", "Rewarewa", "Sugar",
]

# Fuente del informe
_FONT_NAME = "Helvetica"


def _register_unicode_font(pdf: FPDF) -> None:
    """Registra la fuente Arial del sistema para soporte Unicode completo."""
    global _FONT_NAME
    fonts_dir = r"C:\Windows\Fonts"
    regular = os.path.join(fonts_dir, "arial.ttf")
    bold    = os.path.join(fonts_dir, "arialbd.ttf")
    italic  = os.path.join(fonts_dir, "ariali.ttf")
    if os.path.isfile(regular):
        pdf.add_font("Arial", "",  regular)
        if os.path.isfile(bold):
            pdf.add_font("Arial", "B", bold)
        if os.path.isfile(italic):
            pdf.add_font("Arial", "I", italic)
        _FONT_NAME = "Arial"


# ── Layout helpers ──────────────────────────────────────────────────────────

def _section_title(pdf: FPDF, text: str) -> None:
    pdf.set_font(_FONT_NAME, "B", 12)
    pdf.set_text_color(42, 126, 191)
    pdf.cell(0, 8, text, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_text_color(50, 50, 50)
    pdf.ln(1)


def _kv_row(pdf: FPDF, key: str, value: str) -> None:
    pdf.set_font(_FONT_NAME, "B", 10)
    pdf.set_text_color(80, 80, 80)
    pdf.cell(55, 7, key + ":", new_x=XPos.RIGHT)
    pdf.set_font(_FONT_NAME, "", 10)
    pdf.set_text_color(30, 30, 30)
    pdf.cell(0, 7, value, new_x=XPos.LMARGIN, new_y=YPos.NEXT)


# ── Chart helper ────────────────────────────────────────────────────────────

def _build_spectrum_chart(espectro: list[float]) -> Optional[bytes]:
    """Renders the normalised spectrum as a PNG byte string (in-memory)."""
    if not _MPL_OK or len(espectro) != 18:
        return None

    try:
        plt.switch_backend("Agg")
    except Exception:
        pass

    fig, ax = plt.subplots(figsize=(7, 3))
    ax.bar(WAVELENGTHS, espectro, width=18, color="#3a7ebf", alpha=0.85)
    ax.set_xlabel("Longitud de onda (nm)", fontsize=9)
    ax.set_ylabel("Intensidad normalizada", fontsize=9)
    ax.set_title("Huella espectral (espectro normalizado)", fontsize=10)
    ax.set_xticks(WAVELENGTHS)
    ax.set_xticklabels([str(w) for w in WAVELENGTHS], rotation=45, ha="right", fontsize=7)
    ax.set_xlim(390, 960)
    peak = max(espectro) if espectro else 0.0
    ax.set_ylim(0, peak * 1.15 if peak > 0 else 1.0)
    for sp in ("top", "right"):
        ax.spines[sp].set_visible(False)
    fig.tight_layout(pad=1.5)

    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=150)
    plt.close(fig)
    buf.seek(0)
    return buf.read()


# ── Conclusion text ─────────────────────────────────────────────────────────

def _conclusion_text(nombre: str, clase: str, confianza: float, calibrado: bool) -> str:
    cal_str = "con calibración aplicada" if calibrado else "sin calibración"
    conf_pct = round(confianza * 100, 1)

    if conf_pct >= 80.0:
        certainty = "con alta confianza"
        recomendacion = "El resultado puede considerarse fiable."
    elif conf_pct >= 50.0:
        certainty = "con confianza moderada"
        recomendacion = "Se recomienda validar este resultado con análisis adicionales."
    else:
        certainty = "con baja confianza (resultado no concluyente)"
        recomendacion = "Se recomienda repetir el análisis o verificar manualmente la muestra."

    return (
        f"El análisis \u00ab{nombre}\u00bb fue procesado {cal_str}. "
        f"El modelo de clasificación identificó la muestra como miel de tipo "
        f"\u00ab{clase}\u00bb {certainty} ({conf_pct}%). "
        f"{recomendacion}"
    )


# ── Main entry point ────────────────────────────────────────────────────────

def generate_pdf(
    path: str,
    analisis_id: int,
    nombre: str,
    timestamp: str,
    modo: str,
    calibrado: bool,
    espectro: list[float],
    clase: str,
    confianza: float,
    probabilidades: list[float],
) -> None:
    """Generates a PDF analysis report and writes it to *path*."""
    pdf = FPDF()
    _register_unicode_font(pdf)
    pdf.set_auto_page_break(auto=True, margin=20)
    pdf.add_page()
    pdf.set_margins(20, 20, 20)

    # ── Cabecera ─────────────────────────────────────────────────────────
    pdf.set_font(_FONT_NAME, "B", 20)
    pdf.set_text_color(42, 126, 191)
    pdf.cell(0, 12, "HIVES \u2014 Informe de An\u00e1lisis", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_text_color(80, 80, 80)
    pdf.set_font(_FONT_NAME, "", 9)
    pdf.cell(
        0, 6,
        f"Generado el {datetime.now().strftime('%d/%m/%Y a las %H:%M:%S')}",
        new_x=XPos.LMARGIN, new_y=YPos.NEXT,
    )
    pdf.ln(4)
    pdf.set_draw_color(200, 200, 200)
    pdf.line(20, pdf.get_y(), 190, pdf.get_y())
    pdf.ln(6)

    # ── 1. Introducción ───────────────────────────────────────────────────
    _section_title(pdf, "1. Introducci\u00f3n")
    _kv_row(pdf, "ID del an\u00e1lisis", str(analisis_id))
    _kv_row(pdf, "Nombre", nombre)
    _kv_row(pdf, "Fecha y hora", timestamp)
    _kv_row(pdf, "Modo de medici\u00f3n", modo.capitalize())
    _kv_row(pdf, "Calibraci\u00f3n", "Aplicada" if calibrado else "No aplicada")
    pdf.ln(6)

    # ── 2. Huella espectral ───────────────────────────────────────────────
    _section_title(pdf, "2. Huella espectral")
    chart_bytes = _build_spectrum_chart(espectro)
    if chart_bytes:
        pdf.image(io.BytesIO(chart_bytes), x=20, w=170)
    else:
        pdf.set_font(_FONT_NAME, "I", 9)
        pdf.set_text_color(150, 80, 80)
        pdf.cell(
            0, 8,
            "Gr\u00e1fico no disponible (matplotlib no instalado o datos insuficientes)",
            new_x=XPos.LMARGIN, new_y=YPos.NEXT,
        )
    pdf.ln(4)

    # ── 3. Resultado ──────────────────────────────────────────────────────
    _section_title(pdf, "3. Resultado de la clasificaci\u00f3n")
    _kv_row(pdf, "Clase predicha", clase)
    _kv_row(pdf, "Confianza", f"{round(confianza * 100, 2)}%")
    pdf.ln(4)

    if probabilidades and len(probabilidades) == len(HONEY_CLASSES):
        paired = sorted(
            zip(HONEY_CLASSES, probabilidades), key=lambda x: x[1], reverse=True
        )
        col_w = [110, 60]
        pdf.set_font(_FONT_NAME, "B", 9)
        pdf.set_fill_color(230, 240, 250)
        pdf.set_text_color(50, 50, 50)
        pdf.cell(col_w[0], 7, "Clase de miel", border=1, fill=True)
        pdf.cell(col_w[1], 7, "Probabilidad (%)", border=1, fill=True,
                 new_x=XPos.LMARGIN, new_y=YPos.NEXT)

        for i, (cls_name, prob) in enumerate(paired):
            is_winner = cls_name == clase
            fill_color = (240, 248, 255) if i % 2 == 0 else (255, 255, 255)
            pdf.set_fill_color(*fill_color)
            if is_winner:
                pdf.set_font(_FONT_NAME, "B", 9)
                pdf.set_text_color(42, 126, 191)
            else:
                pdf.set_font(_FONT_NAME, "", 9)
                pdf.set_text_color(50, 50, 50)
            pdf.cell(col_w[0], 6, cls_name, border=1, fill=True)
            pdf.cell(col_w[1], 6, f"{round(prob * 100, 2):.2f}%", border=1, fill=True,
                     new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    pdf.ln(6)

    # ── 4. Conclusión ─────────────────────────────────────────────────────
    _section_title(pdf, "4. Conclusi\u00f3n")
    pdf.set_font(_FONT_NAME, "", 10)
    pdf.set_text_color(50, 50, 50)
    conclusion = _conclusion_text(nombre, clase, confianza, calibrado)
    pdf.multi_cell(0, 6, conclusion)

    pdf.output(path)
