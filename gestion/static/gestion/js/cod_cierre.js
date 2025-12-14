// gestion/static/gestion/js/cod_cierre.js

$(document).ready(function() {
    // Obtenemos el total de registros desde el atributo data del contenedor
    const totalRegistrosDB = $('.page-container').data('total-registros') || 0;

    var table = $('#tabla-codigos-cierre').DataTable({
        "language": {
            "lengthMenu": "Mostrar _MENU_ registros por página",
            "zeroRecords": "No se encontraron resultados",
            "info": "Mostrando página _PAGE_ de _PAGES_",
            "infoEmpty": "No hay registros disponibles",
            "infoFiltered": "(filtrado de un total de _MAX_ registros)",
            "search": "Buscar:", // Se cambió a un texto más genérico
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
        "columnDefs": [
            { "width": "5%", "targets": [0, 1] }, // Eliminar y Editar
            { "width": "15%", "targets": 2 }, // Código de Cierre
            { "width": "20%", "targets": 3 }, // Aplicación
            { "width": "30%", "targets": 4 }, // Descripción
            { "width": "30%", "targets": 5 } // Causa de Cierre
        ],
        "initComplete": function(settings, json) {
            $('#tabla-codigos-cierre').removeClass('data-table-loading');
        },
        "drawCallback": function(settings) {
            var api = this.api();
            var filteredCount = api.page.info().recordsDisplay;

            // Usamos la variable JS que obtuvimos del HTML
            const infoHtml = `
                <div class="total-records-info">Total de registros existentes: <strong>${totalRegistrosDB}</strong></div>
                <div class="filtered-records-info">Registros encontrados (filtrados): <strong>${filteredCount}</strong></div>
            `;
            $('#tabla-codigos-cierre_info').html(infoHtml);
        }
    });

    // --- INICIO: CÓDIGO AÑADIDO PARA LOS FILTROS ---
    $('#toggle-filters-btn').on('click', function(event) {
        var filterContainer = $('#filter-container');
        if (filterContainer.is(':visible')) {
            filterContainer.slideUp();
            $(this).text('Mostrar Filtros');
        } else {
            filterContainer.slideDown(function() {
                table.columns.adjust().draw();
            });
            $(this).text('Ocultar Filtros');
        }
    });

    let resizeTimer;
    $(window).on('resize', function() {
        clearTimeout(resizeTimer);
        resizeTimer = setTimeout(function() {
            table.columns.adjust();
        }, 250);
    });
    // --- FIN: CÓDIGO AÑADIDO ---
});