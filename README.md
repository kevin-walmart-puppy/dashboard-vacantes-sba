# 📊 Dashboard Vacantes SBA

Dashboard interactivo para la gestión y seguimiento de vacantes SBA (Selección Basada en Aptitud).

## ✨ Características

- 📤 **Carga de archivos Excel** - Sube tus datos de vacantes fácilmente
- 🔍 **Filtros interactivos** - Filtra por mercado, responsable, rol, estado, criticidad
- 📈 **Gráficos dinámicos** - Visualización en tiempo real con Chart.js
- 📋 **Tabla detallada** - Vista completa de todos los registros
- 🎯 **KPIs principales** - Métricas clave del dashboard
- 💡 **Insights automáticos** - Análisis inteligente de los datos

## 🚀 Inicio Rápido

### Local (Desarrollo)

```bash
# Instalar dependencias
pip install -r requirements.txt

# Ejecutar servidor
python -m uvicorn app:app --reload --host 127.0.0.1 --port 8000

# Abrir en navegador
http://localhost:8000
```

### Producción (Docker)

```bash
# Build
docker build -t dashboard-vacantes-sba .

# Run
docker run -p 8000:8000 dashboard-vacantes-sba
```

## 📋 Requisitos de Archivo Excel

El archivo Excel debe tener estas columnas:

- `ID` - Identificador de la vacante
- `CARGO/ROL` - Nombre del puesto
- `LOCAL` - Ubicación
- `ESTADO` - Estado actual
- `PRÓXIMO PASO` - Próxima acción
- `RESPONSABLE PROX PASO` - Persona responsable
- `DÍAS` - Días desde apertura
- `CRITICIDAD` - Nivel de criticidad (ROJO/AMARILLO/VERDE)

## 🏗️ Arquitectura

```
├── app.py                 # FastAPI server
├── data_processor.py      # Procesamiento de datos
├── config.py              # Configuración
├── index.html             # Frontend
├── dashboard.js           # Lógica del dashboard
├── requirements.txt       # Dependencias Python
└── Dockerfile             # Despliegue
```

## 📚 API Endpoints

- `GET /` - Dashboard principal
- `POST /api/upload` - Carga de archivo Excel
- `GET /api/kpis` - KPIs principales
- `GET /api/filters` - Opciones de filtros
- `GET /api/charts/{chart_name}` - Datos para gráficos
- `GET /api/table` - Datos de tabla
- `GET /api/insights` - Insights automáticos
- `GET /api/status` - Estado del dashboard
- `GET /health` - Health check

## 🔧 Tecnologías

- **Backend**: FastAPI, Pandas, Uvicorn
- **Frontend**: HTML5, CSS3, JavaScript vanilla
- **Gráficos**: Chart.js
- **Data**: Excel (XLSX/XLS)

## 📝 Notas Importantes

- Los datos se procesan **EN EL NAVEGADOR** (no se guardan en servidor)
- Soporta **acentos y caracteres especiales** automáticamente
- Compatible con **múltiples formatos** de Excel
- **Normalización automática** de nombres de columnas

## 👤 Autor

Creado por **Code Puppy** - Felipito 🐶  
Asistente de IA para tareas de código en Walmart

## 📧 Soporte

- Slack: #ai-innovation-lab
- Email: code-puppy@walmart.com
- Documentación: https://wmlink.wal-mart.com/ailab-docs

---

**Versión**: 1.0.0  
**Última actualización**: Mayo 2026
