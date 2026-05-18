"""
Configuración centralizada del dashboard.
"""

from typing import Dict, List
from enum import Enum

# ========== CONFIGURACIÓN DE COLUMNAS ESPERADAS ==========

EXPECTED_COLUMNS = [
    "ID",
    "CARGO/ROL",
    "LOCAL",
    "ESTADO",
    "PROXIMO PASO",
    "RESPONSABLE PROX PASO",
    "DIAS",
    "CRITICIDAD",
]

# Mapeo de columnas reales a nombres estándar
COLUMN_MAPPING = {
    "DÍAS": "DIAS",
    "DÍA": "DIAS",
    "DIAS": "DIAS",
    "DÍA": "DIAS",
    "PRÓXIMO PASO": "PROXIMO PASO",
    "PROXIMO PASO": "PROXIMO PASO",
    "PRÓXIMO": "PROXIMO PASO",
    "RESPONSABLE PROX PASO": "RESPONSABLE PROX PASO",
    "Vacante": "CARGO/ROL",
    "CARGO/ROL": "CARGO/ROL",
    "Semáforo": "CRITICIDAD",
    "CRITICIDAD": "CRITICIDAD",
    "# DÍas": "DIAS",
    "ESTADO": "ESTADO",
    "ID": "ID",
    "LOCAL": "LOCAL",
    "MERCADO": "MERCADO",
    "DÍAS SIN AVANZAR": "DIAS SIN AVANZAR",
    "DIAS SIN AVANZAR": "DIAS SIN AVANZAR",
}

# ========== CONFIGURACIÓN DE FILTROS ==========

AVAILABLE_FILTERS = [
    "MERCADO",
    "RESPONSABLE PROX PASO",
    "CARGO/ROL",
    "PROXIMO PASO",
    "ESTADO",
    "CRITICIDAD",
]

# ========== CONFIGURACIÓN DE GRÁFICOS ==========

CHARTS_CONFIG = {
    "criticidad": {
        "column": "CRITICIDAD",
        "type": "doughnut",
    },
    "mercado": {
        "column": "MERCADO",
        "type": "doughnut",
        "top_n": 8,
    },
    "responsable": {
        "column": "RESPONSABLE PROX PASO",
        "type": "bar",
        "top_n": 10,
    },
    "rol": {
        "column": "CARGO/ROL",
        "type": "doughnut",
        "top_n": 8,
    },
    "proximo_paso": {
        "column": "PROXIMO PASO",
        "type": "bar",
        "top_n": 8,
    },
    "estado": {
        "column": "ESTADO",
        "type": "doughnut",
    },
    "tiempo_abierto": {
        "column": "DIAS",
        "type": "bar",
    },
    "dias_sin_avance": {
        "column": "DIAS SIN AVANZAR",
        "type": "bar",
        "top_n": 10,
    },
    "criticidad_responsable": {
        "type": "custom",
        "name": "criticidad_responsable",
    },
    "promedio_estado": {
        "type": "custom",
        "name": "promedio_estado",
    },
    "criticas_responsable": {
        "type": "custom",
        "name": "criticas_responsable",
    },
}

# ========== COLORES ==========

CRITICIDAD_COLORS = {
    "ROJO": "#ea1100",
    "ROJA": "#ea1100",
    "CRITICA": "#ea1100",
    "AMARILLO": "#ffc220",
    "AMARILLA": "#ffc220",
    "ATENCION": "#ffc220",
    "VERDE": "#2a8703",
    "NORMAL": "#2a8703",
    "SIN CLASIFICAR": "#999999",
}

WALMART_COLORS = {
    "blue": "#0053e2",
    "yellow": "#ffc220",
    "red": "#ea1100",
    "green": "#2a8703",
}

# ========== OTROS ==========

CACHE_TTL = 300  # 5 minutos
AUTO_RELOAD_INTERVAL = 300  # 5 minutos
