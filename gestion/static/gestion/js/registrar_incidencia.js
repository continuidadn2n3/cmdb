// gestion/static/gestion/js/registrar_incidencia.js

document.addEventListener('DOMContentLoaded', function() {

    /**
     * LÓGICA PARA LA PÁGINA DE REGISTRAR/EDITAR INCIDENCIA
     * Se identifica por la presencia del contenedor con la clase 'page-container-incidencia'.
     */
    const pageContainerIncidencia = document.querySelector('.page-container-incidencia');
    if (pageContainerIncidencia) {
        console.log("Página de Incidencia detectada. Inicializando script de códigos de cierre...");

        const ID_APLICACION_SELECCIONADA = pageContainerIncidencia.dataset.aplicacionId;
        const ID_CODIGO_CIERRE_SELECCIONADO = pageContainerIncidencia.dataset.codigoCierreId;
        const URL_CODIGOS_CIERRE = pageContainerIncidencia.dataset.codigosCierreUrl;

        const aplicacionSelect = document.getElementById('aplicacion');
        const codigoCierreSelect = document.getElementById('codigo_cierre');

        if (!aplicacionSelect || !codigoCierreSelect) {
            console.error("No se encontraron los elementos select de aplicación o código de cierre.");
            return;
        }

        const cargarCodigosDeCierre = () => {
            const aplicacionId = aplicacionSelect.value;
            console.log("ID de aplicación seleccionado:", aplicacionId);

            codigoCierreSelect.innerHTML = '<option value="">Cargando...</option>';
            codigoCierreSelect.disabled = true;

            if (!aplicacionId) {
                codigoCierreSelect.innerHTML = '<option value="">Seleccione una aplicación primero...</option>';
                codigoCierreSelect.disabled = true;
                return;
            }

            const url = URL_CODIGOS_CIERRE.replace('0', aplicacionId);
            console.log("Llamando a la URL:", url);

            fetch(url)
                .then(response => {
                    if (!response.ok) throw new Error(`Error de red: ${response.status}`);
                    return response.json();
                })
                .then(data => {
                    console.log("Datos (JSON) recibidos:", data);
                    codigoCierreSelect.innerHTML = '<option value="">Seleccione un código...</option>';
                    codigoCierreSelect.disabled = false;

                    data.forEach(function(codigo) {
                        const option = document.createElement('option');
                        option.value = codigo.id;
                        option.textContent = `${codigo.codigo} - ${codigo.descripcion}`;

                        if (ID_CODIGO_CIERRE_SELECCIONADO && codigo.id == ID_CODIGO_CIERRE_SELECCIONADO) {
                            option.selected = true;
                        }
                        codigoCierreSelect.appendChild(option);
                    });
                })
                .catch(error => {
                    console.error('Error durante la operación fetch:', error);
                    codigoCierreSelect.innerHTML = '<option value="">Error al cargar datos</option>';
                    codigoCierreSelect.disabled = true;
                });
        };

        aplicacionSelect.addEventListener('change', cargarCodigosDeCierre);

        if (ID_APLICACION_SELECCIONADA) {
            console.log("Disparando carga inicial de códigos de cierre.");
            cargarCodigosDeCierre();
        }
    }

    /**
     * LÓGICA PARA LA PÁGINA DE REGISTRAR/EDITAR CÓDIGO DE CIERRE
     * Se identifica por la presencia del contenedor de "últimos códigos".
     */
    const ultimosCodigosContainer = document.getElementById('ultimos-codigos-container');
    if (ultimosCodigosContainer) {
        console.log("Página de Código de Cierre detectada. Inicializando script de últimos códigos...");

        const aplicacionSelect = document.getElementById('aplicacion');
        const lista = document.getElementById('lista-ultimos-codigos');

        if (aplicacionSelect && aplicacionSelect.dataset.url) {
            const urlTemplate = aplicacionSelect.dataset.url;

            aplicacionSelect.addEventListener('change', function() {
                const aplicacionId = this.value;

                if (!aplicacionId) {
                    ultimosCodigosContainer.style.display = 'none';
                    return;
                }

                const url = urlTemplate.replace('0', aplicacionId);

                fetch(url)
                    .then(response => response.ok ? response.json() : Promise.reject('Error de red'))
                    .then(data => {
                        lista.innerHTML = '';
                        if (data.codigos && data.codigos.length > 0) {
                            data.codigos.forEach(codigo => {
                                const li = document.createElement('li');
                                li.innerHTML = `<span class="codigo-item-code">${codigo.cod_cierre}</span> <span class="codigo-item-desc">${codigo.desc_cod_cierre}</span>`;
                                lista.appendChild(li);
                            });
                        } else {
                            lista.innerHTML = `<li class="mensaje-info">No se encontraron códigos de cierre para esta aplicación.</li>`;
                        }
                        ultimosCodigosContainer.style.display = 'block';
                    })
                    .catch(error => {
                        console.error('Error al obtener los códigos de cierre:', error);
                        lista.innerHTML = `<li class="mensaje-info">Ocurrió un error al cargar los datos.</li>`;
                        ultimosCodigosContainer.style.display = 'block';
                    });
            });
        }
    }
});