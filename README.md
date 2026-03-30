# 🍯 HIVES: Honey Identification and Verification by Spectroscopy

![Python](https://img.shields.io/badge/Python-3.10-blue)
![TensorFlow](https://img.shields.io/badge/TensorFlow-AI-orange)
![PyQt6](https://img.shields.io/badge/PyQt6-GUI-green)
![Status](https://img.shields.io/badge/Estado-Desarrollo-yellow)

**HIVES** es una aplicación de escritorio desarrollada para optimizar y reducir los costes del análisis de muestras de miel. Utiliza técnicas de espectrometría combinadas con Inteligencia Artificial para clasificar de forma automática el tipo de miel analizada.

*Proyecto desarrollado como Trabajo de Fin de Grado (TFG) en Ingeniería Informática para la Universidad de Burgos (UBU).*

## ✨ Características principales

* **🔌 Conexión Hardware:** Captura automatizada de datos espectrométricos mediante comunicación por puerto serie con el dispositivo sensor.
* **🧠 Inteligencia Artificial:** Procesamiento e inferencia de datos utilizando un modelo de red neuronal preentrenado con TensorFlow.
* **📊 Interfaz Gráfica:** Interfaz reactiva e intuitiva construida con PyQt6, con soporte de concurrencia (hilos) para evitar bloqueos durante el análisis.
* **🗄️ Histórico Local:** Persistencia de todos los análisis realizados en una base de datos SQLite ligera y libre de dependencias externas.
* **📄 Reportes en PDF:** Generación automática de informes técnicos detallados con los resultados y métricas del análisis.

## 🛠️ Tecnologías utilizadas

* **Lenguaje Principal:** Python 3.10
* **Microcontrolador:** C/C++ (Arduino)
* **GUI:** PyQt6
* **Machine Learning:** TensorFlow
* **Comunicaciones:** PySerial
* **Exportación:** FPDF
* **Base de Datos:** SQLite3 (Nativa)

## 📂 Estructura del proyecto

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
