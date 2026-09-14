/**
 * De un error HTTP al mensaje que lee un funcionario. Una sola implementación.
 *
 * ## Qué defecto cierra
 *
 * Doce `catch` de /plan guardaban una lista vacía sin mirar el error, y el
 * template leía ese vacío como «no hay datos». Dos de ellos llegaban a afirmar
 * un hecho falso con una instrucción accionable equivocada:
 *
 *   · «Todavía no hay Plan cargado. Entra con la Matriz PDL» — lo veían 6 de
 *     los 8 usuarios activos no-superusuario, que reciben 403 en ese endpoint,
 *     con el Plan cargado entero (78 metas). Volver a subir la Matriz no
 *     arregla una falta de permiso.
 *   · «Ninguna meta enganchada aún. Corre la ingesta y el mapeo» — idem, pero
 *     mandando a correr una ingesta.
 *
 * Un vacío y un fallo se ven igual si no se distinguen, y llevan a conclusiones
 * opuestas. Y dentro del fallo, un 401/403 tiene un dueño distinto: no lo
 * arregla quien mira la pantalla, lo arregla quien administra los roles.
 *
 * ## Por qué acá y no en cada componente
 *
 * Porque así nació el defecto: el mismo string estaba copiado letra por letra
 * en dos archivos. Con una función, arreglar el texto lo arregla en todos.
 *
 * Tratamiento de USTED: esta app la usa la Alcaldía de Bogotá y el resto de la
 * interfaz habla así.
 */

export interface ErrorDeCarga {
  /** Clase de Font Awesome, sin el prefijo `fa`. */
  icono: string;
  titulo: string;
  detalle: string;
  /** `true` cuando el dueño del arreglo NO es quien mira la pantalla. */
  esDePermiso: boolean;
}

/**
 * @param e     el error que capturó el `catch` (se lee `e.status`).
 * @param queCosa  qué se estaba leyendo, en minúscula y sin artículo:
 *                 «el Plan», «los CDP», «el gasto». Va dentro de la frase.
 */
export function errorDeCarga(e: any, queCosa: string): ErrorDeCarga {
  const st = e?.status;
  if (st === 401 || st === 403) {
    return {
      icono: 'fa-lock',
      titulo: `No tiene permiso para ver ${queCosa}`,
      detalle:
        'Su rol no incluye este módulo, o se venció la sesión. El dato sí '
        + 'está cargado: pida el acceso a quien administra los roles, o '
        + 'vuelva a entrar.',
      esDePermiso: true,
    };
  }
  if (st === 0 || st === undefined) {
    return {
      icono: 'fa-plug-circle-xmark',
      titulo: 'No se pudo hablar con el servidor',
      detalle: 'Revise la conexión y vuelva a intentar.',
      esDePermiso: false,
    };
  }
  return {
    icono: 'fa-triangle-exclamation',
    titulo: `No se pudo leer ${queCosa}`,
    detalle: `El servidor respondió con un error ${st}. Vuelva a intentar en `
           + 'un momento; si sigue igual, avise.',
    esDePermiso: false,
  };
}
