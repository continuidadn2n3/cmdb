// gestion/static/gestion/js/graficos.js
Chart.register(ChartDataLabels);

/**
 * Módulo autocontenido para la página de Dashboard de Gráficos.
 * No depende de un objeto global 'App' y se autoinicializa.
 */
const dashboardModule = {
    // Propiedades para almacenar las instancias de los gráficos
    chartInstances: {
        aplicativo: null,
        porMes: null,
        severidad: null,
        porCodigoCierre: null,
        porIndraD: null
    },

    // URLs que necesita esta página específica
    urls: {},

    // Paletas de colores centralizadas para los gráficos
    colors: {
        porAplicativo: 'rgba(70, 130, 180, 0.7)',
        porMes: [
            '#8A2BE2', '#4682B4', '#20B2AA', '#FF69B4',
            '#6A5ACD', '#00CED1', '#DA70D6'
        ],
        porSeveridad: ['#14b13bff', '#FFD700', '#DC143C', '#FF8C00'],
        porCodigoCierre: {
            backgroundColor: 'rgba(0, 128, 128, 0.2)',
            borderColor: 'rgba(0, 128, 128, 1)'
        },
        porIndraD: ['#ff6384', '#36a2eb']
    },

    // Punto de entrada para la lógica del dashboard
    init: function() {
        console.log("Inicializando módulo de Dashboard...");
        const pageContainer = document.querySelector('.page-container');
        if (!pageContainer) return;

        this.urls = {
            graficosData: pageContainer.dataset.urlGraficosData,
            codigosCierre: pageContainer.dataset.urlCodigosCierre
        };
        this.addEventListeners();
        
        // Manejo inicial: Cargar códigos si hay aplicativo seleccionado
        const aplicativoVal = $('#aplicativo').val();
        if (aplicativoVal) {
            const urlParams = new URLSearchParams(window.location.search);
            const codigoCierrePreseleccionado = urlParams.get('codigo_cierre');
            this.cargarCodigosCierre(codigoCierrePreseleccionado);
        }

        this.actualizarGraficos();
    },

    // Centralizamos todos los event listeners
    addEventListeners: function() {
        $('#toggle-filters-btn').on('click', function() {
            var filterContainer = $('#filter-container');
            if (filterContainer.is(':visible')) {
                filterContainer.slideUp();
                $(this).text('Mostrar Filtros');
            } else {
                filterContainer.slideDown();
                $(this).text('Ocultar Filtros');
            }
        });

        $('#graficos-filters-form').on('submit', (e) => {
            e.preventDefault();
            this.actualizarGraficos();
        });

        $('#limpiar-filtros-btn').on('click', () => {
            // Reset manual para forzar "Todos" y borrar filtros persistentes
            $('#graficos-filters-form').find('input, select').val('');
            $('#aplicativo').trigger('change');
            this.actualizarGraficos();
        });

        $('#aplicativo').on('change', () => {
            this.cargarCodigosCierre();
        });
    },

    // Lógica para renderizar o actualizar un gráfico
    renderChart: function(canvasId, chartKey, chartData, chartTitle, datasetLabel, colorPalette, chartType = 'bar') {
        const canvas = document.getElementById(canvasId);
        const ctx = canvas.getContext('2d');
        const chartContainer = canvas.parentElement; // El contenedor .chart-container

        // Limpiar gráfico anterior si existe
        if (this.chartInstances[chartKey]) {
            this.chartInstances[chartKey].destroy();
            this.chartInstances[chartKey] = null;
        }

        // --- LÓGICA DE ESTADO "SIN DATOS" ---
        // Verificar si hay datos válidos (array no vacío y suma > 0)
        const hasData = chartData && chartData.values && chartData.values.length > 0 && chartData.values.some(v => v > 0);

        // Identificamos o creamos el elemento de mensaje
        let noDataMsg = chartContainer.querySelector('.no-data-message');
        if (!noDataMsg) {
            noDataMsg = document.createElement('div');
            noDataMsg.className = 'no-data-message';
            noDataMsg.style.cssText = 'position:absolute; top:0; left:0; width:100%; height:100%; display:flex; justify-content:center; align-items:center; color:#ccc; font-size:14px; background:rgba(0,0,0,0.2); text-align:center; padding:1rem; pointer-events:none;';
            noDataMsg.innerHTML = '<p>Sin datos para mostrar<br><span style="font-size:12px; opacity:0.7">(Prueba cambiar los filtros)</span></p>';
            chartContainer.style.position = 'relative'; // Asegurar posicionamiento
            chartContainer.appendChild(noDataMsg);
        }

        if (!hasData) {
            // Si NO hay datos: Ocultar canvas, Mostrar mensaje
            canvas.style.display = 'none';
            noDataMsg.style.display = 'flex';
            
            // Opcional: Mostrar el título aunque no haya gráfico, para saber de qué era
            // Pero Chart.js dibuja el título dentro del canvas, así que aquí
            // podríamos poner un título HTML si quisiéramos, pero por ahora solo el mensaje.
            return; // Terminamos aquí, no dibujamos nada.
        } else {
            // Si SÍ hay datos: Mostrar canvas, Ocultar mensaje
            canvas.style.display = 'block';
            noDataMsg.style.display = 'none';
        }
        // -------------------------------------

        const isRadialChart = ['pie', 'doughnut', 'polarArea'].includes(chartType);

        const datasetConfig = {
            label: datasetLabel,
            data: chartData.values,
            borderWidth: 1
        };

        if (chartType === 'line') {
            datasetConfig.backgroundColor = colorPalette.backgroundColor;
            datasetConfig.borderColor = colorPalette.borderColor;
            datasetConfig.fill = true;
            datasetConfig.tension = 0.1;
        } else {
            datasetConfig.backgroundColor = colorPalette;
            datasetConfig.borderColor = isRadialChart ? '#2c2f33' : 'rgba(0,0,0,0.2)';
        }

        this.chartInstances[chartKey] = new Chart(ctx, {
            type: chartType,
            data: {
                labels: chartData.labels,
                datasets: [datasetConfig]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,

                // --- INICIO: MODIFICACIÓN DE ESCALAS ---
                scales: isRadialChart ? {
                    // 'r' es el eje radial para gráficos polares
                    r: {
                        // Color de las líneas circulares (la "telaraña")
                        grid: {
                            color: 'rgba(255, 255, 255, 0.2)'
                        },
                        // Color de las líneas que van del centro hacia afuera
                        angleLines: {
                            color: 'rgba(255, 255, 255, 0.2)'
                        },
                        // Color de las etiquetas de los puntos (ej: "Abril 2025")
                        pointLabels: {
                            color: '#FFFFFF'
                        },
                        // Estilos para los números de la escala (ej: 50, 100, 150)
                        ticks: {
                            color: '#E0E0E0',
                            backdropColor: 'rgba(0, 0, 0, 0.5)', // Fondo para que los números resalten
                            backdropPadding: 2
                        }
                    }
                } : {
                    // Configuración para gráficos no-radiales (barras, líneas)
                    y: {
                        beginAtZero: true,
                        ticks: { precision: 0, color: '#E0E0E0' }
                    },
                    x: { ticks: { color: '#E0E0E0' } }
                },
                // --- FIN: MODIFICACIÓN DE ESCALAS ---

                plugins: {
                    title: {
                        display: true,
                        text: chartTitle,
                        font: { size: 18 },
                        padding: { bottom: 20 },
                        color: '#FFFFFF'
                    },
                    legend: {
                        labels: { color: '#B0B0B0' }
                    },
                    datalabels: {
                        display: function(context) {
                            return context.dataset.data[context.dataIndex] > 0;
                        },
                        formatter: (value, context) => {
                            // Para gráficos de torta o dona, mostramos el valor y el porcentaje.
                            const isRadial = ['pie', 'doughnut'].includes(context.chart.config.type);
                            if (isRadial) {
                                const sum = context.chart.data.datasets[0].data.reduce((a, b) => a + b, 0);
                                if (sum === 0) return '0 (0.00%)';
                                const percentage = (value * 100 / sum).toFixed(2) + "%";
                                return `${value}\n(${percentage})`;
                            }
                            return new Intl.NumberFormat('es-ES').format(value);
                        },
                        color: '#FFFFFF',
                        font: function(context) {
                            const isRadial = ['pie', 'doughnut', 'polarArea'].includes(context.chart.config.type);
                            return {
                                weight: 'bold',
                                size: isRadial ? 16 : 13
                            };
                        },
                        backgroundColor: function(context) {
                            const isRadial = ['pie', 'doughnut', 'polarArea'].includes(context.chart.config.type);
                            return isRadial ? 'rgba(0, 0, 0, 0.5)' : null;
                        },
                        borderRadius: 5,
                        padding: 4,
                        anchor: function(context) {
                            const isRadial = ['pie', 'doughnut', 'polarArea'].includes(context.chart.config.type);
                            return isRadial ? 'center' : 'end';
                        },
                        align: function(context) {
                            const isRadial = ['pie', 'doughnut', 'polarArea'].includes(context.chart.config.type);
                            return isRadial ? 'center' : 'top';
                        },
                        offset: 8
                    }
                }
            }
        });
    },

    // Lógica para obtener datos y actualizar todos los gráficos
    actualizarGraficos: function() {
        const form = $('#graficos-filters-form');
        const serializedData = form.serialize();
        const url = `${this.urls.graficosData}?${serializedData}`;
        const spinner = document.getElementById('loading-spinner');

        // Actualizar URL del navegador sin recargar
        const newUrlContext = window.location.protocol + "//" + window.location.host + window.location.pathname + '?' + serializedData;
        window.history.pushState({path: newUrlContext}, '', newUrlContext);

        if (spinner) spinner.style.display = 'flex';

        fetch(url)
            .then(response => {
                if (!response.ok) throw new Error('La respuesta del servidor no fue exitosa.');
                return response.json();
            })
            .then(data => {
                $('#total-general-valor').text((data.total_general || 0).toLocaleString('es-ES'));
                $('#total-filtrado-valor').text((data.total_filtrado || 0).toLocaleString('es-ES'));

                if (data && data.por_aplicativo) {
                    this.renderChart('chartPorAplicativo', 'aplicativo', data.por_aplicativo, 'Incidencias por Aplicativo (Top 15)', 'Nº de Incidencias', this.colors.porAplicativo, 'bar');
                }
                if (data && data.por_mes) {
                    this.renderChart('chartPorMes', 'porMes', data.por_mes, 'Incidencias por Mes', 'Nº de Incidencias', this.colors.porMes, 'bar');
                }
                if (data && data.por_severidad) {
                    this.renderChart('chartPorSeveridad', 'severidad', data.por_severidad, 'Incidencias por Severidad', 'Nº de Incidencias', this.colors.porSeveridad, 'pie');
                }
                if (data && data.por_codigo_cierre) {
                    this.renderChart('chartPorCodigoCierre', 'porCodigoCierre', data.por_codigo_cierre, 'Top 15 Códigos de Cierre', 'Nº de Incidencias', this.colors.porCodigoCierre, 'line');
                }
                if (data && data.por_indra_d) {
                    this.renderChart('chartPorIndraD', 'porIndraD', data.por_indra_d, 'Incidencias por Grupo INDRA_D vs. Otros', 'Nº de Incidencias', this.colors.porIndraD, 'pie');
                }

                if (spinner) spinner.style.display = 'none';
            })
            .catch(error => {
                console.error('Error al cargar datos de los gráficos:', error);
                if (spinner) spinner.style.display = 'none';
                alert('No se pudieron cargar los datos para los gráficos.');
            });
    },

    // Lógica para cargar dinámicamente los códigos de cierre
    cargarCodigosCierre: function(selectedValue = null) {
        const aplicativoId = $('#aplicativo').val();
        const codigoCierreSelect = $('#codigo_cierre');
        const url = `${this.urls.codigosCierre}?aplicativo_id=${aplicativoId}`;

        codigoCierreSelect.html('<option value="">Cargando...</option>').prop('disabled', true);

        fetch(url)
            .then(response => response.json())
            .then(data => {
                codigoCierreSelect.html('<option value="">Todos</option>').prop('disabled', false);
                data.codigos.forEach(codigo => {
                    codigoCierreSelect.append($('<option></option>').val(codigo.id).text(codigo.text));
                });
                
                // Si se proporcionó un valor preseleccionado (ej: al cargar página), asignarlo
                if (selectedValue) {
                    codigoCierreSelect.val(selectedValue);
                }
            })
            .catch(error => {
                console.error('Error al cargar los códigos de cierre:', error);
                codigoCierreSelect.html('<option value="">Error al cargar</option>').prop('disabled', true);
            });
    }
};

$(document).ready(function() {
    dashboardModule.init();
});