import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

last_load_error: str = ""

try:
    import numpy as np
    import tensorflow as tf
    TF_AVAILABLE = True
except (ImportError, OSError) as _tf_err:
    TF_AVAILABLE = False
    logger.warning("TensorFlow no está disponible — la inferencia no funcionará: %s", _tf_err)


def load_model(model_path: str):
    """Carga el primer archivo .keras encontrado en model_path y asigna nombres de clase si existe clases.json."""
    global last_load_error

    if not TF_AVAILABLE:
        last_load_error = "TensorFlow no está disponible en el sistema"
        logger.error("load_model: %s", last_load_error)
        return None

    model_dir = Path(model_path)
    logger.info("load_model: buscando en %s", model_dir)

    if not model_dir.is_dir():
        last_load_error = f"El directorio del modelo no existe: {model_dir}"
        logger.error("load_model: %s", last_load_error)
        return None

    keras_files = list(model_dir.glob("mejor_modelo.keras"))
    if not keras_files:
        contenido = list(model_dir.iterdir())
        last_load_error = f"No se encontró mejor_modelo.keras en {model_dir} (contiene: {contenido})"
        logger.error("load_model: %s", last_load_error)
        return None

    try:
        model = tf.keras.models.load_model(str(keras_files[0]))
        logger.info("load_model: modelo cargado correctamente desde %s", keras_files[0])
    except Exception as e:
        last_load_error = f"Error al cargar el modelo con tf.keras: {e}"
        logger.error("load_model: %s", last_load_error, exc_info=True)
        return None

    try:
        json_file = model_dir / "clases.json"
        if json_file.exists():
            with open(json_file, "r", encoding="utf-8") as f:
                model._clase_names = json.load(f)
            logger.info("load_model: clases.json cargado (%d clases)", len(model._clase_names))
        else:
            logger.warning("load_model: no se encontró clases.json en %s", model_dir)
    except Exception as e:
        logger.warning("load_model: error al leer clases.json: %s", e)

    last_load_error = ""
    return model


def run_inference(model, norm_vector: list) -> tuple:
    """
    Ejecuta el modelo sobre norm_vector (ya normalizado).

    Returns:
        (clase_miel: str, probabilidades: list[float])
    """
    if model is None:
        return "Sin modelo", [0.0]

    x     = np.array(norm_vector, dtype=np.float32).reshape(1, -1)
    probs = model.predict(x, verbose=0)[0].tolist()
    idx   = int(np.argmax(probs))

    clases = getattr(model, '_clase_names', None)
    if clases is None:
        try:
            clases = model.output_names
        except AttributeError:
            clases = [f"Clase_{i}" for i in range(len(probs))]

    clase = clases[idx] if idx < len(clases) else f"Clase_{idx}"
    return clase, [round(p, 6) for p in probs]
