import pytest
from unittest.mock import MagicMock
import numpy as np

# -------------------------------------------------------------------- #
#                      Carga del modelo                                #
# -------------------------------------------------------------------- #


def test_load_model_returns_none_xgb_unavailable(mocker, tmp_path):
    mocker.patch("hives.inference.model.XGB_AVAILABLE", False)
    from hives.inference.model import load_model
    assert load_model(str(tmp_path)) is None


def test_load_model_xgb_not_available_sets_error(mocker, tmp_path):
    mocker.patch("hives.inference.model.XGB_AVAILABLE", False)
    import hives.inference.model as model_mod
    model_mod.load_model(str(tmp_path))
    assert "XGBoost" in model_mod.last_load_error


def test_load_model_model_dir_not_exist(mocker, tmp_path):
    mocker.patch("hives.inference.model.XGB_AVAILABLE", True)
    mocker.patch("hives.inference.model.xgb", mocker.MagicMock(), create=True)
    from hives.inference.model import load_model
    nonexistent = str(tmp_path / "nope")
    assert load_model(nonexistent) is None


def test_load_model_load_exception(mocker, tmp_path):
    (tmp_path / "mejor_modelo.json").touch()
    mock_xgb = mocker.MagicMock()
    mock_xgb.Booster.side_effect = Exception("load failed")
    mocker.patch("hives.inference.model.XGB_AVAILABLE", True)
    mocker.patch("hives.inference.model.xgb", mock_xgb, create=True)
    from hives.inference.model import load_model
    assert load_model(str(tmp_path)) is None


def test_load_model_missing_clases_json(mocker, tmp_path):
    (tmp_path / "mejor_modelo.json").touch()
    mock_xgb = mocker.MagicMock()
    mock_booster = mocker.MagicMock(spec=object)
    mock_xgb.Booster.return_value = mock_booster
    mocker.patch("hives.inference.model.XGB_AVAILABLE", True)
    mocker.patch("hives.inference.model.xgb", mock_xgb, create=True)
    from hives.inference.model import load_model
    result = load_model(str(tmp_path))
    assert result is mock_booster


def test_load_model_returns_none_no_json_file(mocker, tmp_path):
    mocker.patch("hives.inference.model.XGB_AVAILABLE", True)
    mocker.patch("hives.inference.model.xgb", MagicMock(), create=True)
    from hives.inference.model import load_model
    assert load_model(str(tmp_path)) is None


def test_load_model_returns_model_object(mocker, tmp_path):
    (tmp_path / "mejor_modelo.json").touch()
    mock_xgb = MagicMock()
    mock_booster = MagicMock()
    mock_xgb.Booster.return_value = mock_booster
    mocker.patch("hives.inference.model.XGB_AVAILABLE", True)
    mocker.patch("hives.inference.model.xgb", mock_xgb, create=True)
    from hives.inference.model import load_model
    result = load_model(str(tmp_path))
    assert result is mock_booster


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

    model = MagicMock()
    model._clase_names = None
    raw_probs = [0.0] * 5
    raw_probs[3] = 0.9
    raw_probs[0] = 0.1
    model.predict.return_value = np.array([raw_probs])

    clases = ["Miel Jaramago", "Miel Sintética", "Miel de Bosque",
              "Miel de Retama", "Miel de milflores"]
    model._clase_names = list(clases)

    clase, probs = run_inference(model, [0.1] * 18)
    assert clase == "Miel de Retama"
    assert len(probs) == 5
    assert probs[3] == pytest.approx(0.9, abs=1e-5)


def test_run_inference_class_fallback_no_clase_names():
    from hives.inference.model import run_inference

    model = MagicMock()
    model._clase_names = None
    raw_probs = [0.0, 0.95, 0.05]
    model.predict.return_value = np.array([raw_probs])

    clase, _ = run_inference(model, [0.1] * 3)
    assert clase == "Clase_1"


def test_run_inference_probs_rounded():
    from hives.inference.model import run_inference

    model = MagicMock()
    model._clase_names = None
    raw_probs = [1 / 5] * 5
    model.predict.return_value = np.array([raw_probs])
    model._clase_names = [f"Clase_{i}" for i in range(5)]

    _, probs = run_inference(model, [0.1] * 18)
    for p in probs:
        assert p == round(p, 6)


def test_run_inference_argmax_correctness():
    from hives.inference.model import run_inference

    model = MagicMock()
    model._clase_names = None
    raw_probs = [0.0, 0.95, 0.05]
    model.predict.return_value = np.array([raw_probs])
    model._clase_names = ["Clase_0", "Clase_1", "Clase_2"]

    clase, probs = run_inference(model, [0.1] * 3)
    assert clase == "Clase_1"
    assert len(probs) == 3


def test_run_inference_all_zero_probs():
    from hives.inference.model import run_inference

    model = MagicMock()
    model._clase_names = None
    raw_probs = [0.0] * 5
    model.predict.return_value = np.array([raw_probs])
    model._clase_names = [f"Clase_{i}" for i in range(5)]

    clase, probs = run_inference(model, [0.0] * 3)
    assert clase == "Clase_0"
    assert len(probs) == 5
