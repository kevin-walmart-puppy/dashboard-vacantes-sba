// ========== ESTADO GLOBAL ==========

const state = {
    currentFilters: {
        mercado: [],
        responsable: [],
        rol: [],
        proximo_paso: [],
        estado: [],
        criticidad: [],
    },
    chartsMap: new Map(),  // Usar Map en lugar de Object
    maxCharts: 15,  // Límite de gráficos en memoria
    isLoaded: false,
    filtersVisible: false,
};

console.log("🐶 Dashboard.js cargado correctamente");

// ========== UPLOAD DE ARCHIVO ==========

const uploadArea = document.getElementById("uploadArea");
const fileInput = document.getElementById("fileInput");
const uploadStatus = document.getElementById("uploadStatus");
const uploadScreen = document.getElementById("uploadScreen");
const dashboardContainer = document.getElementById("dashboardContainer");

// Drag and drop
uploadArea.addEventListener("click", () => fileInput.click());
uploadArea.addEventListener("dragover", (e) => {
    e.preventDefault();
    uploadArea.classList.add("dragover");
});
uploadArea.addEventListener("dragleave", () => {
    uploadArea.classList.remove("dragover");
});
uploadArea.addEventListener("drop", (e) => {
    e.preventDefault();
    uploadArea.classList.remove("dragover");
    const files = e.dataTransfer.files;
    if (files.length > 0) {
        handleFile(files[0]);
    }
});

fileInput.addEventListener("change", (e) => {
    if (e.target.files.length > 0) {
        handleFile(e.target.files[0]);
    }
});

async function handleFile(file) {
    console.log("📄 Archivo seleccionado:", file.name);
    
    if (!file.name.endsWith(".xlsx") && !file.name.endsWith(".xls")) {
        console.error("❌ Extensión inválida:", file.name);
        alert("❌ Solo se aceptan archivos Excel (.xlsx, .xls)");
        return;
    }

    uploadStatus.style.display = "block";
    uploadArea.style.pointerEvents = "none";
    uploadArea.style.opacity = "0.5";

    const formData = new FormData();
    formData.append("file", file);

    try {
        console.log("📤 Enviando archivo a /api/upload...");
        const response = await fetch("/api/upload", {
            method: "POST",
            body: formData,
        });

        console.log("Respuesta status:", response.status);
        const result = await response.json();
        console.log("Respuesta JSON:", result);

        if (result.success) {
            console.log("✅ Archivo cargado:", result);
            document.getElementById("fileInfo").textContent = `${result.rows} candidatos | ${result.columns} campos`;
            
            // Mostrar dashboard
            uploadScreen.style.display = "none";
            dashboardContainer.classList.add("active");
            state.isLoaded = true;

            console.log("📊 Cargando datos del dashboard...");
            // Cargar datos
            await Promise.all([
                loadFilters(),
                loadKPIs(),
                loadInsights(),
                loadChart("criticidad"),
                loadChart("tiempo-abierto"),
                loadChart("responsable"),
                loadChart("rol"),
                loadChart("proximo-paso"),
                loadChart("estado"),
                loadChart("mercado"),
                loadChart("dias-sin-avance"),
                loadChart("criticidad-responsable"),
                loadChart("promedio-estado"),
                loadChart("criticas-responsable"),
                loadTable(),
            ]);
            console.log("✅ Dashboard completamente cargado");
        } else {
            console.error("❌ Error en respuesta:", result.message);
            alert(`❌ Error: ${result.message}`);
            uploadStatus.style.display = "none";
            uploadArea.style.pointerEvents = "auto";
            uploadArea.style.opacity = "1";
        }
    } catch (error) {
        console.error("❌ Error fatal al cargar archivo:", error);
        alert(`❌ Error al cargar archivo: ${error.message}`);
        uploadStatus.style.display = "none";
        uploadArea.style.pointerEvents = "auto";
        uploadArea.style.opacity = "1";
    }
}

// ========== RESET DASHBOARD ==========

function resetDashboard() {
    uploadScreen.style.display = "flex";
    dashboardContainer.classList.remove("active");
    state.isLoaded = false;
    fileInput.value = "";
    uploadArea.style.pointerEvents = "auto";
    uploadArea.style.opacity = "1";
    uploadStatus.style.display = "none";
}

// ========== FUNCIONES AUXILIARES ==========

async function apiCall(endpoint, params = {}) {
    const queryString = new URLSearchParams(params).toString();
    const url = queryString ? `${endpoint}?${queryString}` : endpoint;
    
    console.log(`📡 Llamando: ${url}`);
    try {
        const response = await fetch(url);
        console.log(`📊 Respuesta status:`, response.status);
        
        if (!response.ok) {
            console.error(`❌ Error HTTP ${response.status} en ${endpoint}`);
            const text = await response.text();
            console.error("Respuesta:", text);
            return null;
        }
        
        const data = await response.json();
        console.log(`✅ Datos recibidos de ${endpoint}:`, data);
        return data;
    } catch (error) {
        console.error(`❌ Error en ${endpoint}:`, error.message);
        return null;
    }
}

function showModal(text) {
    const modal = document.getElementById("commentModal");
    const modalText = document.getElementById("modal-text");
    modalText.textContent = text || "(Sin comentarios)";
    modal.classList.add("show");
}

function closeModal() {
    const modal = document.getElementById("commentModal");
    modal.classList.remove("show");
}

window.addEventListener("click", (e) => {
    const modal = document.getElementById("commentModal");
    if (e.target === modal) {
        closeModal();
    }
});

// ========== CARGAR DATOS ==========

async function loadKPIs(params = {}) {
    const data = await apiCall("/api/kpis", params);

    if (data) {
        document.getElementById("kpi-total").textContent = data.total_vacantes || 0;
        document.getElementById("kpi-criticas").textContent = data.vacantes_criticas || 0;
        document.getElementById("kpi-sin-gestion").textContent = data.sin_gestion || 0;
        document.getElementById("kpi-promedio").textContent = (data.promedio_dias || 0).toFixed(1);
    }
}

async function loadFilters() {
    console.log("🔄 Cargando filtros...");
    const data = await apiCall("/api/filters");
    console.log("Datos de filtros recibidos:", data);
    
    if (!data) {
        console.error("❌ No se pudieron cargar los filtros");
        return;
    }

    const filterConfig = [
        { id: "mercado", values: data.mercados || [] },
        { id: "responsable", values: data.responsables || [] },
        { id: "rol", values: data.roles || [] },
        { id: "proximo-paso", values: data.pasos || [], key: "proximo_paso" },
        { id: "estado", values: data.estados || [] },
        { id: "criticidad", values: data.criticidades || [] },
    ];

    console.log("Config de filtros:", filterConfig);

    filterConfig.forEach(({ id, values, key }) => {
        const containerId = `checkboxes-${id}`;
        const container = document.getElementById(containerId);
        
        console.log(`Procesando filtro ${id}:`, { containerId, containerExists: !!container, valuesLength: values ? values.length : 0 });
        
        if (!container) {
            console.warn(`⚠️ Contenedor no encontrado: ${containerId}`);
            return;
        }

        container.innerHTML = "";
        values.forEach((value) => {
            const checkboxDiv = document.createElement("div");
            checkboxDiv.className = "filter-checkbox";
            checkboxDiv.innerHTML = `
                <input type="checkbox" id="cb-${id}-${value}" value="${value}">
                <label for="cb-${id}-${value}">${value}</label>
            `;
            container.appendChild(checkboxDiv);
        });
    });
    
    console.log("✅ Filtros cargados correctamente");
}

function toggleFilters() {
    const grid = document.getElementById("filtersGrid");
    const actions = document.getElementById("filtersActions");
    const btn = event.target;
    
    state.filtersVisible = !state.filtersVisible;
    
    if (state.filtersVisible) {
        grid.style.display = "grid";
        actions.style.display = "flex";
        btn.textContent = "🔍 Ocultar Filtros";
    } else {
        grid.style.display = "none";
        actions.style.display = "none";
        btn.textContent = "🔍 Mostrar Filtros";
    }
}

function clearAllFilters() {
    const checkboxes = document.querySelectorAll('.filter-checkbox input[type="checkbox"]');
    checkboxes.forEach(cb => cb.checked = false);
    state.currentFilters = {
        mercado: [],
        responsable: [],
        rol: [],
        proximo_paso: [],
        estado: [],
        criticidad: [],
    };
    applyFilters();
}

async function loadInsights() {
    const data = await apiCall("/api/insights");
    if (!data || !data.insights) return;

    const container = document.getElementById("insightsContainer");
    container.innerHTML = "";

    data.insights.forEach((insight) => {
        const card = document.createElement("div");
        card.className = `insight-card ${insight.type}`;
        card.innerHTML = `
            <div class="insight-icon">${insight.icon}</div>
            <div class="insight-title">${insight.title}</div>
            <div class="insight-value">${insight.value}</div>
            <div class="insight-description">${insight.description}</div>
        `;
        container.appendChild(card);
    });
}

async function loadChart(chartName, params = {}) {
    // Mapeo de nombres de gráficos a endpoints
    const chartEndpoints = {
        "criticidad": "criticidad",
        "tiempo-abierto": "tiempo-abierto",
        "responsable": "responsable",
        "rol": "rol",
        "proximo-paso": "proximo-paso",
        "estado": "estado",
        "mercado": "mercado",
        "dias-sin-avance": "dias-sin-avance",
        "criticidad-responsable": "criticidad-responsable",
        "promedio-estado": "promedio-estado",
        "criticas-responsable": "criticas-responsable"
    };
    
    const endpoint = chartEndpoints[chartName] || chartName;
    const data = await apiCall(`/api/charts/${endpoint}`, params);

    const canvasId = `chart-${chartName}`;
    const canvas = document.getElementById(canvasId);

    if (!canvas) return;

    // Destruir gráfico anterior PRIMERO
    if (state.chartsMap.has(chartName)) {
        const oldChart = state.chartsMap.get(chartName);
        oldChart.destroy();
        state.chartsMap.delete(chartName);
    }

    // Si no hay datos, mostrar aviso
    if (!data || !data.labels || !data.data || data.data.length === 0) {
        console.warn(`⚠️ Sin datos para gráfico: ${chartName}`);
        const ctx = canvas.getContext("2d");
        ctx.fillStyle = "#ccc";
        ctx.fillRect(0, 0, canvas.width, canvas.height);
        ctx.fillStyle = "#666";
        ctx.font = "14px Arial";
        ctx.textAlign = "center";
        ctx.fillText("Sin datos disponibles", canvas.width / 2, canvas.height / 2);
        return;
    }

    const ctx = canvas.getContext("2d");
    const chartType = ["criticidad", "mercado", "rol", "estado"].includes(chartName) ? "doughnut" : "bar";

    try {
        console.log(`📊 Inicializando gráfico: ${chartName}`, { labels: data.labels.length, data: data.data.length });
        
        const chart = new Chart(ctx, {
            type: chartType,
            data: {
                labels: data.labels,
                datasets: [
                    {
                        label: chartName.toUpperCase(),
                        data: data.data,
                        backgroundColor: Array.isArray(data.backgroundColor) ? data.backgroundColor : data.backgroundColor || "#0053e2",
                        borderColor: "white",
                        borderWidth: 2,
                    },
                ],
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                indexAxis: chartType === "bar" && chartName.includes("responsable") ? undefined : undefined,
                plugins: {
                    legend: {
                        display: ["criticidad", "mercado", "rol", "estado", "tiempo-abierto", "dias-sin-avance"].includes(chartName),
                        position: "bottom",
                    },
                    tooltip: {
                        enabled: true,
                        backgroundColor: "rgba(0, 0, 0, 0.8)",
                        padding: 10,
                        titleColor: "#fff",
                        bodyColor: "#fff",
                    },
                },
                scales: chartType === "bar" ? {
                    y: {
                        beginAtZero: true,
                        ticks: {
                            stepSize: 1,
                        },
                    },
                } : undefined,
            },
        });

        // Agregar chart al mapa con límite de memoria
        if (state.chartsMap.size >= state.maxCharts) {
            // Eliminar el gráfico más antiguo
            const firstKey = state.chartsMap.keys().next().value;
            const oldChart = state.chartsMap.get(firstKey);
            oldChart.destroy();
            state.chartsMap.delete(firstKey);
            console.log(`Gráfico antiguo ${firstKey} eliminado para liberar memoria`);
        }
        
        state.chartsMap.set(chartName, chart);
        console.log(`✅ Gráfico ${chartName} inicializado correctamente (${state.chartsMap.size}/${state.maxCharts})`);
    } catch (error) {
        console.error(`❌ Error en gráfico ${chartName}:`, error);
    }
}

async function loadTable(params = {}) {
    const data = await apiCall("/api/table", params);

    if (!data) return;

    const tableHead = document.getElementById("table-head");
    const tableBody = document.getElementById("table-body");

    tableHead.innerHTML = "";
    tableBody.innerHTML = "";

    if (data.rows && data.rows.length > 0) {
        const columns = data.columns || Object.keys(data.rows[0]);

        // Headers
        const headerRow = document.createElement("tr");
        columns.forEach((col) => {
            const th = document.createElement("th");
            th.textContent = col;
            headerRow.appendChild(th);
        });
        tableHead.appendChild(headerRow);

        // Rows
        data.rows.forEach((row) => {
            const tr = document.createElement("tr");

            columns.forEach((col) => {
                const td = document.createElement("td");
                const value = row[col] || "-";
                
                // Si es un campo de comentarios, mostrar botón dentro
                if ((col.toLowerCase().includes("motivo") || 
                     col.toLowerCase().includes("observaciones") ||
                     col.toLowerCase().includes("comentario")) && value && value !== "-") {
                    
                    // Crear contenedor para botón
                    const container = document.createElement("div");
                    container.style.display = "flex";
                    container.style.alignItems = "center";
                    container.style.gap = "8px";
                    
                    // Mostrar abreviatura
                    const span = document.createElement("span");
                    span.textContent = "• • •";
                    span.style.fontWeight = "bold";
                    span.style.color = "#0053e2";
                    
                    // Botón
                    const btn = document.createElement("button");
                    btn.className = "btn-see";
                    btn.textContent = "Ver";
                    btn.style.marginLeft = "auto";
                    btn.onclick = () => showModal(value);
                    
                    container.appendChild(span);
                    container.appendChild(btn);
                    td.appendChild(container);
                } else {
                    td.textContent = value;
                }
                
                tr.appendChild(td);
            });

            tableBody.appendChild(tr);
        });
    } else {
        const tr = document.createElement("tr");
        tr.innerHTML = '<td style="text-align: center; padding: 40px; color: #999;">Sin datos disponibles</td>';
        tableBody.appendChild(tr);
    }
}

async function applyFilters() {
    // Leer checkboxes
    state.currentFilters.mercado = getCheckedValues("mercado");
    state.currentFilters.responsable = getCheckedValues("responsable");
    state.currentFilters.rol = getCheckedValues("rol");
    state.currentFilters.proximo_paso = getCheckedValues("proximo-paso");
    state.currentFilters.estado = getCheckedValues("estado");
    state.currentFilters.criticidad = getCheckedValues("criticidad");

    // Construir parametros
    const params = {};
    if (state.currentFilters.mercado.length > 0) params.mercado = state.currentFilters.mercado.join(",");
    if (state.currentFilters.responsable.length > 0) params.responsable = state.currentFilters.responsable.join(",");
    if (state.currentFilters.rol.length > 0) params.rol = state.currentFilters.rol.join(",");
    if (state.currentFilters.proximo_paso.length > 0) params.proximo_paso = state.currentFilters.proximo_paso.join(",");
    if (state.currentFilters.estado.length > 0) params.estado = state.currentFilters.estado.join(",");
    if (state.currentFilters.criticidad && state.currentFilters.criticidad.length > 0) params.criticidad = state.currentFilters.criticidad.join(",");

    await Promise.all([
        loadKPIs(params),
        loadChart("criticidad", params),
        loadChart("tiempo-abierto", params),
        loadChart("responsable", params),
        loadChart("rol", params),
        loadChart("proximo-paso", params),
        loadChart("estado", params),
        loadChart("mercado", params),
        loadChart("dias-sin-avance", params),
        loadChart("criticidad-responsable", params),
        loadChart("promedio-estado", params),
        loadChart("criticas-responsable", params),
        loadTable(params),
    ]);
}

function getCheckedValues(filterId) {
    const checkboxes = document.querySelectorAll(`#checkboxes-${filterId} input[type="checkbox"]:checked`);
    return Array.from(checkboxes).map(cb => cb.value);
}

// ========== AUTO-CERRAR MODAL ==========

document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") {
        closeModal();
    }
});

console.log("✅ Script completamente cargado y listo");
