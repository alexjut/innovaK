document.addEventListener("DOMContentLoaded", () => {
  // =========================
  // Sidebar
  // =========================
  const toggleBtn = document.querySelector(".base-toggle-btn");
  const sidebar = document.querySelector(".base-sidebar");

  if (toggleBtn && sidebar) {
    toggleBtn.addEventListener("click", (e) => {
      e.preventDefault();
      sidebar.classList.toggle("active");
    });
  }

  // =========================
  // Dropdown de usuario
  // =========================
  const userDropdown = document.querySelector(".user-dropdown-toggle");
  const dropdownMenu = document.querySelector(".base-user-dropdown .dropdown-menu");

  // Si no hay usuario autenticado, no existe dropdown -> no rompas el JS
  if (userDropdown && dropdownMenu) {
    userDropdown.addEventListener("click", (event) => {
      event.preventDefault();
      event.stopPropagation();
      dropdownMenu.classList.toggle("show");
    });

    // Cerrar dropdown al hacer clic fuera
    document.addEventListener("click", (event) => {
      if (!userDropdown.contains(event.target) && !dropdownMenu.contains(event.target)) {
        dropdownMenu.classList.remove("show");
      }
    });

    // Cerrar con tecla ESC
    document.addEventListener("keydown", (event) => {
      if (event.key === "Escape") {
        dropdownMenu.classList.remove("show");
      }
    });
  }
});
