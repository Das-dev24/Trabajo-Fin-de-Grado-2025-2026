import os
import pytest

fpdf = pytest.importorskip("fpdf", reason="fpdf2 not installed")


# -------------------------------------------------------------------- #
#             Texto de la conclusioón                                  #
# -------------------------------------------------------------------- #

def test_conclusion_text_high_confidence():
    from hives.reports.pdf_report import _conclusion_text
    text = _conclusion_text("MielA", "Manuka", 0.85, True)
    assert "alta confianza" in text
    assert "puede considerarse fiable" in text


def test_conclusion_text_medium_confidence():
    from hives.reports.pdf_report import _conclusion_text
    text = _conclusion_text("MielA", "Clover", 0.65, False)
    assert "confianza moderada" in text
    assert "validar" in text


def test_conclusion_text_low_confidence():
    from hives.reports.pdf_report import _conclusion_text
    text = _conclusion_text("MielA", "Sugar", 0.30, False)
    assert "baja confianza" in text
    assert "repetir" in text


def test_conclusion_text_boundary_80():
    from hives.reports.pdf_report import _conclusion_text
    text = _conclusion_text("MielA", "Manuka", 0.80, True)
    assert "alta confianza" in text


def test_conclusion_text_boundary_50():
    from hives.reports.pdf_report import _conclusion_text
    text = _conclusion_text("MielA", "Manuka", 0.50, True)
    assert "confianza moderada" in text


def test_conclusion_text_calibrado_true():
    from hives.reports.pdf_report import _conclusion_text
    text = _conclusion_text("MielA", "Manuka", 0.90, True)
    assert "con calibración aplicada" in text


def test_conclusion_text_calibrado_false():
    from hives.reports.pdf_report import _conclusion_text
    text = _conclusion_text("MielA", "Manuka", 0.90, False)
    assert "sin calibración" in text


# -------------------------------------------------------------------- #
#               Construcción del gráfico                               #
# -------------------------------------------------------------------- #

mpl = pytest.importorskip("matplotlib", reason="matplotlib not installed")


def test_build_spectrum_chart_returns_bytes():
    from hives.reports.pdf_report import _build_spectrum_chart
    result = _build_spectrum_chart([0.5] * 18)
    assert result is not None
    assert isinstance(result, bytes)
    assert len(result) > 0


def test_build_spectrum_chart_wrong_length_17():
    from hives.reports.pdf_report import _build_spectrum_chart
    assert _build_spectrum_chart([0.5] * 17) is None


def test_build_spectrum_chart_wrong_length_0():
    from hives.reports.pdf_report import _build_spectrum_chart
    assert _build_spectrum_chart([]) is None


def test_build_spectrum_chart_mpl_unavailable(mocker):
    mocker.patch("hives.reports.pdf_report._MPL_OK", False)
    from hives.reports.pdf_report import _build_spectrum_chart
    assert _build_spectrum_chart([0.5] * 18) is None


# -------------------------------------------------------------------- #
#                      Generación del PDF                              #
# -------------------------------------------------------------------- #

_PDF_KWARGS = dict(
    analisis_id=1,
    nombre="TestMiel",
    timestamp="2025-01-01 12:00:00",
    modo="reflectancia",
    calibrado=True,
    espectro=[0.5] * 18,
    clase="Manuka",
    confianza=0.85,
    probabilidades=[1.0 / 12] * 12,
)


def test_generate_pdf_creates_file(tmp_path):
    from hives.reports.pdf_report import generate_pdf
    path = str(tmp_path / "out.pdf")
    generate_pdf(path=path, **_PDF_KWARGS)
    assert os.path.exists(path)


def test_generate_pdf_file_nonempty(tmp_path):
    from hives.reports.pdf_report import generate_pdf
    path = str(tmp_path / "out.pdf")
    generate_pdf(path=path, **_PDF_KWARGS)
    assert os.path.getsize(path) > 0


def test_generate_pdf_without_matplotlib(tmp_path, mocker):
    mocker.patch("hives.reports.pdf_report._MPL_OK", False)
    from hives.reports.pdf_report import generate_pdf
    path = str(tmp_path / "out_nompl.pdf")
    generate_pdf(path=path, **_PDF_KWARGS)
    assert os.path.getsize(path) > 0


def test_generate_pdf_empty_probabilities(tmp_path):
    from hives.reports.pdf_report import generate_pdf
    kwargs = dict(_PDF_KWARGS, probabilidades=[])
    path = str(tmp_path / "out_empty.pdf")
    generate_pdf(path=path, **kwargs)  # No debe fallar
    assert os.path.exists(path)
