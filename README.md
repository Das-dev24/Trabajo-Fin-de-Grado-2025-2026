# HIVES: Honey Identification and Verification by Spectroscopy

![Python](https://img.shields.io/badge/Python-3.10-blue)
![TensorFlow](https://img.shields.io/badge/TensorFlow-AI-orange)
![PyQt6](https://img.shields.io/badge/PyQt6-GUI-green)
![Status](https://img.shields.io/badge/Estado-Desarrollo-yellow)

**HIVES** es una aplicación de escritorio desarrollada para optimizar y reducir los costes del análisis de muestras de miel. Utiliza técnicas de espectrometría combinadas con Inteligencia Artificial para clasificar de forma automática el tipo de miel analizada.

*Proyecto desarrollado como Trabajo de Fin de Grado (TFG) en Ingeniería Informática para la Universidad de Burgos (UBU).*

## Características principales

* **Conexión Hardware:** Captura automatizada de datos espectrométricos mediante comunicación por puerto serie con un sensor SparkFun AS7265X controlado por Arduino.
* **Inteligencia Artificial:** Procesamiento e inferencia de datos utilizando un modelo de red neuronal preentrenado con TensorFlow capaz de clasificar 5 tipos de miel.
* **Interfaz Gráfica:** Interfaz reactiva e intuitiva construida con PyQt6, con soporte de concurrencia (hilos workers) para evitar bloqueos durante la captura y el análisis.
* **Histórico Local:** Persistencia de todos los análisis realizados en una base de datos SQLite ligera y sin dependencias externas.
* **Reportes en PDF:** Generación automática de informes técnicos detallados con los resultados del análisis, espectros y métricas de clasificación.
* **Calibración Integrada:** Flujo de calibración blanco/oscuro incorporado para garantizar la precisión de las lecturas espectrales.

## Requisitos previos

### Hardware

* Placa compatible con Arduino (Uno, Nano, Mega, etc.)
* Sensor espectrométrico **SparkFun AS7265X** (triple sensor de 18 canales: 410–940 nm)
* Cable USB para comunicación serie

### Software

| Requisito | Versión |
|---|---|
| Python | 3.10 – 3.13 (TensorFlow) |
| Arduino IDE | Cualquier versión reciente |
| Sistema operativo | Windows 10/11, macOS o Linux |

### Dependencias Python

El archivo `requirements.txt` incluye:

| Paquete | Propósito |
|---|---|
| `PyQt6` | Interfaz gráfica de usuario |
| `pyserial` | Comunicación serie con el Arduino |
| `tensorflow` | Carga y ejecución del modelo de IA |
| `numpy` | Procesamiento numérico de espectros |
| `matplotlib` | Visualización de espectros en la GUI |
| `fpdf2` | Generación de reportes PDF |
| `pytest` | Ejecución de tests unitarios |
| `pytest-qt` | Tests de la interfaz gráfica |
| `pytest-mock` | Mocking en tests |

## Instalación

Hay dos formas de poner en marcha HIVES: generar el **ejecutable autocontenido** con
los scripts de build (recomendado para uso normal) o ejecutar **desde código fuente**
(recomendado para desarrollo).

### Opción A — Ejecutable (recomendado)

No necesitas gestionar Python ni dependencias manualmente: el script de build elige un
intérprete compatible, crea un entorno aislado, instala todo y empaqueta la aplicación.

1. **Clonar el repositorio:**

```bash
git clone https://github.com/tuusuario/HIVES.git
cd HIVES
```

2. **Ejecutar el script de build de tu sistema operativo:**

```powershell
# Windows
.\build_windows.ps1
```

```bash
# macOS
chmod +x build_macos.sh && ./build_macos.sh

# Linux
chmod +x build_linux.sh && ./build_linux.sh
```

> Consulta la sección [Construcción del ejecutable](#construcción-del-ejecutable) para
> los detalles (requisito de Python 3.9–3.13 por TensorFlow y override del intérprete
> con `PYTHON` / `$env:PYTHON`).

3. **Lanzar la aplicación generada:**

| Sistema | Artefacto |
|---|---|
| Windows | `dist\HIVES\HIVES.exe` |
| macOS | `dist/HIVES.app` |
| Linux | `dist/HIVES/HIVES` |

> **Sin pasos extra:** el modelo de IA va incluido en el paquete y la base de datos
> SQLite se crea automáticamente en `data/` (junto al ejecutable) la primera vez que
> arranca la aplicación.

### Opción B — Desde código fuente (desarrollo)

1. **Clonar el repositorio:**

```bash
git clone https://github.com/tuusuario/HIVES.git
cd HIVES
```

2. **Crear y activar un entorno virtual:**

```bash
python -m venv venv
# Windows
venv\Scripts\activate
# macOS / Linux
source venv/bin/activate
```

3. **Instalar dependencias:**

```bash
pip install -r requirements.txt
```

4. **Ejecutar la aplicación:**

```bash
python src/main.py
```

> La base de datos se inicializa automáticamente al arrancar. Si quieres prepararla sin
> abrir la GUI, ejecuta desde el directorio `src/`:
> ```bash
> python -c "from hives.core.database import seed_database; seed_database()"
> ```

### Preparar el hardware (opcional)

Aplica a ambas opciones:

- Abre `arduino/LecturasParaInterfaz.ino` con Arduino IDE.
- Instala la librería **SparkFun AS7265X** desde el Gestor de Librerías.
- Conecta el sensor al Arduino siguiendo el esquema de pines I²C.
- Sube el sketch al Arduino.

## Uso

Si generaste el ejecutable (Opción A), basta con lanzar el binario correspondiente de
`dist/` (`HIVES.exe`, `HIVES.app` o `HIVES`). Para ejecutar desde código fuente
(Opción B), arranca desde la raíz del proyecto:

```bash
python src/main.py
```

### Flujo de trabajo

1. **Conectar:** Selecciona el puerto serie donde está conectado el Arduino.
2. **Calibrar:** Realiza una calibración oscuro/blanco siguiendo las instrucciones en pantalla.
3. **Escanear:** Coloca la muestra de miel y pulsa "Escanear". La aplicación capturará múltiples lecturas y calculará el espectro medio normalizado.
4. **Clasificar:** El modelo de IA procesa el espectro y muestra el tipo de miel predicho con su nivel de confianza.
5. **Guardar:** Los resultados se almacenan automáticamente en el historial local.
6. **Exportar:** Genera un reporte PDF con los detalles del análisis.

## Estructura del proyecto

```text
HIVES/
├── arduino/            # Código fuente (C/C++) para el microcontrolador del espectrómetro
├── assets/             # Recursos gráficos de la interfaz (iconos, logos)
├── data/               # Almacenamiento local (base de datos SQLite)
├── models/             # Archivos de la red neuronal (.h5)
├── src/                # Código fuente principal de la aplicación Python
│   └── main.py         # Punto de entrada de la aplicación
├── requirements.txt    # Dependencias del proyecto Python
└── README.md           # Documentación del repositorio
