/* gestion/static/gestion/js/dashboard.js */

document.addEventListener('DOMContentLoaded', function() {
    // --- Lógica para el botón de mostrar/ocultar filtros ---
    const toggleFiltersBtn = document.getElementById('toggle-filters-btn');
    const filterContainer = document.getElementById('filter-container');

    if (toggleFiltersBtn && filterContainer) {
        toggleFiltersBtn.addEventListener('click', function() {
            // Comprueba si el contenedor está visible o no
            const isVisible = filterContainer.style.display === 'block';

            // Cambia la visibilidad y el texto del botón
            if (isVisible) {
                filterContainer.style.display = 'none';
                this.textContent = 'Mostrar Filtros';
            } else {
                filterContainer.style.display = 'block';
                this.textContent = 'Ocultar Filtros';
            }
        });
    }

    // --- Lógica para el botón de limpiar filtros ---
    const limpiarFiltrosBtn = document.getElementById('limpiar-filtros-btn');
    const filterForm = document.querySelector('form[method="get"]'); // Selecciona el formulario de filtros

    if (limpiarFiltrosBtn && filterForm) {
        limpiarFiltrosBtn.addEventListener('click', function() {
            // Itera sobre todos los elementos del formulario
            Array.from(filterForm.elements).forEach(element => {
                if (element.type === 'text' || element.type === 'date') {
                    element.value = ''; // Limpia campos de texto y fecha
                } else if (element.tagName === 'SELECT') {
                    element.selectedIndex = 0; // Restablece los <select> a la primera opción ("Todos")
                }
            });

            // Opcional: puedes enviar el formulario automáticamente para ver los resultados sin filtros
            // filterForm.submit(); 
        });
    }
});