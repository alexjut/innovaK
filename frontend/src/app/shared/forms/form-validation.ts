/**
 * Utilidades de validación de formularios — agnósticas al componente.
 *
 * El SPA usa formularios template-driven (`[(ngModel)]` sobre objetos
 * planos), no `FormGroup`. Estas funciones operan sobre el DOM por
 * atributo `name` / `data-field`, así sirven a cualquier componente sin
 * acoplarse a su modelo. Mantienen la lógica fuera de la presentación
 * (regla Angular-ready §1).
 *
 * Patrón de uso típico en un componente con signals:
 *
 *   campoErrores = signal<Record<string, string>>({});
 *
 *   guardar() {
 *     const faltan = camposVacios(this.form, ['nombre', 'fecha_inicio']);
 *     if (faltan.length) {
 *       this.campoErrores.set(erroresObligatorios(faltan));
 *       enfocarPrimerInvalido(this.host, faltan);
 *       return;
 *     }
 *     this.api.crear(...).subscribe({
 *       error: (err) => {
 *         const errs = mapearErroresBackend(err);
 *         this.campoErrores.set(errs);
 *         enfocarPrimerInvalido(this.host, Object.keys(errs));
 *       },
 *     });
 *   }
 *
 *   // En el (input)/(change) de cada control:
 *   limpiarError(campo: string) {
 *     this.campoErrores.update((e) => limpiarCampo(e, campo));
 *   }
 *
 * La clase CSS global `.is-invalid` (ver `src/styles/_forms.scss`)
 * resalta el control en rojo. Se aplica con `[class.is-invalid]`.
 */

/** Forma del 400 que devuelve el backend para errores por campo. */
export interface BackendErrorBody {
  detail?: string;
  errors?: Record<string, string | string[]>;
  non_field_errors?: string[];
  [campo: string]: unknown;
}

export interface HttpErrorLike {
  error?: BackendErrorBody;
  status?: number;
  message?: string;
}

/**
 * Devuelve los nombres de campo que están vacíos (null / undefined /
 * cadena en blanco) dentro de `model`, en el orden de `requeridos`.
 */
export function camposVacios(
  model: Record<string, unknown>,
  requeridos: string[],
): string[] {
  return requeridos.filter((campo) => {
    const v = model[campo];
    return v === null || v === undefined || (typeof v === 'string' && v.trim() === '');
  });
}

/**
 * Construye un dict `{campo: mensaje}` para una lista de campos
 * obligatorios faltantes.
 */
export function erroresObligatorios(
  campos: string[],
  mensaje = 'Este campo es obligatorio.',
): Record<string, string> {
  const out: Record<string, string> = {};
  for (const c of campos) out[c] = mensaje;
  return out;
}

/**
 * Mapea el cuerpo de error del backend a `{campo: mensaje}`.
 * Soporta tanto `{errors: {campo: msg}}` (contrato nuevo) como el
 * formato DRF clásico `{campo: [msg]}`. `detail` / `non_field_errors`
 * se exponen bajo la clave `__all__` para mensajes generales.
 */
export function mapearErroresBackend(err: HttpErrorLike): Record<string, string> {
  const body = err?.error ?? {};
  const out: Record<string, string> = {};

  const errores = body.errors;
  if (errores && typeof errores === 'object') {
    for (const [campo, msg] of Object.entries(errores)) {
      out[campo] = Array.isArray(msg) ? String(msg[0] ?? '') : String(msg ?? '');
    }
  }

  // Fallback DRF clásico: claves de campo directas con arrays de strings.
  if (!Object.keys(out).length) {
    for (const [k, v] of Object.entries(body)) {
      if (k === 'detail' || k === 'errors' || k === 'non_field_errors') continue;
      if (Array.isArray(v) && v.length) out[k] = String(v[0]);
    }
  }

  if (body.non_field_errors?.length) out['__all__'] = body.non_field_errors[0];
  else if (body.detail && !Object.keys(out).length) out['__all__'] = body.detail;

  return out;
}

/** Mensaje general legible para mostrar arriba del formulario. */
export function mensajeGeneral(err: HttpErrorLike, fallback = 'Error inesperado.'): string {
  const body = err?.error;
  if (body?.detail) return body.detail;
  if (body?.non_field_errors?.length) return body.non_field_errors[0];
  if (err?.status === 401 || err?.status === 403) return 'No tienes permiso para esta acción.';
  return err?.message || fallback;
}

/**
 * Quita un campo del dict de errores (limpieza reactiva al corregir).
 * Devuelve un objeto nuevo (inmutable, apto para `signal.update`).
 */
export function limpiarCampo(
  errores: Record<string, string>,
  campo: string,
): Record<string, string> {
  if (!(campo in errores)) return errores;
  const { [campo]: _omitido, ...resto } = errores;
  return resto;
}

/**
 * Hace scroll suave hasta el primer control inválido y lo enfoca.
 *
 * Busca por `[name="campo"]` o `[data-field="campo"]` dentro de `host`
 * (o `document` si no se pasa). Respeta el orden de `campos`, de modo
 * que el primero de la lista que exista en el DOM es el que recibe foco.
 */
export function enfocarPrimerInvalido(
  host: { nativeElement: HTMLElement } | HTMLElement | null,
  campos: string[],
): void {
  const root: ParentNode =
    host == null
      ? document
      : host instanceof HTMLElement
        ? host
        : host.nativeElement;

  for (const campo of campos) {
    const sel = `[name="${campo}"],[data-field="${campo}"]`;
    const el = root.querySelector<HTMLElement>(sel);
    if (el) {
      el.scrollIntoView({ behavior: 'smooth', block: 'center' });
      // El scroll suave y el focus pueden competir; demoramos el focus.
      setTimeout(() => el.focus({ preventScroll: true }), 150);
      return;
    }
  }
}
