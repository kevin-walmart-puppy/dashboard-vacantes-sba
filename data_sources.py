"""
Capa de integración con múltiples fuentes de datos.
Soporta: Excel local, OneDrive, Google Sheets, APIs REST.
"""

import os
import pandas as pd
from typing import Optional, Dict, Any
from abc import ABC, abstractmethod
import asyncio
from datetime import datetime
import httpx

from config import DataSourceType
from folder_manager import MultiCategoryFolderManager


class DataSource(ABC):
    """Clase base para todas las fuentes de datos."""

    def __init__(self, config: Dict[str, Any], name: str):
        self.config = config
        self.name = name
        self.last_error: Optional[str] = None
        self.last_fetch: Optional[datetime] = None

    @abstractmethod
    async def fetch(self) -> Optional[pd.DataFrame]:
        """Obtiene datos de la fuente. Retorna DataFrame o None si error."""
        pass

    @abstractmethod
    def validate(self) -> bool:
        """Valida que la fuente esté configurada correctamente."""
        pass

    async def get_data(self) -> Optional[pd.DataFrame]:
        """Wrapper que maneja errores y registro."""
        try:
            df = await self.fetch()
            if df is not None and not df.empty:
                self.last_fetch = datetime.now()
                self.last_error = None
                print(f"[OK] {self.name}: {len(df)} registros cargados")
            return df
        except Exception as e:
            self.last_error = str(e)
            print(f"[ERROR] {self.name}: {self.last_error}")
            return None


class ExcelLocalDataSource(DataSource):
    """Fuente de datos local en Excel."""

    async def fetch(self) -> Optional[pd.DataFrame]:
        path = self.config.get("path")
        sheet_name = self.config.get("sheet_name", 0)

        if not os.path.exists(path):
            raise FileNotFoundError(f"Archivo {path} no encontrado")

        df = pd.read_excel(path, sheet_name=sheet_name)
        return df if not df.empty else None

    def validate(self) -> bool:
        path = self.config.get("path")
        return bool(path) and os.path.exists(path)


class OneDriveDataSource(DataSource):
    """Fuente de datos desde OneDrive/SharePoint."""

    async def fetch(self) -> Optional[pd.DataFrame]:
        url = self.config.get("url")
        sheet_name = self.config.get("sheet_name", 0)

        if not url:
            raise ValueError("URL de OneDrive no configurada")

        # Nota: OneDrive requiere autenticación OAuth
        # Para now, usamos la URL de descarga directa
        # Reemplaza ?download=1 o similar según el tipo de share
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url, timeout=30)
                response.raise_for_status()

            # Guardar temporalmente y leer con pandas
            temp_path = "/tmp/onedrive_temp.xlsx"
            with open(temp_path, "wb") as f:
                f.write(response.content)

            df = pd.read_excel(temp_path, sheet_name=sheet_name)
            os.remove(temp_path)
            return df if not df.empty else None
        except Exception as e:
            raise Exception(f"Error descargando de OneDrive: {e}")

    def validate(self) -> bool:
        return bool(self.config.get("url"))


class GoogleSheetsDataSource(DataSource):
    """Fuente de datos desde Google Sheets."""

    async def fetch(self) -> Optional[pd.DataFrame]:
        url = self.config.get("url")
        sheet_id = self.config.get("sheet_id", 0)

        if not url:
            raise ValueError("URL de Google Sheets no configurada")

        # Google Sheets export a CSV: /export?format=csv&gid=SHEET_ID
        try:
            # Extraer spreadsheet ID de la URL
            if "/spreadsheets/d/" in url:
                sheet_url = url.split("/spreadsheets/d/")[1].split("/")[0]
                csv_url = f"https://docs.google.com/spreadsheets/d/{sheet_url}/export?format=csv&gid={sheet_id}"

                async with httpx.AsyncClient() as client:
                    response = await client.get(csv_url, timeout=30)
                    response.raise_for_status()

                df = pd.read_csv(pd.io.common.StringIO(response.text))
                return df if not df.empty else None
            else:
                raise ValueError("URL de Google Sheets inválida")
        except Exception as e:
            raise Exception(f"Error descargando de Google Sheets: {e}")

    def validate(self) -> bool:
        return bool(self.config.get("url"))


class APIRestDataSource(DataSource):
    """Fuente de datos desde API REST genérica."""

    async def fetch(self) -> Optional[pd.DataFrame]:
        url = self.config.get("url")
        method = self.config.get("method", "GET")
        headers = self.config.get("headers", {})
        params = self.config.get("params", {})
        data_path = self.config.get("data_path", None)  # ej: "data.results"

        if not url:
            raise ValueError("URL de API no configurada")

        try:
            async with httpx.AsyncClient() as client:
                response = await client.request(method, url, headers=headers, params=params, timeout=30)
                response.raise_for_status()

            json_data = response.json()

            # Navegar por data_path si está especificado (ej: "data.results")
            if data_path:
                for key in data_path.split("."):
                    json_data = json_data[key]

            df = pd.DataFrame(json_data)
            return df if not df.empty else None
        except Exception as e:
            raise Exception(f"Error llamando API: {e}")

    def validate(self) -> bool:
        return bool(self.config.get("url"))


class DataSourceFactory:
    """Factory para crear DataSources según configuración."""

    @staticmethod
    def create(name: str, config: Dict[str, Any]) -> Optional[DataSource]:
        """Crea una DataSource según su tipo."""
        source_type = config.get("type")

        sources = {
            DataSourceType.EXCEL_LOCAL.value: ExcelLocalDataSource,
            DataSourceType.ONEDRIVE.value: OneDriveDataSource,
            DataSourceType.GOOGLE_SHEETS.value: GoogleSheetsDataSource,
            DataSourceType.API_REST.value: APIRestDataSource,
        }

        SourceClass = sources.get(source_type)
        if not SourceClass:
            print(f"[WARN] Tipo de fuente desconocido: {source_type}")
            return None

        source = SourceClass(config, name)
        if not source.validate():
            print(f"[WARN] Fuente '{name}' no validó correctamente")
            return None

        return source


class MultiSourceDataManager:
    """Gestor de múltiples fuentes de datos."""

    def __init__(self, sources_config: Dict[str, Dict[str, Any]]):
        self.sources_config = sources_config
        self.sources: Dict[str, DataSource] = {}
        self._initialize_sources()

    def _initialize_sources(self):
        """Inicializa todas las fuentes configuradas."""
        for name, config in self.sources_config.items():
            source = DataSourceFactory.create(name, config)
            if source:
                self.sources[name] = source
                print(f"[OK] Fuente registrada: {name}")

    async def fetch_all(self) -> Dict[str, Optional[pd.DataFrame]]:
        """Obtiene datos de todas las fuentes en paralelo."""
        tasks = {name: source.get_data() for name, source in self.sources.items()}
        results = await asyncio.gather(*tasks.values())
        return dict(zip(tasks.keys(), results))

    async def fetch_by_category(self, category: str) -> Optional[pd.DataFrame]:
        """Obtiene datos de la fuente correspondiente a una categoría."""
        for name, config in self.sources_config.items():
            if config.get("category") == category:
                source = self.sources.get(name)
                if source:
                    return await source.get_data()
        return None

    def get_status(self) -> Dict[str, Any]:
        """Retorna estado de todas las fuentes."""
        return {
            name: {
                "last_fetch": source.last_fetch.isoformat() if source.last_fetch else None,
                "last_error": source.last_error,
                "status": "OK" if source.last_error is None else "ERROR",
            }
            for name, source in self.sources.items()
        }
