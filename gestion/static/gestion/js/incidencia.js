// gestion/static/gestion/js/incidencia.js

/**
 * Obtiene el valor de una cookie por su nombre.
 * @param {string} name - El nombre de la cookie.
 * @returns {string|null} El valor de la cookie o null si no se encuentra.
 */
function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

/**
 * Convierte una cadena de tiempo de SLA (ej. "1 día, 4:05:10" o "8:30:00")
 * al formato hh:mm:ss (ej. "28:05:10" o "08:30:00").
 * @param {string} slaString - La cadena de tiempo a formatear.
 * @returns {string} El tiempo formateado o el valor original si no se puede procesar.
 */
function formatSlaToHHMMSS(slaString) {
    if (!slaString || slaString.trim().toLowerCase() === 'n/a') {
        return 'N/A';
    }

    let totalHours = 0;
    let timePart = slaString.trim();

    // Busca si la cadena contiene días
    if (timePart.includes('día') || timePart.includes('day')) {
        const parts = timePart.split(',');
        const dayPart = parts[0];
        timePart = parts.length > 1 ? parts[1].trim() : '0:0:0';

        const days = parseInt(dayPart, 10); // parseInt extrae el número inicial
        if (!isNaN(days)) {
            totalHours += days * 24;
        }
    }

    const timeComponents = timePart.split(':');
    if (timeComponents.length === 3) {
        totalHours += parseInt(timeComponents[0], 10);
        const hours = String(totalHours).padStart(2, '0');
        const minutes = String(timeComponents[1]).padStart(2, '0');
        const seconds = String(timeComponents[2]).padStart(2, '0');
        return `${hours}:${minutes}:${seconds}`;
    }
    return slaString; // Devuelve el original si el formato no es el esperado
}

$(document).ready(function() {
    // --- OBTENER VARIABLES DESDE EL HTML ---
    // Obtenemos las URLs y datos dinámicos desde los atributos data-* del contenedor principal.
    const pageContainer = document.querySelector('.page-container');
    const urls = {
        calcularSla: pageContainer.dataset.urlCalcularSla,
        exportarCsv: pageContainer.dataset.urlExportarCsv,
        exportarReporte: pageContainer.dataset.urlExportarReporte
    };
    const totalRegistrosDB = pageContainer.dataset.totalRegistros;

    // --- INICIALIZACIÓN DE DATATABLE ---
    var table = $('#tabla-incidencias').DataTable({
        "language": {
            "lengthMenu": "Mostrar _MENU_ registros por página",
            "zeroRecords": "No se encontraron resultados",
            "info": "Mostrando página _PAGE_ de _PAGES_",
            "infoEmpty": "No hay registros disponibles",
            "infoFiltered": "(filtrado de un total de _MAX_ registros)",
            "search": "Buscar:",
            "paginate": {
                "first": "Primero",
                "last": "Último",
                "next": "Siguiente",
                "previous": "Anterior"
            }
        },
        "lengthMenu": [
            [10, 25, 50, 100, -1],
            [10, 25, 50, 100, "Todas"]
        ],

        "dom": "<'top-bar d-flex justify-content-between'<'top-left'l<'.custom-counters'>><'top-right'f>>" +
            "<'table-responsive't>" +
            "<'bottom-bar d-flex justify-content-between align-items-center'ip>",

        "width": "100%",
        "scrollY": "48vh",
        "scrollCollapse": true,
        "paging": true,
        "pageLength": 25,
        "order": [
            [3, "asc"]
        ],
        "columnDefs": [
            // --- Definición de Anchos de Columna ---
            { "width": "2%", "targets": [0, 1, 2] }, // Íconos Eliminar, Checkbox, Editar
            { "width": "4%", "targets": [] }, // Cod. Aplicativo, Cod. Cierre
            { "width": "5%", "targets": [3, 8, 9] }, // Cod. Aplicativo, Cod. Cierre
            { "width": "6%", "targets": [11] }, // Incidencia
            { "width": "8%", "targets": [10, 14] }, // Estado, Severidad, Cumple SLA
            { "width": "10%", "targets": [5] }, // Usuario, Fechas, Tiempo SLA
            { "width": "12%", "targets": [15] }, // Aplicativo, Bloque, Grupo Resolutor
            { "width": "14%", "targets": [12, 13] }

        ],
        "initComplete": function(settings, json) {
            $('#tabla-incidencias').removeClass('data-table-loading');
        },
        "drawCallback": function(settings) {
            var api = this.api();
            var filteredCount = api.page.info().recordsDisplay;

            var countersHTML = `
                <div class="total-records-info">Total registros en BD <strong>${totalRegistrosDB}</strong></div>
                <div class="filtered-records-info">Registros encontrados: <strong>${filteredCount}</strong></div>
            `;

            // 2. Lo insertamos en nuestro contenedor personalizado de arriba
            $('.custom-counters').html(countersHTML);

            $('.celda-tiempo-sla', api.table().body()).each(function() {
                var originalText = $(this).text().trim();
                $(this).text(formatSlaToHHMMSS(originalText));
            });
        }
    });

    // --- MANEJADORES DE EVENTOS ---

    // Botón para mostrar/ocultar filtros
    $('#toggle-filters-btn').on('click', function(event) {
        var filterContainer = $('#filter-container');
        if (filterContainer.is(':visible')) {
            filterContainer.slideUp();
            $(this).text('Mostrar Filtros');
        } else {
            filterContainer.slideDown(function() {
                // Al mostrar los filtros, también ajustamos las columnas
                table.columns.adjust().draw();
            });
            $(this).text('Ocultar Filtros');
        }
    });

    // Botón para limpiar filtros sin recargar la página
    $('#limpiar-filtros-btn').on('click', function() {
        const form = $(this).closest('form');
        form.find('input[type="text"], input[type="date"]').val('');
        form.find('select').prop('selectedIndex', 0);
        // Añadido: enviar el formulario para aplicar la limpieza de filtros al instante.
        form.submit();
    });

    // Checkbox "Seleccionar Todo"
    $('#select-all-checkbox').on('click', function() {
        $('.incidencia-checkbox').prop('checked', this.checked);
    });

    // Botón "Calcular SLA"
    $('#btn-asignar-sla').on('click', function() {
        var selected_ids = [];
        $('.incidencia-checkbox:checked').each(function() {
            selected_ids.push($(this).val());
        });

        if (selected_ids.length === 0) {
            alert('Por favor, selecciona al menos una incidencia para calcular el SLA.');
            return;
        }

        $('#loading-spinner').css('display', 'flex');

        const csrftoken = getCookie('csrftoken'); // Usamos la función de ayuda

        fetch(urls.calcularSla, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrftoken
                },
                body: JSON.stringify({
                    'incidencia_ids': selected_ids
                })
            })
            .then(response => response.json())
            .then(data => {
                if (data.status === 'success') {
                    alert(data.message);
                    data.results.forEach(function(result) {
                        var fila = $('tr[data-incidencia-id="' + result.id + '"]');
                        fila.find('.celda-cumple-sla').text(result.cumple_sla);
                        fila.find('.celda-tiempo-sla').text(formatSlaToHHMMSS(result.tiempo_sla));
                    });
                } else {
                    alert('Error: ' + data.message);
                }
                $('#loading-spinner').hide();
            })
            .catch(error => {
                console.error('Error en la petición AJAX:', error);
                alert('Ocurrió un error de comunicación con el servidor.');
                $('#loading-spinner').hide();
            });
    });

    // Botón para exportar SLA a CSV
    $('#btn-exportar-csv').on('click', function() {
        var incidencia = $('#incidencia').val();
        var fechaDesde = $('#fecha_desde').val();
        var fechaHasta = $('#fecha_hasta').val();
        var url = new URL(urls.exportarCsv, window.location.origin);
        if (incidencia) url.searchParams.append('incidencia', incidencia);
        if (fechaDesde) url.searchParams.append('fecha_desde', fechaDesde);
        if (fechaHasta) url.searchParams.append('fecha_hasta', fechaHasta);
        console.log("Iniciando descarga desde: " + url.href);
        window.location.href = url.href;
    });

    // Botón para exportar reporte a Excel
    $('#btn-exportar-reporte').on('click', function() {
        var incidencia = $('#incidencia').val();
        var aplicativo = $('#aplicativo').val();
        var bloque = $('#bloque').val();
        var codigoCierre = $('#codigo_cierre').val();
        var fechaDesde = $('#fecha_desde').val();
        var fechaHasta = $('#fecha_hasta').val();
        var url = new URL(urls.exportarReporte, window.location.origin);
        if (incidencia) url.searchParams.append('incidencia', incidencia);
        if (aplicativo) url.searchParams.append('aplicativo', aplicativo);
        if (bloque) url.searchParams.append('bloque', bloque);
        if (codigoCierre) url.searchParams.append('codigo_cierre', codigoCierre);
        if (fechaDesde) url.searchParams.append('fecha_desde', fechaDesde);
        if (fechaHasta) url.searchParams.append('fecha_hasta', fechaHasta);
        console.log("Iniciando descarga de reporte Excel desde: " + url.href);
        window.location.href = url.href;
    });

    // --- CÓDIGO NUEVO PARA AJUSTAR COLUMNAS AL REDIMENSIONAR ---
    let resizeTimer;
    $(window).on('resize', function() {
        clearTimeout(resizeTimer);
        resizeTimer = setTimeout(function() {
            console.log('Ajustando columnas de la tabla...');
            table.columns.adjust();
        }, 250); // Espera 250ms después de que se deja de cambiar el tamaño
    });
});