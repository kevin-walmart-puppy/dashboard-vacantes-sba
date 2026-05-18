"""
Procesamiento y transformación de datos para dashboard.
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Any, Optional
from config import (
    AVAILABLE_FILTERS,
    CHARTS_CONFIG,
    CRITICIDAD_COLORS,
)


class DataProcessor:
    """Procesa y transforma datos para el dashboard."""

    def __init__(self, df: Optional[pd.DataFrame] = None):
        self.df = df
        self.df_processed = None

    def load(self, df: pd.DataFrame) -> "DataProcessor":
        """Carga un DataFrame."""
        self.df = df
        return self

    def clean(self) -> "DataProcessor":
        """Limpia y normaliza datos."""
        if self.df is None or self.df.empty:
            return self

        df = self.df.copy()

        # PASO 1: Normalizar nombres de columnas (remover acentos, espacios)
        new_columns = {}
        for col in df.columns:
            # Remover acentos
            normalized = col.replace("Á", "A").replace("á", "a").replace("À", "A").replace("à", "a")
            normalized = normalized.replace("É", "E").replace("é", "e").replace("È", "E").replace("è", "e")
            normalized = normalized.replace("Í", "I").replace("í", "i").replace("Ì", "I").replace("ì", "i")
            normalized = normalized.replace("Ó", "O").replace("ó", "o").replace("Ò", "O").replace("ò", "o")
            normalized = normalized.replace("Ú", "U").replace("ú", "u").replace("Ù", "U").replace("ù", "u")
            normalized = normalized.replace("Ñ", "N").replace("ñ", "n")
            # Convertir a mayúsculas
            normalized = normalized.upper().strip()
            new_columns[col] = normalized
        
        df.rename(columns=new_columns, inplace=True)
        
        # PASO 2: Aplicar mapeo de columnas conocidas
        from config import COLUMN_MAPPING
        df.rename(columns=COLUMN_MAPPING, inplace=True)

        # PASO 3: Llenar valores faltantes y convertir tipos
        for col in df.columns:
            try:
                if col in ["DIAS SIN AVANZAR", "DIAS", "LOCAL", "ID"]:
                    df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).astype(int)
                elif col in ["MERCADO", "RESPONSABLE PROX PASO", "RESPONSABLE"]:
                    df[col] = df[col].fillna("SIN ASIGNAR")
                elif col in ["CRITICIDAD", "SEMAFORO"]:
                    df[col] = df[col].fillna("SIN CLASIFICAR")
                else:
                    # Para otras columnas, convertir a string
                    df[col] = df[col].astype(str).str.strip()
            except Exception as e:
                import logging
                logging.warning(f"Error procesando columna {col}: {e}")
                continue

        self.df = df
        return self

    def filter(
        self,
        mercado: Optional[List[str]] = None,
        responsable: Optional[List[str]] = None,
        rol: Optional[List[str]] = None,
        proximo_paso: Optional[List[str]] = None,
        estado: Optional[List[str]] = None,
        criticidad: Optional[List[str]] = None,
    ) -> "DataProcessor":
        """Aplica filtros al DataFrame."""
        if self.df is None or self.df.empty:
            return self

        df = self.df.copy()

        if mercado and len(mercado) > 0:
            df = df[df.get("MERCADO", "").isin(mercado)]
        if responsable and len(responsable) > 0:
            df = df[df.get("RESPONSABLE PROX PASO", "").isin(responsable)]
        if rol and len(rol) > 0:
            df = df[df.get("CARGO/ROL", "").isin(rol)]
        if proximo_paso and len(proximo_paso) > 0:
            df = df[df.get("PROXIMO PASO", "").isin(proximo_paso)]
        if estado and len(estado) > 0:
            df = df[df.get("ESTADO", "").isin(estado)]
        if criticidad and len(criticidad) > 0:
            df = df[df.get("CRITICIDAD", "").isin(criticidad)]

        self.df_processed = df
        return self

    def get_filtered(self) -> pd.DataFrame:
        """Retorna el DataFrame filtrado."""
        return self.df_processed if self.df_processed is not None else self.df

    def calculate_kpis(self) -> Dict[str, Any]:
        """Calcula KPIs principales."""
        df = self.get_filtered()

        if df is None or df.empty:
            return {
                "total_vacantes": 0,
                "vacantes_criticas": 0,
                "sin_gestion": 0,
                "promedio_dias": 0.0,
                "time_to_hire": 0,
            }

        kpis = {}

        # Total vacantes
        kpis["total_vacantes"] = len(df)

        # Vacantes críticas
        try:
            criticas = df[
                df.get("CRITICIDAD", "").astype(str).str.contains("ROJO|ROJA|CRITICA", case=False, na=False)
            ]
            kpis["vacantes_criticas"] = len(criticas)
        except:
            kpis["vacantes_criticas"] = 0

        # Sin gestión (>30 días sin avanzar)
        try:
            sin_gestion = df[pd.to_numeric(df.get("DIAS SIN AVANZAR", 0), errors="coerce") > 30]
            kpis["sin_gestion"] = len(sin_gestion)
        except:
            kpis["sin_gestion"] = 0

        # Promedio de días
        try:
            dias = pd.to_numeric(df.get("DIAS", 0), errors="coerce")
            kpis["promedio_dias"] = round(dias.mean(), 1)
        except:
            kpis["promedio_dias"] = 0.0

        # Time to hire (máximo de días)
        try:
            dias = pd.to_numeric(df.get("DIAS", 0), errors="coerce")
            kpis["time_to_hire"] = int(dias.max()) if len(dias) > 0 else 0
        except:
            kpis["time_to_hire"] = 0

        return kpis



    def get_chart_data(self, chart_name: str) -> Dict[str, List]:
        """Prepara datos para graficos."""
        df = self.get_filtered()
        if df is None or df.empty:
            return {"labels": [], "data": []}

        if chart_name == "dias_sin_avance":
            return self._chart_dias_sin_avance(df)
        elif chart_name == "criticidad_responsable":
            return self._chart_criticidad_responsable(df)
        elif chart_name == "promedio_estado":
            return self._chart_promedio_estado(df)
        elif chart_name == "criticas_responsable":
            return self._chart_criticas_responsable(df)

        chart_config = CHARTS_CONFIG.get(chart_name, {})
        column = chart_config.get("column")
        top_n = chart_config.get("top_n")

        if not column or column not in df.columns:
            return {"labels": [], "data": []}

        try:
            series = df[column]
            if isinstance(series, pd.DataFrame):
                series = series.iloc[:, 0]
            
            value_counts = series.fillna("SIN ASIGNAR").astype(str).value_counts()
            if top_n:
                value_counts = value_counts.head(top_n)

            labels = value_counts.index.tolist()
            data = value_counts.values.tolist()

            return {
                "labels": labels,
                "data": data,
                "backgroundColor": self._get_colors_for_chart(chart_name, labels),
            }
        except Exception as e:
            print(f"[ERROR] {chart_name}: {e}")
            return {"labels": [], "data": []}

    def _chart_dias_sin_avance(self, df: pd.DataFrame) -> Dict[str, List]:
        """Dias sin avance por rango."""
        if "DIAS SIN AVANZAR" not in df.columns:
            return {"labels": [], "data": []}
        
        dias = pd.to_numeric(df["DIAS SIN AVANZAR"], errors="coerce").fillna(0)
        bins = [0, 7, 14, 30, 60, 100000]
        labels = ["0-7", "8-14", "15-30", "31-60", "60+"]
        counts = pd.cut(dias, bins=bins, labels=labels).value_counts().sort_index()
        
        return {
            "labels": counts.index.tolist(),
            "data": counts.values.tolist(),
            "backgroundColor": ["#2a8703", "#ffc220", "#ff9800", "#f44336", "#ea1100"],
        }

    def _chart_criticidad_responsable(self, df: pd.DataFrame) -> Dict[str, List]:
        """Tasa criticidad por responsable."""
        if "RESPONSABLE PROX PASO" not in df.columns or "CRITICIDAD" not in df.columns:
            return {"labels": [], "data": []}
        
        try:
            responsables = df["RESPONSABLE PROX PASO"].fillna("SIN ASIGNAR").unique()[:10]
            tasa_criticidad = []
            
            for resp in responsables:
                resp_df = df[df["RESPONSABLE PROX PASO"] == resp]
                criticas = len(resp_df[resp_df["CRITICIDAD"].astype(str).str.contains("ROJO|ROJA|CRITICA", case=False, na=False)])
                total = len(resp_df)
                tasa = (criticas / total * 100) if total > 0 else 0
                tasa_criticidad.append(round(tasa, 1))
            
            return {
                "labels": responsables.tolist(),
                "data": tasa_criticidad,
                "backgroundColor": "#ea1100",
            }
        except:
            return {"labels": [], "data": []}

    def _chart_promedio_estado(self, df: pd.DataFrame) -> Dict[str, List]:
        """Promedio dias por estado."""
        if "ESTADO" not in df.columns or "DIAS" not in df.columns:
            return {"labels": [], "data": []}
        
        try:
            estados = df["ESTADO"].unique()
            promedios = []
            
            for estado in estados:
                estado_df = df[df["ESTADO"] == estado]
                dias = pd.to_numeric(estado_df["DIAS"], errors="coerce")
                promedio = dias.mean()
                promedios.append(round(promedio, 1))
            
            return {
                "labels": estados.tolist(),
                "data": promedios,
                "backgroundColor": ["#0053e2", "#ffc220", "#2a8703", "#ea1100"][:len(estados)],
            }
        except:
            return {"labels": [], "data": []}

    def _chart_criticas_responsable(self, df: pd.DataFrame) -> Dict[str, List]:
        """Vacantes criticas por responsable."""
        if "RESPONSABLE PROX PASO" not in df.columns or "CRITICIDAD" not in df.columns:
            return {"labels": [], "data": []}
        
        try:
            criticas_df = df[df["CRITICIDAD"].astype(str).str.contains("ROJO|ROJA|CRITICA", case=False, na=False)]
            if criticas_df.empty:
                return {"labels": [], "data": []}
            
            counts = criticas_df["RESPONSABLE PROX PASO"].value_counts().head(10)
            
            return {
                "labels": counts.index.tolist(),
                "data": counts.values.tolist(),
                "backgroundColor": "#ea1100",
            }
        except:
            return {"labels": [], "data": []}

    def _get_colors_for_chart(self, chart_name: str, labels: List) -> List[str]:
        """Retorna lista de colores para un gráfico."""
        colors = [
            "#0053e2",  # Walmart Blue
            "#ffc220",  # Walmart Yellow
            "#2a8703",  # Walmart Green
            "#ea1100",  # Walmart Red
            "#f59e0b",  # Orange
            "#ec4899",  # Pink
            "#14b8a6",  # Teal
            "#8b5cf6",  # Purple
            "#f97316",  # Orange-red
            "#06b6d4",  # Cyan
        ]

        # Para criticidad, usar colores específicos
        if chart_name == "criticidad":
            return [CRITICIDAD_COLORS.get(str(label).upper(), "#666666") for label in labels]

        # Repetir colores si hay más etiquetas que colores
        return [colors[i % len(colors)] for i in range(len(labels))]

    def get_table_data(
        self,
        sort_by: str = "DIAS",
        limit: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Prepara datos para tabla detallada."""
        df = self.get_filtered()

        if df is None or df.empty:
            return {"total": 0, "rows": [], "columns": []}

        # Sorting
        if sort_by == "DIAS" and "DIAS" in df.columns:
            df = df.sort_values("DIAS", ascending=False, na_position="last")
        elif sort_by == "CRITICIDAD" and "CRITICIDAD" in df.columns:
            df = df.sort_values("CRITICIDAD", ascending=True, na_position="last")

        # Limitar si aplica
        if limit:
            df = df.head(limit)

        # Identificar columnas con datos
        columns_with_data = []
        for col in df.columns:
            # Si la columna tiene al menos un valor no nulo/vacío
            non_empty = df[col].fillna("").astype(str).str.strip().ne("").sum()
            if non_empty > 0:
                columns_with_data.append(col)

        # Reordenar: primero RUT, ID, CARGO/ROL, luego el resto
        priority_cols = ["RUT", "ID", "CARGO/ROL", "CARGO", "VACANTE"]
        ordered_cols = [c for c in priority_cols if c in columns_with_data]
        for col in columns_with_data:
            if col not in ordered_cols:
                ordered_cols.append(col)

        rows = []
        for _, row in df.iterrows():
            row_dict = {}
            for col in ordered_cols:
                value = row.get(col)
                row_dict[col] = str(value) if pd.notna(value) else ""
            rows.append(row_dict)

        return {
            "total": len(rows),
            "rows": rows,
            "columns": ordered_cols,
        }

    def get_available_filters(self) -> Dict[str, List[str]]:
        """Retorna opciones disponibles para cada filtro."""
        df = self.df

        if df is None or df.empty:
            return {col: ["TODOS"] for col in AVAILABLE_FILTERS}

        filters = {}
        for col in AVAILABLE_FILTERS:
            if col in df.columns:
                try:
                    series = df[col]
                    if isinstance(series, pd.DataFrame):
                        series = series.iloc[:, 0]
                    
                    unique_values = (
                        series
                        .fillna("SIN ASIGNAR")
                        .astype(str)
                        .unique()
                        .tolist()
                    )
                    filters[col] = ["TODOS"] + sorted(
                        [str(v) for v in unique_values if str(v) != "SIN ASIGNAR"]
                    ) + (["SIN ASIGNAR"] if "SIN ASIGNAR" in unique_values else [])
                except Exception as e:
                    print(f"[WARN] Error procesando columna {col}: {e}")
                    filters[col] = ["TODOS"]
            else:
                filters[col] = ["TODOS"]

        return filters
