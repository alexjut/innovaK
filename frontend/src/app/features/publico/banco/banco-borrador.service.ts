import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable, of } from 'rxjs';
import { catchError, map } from 'rxjs/operators';

import { ConfigService } from '../../../core/config/config.service';
import { BancoForm, formInicial } from './banco-form.model';

/**
 * Guardado progresivo del formulario del Banco.
 *
 * ── Por qué existe ─────────────────────────────────────────────────────
 * El documento estima entre 45 y 60 minutos de diligenciamiento, y lo llena
 * una organización desde un celular. Perder eso por un timeout, una llamada
 * entrante o un toque en "atrás" es perder la postulación entera: no hay etapa
 * de subsanación en el modelo ciego.
 *
 * ── Dos capas, y ninguna sobra (2026-08-10) ────────────────────────────
 * Nació solo con localStorage porque el backend no tenía dónde guardar un
 * borrador. Desde el 2026-08-10 existe `…/borrador/` (Mongo cifrado, token
 * HMAC), así que ahora se escribe en los dos lados y cada capa cubre el hueco
 * de la otra:
 *
 *   localStorage  síncrono, instantáneo y funciona SIN señal — que es el caso
 *                 real de quien llena esto desde un celular en territorio.
 *                 No cruza de un dispositivo a otro.
 *   servidor      sobrevive a cambiar de teléfono, a limpiar el navegador y al
 *                 modo privado. Depende de la conexión, así que va best-effort:
 *                 si falla, el formulario sigue igual de usable.
 *
 * Al retomar se prefiere **el más reciente de los dos**, comparando la marca
 * de tiempo. El servidor no manda por ser servidor: si alguien siguió
 * escribiendo sin señal, lo de este aparato es lo bueno.
 *
 * El Documento Guía pide «guardado progresivo síncrono en el servidor»: esa es
 * la capa nueva. La local se conserva porque quitarla empeoraría el caso que
 * más importa.
 *
 * ── Qué NO se guarda ───────────────────────────────────────────────────
 * Los archivos. Un `File` no es serializable y "guardar el nombre" sería peor
 * que no guardarlo: el usuario creería que su cédula quedó adjunta. Al
 * restaurar, la UI pide volver a adjuntar los soportes, explícitamente.
 */

/** Bump cuando el modelo cambie de forma incompatible: descarta borradores viejos. */
const VERSION = 1;

/** Respuesta de `PUT …/borrador/`. */
interface RespuestaGuardar {
  guardado: boolean;
  token?: string;
  guardado_en?: string;
}

/** Respuesta de `GET …/borrador/`. */
interface RespuestaLeer {
  encontrado: boolean;
  datos?: { form?: unknown; seccion?: number };
  guardado_en?: string;
}

interface Sobre {
  version: number;
  guardado_en: string;
  seccion: number;
  form: unknown;
}

export interface BorradorRecuperado {
  form: BancoForm;
  seccion: number;
  guardadoEn: Date;
}

@Injectable({ providedIn: 'root' })
export class BancoBorradorService {
  private http = inject(HttpClient);
  private cfg = inject(ConfigService);

  private clave(eventoId: number): string {
    return `banco_borrador_v${VERSION}_${eventoId}`;
  }

  /** Dónde se recuerda el token del borrador del servidor, por evento. */
  private claveToken(eventoId: number): string {
    return `banco_borrador_token_v${VERSION}_${eventoId}`;
  }

  private url(eventoId: number): string {
    return this.cfg.url(`/banco-iniciativas/api/publico/${eventoId}/borrador/`);
  }

  /** Token del borrador en el servidor, si este dispositivo tiene uno. */
  token(eventoId: number): string | null {
    try {
      return localStorage.getItem(this.claveToken(eventoId));
    } catch {
      return null;
    }
  }

  private recordarToken(eventoId: number, token: string): void {
    try {
      localStorage.setItem(this.claveToken(eventoId), token);
    } catch {
      /* sin storage el token se pierde al recargar: se creará otro borrador */
    }
  }

  /** Escribe el borrador. Nunca lanza: si el storage falla, no se pierde nada más. */
  guardar(eventoId: number, form: BancoForm, seccion: number): boolean {
    try {
      const sobre: Sobre = {
        version: VERSION,
        guardado_en: new Date().toISOString(),
        seccion,
        form: aPlano(form),
      };
      localStorage.setItem(this.clave(eventoId), JSON.stringify(sobre));
      return true;
    } catch {
      // Modo privado de Safari, cuota llena, storage deshabilitado… el
      // formulario sigue usable; solo se pierde la red de seguridad.
      return false;
    }
  }

  /** Devuelve el borrador guardado, o `null` si no hay o está corrupto. */
  cargar(eventoId: number): BorradorRecuperado | null {
    try {
      const crudo = localStorage.getItem(this.clave(eventoId));
      if (!crudo) return null;
      const sobre = JSON.parse(crudo) as Sobre;
      if (sobre?.version !== VERSION || !sobre.form) return null;
      return {
        // Se hidrata SOBRE el estado inicial: si el modelo ganó campos desde
        // que se guardó, entran con su valor por defecto en lugar de undefined.
        form: hidratar(formInicial(), revivir(sobre.form)),
        seccion: Number(sobre.seccion) || 1,
        guardadoEn: new Date(sobre.guardado_en),
      };
    } catch {
      return null;
    }
  }

  /**
   * Sube el borrador al servidor. Best-effort: NUNCA propaga el error.
   *
   * Que falle la sincronización no puede interrumpir a quien está escribiendo;
   * ya quedó guardado en el dispositivo, que es la capa que de verdad no puede
   * fallar. Devuelve si logró subirlo, solo para que la UI pueda decir la
   * verdad sobre dónde está el respaldo.
   */
  sincronizar(eventoId: number, form: BancoForm, seccion: number): Observable<boolean> {
    const cuerpo = {
      token: this.token(eventoId),
      datos: { form: aPlano(form), seccion },
    };
    return this.http.put<RespuestaGuardar>(this.url(eventoId), cuerpo).pipe(
      map((r) => {
        if (r?.token) this.recordarToken(eventoId, r.token);
        return !!r?.guardado;
      }),
      catchError(() => of(false)),
    );
  }

  /**
   * Trae el borrador del servidor, o `null` si no hay.
   *
   * Sirve para el caso que localStorage no cubre: el ciudadano empezó en el
   * computador de la casa y sigue en el celular, o limpió el navegador.
   */
  cargarDelServidor(eventoId: number): Observable<BorradorRecuperado | null> {
    const token = this.token(eventoId);
    if (!token) return of(null);
    const url = `${this.url(eventoId)}?borrador=${encodeURIComponent(token)}`;
    return this.http.get<RespuestaLeer>(url).pipe(
      map((r) => {
        if (!r?.encontrado || !r.datos?.form) return null;
        return {
          form: hidratar(formInicial(), revivir(r.datos.form)),
          seccion: Number(r.datos.seccion) || 1,
          guardadoEn: new Date(r.guardado_en ?? Date.now()),
        };
      }),
      catchError(() => of(null)),
    );
  }

  /** El más reciente entre el del dispositivo y el del servidor. */
  masReciente(
    local: BorradorRecuperado | null,
    remoto: BorradorRecuperado | null,
  ): BorradorRecuperado | null {
    if (!local) return remoto;
    if (!remoto) return local;
    return remoto.guardadoEn > local.guardadoEn ? remoto : local;
  }

  /** Borra el borrador de los dos lados. */
  descartar(eventoId: number): void {
    const token = this.token(eventoId);
    try {
      localStorage.removeItem(this.clave(eventoId));
      localStorage.removeItem(this.claveToken(eventoId));
    } catch {
      /* sin storage no hay nada que borrar */
    }
    if (!token) return;
    // Se dispara y se olvida: si el servidor no responde, el borrador vence
    // solo a los 30 días y el comando de purga lo recoge.
    this.http
      .delete(`${this.url(eventoId)}?borrador=${encodeURIComponent(token)}`)
      .subscribe({ next: () => undefined, error: () => undefined });
  }
}

// ═══════════════════════════════════════════════════════════════════════
// Serialización
//
// JSON no conoce Set, y el formulario los usa para toda selección múltiple.
// Se marcan con `__set` en vez de convertirlos a arreglo a secas para que al
// hidratar se pueda distinguir un Set de una lista ordenada (los enfoques SON
// una lista ordenada: su posición es el puntaje).
// ═══════════════════════════════════════════════════════════════════════

function aPlano(valor: unknown): unknown {
  if (valor instanceof Set) return { __set: [...valor] };
  if (valor instanceof File || valor instanceof Blob) return null;
  if (Array.isArray(valor)) return valor.map(aPlano);
  if (valor && typeof valor === 'object') {
    const salida: Record<string, unknown> = {};
    for (const [k, v] of Object.entries(valor as Record<string, unknown>)) {
      salida[k] = aPlano(v);
    }
    return salida;
  }
  return valor;
}

function esSobreSet(valor: unknown): valor is { __set: unknown[] } {
  return (
    !!valor &&
    typeof valor === 'object' &&
    Array.isArray((valor as { __set?: unknown }).__set)
  );
}

/**
 * Deshace `aPlano`: todo `{__set:[…]}` vuelve a ser un `Set`, a cualquier
 * profundidad. Se hace en una pasada aparte (y no dentro de `hidratar`) porque
 * hay Sets en filas que el estado inicial no tiene — `enfoques_52` arranca
 * vacío y sus filas llevan `opciones: Set`. Si eso no se revive, el template
 * llamaría `.has()` sobre un objeto plano y la sección revienta en runtime.
 */
function revivir(valor: unknown): unknown {
  if (esSobreSet(valor)) return new Set(valor.__set.map(String));
  if (Array.isArray(valor)) return valor.map(revivir);
  if (valor && typeof valor === 'object') {
    const salida: Record<string, unknown> = {};
    for (const [k, v] of Object.entries(valor as Record<string, unknown>)) {
      salida[k] = revivir(v);
    }
    return salida;
  }
  return valor;
}

/**
 * Copia `guardado` encima de `base` respetando la forma de `base`. Solo se
 * hidratan claves que el modelo actual conoce: un borrador viejo con campos
 * retirados no puede reinyectarlos.
 */
function hidratar<T>(base: T, guardado: unknown): T {
  if (!guardado || typeof guardado !== 'object') return base;
  const origen = guardado as Record<string, unknown>;
  const destino = base as unknown as Record<string, unknown>;

  for (const clave of Object.keys(destino)) {
    if (!(clave in origen)) continue;
    const actual = destino[clave];
    const nuevo = origen[clave];

    if (actual instanceof Set) {
      if (nuevo instanceof Set) destino[clave] = nuevo;
      continue;
    }
    if (Array.isArray(actual)) {
      if (Array.isArray(nuevo)) destino[clave] = nuevo;
      continue;
    }
    if (actual && typeof actual === 'object') {
      destino[clave] = hidratar(actual, nuevo);
      continue;
    }
    destino[clave] = nuevo;
  }
  return base;
}
