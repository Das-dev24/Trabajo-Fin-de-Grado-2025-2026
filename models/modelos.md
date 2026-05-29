# Modelos de clasificación de miel

## Datasets

| Archivo | Notebook | Columna objetivo |
|---|---|---|
| `dataset.csv` | `pruebaTensorDataSetCorregido.ipynb` | `Class` |
| `dataset_completo_40036_v2.csv` | `pruebaColab.ipynb` | `Tipo` |

**Columnas**: 18 longitudes de onda (410–940 nm) + auxiliares (`L`, `B`, `A`, objetivo).

**Preprocesado** (ambos notebooks):
- Eliminación de clases con < 10 muestras
- Codificación con `sklearn.preprocessing.LabelEncoder`
- Imputación de NaN con `SimpleImputer` (mediana)
- Estandarización con `StandardScaler`

---

## Modelo original — `pruebaTensorDataSetCorregido.ipynb`

- Red neuronal `keras.Sequential` con capas `Dense` + `softmax`
- Guardado vía `ModelCheckpoint` durante entrenamiento:
  - `mejor_resultado.keras` — primera ejecución
  - `mejor_modelo_final.keras` — mejor modelo tras hiperparámetros
- `LabelEncoder` usado para codificar `y`, pero `le.classes_` **nunca se persistió**
- ➜ Las clases reales se perdían al cargar el modelo; la inferencia mostraba `Clase_0`, `Clase_1`, ...

---

## Modelo nuevo — `pruebaColab.ipynb`

### Entrenamiento
1. **`XGBClassifier`** con `GridSearchCV` (5-fold, hiperparámetros: `max_depth`, `learning_rate`, `n_estimators`, `subsample`)
2. El XGBoost genera *soft labels* (probabilidades predichas sobre el conjunto de train)
3. Una red **`keras.Sequential`** (capas: 128 → 64 → 32 → softmax) se entrena para imitar esas soft labels usando `categorical_crossentropy`
4. El modelo se guarda como **`mejor_modelo.keras`**

### Clases (5 tipos de miel)

Según los reportes de `RandomForest` / `XGBoost` dentro del notebook:

| Índice | Clase |
|---|---|
| 0 | Miel Jaramago |
| 1 | Miel Sintética |
| 2 | Miel de Bosque |
| 3 | Miel de Retama |
| 4 | Miel de milflores |

Estas clases están almacenadas en `le.classes_` (del `LabelEncoder`).

---

## Problema detectado

`model.output_names` en un modelo `keras.Sequential` devuelve **nombres de tensor de salida** (ej. `"dense_1"`), **no nombres de clase humanamente legibles**. El código de inferencia (`src/hives/inference/model.py`) intentaba usar `output_names` y, al fallar, generaba nombres `Clase_N` de relleno, sin importar qué modelo se hubiese cargado.

---

## Cambios realizados

### 1. `models/pruebaColab.ipynb`
Se añadió al final de la celda de entrenamiento Keras (tras `model_keras.save(...)`):

```python
import json
with open('clases.json', 'w', encoding='utf-8') as f:
    json.dump(le.classes_.tolist(), f, ensure_ascii=False)
```

Esto genera **`clases.json`** junto al modelo, con las clases reales en el orden correcto.

### 2. `src/hives/inference/model.py`

**`load_model()`**: después de cargar el `.keras`, busca `clases.json` en el mismo directorio y lo asigna como `model._clase_names`.

**`run_inference()`**: la resolución de nombres ahora sigue este orden:

```
model._clase_names  (del JSON)       ← nuevo
model.output_names  (tensor names)   ← existente
Clase_N             (fallback)       ← existente
```

### 3. `tests/test_inference.py`
- Corregido nombre de archivo en `test_load_model_returns_model_object` (`model.keras` → `mejor_modelo.keras`)
- Añadido `model._clase_names = None` en tests con `MagicMock` para evitar la auto-creación de atributos (Python 3.13).

---

## Flujo final

```
pruebaColab.ipynb
    │
    ├── mejor_modelo.keras    (red entrenada)
    └── clases.json           (nombres reales: le.classes_)
                │
                ▼
         load_model()
                │
                ├── tf.keras.models.load_model() → modelo
                └── asigna model._clase_names desde clases.json
                │
                ▼
         run_inference()
                │
                ├── 1. model._clase_names  → nombre real
                ├── 2. model.output_names  → nombre de tensor
                └── 3. Clase_N             → fallback
```

---

## Archivos generados en `models/`

| Archivo | Origen |
|---|---|
| `mejor_modelo.keras` | Guardado por `pruebaColab.ipynb` (celda Keras) |
| `clases.json` | Generado automáticamente al ejecutar la celda Keras |
| `mejor_modelo_final.keras` | Modelo original de `pruebaTensorDataSetCorregido.ipynb` |
| `mejor_resultado.keras` | Modelo original de `pruebaTensorDataSetCorregido.ipynb` |
| `datasets.csv` / `dataset_completo_40036_v2.csv` | Datos de entrada |
