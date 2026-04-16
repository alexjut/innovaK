document.addEventListener("DOMContentLoaded", function () {
  // =========================
  // Sidebar
  // =========================
  const toggleBtn = document.getElementById("toggleSidebar");
  const sidebar = document.getElementById("baseSidebar");

  if (toggleBtn && sidebar) {
    toggleBtn.addEventListener("click", function (e) {
      e.preventDefault();
      e.stopPropagation();
      sidebar.classList.toggle("active");
    });

    // Cerrar sidebar al hacer clic fuera
    document.addEventListener("click", function (e) {
      const clickDentroSidebar = sidebar.contains(e.target);
      const clickEnBoton = toggleBtn.contains(e.target);

      if (!clickDentroSidebar && !clickEnBoton) {
        sidebar.classList.remove("active");
      }
    });

    // Cerrar con ESC
    document.addEventListener("keydown", function (e) {
      if (e.key === "Escape") {
        sidebar.classList.remove("active");
      }
    });
  }

  // =========================
  // Dropdown de usuario
  // =========================
  const userDropdown = document.querySelector(".user-dropdown-toggle");
  const dropdownMenu = document.querySelector(".base-user-dropdown .dropdown-menu");

  if (userDropdown && dropdownMenu) {
    userDropdown.addEventListener("click", function (event) {
      event.preventDefault();
      event.stopPropagation();
      dropdownMenu.classList.toggle("show");
    });

    // Evita que se cierre al hacer clic dentro del menú
    dropdownMenu.addEventListener("click", function (event) {
      event.stopPropagation();
    });

    // Cerrar dropdown al hacer clic fuera
    document.addEventListener("click", function (event) {
      if (!userDropdown.contains(event.target) && !dropdownMenu.contains(event.target)) {
        dropdownMenu.classList.remove("show");
      }
    });

    // Cerrar con ESC
    document.addEventListener("keydown", function (event) {
      if (event.key === "Escape") {
        dropdownMenu.classList.remove("show");
      }
    });
  }
});