document.addEventListener("DOMContentLoaded", function () {
    let toggleBtn = document.querySelector('.base-toggle-btn');
    let sidebar = document.querySelector('.base-sidebar');

    // Alternar menú lateral sin mover el contenido
    toggleBtn.addEventListener("click", function () {
        sidebar.classList.toggle('active');
    });

    // Dropdown de usuario
    let userDropdown = document.querySelector(".user-dropdown-toggle");
    let dropdownMenu = document.querySelector(".dropdown-menu");

    userDropdown.addEventListener("click", function (event) {
        event.stopPropagation(); // Evita que el evento se propague y cierre de inmediato
        dropdownMenu.classList.toggle("show");
    });

    // Cerrar dropdown al hacer clic fuera
    document.addEventListener("click", function (event) {
        if (!userDropdown.contains(event.target) && !dropdownMenu.contains(event.target)) {
            dropdownMenu.classList.remove("show");
        }
    });
});
