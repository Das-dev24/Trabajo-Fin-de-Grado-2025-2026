import pytest
from unittest.mock import MagicMock, PropertyMock
import numpy as np

# -------------------------------------------------------------------- #
#                      Carga dle modelo                                #
# -------------------------------------------------------------------- #

def test_load_model_returns_none_tf_unavailable(mocker, tmp_path):
    mocker.patch("hives.inference.model.TF_AVAILABLE", False)
    from hives.inference.model import load_model
    assert load_model(str(tmp_path)) is None


def test_load_model_tf_not_available_sets_error(mocker, tmp_path):
    mocker.patch("hives.inference.model.TF_AVAILABLE", False)
    import hives.inference.model as model_mod
    model_mod.load_model(str(tmp_path))
    assert "TensorFlow" in model_mod.last_load_error


def test_load_model_model_dir_not_exist(mocker, tmp_path):
    mocker.patch("hives.inference.model.TF_AVAILABLE", True)
    mocker.patch("hives.inference.model.tf", mocker.MagicMock(), create=True)
    from hives.inference.model import load_model
    nonexistent = str(tmp_path / "nope")
    assert load_model(nonexistent) is None


def test_load_model_load_exception(mocker, tmp_path):
    (tmp_path / "mejor_modelo.keras").touch()
    mock_tf = mocker.MagicMock()
    mock_tf.keras.models.load_model.side_effect = Exception("load failed")
    mocker.patch("hives.inference.model.TF_AVAILABLE", True)
    mocker.patch("hives.inference.model.tf", mock_tf, create=True)
    from hives.inference.model import load_model
    assert load_model(str(tmp_path)) is None


def test_load_model_missing_clases_json(mocker, tmp_path):
    (tmp_path / "mejor_modelo.keras").touch()
    mock_keras_model = mocker.MagicMock(spec=object)
    mock_tf = mocker.MagicMock()
    mock_tf.keras.models.load_model.return_value = mock_keras_model
    mocker.patch("hives.inference.model.TF_AVAILABLE", True)
    mocker.patch("hives.inference.model.tf", mock_tf, create=True)
    from hives.inference.model import load_model
    result = load_model(str(tmp_path))
    assert result is mock_keras_model


def test_load_model_returns_none_no_keras_file(mocker, tmp_path):
    mocker.patch("hives.inference.model.TF_AVAILABLE", True)
    mocker.patch("hives.inference.model.tf", MagicMock(), create=True)
    from hives.inference.model import load_model
    assert load_model(str(tmp_path)) is None


def test_load_model_returns_none_on_load_exception(mocker, tmp_path):
    (tmp_path / "model.keras").touch()
    mock_tf = MagicMock()
    mock_tf.keras.models.load_model.side_effect = Exception("load failed")
    mocker.patch("hives.inference.model.TF_AVAILABLE", True)
    mocker.patch("hives.inference.model.tf", mock_tf, create=True)
    from hives.inference.model import load_model
    assert load_model(str(tmp_path)) is None


def test_load_model_returns_model_object(mocker, tmp_path):
    (tmp_path / "mejor_modelo.keras").touch()
    mock_keras_model = MagicMock()
    mock_tf = MagicMock()
    mock_tf.keras.models.load_model.return_value = mock_keras_model
    mocker.patch("hives.inference.model.TF_AVAILABLE", True)
    mocker.patch("hives.inference.model.tf", mock_tf, create=True)
    from hives.inference.model import load_model
    result = load_model(str(tmp_path))
    assert result is mock_keras_model


# -------------------------------------------------------------------- #
#                    Ejecutar clasificación                            #
# -------------------------------------------------------------------- #

def test_run_inference_model_none():
    from hives.inference.model import run_inference
    clase, probs = run_inference(None, [0.1] * 18)
    assert clase == "Sin modelo"
    assert probs == [0.0]


def test_run_inference_returns_class_and_probs():
    from hives.inference.model import run_inference
    from hives.reports.pdf_report import HONEY_CLASSES

    model = MagicMock()
    model._clase_names = None  # preevee creación de MagicMock
    raw_probs = [0.0] * 12
    raw_probs[3] = 0.9   # 3ª clase Manuka más probable
    raw_probs[0] = 0.1
    model.predict.return_value = np.array([raw_probs])
    model.output_names = list(HONEY_CLASSES)

    clase, probs = run_inference(model, [0.1] * 18)
    assert clase == "Manuka"
    assert len(probs) == 12
    assert probs[3] == pytest.approx(0.9, abs=1e-5)


def test_run_inference_class_fallback_no_output_names():
    from hives.inference.model import run_inference

    model = MagicMock()
    model._clase_names = None  # preevee creación de MagicMock
    raw_probs = [0.0, 0.95, 0.05]
    model.predict.return_value = np.array([raw_probs])
    # Lanza Attribute Error
    type(model).output_names = PropertyMock(side_effect=AttributeError)

    clase, _ = run_inference(model, [0.1] * 3)
    assert clase == "Clase_1"


def test_run_inference_probs_rounded():
    from hives.inference.model import run_inference
    from hives.reports.pdf_report import HONEY_CLASSES

    model = MagicMock()
    model._clase_names = None  # preevee creación de MagicMock
    raw_probs = [1 / 12] * 12
    model.predict.return_value = np.array([raw_probs])
    model.output_names = list(HONEY_CLASSES)

    _, probs = run_inference(model, [0.1] * 18)
    for p in probs:
        # Se aproxima a 6 decimales
        assert p == round(p, 6)


def test_run_inference_argmax_correctness():
    from hives.inference.model import run_inference

    model = MagicMock()
    model._clase_names = None  # preevee creación de MagicMock
    raw_probs = [0.0, 0.95, 0.05]
    model.predict.return_value = np.array([raw_probs])
    model.output_names = ["Clase_0", "Clase_1", "Clase_2"]

    clase, probs = run_inference(model, [0.1] * 3)
    assert clase == "Clase_1"
    assert len(probs) == 3


def test_run_inference_all_zero_probs():
    from hives.inference.model import run_inference

    model = MagicMock()
    model._clase_names = None  # preevee creación de MagicMock
    raw_probs = [0.0] * 12
    model.predict.return_value = np.array([raw_probs])
    model.output_names = [f"Clase_{i}" for i in range(12)]

    clase, probs = run_inference(model, [0.0] * 12)
    assert clase == "Clase_0"  # se elige la primer clase
    assert len(probs) == 12
