from pathlib import Path

try:
    import numpy as np
    import tensorflow as tf
    TF_AVAILABLE = True
except ImportError:
    TF_AVAILABLE = False


def load_model(model_path: str):
    """Carga el primer archivo .keras encontrado en model_path. Devuelve None si no está disponible."""
    if not TF_AVAILABLE:
        return None
    keras_files = list(Path(model_path).glob("*.keras"))
    if not keras_files:
        return None
    try:
        return tf.keras.models.load_model(str(keras_files[0]))
    except Exception:
        return None


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

    try:
        clases = model.output_names
    except AttributeError:
        clases = [f"Clase_{i}" for i in range(len(probs))]

    clase = clases[idx] if idx < len(clases) else f"Clase_{idx}"
    return clase, [round(p, 6) for p in probs]
