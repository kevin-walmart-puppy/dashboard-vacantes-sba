"""
Dashboard Vacantes SBA - Versión Refactorizada v3
Carga manual de archivos Excel
"""

import os
import logging
import pandas as pd
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
# from starlette.middleware.gzip import GZIPMiddleware  # Comentado por compatibilidad de versión
from fastapi.responses import HTMLResponse
from typing import Optional, Dict, Any, List
from datetime import datetime
import tempfile
from threading import Lock

# ========== LOGGING ==========
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Importar procesadores
from data_processor import DataProcessor
from config import EXPECTED_COLUMNS

# ========== RUTAS ABSOLUTAS ==========
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
HTML_FILE = os.path.join(BASE_DIR, "index.html")

# ========== CONFIGURACIÓN ==========

app = FastAPI(title="Dashboard Vacantes SBA v3", description="Carga manual de archivos")



# ========== CORS MIDDLEWARE ==========
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)





# ========== CLASE PARA ESTADO THREAD-SAFE ==========

class DataStore:
    """Gestor de estado thread-safe para el DataFrame actual."""
    def __init__(self):
        self.df: Optional[pd.DataFrame] = None
        self.last_reload: Optional[datetime] = None
        self.file_name: Optional[str] = None
        self.lock = Lock()
    
    def set_data(self, df: pd.DataFrame, file_name: str) -> None:
        """Establece los datos de forma segura."""
        with self.lock:
            self.df = df
            self.file_name = file_name
            self.last_reload = datetime.now()
            logger.info(f"DataStore actualizado: {file_name} ({len(df)} filas)")
    
    def get_data(self) -> Optional[pd.DataFrame]:
        """Obtiene el DataFrame de forma segura."""
        with self.lock:
            return self.df.copy() if self.df is not None else None
    
    def get_info(self) -> Dict[str, Any]:
        """Obtiene información de estado de forma segura."""
        with self.lock:
            return {
                "loaded": self.df is not None,
                "file_name": self.file_name,
                "rows": len(self.df) if self.df is not None else 0,
                "columns": len(self.df.columns) if self.df is not None else 0,
                "last_reload": self.last_reload.isoformat() if self.last_reload else None,
            }

data_store = DataStore()

# ========== ESTADO GLOBAL ==========

_current_dataframe: Optional[pd.DataFrame] = None
_last_reload: Optional[datetime] = None
_file_name: Optional[str] = None


# ========== ENDPOINTS - INTERFAZ ==========

@app.get("/", response_class=HTMLResponse)
async def root():
    """Retorna la página principal."""
    if not os.path.exists(HTML_FILE):
        raise HTTPException(status_code=404, detail="index.html no encontrado")
    with open(HTML_FILE, "r", encoding="utf-8") as f:
        return f.read()


@app.get("/health")
async def health():
    """Endpoint de salud para monitoreo."""
    return {
        "status": "ok",
        "timestamp": datetime.now().isoformat(),
        "data_loaded": _current_dataframe is not None,
        "rows": len(_current_dataframe) if _current_dataframe is not None else 0,
    }


@app.get("/api/diagnose")
async def diagnose():
    """Endpoint de diagnóstico para debugging."""
    return {
        "server_status": "ok",
        "data_loaded": _current_dataframe is not None,
        "data_rows": len(_current_dataframe) if _current_dataframe is not None else 0,
        "data_columns": list(_current_dataframe.columns) if _current_dataframe is not None else [],
        "timestamp": datetime.now().isoformat(),
        "message": "Dashboard funcionando correctamente",
    }


# ========== ENDPOINTS - CARGA DE ARCHIVO ==========

@app.post("/api/upload")
async def upload_file(file: UploadFile = File(...)) -> Dict[str, Any]:
    """Carga un archivo Excel y procesa los datos."""
    global _current_dataframe, _last_reload, _file_name
    
    logger.info(f"Iniciando carga de archivo: {file.filename}")
    tmp_path = None  # Inicializar para usar en finally

    if not file.filename.endswith(('.xlsx', '.xls')):
        logger.warning(f"Archivo rechazado (extensión inválida): {file.filename}")
        raise HTTPException(status_code=400, detail="Solo se aceptan archivos Excel (.xlsx, .xls)")

    try:
        # Leer archivo
        contents = await file.read()
        file_size_mb = len(contents) / (1024 * 1024)
        logger.info(f"Archivo leído: {file_size_mb:.2f} MB")
        
        # Validar tamaño (máximo 50 MB)
        MAX_FILE_SIZE_MB = 50
        if file_size_mb > MAX_FILE_SIZE_MB:
            logger.error(f"Archivo demasiado grande: {file_size_mb:.2f} MB (máximo: {MAX_FILE_SIZE_MB} MB)")
            raise HTTPException(status_code=413, detail=f"Archivo muy grande ({file_size_mb:.1f}MB, máximo {MAX_FILE_SIZE_MB}MB)")
        
        # Guardar temporalmente
        with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as tmp:
            tmp.write(contents)
            tmp_path = tmp.name
            logger.info(f"Archivo temporal creado: {tmp_path}")

        # Leer con pandas
        try:
            # Intentar leer hoja "CANDIDATOS" primero
            df = pd.read_excel(tmp_path, sheet_name="CANDIDATOS")
            logger.info(f"Hoja CANDIDATOS leída: {len(df)} filas")
        except:
            try:
                # Intentar "Gestión"
                df = pd.read_excel(tmp_path, sheet_name="Gestión", skiprows=1)
                logger.info(f"Hoja Gestión leída: {len(df)} filas")
            except:
                # Usar primera hoja
                df = pd.read_excel(tmp_path)
                logger.info(f"Primera hoja leída: {len(df)} filas")

        if df.empty:
            logger.error("El archivo Excel está vacío")
            raise HTTPException(status_code=400, detail="El archivo está vacío")
        
        # Procesar PRIMERO (normalizar columnas)
        processor = DataProcessor(df)
        processor.clean()
        df_cleaned = processor.df
        
        logger.info(f"Columnas después de limpiar: {list(df_cleaned.columns)}")
        
        # Validar que tenga columnas esperadas
        missing_cols = [col for col in EXPECTED_COLUMNS if col not in df_cleaned.columns]
        if missing_cols:
            logger.error(f"Columnas faltantes: {', '.join(missing_cols)}")
            raise HTTPException(status_code=400, detail=f"El archivo debe tener estas columnas: {', '.join(EXPECTED_COLUMNS)}")
        
        logger.info(f"Validación de columnas OK: {len(df_cleaned.columns)} columnas")
        
        # Usar el DataFrame ya procesado
        _current_dataframe = df_cleaned
        _last_reload = datetime.now()
        _file_name = file.filename
        logger.info(f"Archivo procesado exitosamente: {file.filename} ({len(_current_dataframe)} filas)")

        return {
            "success": True,
            "message": f"Archivo '{file.filename}' cargado exitosamente",
            "rows": len(_current_dataframe),
            "columns": len(_current_dataframe.columns),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error al procesar archivo: {str(e)}")
        return {
            "success": False,
            "message": f"Error al procesar archivo: {str(e)}",
        }
    finally:
        # Limpiar archivo temporal (siempre se ejecuta)
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.unlink(tmp_path)
                logger.info(f"Archivo temporal eliminado: {tmp_path}")
            except Exception as e:
                logger.warning(f"No se pudo eliminar archivo temporal {tmp_path}: {e}")


@app.get("/api/status")
async def get_status() -> Dict[str, Any]:
    """Retorna estado actual del dashboard."""
    if _current_dataframe is None:
        return {"loaded": False, "message": "No hay archivo cargado"}

    return {
        "loaded": True,
        "file_name": _file_name,
        "rows": len(_current_dataframe),
        "columns": len(_current_dataframe.columns),
        "last_reload": _last_reload.isoformat() if _last_reload else None,
    }


# ========== ENDPOINTS - DATOS CRUDOS ==========

@app.get("/api/kpis")
async def get_kpis(
    mercado: Optional[str] = None,
    responsable: Optional[str] = None,
    rol: Optional[str] = None,
    proximo_paso: Optional[str] = None,
    estado: Optional[str] = None,
    criticidad: Optional[str] = None,
) -> Dict[str, Any]:
    """Retorna KPIs principales."""
    if _current_dataframe is None or _current_dataframe.empty:
        return {
            "total_vacantes": 0,
            "vacantes_criticas": 0,
            "sin_gestion": 0,
            "promedio_dias": 0.0,
            "time_to_hire": 0,
        }

    processor = DataProcessor(_current_dataframe)
    processor.clean()
    
    # Convertir strings separados por comas a listas
    processor.filter(
        mercado=mercado.split(",") if mercado else None,
        responsable=responsable.split(",") if responsable else None,
        rol=rol.split(",") if rol else None,
        proximo_paso=proximo_paso.split(",") if proximo_paso else None,
        estado=estado.split(",") if estado else None,
        criticidad=criticidad.split(",") if criticidad else None,
    )

    return processor.calculate_kpis()


@app.get("/api/filters")
async def get_filters() -> Dict[str, list]:
    """Retorna opciones disponibles para cada filtro."""
    if _current_dataframe is None or _current_dataframe.empty:
        return {
            "mercados": ["TODOS"],
            "responsables": ["TODOS"],
            "roles": ["TODOS"],
            "pasos": ["TODOS"],
            "estados": ["TODOS"],
        }

    processor = DataProcessor(_current_dataframe)
    processor.clean()
    filters = processor.get_available_filters()

    return {
        "mercados": filters.get("MERCADO", ["TODOS"]),
        "responsables": filters.get("RESPONSABLE PROX PASO", ["TODOS"]),
        "roles": filters.get("CARGO/ROL", ["TODOS"]),
        "pasos": filters.get("PROXIMO PASO", ["TODOS"]),
        "estados": filters.get("ESTADO", ["TODOS"]),
        "criticidades": filters.get("CRITICIDAD", ["TODOS"]),
    }


# ========== ENDPOINTS - GRÁFICOS ==========

def _get_chart(
    chart_name: str,
    mercado: Optional[str] = None,
    responsable: Optional[str] = None,
    rol: Optional[str] = None,
    proximo_paso: Optional[str] = None,
    estado: Optional[str] = None,
    criticidad: Optional[str] = None,
) -> Dict[str, Any]:
    """Genera datos para un gráfico."""
    if _current_dataframe is None or _current_dataframe.empty:
        return {"labels": [], "data": []}

    processor = DataProcessor(_current_dataframe)
    processor.clean()
    processor.filter(
        mercado=mercado.split(",") if mercado else None,
        responsable=responsable.split(",") if responsable else None,
        rol=rol.split(",") if rol else None,
        proximo_paso=proximo_paso.split(",") if proximo_paso else None,
        estado=estado.split(",") if estado else None,
        criticidad=criticidad.split(",") if criticidad else None,
    )

    return processor.get_chart_data(chart_name)


@app.get("/api/charts/criticidad")
async def chart_criticidad(
    mercado: Optional[str] = None,
    responsable: Optional[str] = None,
    rol: Optional[str] = None,
    proximo_paso: Optional[str] = None,
    estado: Optional[str] = None,
    criticidad: Optional[str] = None,
) -> Dict[str, Any]:
    return _get_chart("criticidad", mercado, responsable, rol, proximo_paso, estado, criticidad)


@app.get("/api/charts/responsable")
async def chart_responsable(
    mercado: Optional[str] = None,
    responsable: Optional[str] = None,
    rol: Optional[str] = None,
    proximo_paso: Optional[str] = None,
    estado: Optional[str] = None,
    criticidad: Optional[str] = None,
) -> Dict[str, Any]:
    return _get_chart("responsable", mercado, responsable, rol, proximo_paso, estado, criticidad)


@app.get("/api/charts/mercado")
async def chart_mercado(
    mercado: Optional[str] = None,
    responsable: Optional[str] = None,
    rol: Optional[str] = None,
    proximo_paso: Optional[str] = None,
    estado: Optional[str] = None,
    criticidad: Optional[str] = None,
) -> Dict[str, Any]:
    return _get_chart("mercado", mercado, responsable, rol, proximo_paso, estado, criticidad)


@app.get("/api/charts/rol")
async def chart_rol(
    mercado: Optional[str] = None,
    responsable: Optional[str] = None,
    rol: Optional[str] = None,
    proximo_paso: Optional[str] = None,
    estado: Optional[str] = None,
    criticidad: Optional[str] = None,
) -> Dict[str, Any]:
    return _get_chart("rol", mercado, responsable, rol, proximo_paso, estado, criticidad)


@app.get("/api/charts/proximo-paso")
async def chart_proximo_paso(
    mercado: Optional[str] = None,
    responsable: Optional[str] = None,
    rol: Optional[str] = None,
    proximo_paso: Optional[str] = None,
    estado: Optional[str] = None,
    criticidad: Optional[str] = None,
) -> Dict[str, Any]:
    return _get_chart("proximo_paso", mercado, responsable, rol, proximo_paso, estado, criticidad)


@app.get("/api/charts/estado")
async def chart_estado(
    mercado: Optional[str] = None,
    responsable: Optional[str] = None,
    rol: Optional[str] = None,
    proximo_paso: Optional[str] = None,
    estado: Optional[str] = None,
    criticidad: Optional[str] = None,
) -> Dict[str, Any]:
    return _get_chart("estado", mercado, responsable, rol, proximo_paso, estado, criticidad)


@app.get("/api/charts/dias-sin-avance")
async def chart_dias_sin_avance(
    mercado: Optional[str] = None,
    responsable: Optional[str] = None,
    rol: Optional[str] = None,
    proximo_paso: Optional[str] = None,
    estado: Optional[str] = None,
    criticidad: Optional[str] = None,
) -> Dict[str, Any]:
    return _get_chart("dias_sin_avance", mercado, responsable, rol, proximo_paso, estado, criticidad)


@app.get("/api/charts/criticidad-responsable")
async def chart_criticidad_responsable(
    mercado: Optional[str] = None,
    responsable: Optional[str] = None,
    rol: Optional[str] = None,
    proximo_paso: Optional[str] = None,
    estado: Optional[str] = None,
    criticidad: Optional[str] = None,
) -> Dict[str, Any]:
    return _get_chart("criticidad_responsable", mercado, responsable, rol, proximo_paso, estado, criticidad)


@app.get("/api/charts/promedio-estado")
async def chart_promedio_estado(
    mercado: Optional[str] = None,
    responsable: Optional[str] = None,
    rol: Optional[str] = None,
    proximo_paso: Optional[str] = None,
    estado: Optional[str] = None,
    criticidad: Optional[str] = None,
) -> Dict[str, Any]:
    return _get_chart("promedio_estado", mercado, responsable, rol, proximo_paso, estado, criticidad)


@app.get("/api/charts/criticas-responsable")
async def chart_criticas_responsable(
    mercado: Optional[str] = None,
    responsable: Optional[str] = None,
    rol: Optional[str] = None,
    proximo_paso: Optional[str] = None,
    estado: Optional[str] = None,
    criticidad: Optional[str] = None,
) -> Dict[str, Any]:
    return _get_chart("criticas_responsable", mercado, responsable, rol, proximo_paso, estado, criticidad)


@app.get("/api/charts/tiempo-abierto")
async def chart_tiempo_abierto(
    mercado: Optional[str] = None,
    responsable: Optional[str] = None,
    rol: Optional[str] = None,
    proximo_paso: Optional[str] = None,
    estado: Optional[str] = None,
    criticidad: Optional[str] = None,
) -> Dict[str, Any]:
    """Distribucion de vacantes por tiempo abierto."""
    return _get_chart("tiempo_abierto", mercado, responsable, rol, proximo_paso, estado, criticidad)


# ========== ENDPOINTS - TABLA ==========

@app.get("/api/table")
async def get_table(
    mercado: Optional[str] = None,
    responsable: Optional[str] = None,
    rol: Optional[str] = None,
    proximo_paso: Optional[str] = None,
    estado: Optional[str] = None,
    criticidad: Optional[str] = None,
    sort_by: str = "DIAS",
    limit: Optional[int] = None,
) -> Dict[str, Any]:
    """Retorna tabla detallada con formato."""
    if _current_dataframe is None or _current_dataframe.empty:
        return {"total": 0, "rows": []}

    processor = DataProcessor(_current_dataframe)
    processor.clean()
    processor.filter(
        mercado=mercado.split(",") if mercado else None,
        responsable=responsable.split(",") if responsable else None,
        rol=rol.split(",") if rol else None,
        proximo_paso=proximo_paso.split(",") if proximo_paso else None,
        estado=estado.split(",") if estado else None,
    )

    table_data = processor.get_table_data(sort_by=sort_by, limit=limit)
    return table_data


# ========== ENDPOINTS - INSIGHTS ==========

@app.get("/api/insights")
async def get_insights() -> Dict[str, Any]:
    """Retorna insights automáticos sobre los datos."""
    if _current_dataframe is None or _current_dataframe.empty:
        return {"insights": []}

    processor = DataProcessor(_current_dataframe)
    processor.clean()
    df = processor.get_filtered()

    insights = []

    # Insight 1: Vacantes críticas
    try:
        criticas = len(df[df.get("CRITICIDAD", "").astype(str).str.contains("ROJO|ROJA", case=False, na=False)])
        if criticas > 0:
            insights.append({
                "type": "alert",
                "icon": "🔴",
                "title": "Vacantes Críticas",
                "value": str(criticas),
                "description": f"{criticas} vacante(s) en estado crítico requieren atención inmediata",
            })
    except:
        pass

    # Insight 2: Sin gestión
    try:
        sin_gestion = len(df[pd.to_numeric(df.get("DIAS SIN AVANZAR", 0), errors="coerce") > 30])
        if sin_gestion > 0:
            insights.append({
                "type": "warning",
                "icon": "⏰",
                "title": "Sin Avance (>30 días)",
                "value": str(sin_gestion),
                "description": f"{sin_gestion} vacante(s) sin movimiento en más de 30 días",
            })
    except:
        pass

    # Insight 3: Promedio de días
    try:
        dias_mean = pd.to_numeric(df.get("DIAS", 0), errors="coerce").mean()
        insights.append({
            "type": "info",
            "icon": "📅",
            "title": "Promedio de Días Abiertos",
            "value": f"{dias_mean:.0f}",
            "description": f"Las vacantes están abiertas en promedio {dias_mean:.0f} días",
        })
    except:
        pass

    # Insight 4: Responsable con más carga
    try:
        resp_counts = df.get("RESPONSABLE PROX PASO", "").value_counts()
        if len(resp_counts) > 0:
            top_resp = resp_counts.index[0]
            count = resp_counts.values[0]
            insights.append({
                "type": "info",
                "icon": "👤",
                "title": "Mayor Carga de Trabajo",
                "value": str(count),
                "description": f"{top_resp} tiene {count} candidato(s) asignado(s)",
            })
    except:
        pass

    # Insight 5: Próximo paso más común
    try:
        paso_counts = df.get("PROXIMO PASO", "").value_counts()
        if len(paso_counts) > 0:
            top_paso = paso_counts.index[0]
            count = paso_counts.values[0]
            insights.append({
                "type": "info",
                "icon": "→",
                "title": "Próximo Paso Más Frecuente",
                "value": str(count),
                "description": f"{count} candidato(s) en: {top_paso}",
            })
    except:
        pass

    return {"insights": insights}


# ========== STATIC FILES (AL FINAL PARA FALLBACK) ==========
app.mount("/", StaticFiles(directory=BASE_DIR, html=False), name="static")


if __name__ == "__main__":
    import uvicorn

    
    uvicorn.run(app, host="0.0.0.0", port=8896)
