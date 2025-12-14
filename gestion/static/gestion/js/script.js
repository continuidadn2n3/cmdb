// gestion/static/gestion/js/script.js

// Creamos un objeto principal para toda nuestra aplicación.
// Esto nos ayuda a mantener el código organizado y evitar conflictos.
const App = {
    // La función init será el punto de entrada principal.
    init: function() {
        console.log("Inicializando App global...");
        this.initSpinner();
        this.initFooter();
    },

    // Módulo para manejar toda la lógica del spinner de carga.
    initSpinner: function() {
        const spinner = document.getElementById('loading-spinner');
        if (!spinner) return; // Si no hay spinner en la página, no hacemos nada.

        // Lógica para Formularios
        const formsConSpinner = document.querySelectorAll('.form-con-spinner');
        formsConSpinner.forEach(form => {
            form.addEventListener('submit', function() {
                spinner.style.display = 'flex';
            });
        });

        // Lógica para Enlaces de Navegación (que no son de descarga)
        const navLinks = document.querySelectorAll('.link-con-spinner:not(.download-link)');
        navLinks.forEach(link => {
            link.addEventListener('click', function() {
                spinner.style.display = 'flex';
            });
        });

        // Lógica para Enlaces de Descarga
        const downloadLinks = document.querySelectorAll('.download-link');
        downloadLinks.forEach(link => {
            link.addEventListener('click', function() {
                spinner.style.display = 'flex';
                const cookieCheckInterval = setInterval(function() {
                    if (document.cookie.split(';').some((item) => item.trim().startsWith('descargaFinalizada='))) {
                        clearInterval(cookieCheckInterval);
                        spinner.style.display = 'none';
                        document.cookie = "descargaFinalizada=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;";
                    }
                }, 500);
            });
        });
    },

    // Módulo para actualizar el año en el footer.
    initFooter: function() {
        const dateElement = document.getElementById('footer-date');
        if (dateElement) {
            const currentYear = new Date().getFullYear();
            dateElement.textContent = `© ${currentYear} CMDB Systems. Todos los derechos reservados.`;
        }
    }
};

// Punto de entrada: Se asegura de que todo el HTML esté listo antes de ejecutar el código.
document.addEventListener('DOMContentLoaded', function() {
    App.init();
});