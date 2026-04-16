document.addEventListener("DOMContentLoaded", function () {
  const form = document.getElementById("form-participante");
  const curso = document.getElementById("id_curso");
  const evento = document.getElementById("id_evento");
  const actividad = document.getElementById("id_actividad");

  form.addEventListener("submit", function (e) {
    // Verifica que solo se haya seleccionado uno entre curso, evento o actividad
    const seleccionados = [curso, evento, actividad].filter(el => el.value && el.value !== "").length;
    if (seleccionados !== 1) {
      e.preventDefault();
      alert("❌ Debe seleccionar exactamente uno entre Curso, Evento o Actividad.");
      return;
    }

    // Validación estándar de Bootstrap
    if (!form.checkValidity()) {
      e.preventDefault();
      e.stopPropagation();
    }

    form.classList.add("was-validated");
  });
});
