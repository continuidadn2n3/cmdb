// gestion/static/gestion/js/aplicaciones.js

$(document).ready(function() {
    // Obtenemos el total de registros desde el atributo data-* del contenedor principal
    const totalRegistros = $('.page-container').data('total-registros') || 0;

    // Guardamos la instancia de la tabla en una variable para poder usarla después
    var table = $('#tabla-aplicaciones').DataTable({
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
        "scrollY": "60vh",
        "scrollCollapse": true,
        "paging": true,
        "pageLength": 25,
        "order": [
            [2, "asc"]
        ],
        "initComplete": function(settings, json) {
            $('#tabla-aplicaciones').removeClass('data-table-loading');
        },
        "drawCallback": function(settings) {
            var filteredCount = this.api().page.info().recordsDisplay;
            var infoContainer = $('#tabla-aplicaciones_info');

            // Construimos el texto con el total de registros filtrados y el total general
            var filteredInfo = '<div class="filtered-records-info">Registros encontrados (filtrados): <strong>' + filteredCount + '</strong></div>';
            var totalInfo = '<div class="total-records-info">Total de registros existentes: <strong>' + totalRegistros + '</strong></div>';

            // Limpiamos los mensajes anteriores y añadimos los nuevos
            infoContainer.find('.filtered-records-info').remove();
            infoContainer.find('.total-records-info').remove();
            infoContainer.append(totalInfo);
            infoContainer.append(filteredInfo);
        }
    });

    // --- INICIO: CÓDIGO AÑADIDO PARA LOS FILTROS ---

    // Script para el botón de mostrar/ocultar filtros
    $('#toggle-filters-btn').on('click', function(event) {
        var filterContainer = $('#filter-container');
        if (filterContainer.is(':visible')) {
            filterContainer.slideUp();
            $(this).text('Mostrar Filtros');
        } else {
            filterContainer.slideDown(function() {
                // Ajustamos las columnas de la tabla para evitar desalineación
                table.columns.adjust().draw();
            });
            $(this).text('Ocultar Filtros');
        }
    });
    // --- FIN: CÓDIGO AÑADIDO PARA LOS FILTROS ---

    // ==================================================================
    // === INICIO: CÓDIGO AÑADIDO PARA CORREGIR ALINEACIÓN DE HEADER ===
    // ==================================================================
    let resizeTimer;
    $(window).on('resize', function() {
        clearTimeout(resizeTimer);
        resizeTimer = setTimeout(function() {
            console.log('Ajustando columnas de la tabla de aplicaciones...');
            table.columns.adjust();
        }, 250); // Espera un momento después de cambiar el tamaño para ajustar
    });
    // ==================================================================
    // === FIN: CÓDIGO AÑADIDO ==========================================
    // ==================================================================

    // ==================================================================
    // === INICIO: VALIDADOR PARA FORMULARIO DE CARGA MASIVA          ===
    // ==================================================================
    // Buscamos el formulario de carga en la página.
    const uploadForm = document.getElementById('upload-form');

    // Solo si el formulario existe, le añadimos el evento 'submit'.
    // Esto previene errores en páginas que no tienen este formulario.
    if (uploadForm) {
        uploadForm.addEventListener('submit', function(event) {
            const fileInput = document.getElementById('json_file');
            if (!fileInput.value) {
                // Previene el envío del formulario si está vacío
                event.preventDefault();
                // Muestra una alerta personalizada
                alert('Por favor, selecciona un archivo JSON antes de continuar.');
            }
        });
    }
    // ==================================================================
    // === FIN: VALIDADOR PARA FORMULARIO DE CARGA MASIVA             ===
    // ==================================================================
});