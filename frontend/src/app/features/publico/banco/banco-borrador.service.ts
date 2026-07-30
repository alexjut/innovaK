import { Injectable } from '@angular/core';

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
 * ── Por qué localStorage y no el servidor ──────────────────────────────
 * El formulario es público (sin login) y se abre con un token HMAC del QR; no
 * hay identidad con la que amarrar un borrador en la BD, y la tabla cabecera
 * solo se escribe al radicar (`radicado_at`). Mientras el contrato no exponga
 * un endpoint de borrador, el respaldo vive en el dispositivo:
 *   · es síncrono e instantáneo, sin depender de la señal;
 *   · sobrevive al cierre del navegador;
 *   · no crea inscripciones a medias que después haya que barrer.
 * La contrapartida está asumida y avisada en la UI: el borrador NO viaja de un
 * dispositivo a otro. Si el backend agrega `POST …/borrador/`, se cambia
 * `guardar`/`cargar` acá y el componente no se toca.
 *
 * ── Qué NO se guarda ───────────────────────────────────────────────────
 * Los archivos. Un `File` no es serializable y "guardar el nombre" sería peor
 * que no guardarlo: el usuario creería que su cédula quedó adjunta. Al
 * restaurar, la UI pide volver a adjuntar los soportes, explícitamente.
 */

/** Bump cuando el modelo cambie de forma incompatible: descarta borradores viejos. */
const VERSION = 1;

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
  private clave(eventoId: number): string {
    return `banco_borrador_v${VERSION}_${eventoId}`;
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

  descartar(eventoId: number): void {
    try {
      localStorage.removeItem(this.clave(eventoId));
    } catch {
      /* sin storage no hay nada que borrar */
    }
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
