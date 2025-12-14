// gestion/static/gestion/js/mantenedores.js

$(document).ready(function() {
    // Inicializamos la tabla DataTables
    const table = $('#tabla-mantenedor').DataTable({
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
        "initComplete": function(settings, json) {
            $('#tabla-mantenedor').removeClass('data-table-loading');
        }
    });

    // Lógica para mostrar/ocultar el formulario de registro
    const formContainer = $('#form-container');
    const registerButton = $('#btn-registrar');
    const cancelButton = $('.btn-cancelar');

    if (formContainer.length && registerButton.length) {
        registerButton.on('click', function() {
            formContainer.slideDown(function() {
                // Ajustar las columnas después de mostrar el formulario
                table.columns.adjust().draw();
            });
            $(this).hide();
        });

        cancelButton.on('click', function() {
            formContainer.slideUp();
            registerButton.show();
        });
    }

    // Lógica para el botón de mostrar/ocultar filtros (si existe)
    $('#toggle-filters-btn').on('click', function() {
        const filterContainer = $('#filter-container');
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

    // Ajuste de columnas en el cambio de tamaño de la ventana
    let resizeTimer;
    $(window).on('resize', function() {
        clearTimeout(resizeTimer);
        resizeTimer = setTimeout(function() {
            table.columns.adjust();
        }, 250);
    });

});