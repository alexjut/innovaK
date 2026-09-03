import { CommonModule } from '@angular/common';
import { HttpClient } from '@angular/common/http';
import {
  Component, ElementRef, OnInit, ViewChild, computed, inject, signal,
} from '@angular/core';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { AuthService } from '../../../core/auth/auth.service';
import { ConfigService } from '../../../core/config/config.service';
import { LayoutService } from '../../../core/layout/layout.service';
import { ActionNoticeComponent, NoticeVariant } from '../../../shared/ui/action-notice.component';
import { ConfirmService } from '../../../shared/ui/confirm.service';
import { PageHeaderComponent } from '../../../shared/ui/page-header.component';
import { StatGridComponent, StatItem } from '../../../shared/ui/stat-grid.component';
import { ToastService } from '../../../shared/ui/toast.service';

/** El módulo N15 que gatea toda la sección `/presupuesto`. Se reusa a
 *  propósito: un código nuevo sin sembrar en `seed_modulos` deja afuera a
 *  todo el mundo menos a los superusuarios, y falla en silencio. */
const MODULO = 'presupuesto_proyectos';

// ── Contrato con el backend (apps/presupuesto/api/matriz_carga_views.py) ─────────

type EstadoCarga = 'borrador' | 'aplicada' | 'descartada';

/** Tres valores, no un booleano nullable. `MatrizPDLCarga.sin_cambios`
 *  devuelve None cuando todavía no hay diff, y en TypeScript
 *  `!carga.sin_cambios` trataría ese None como «sí hay cambios», que es
 *  justo al revés de lo prudente. Con un string de tres valores el bug
 *  no se puede representar. */
type EstadoRevision = 'con_cambios' | 'sin_cambios' | 'sin_calcular';

type ClaseCambio = 'altas' | 'cambios' | 'reactivaciones' | 'retiros';

interface CampoCambio {
  campo: string;
  campo_label?: string | null;
  de: string | number | null;
  a: string | number | null;
}

/** Un renglón ya normalizado por el servidor. El `diff` crudo tiene tres
 *  formas distintas para la misma idea —sector es un string sin código, el
 *  cambio de objetivo es plano, el de programa va anidado bajo `campos` con
 *  códigos donde debería ir un nombre—; el servidor las aplana a esta forma
 *  única y resuelve los nombres, que viven en la base y no en el payload. */
interface Renglon {
  entidad: 'sector' | 'objetivo' | 'programa';
  entidad_label: string;
  clase: ClaseCambio;
  codigo: number | null;
  titulo: string;
  campos?: CampoCambio[];
  contexto?: string | null;
}

/** El mismo renglón con `campos` ya normalizado a lista. La plantilla no
 *  tiene que preguntarse si vinieron, y con `strictTemplates` un `@for` no
 *  puede iterar algo que podría ser undefined. */
type RenglonPintable = Omit<Renglon, 'campos'> & { campos: CampoCambio[] };

interface Aviso { tipo: string; texto: string; }

interface ResumenDiff {
  altas: number;
  cambios: number;
  reactivaciones: number;
  retiros: number;
}

interface Carga {
  id: number;
  archivo_nombre: string;
  corte_oficial: string;
  estado: EstadoCarga;
  n_altas: number;
  n_cambios: number;
  n_retiros: number;
  n_errores: number;
  subido_por?: string | null;
  subido_at: string | null;
  aplicado_por?: string | null;
  aplicado_at: string | null;
  nota?: string | null;
  hash_sha256?: string | null;
  /** Solo en el detalle. */
  estado_revision?: EstadoRevision;
  puede_aplicar?: boolean | null;
  puede_aplicar_motivo?: string | null;
  resumen?: ResumenDiff;
  cambios?: Renglon[];
  avisos?: Aviso[];
}

interface Vigente {
  sectores: number;
  objetivos: number;
  programas: number;
  ultima_aplicada: {
    id: number;
    corte_oficial: string;
    aplicado_at: string | null;
    aplicado_por: string | null;
  } | null;
}

interface Contexto {
  cargas: Carga[];
  vigente?: Vigente | null;
  borrador_abierto?: { id: number; corte_oficial: string } | null;
  /** La regla la resuelve el SERVIDOR y viaja en el payload. La pantalla no la
   *  recalcula: ya existe un rol —`Planeacion`— que decide quién aplica, y una
   *  copia en TypeScript de «¿quién puede escribir?» envejece de a una mitad. */
  puede_subir?: boolean;
  puede_subir_motivo?: string | null;
}

interface Revision {
  estado_revision?: EstadoRevision;
  /** El nombre y el peso viajan acá, NO dentro de `resumen`: la API manda
   *  `archivo: {nombre, bytes, hash_sha256}` y `resumen` son solo los cuatro
   *  conteos del diff. El tipo declaraba `resumen.archivo` —un campo que la
   *  API nunca envía—, así que `strict` no podía verlo y la línea que
   *  identifica el archivo se pintaba con las comillas vacías. */
  archivo: { nombre: string; bytes: number; hash_sha256: string };
  resumen: ResumenDiff;
  cambios: Renglon[];
  avisos?: Aviso[];
  duplicado: { carga_id: number; estado: EstadoCarga; subido_at: string | null } | null;
  puede_subir: boolean;
  siguiente_paso: string;
}

interface ResultadoAplicar {
  hecho: ResumenDiff;
  carga: Carga;
  coincide: boolean;
  resultado_texto: string;
}

/** Los cuatro grupos del diff, y el ORDEN en que se leen.
 *
 *  «Salen» va primero y no al final: es la única clase que quita algo y es
 *  el síntoma de un archivo equivocado —un Excel truncado o de otro corte se
 *  manifiesta como una lista enorme de retiros—, así que va donde se lee sin
 *  scroll. Los títulos son verbos, no etiquetas técnicas: quien sube la
 *  matriz no tiene por qué saber qué es un «alta». */
const GRUPOS: { clase: ClaseCambio; titulo: string; explica: string }[] = [
  {
    clase: 'retiros',
    titulo: 'Salen del Plan',
    explica: 'Dejan de aparecer en la matriz. No se borran: quedan marcados como '
      + 'inactivos y se pueden seguir consultando, junto con la carga que los retiró.',
  },
  {
    clase: 'altas',
    titulo: 'Entran al Plan',
    explica: 'Aparecen por primera vez en la matriz y se crean en el catálogo.',
  },
  {
    clase: 'cambios',
    titulo: 'Se corrigen',
    explica: 'Ya existen y cambia alguno de sus datos. Se muestra el valor de antes '
      + 'y el de después, campo por campo.',
  },
  {
    clase: 'reactivaciones',
    titulo: 'Vuelven al Plan',
    explica: 'Estaban inactivos —los había retirado una carga anterior— y esta '
      + 'matriz los trae de vuelta.',
  },
];

/** Tipo de aviso → variante de la barra. El TEXTO lo redacta el servidor;
 *  acá solo se decide el color, que nunca va solo (la frase se lee igual en
 *  gris). Un tipo que no conozcamos se pinta como advertencia: los avisos
 *  existen para llamar la atención, y errar hacia «mirá esto» es más barato
 *  que errar hacia «no pasa nada». */
const VARIANTE_AVISO: Record<string, NoticeVariant> = {
  retiro_masivo: 'danger',
  sector_renombre: 'warning',
  programa_cambia_objetivo: 'info',
};

/**
 * Carga de la Matriz PDL — una pantalla, tres momentos.
 *
 *   1. Revisar   → POST .../prevalidar/  lee el archivo y muestra el diff.
 *                  **No persiste nada**, y eso importa acá más que en otros
 *                  cargues: el hash del archivo es UNIQUE y NADA lo libera
 *                  —ni descartar—, así que subir «solo para mirar» quemaría
 *                  el archivo para siempre.
 *   2. Crear el borrador → POST .../  guarda la comparación con su corte.
 *   3. Aplicar / Descartar → el paso que escribe, o el que cierra.
 *
 * Los tres viven en UNA ruta (`/presupuesto/carga-matriz`) y no en tres:
 * navegar entre pasos perdería el diff que la persona acaba de mirar. El
 * borrador igual sobrevive al cierre de la pestaña —el servidor lo devuelve
 * como `borrador_abierto`— y por ahí entra Planeación a aplicarlo.
 *
 * La regla del proyecto se respeta hacia los dos lados: la pantalla LLAMA al
 * servicio (`apps/presupuesto/services/matriz_carga.py`) y no reimplementa su
 * lógica; y lo que se aplica es el diff GUARDADO, así que acá nunca se
 * recalcula ni se reenvía nada del diff — solo el id de la carga.
 *
 * Backend: `apps/presupuesto/api/matriz_carga_views.py`.
 */
@Component({
  standalone: true,
  selector: 'app-carga-matriz',
  imports: [
    CommonModule, FormsModule, RouterLink,
    PageHeaderComponent, StatGridComponent, ActionNoticeComponent,
  ],
  templateUrl: './carga-matriz.component.html',
  styleUrl: './carga-matriz.component.scss',
})
export class CargaMatrizComponent implements OnInit {
  private http = inject(HttpClient);
  private cfg = inject(ConfigService);
  private auth = inject(AuthService);
  private layout = inject(LayoutService);
  private confirm = inject(ConfirmService);
  private toast = inject(ToastService);

  /** Con `cfg.url(...)`, nunca la ruta cruda: en dev `apiBaseUrl` es '' y la
   *  ruta pelada funciona igual, pero en producción es una URL absoluta que
   *  se sustituye al desplegar y la petición saldría al origen equivocado. */
  private readonly base = this.cfg.url('/presupuesto/api/matriz/cargas');

  @ViewChild('inputArchivo') private inputArchivo?: ElementRef<HTMLInputElement>;

  // ── Estado ──────────────────────────────────────────────────────────────
  contexto = signal<Contexto | null>(null);
  /** Señal aparte de «no hay cargas»: un 500 no se puede pintar como vacío.
   *  Ya pasó en el cargue de jóvenes —un fallo del servidor se mostró como
   *  «cree un evento», y el evento existía—. */
  contextoFallo = signal<string | null>(null);

  archivo = signal<File | null>(null);
  corte = '';
  revision = signal<Revision | null>(null);
  carga = signal<Carga | null>(null);
  aplicado = signal<ResultadoAplicar | null>(null);

  cargando = signal(false);
  error = signal<string | null>(null);
  pidiendoNota = signal(false);
  nota = '';

  // ── Permisos ────────────────────────────────────────────────────────────

  /** ¿Se esconde la barra de subida? Lo decide el SERVIDOR.
   *
   *  Antes esto era un espejo en TypeScript de `es_solo_lectura` —«todos sus
   *  grupos son Visor»—, y ese espejo ya quedó viejo: desde que existe el rol
   *  `Planeacion`, quien puede VER no es el mismo que puede APLICAR, y la
   *  pantalla habría seguido ofreciendo un botón que el backend contesta 403.
   *
   *  El payload trae `puede_subir` con su motivo. Mientras no haya llegado
   *  —primer pintado— se asume que NO, que es el lado seguro: es preferible
   *  una barra que aparece un instante después a una que promete algo que el
   *  servidor va a rechazar. */
  soloLectura = computed<boolean>(() => {
    const ctx = this.contexto();
    if (ctx?.puede_subir != null) return !ctx.puede_subir;
    return true;
  });

  /** El módulo se chequea local; si esta carga se puede aplicar lo dice el
   *  SERVIDOR en el payload (`puede_aplicar`), no una segunda máquina de
   *  estados escrita en TypeScript. Mientras venga null/undefined el botón
   *  NO se pinta. */
  puedeAplicar = computed<boolean>(() => {
    const c = this.carga();
    if (!c || c.estado !== 'borrador') return false;
    if (this.estadoRevision() === 'sin_calcular') return false;
    if (!this.auth.hasModule(MODULO)) return false;
    return c.puede_aplicar === true;
  });

  // ── Derivados de la revisión ────────────────────────────────────────────

  hayRevision = computed<boolean>(() => !!this.carga() || !!this.revision());

  /** El borrador manda sobre la revisión suelta: es su diff guardado el que
   *  se va a aplicar. */
  renglones = computed<Renglon[]>(
    () => this.carga()?.cambios ?? this.revision()?.cambios ?? [],
  );

  avisos = computed<Aviso[]>(
    () => this.carga()?.avisos ?? this.revision()?.avisos ?? [],
  );

  estadoRevision = computed<EstadoRevision>(() => {
    const c = this.carga();
    if (c) return c.estado_revision ?? this.deducir(c.cambios);
    const r = this.revision();
    if (r) return r.estado_revision ?? this.deducir(r.cambios);
    return 'sin_calcular';
  });

  /** Los cuatro conteos del resumen. Se cuentan los renglones y NO se usan
   *  `n_altas/n_cambios/n_retiros`: esas columnas suman las reactivaciones
   *  DENTRO de `n_cambios` (así las cuenta el servicio, y para el registro
   *  está bien), y mostrarlas además en su propio tile las contaría dos
   *  veces en la misma fila. */
  resumen = computed<ResumenDiff>(() => {
    const dado = this.carga()?.resumen ?? this.revision()?.resumen;
    if (dado) {
      return {
        altas: dado.altas, cambios: dado.cambios,
        reactivaciones: dado.reactivaciones, retiros: dado.retiros,
      };
    }
    const rs = this.renglones();
    const cuenta = (clase: ClaseCambio) => rs.filter((r) => r.clase === clase).length;
    return {
      altas: cuenta('altas'), cambios: cuenta('cambios'),
      reactivaciones: cuenta('reactivaciones'), retiros: cuenta('retiros'),
    };
  });

  grupos = computed(() => {
    const rs = this.renglones();
    return GRUPOS
      .map((g) => ({
        ...g,
        renglones: rs
          .filter((r) => r.clase === g.clase)
          .map<RenglonPintable>((r) => ({ ...r, campos: r.campos ?? [] })),
      }))
      .filter((g) => g.renglones.length > 0);
  });

  /** ¿Hay sectores entrando Y saliendo sin que el servidor ya lo haya
   *  avisado? La llave del sector es su NOMBRE, así que una tilde corregida
   *  por la ALK se ve como uno que sale y otro que entra. Se comprueba que
   *  el aviso no venga ya del servidor para no decir lo mismo dos veces. */
  avisaRenombreSector = computed<boolean>(() => {
    if (this.avisos().some((a) => a.tipo === 'sector_renombre')) return false;
    const rs = this.renglones();
    return rs.some((r) => r.entidad === 'sector' && r.clase === 'altas')
      && rs.some((r) => r.entidad === 'sector' && r.clase === 'retiros');
  });

  duplicado = computed(() => this.revision()?.duplicado ?? null);

  /** null mientras no se haya aplicado en esta sesión: la plantilla compara
   *  contra `false` para no pintar el aviso cuando simplemente no hay dato. */
  coincide = computed<boolean | null>(() => this.aplicado()?.coincide ?? null);

  textoBotonAplicar = computed<string>(() =>
    this.estadoRevision() === 'sin_cambios'
      ? 'Registrar el corte (no cambia nada)'
      : 'Aplicar la matriz al Plan');

  puedeCrearBorrador = computed<boolean>(() => {
    const r = this.revision();
    return !!this.archivo() && !!this.corte && !!r && r.puede_subir !== false;
  });

  // ── Tiles ───────────────────────────────────────────────────────────────

  statsVigente = computed<StatItem[]>(() => {
    const v = this.contexto()?.vigente;
    if (!v) return [];
    return [
      { value: v.sectores, label: 'Sectores', sublabel: 'activos' },
      { value: v.objetivos, label: 'Objetivos estratégicos', sublabel: 'activos' },
      { value: v.programas, label: 'Programas', sublabel: 'activos' },
    ];
  });

  statsCambios = computed<StatItem[]>(() => {
    const r = this.resumen();
    return [
      { value: r.retiros, label: 'Salen', sublabel: 'retiros', variant: 'warn' },
      { value: r.altas, label: 'Entran', sublabel: 'altas', variant: 'ok' },
      { value: r.cambios, label: 'Se corrigen', sublabel: 'cambios', variant: 'plan' },
      { value: r.reactivaciones, label: 'Vuelven', sublabel: 'reactivaciones' },
    ];
  });

  // ── Ciclo de vida ───────────────────────────────────────────────────────

  ngOnInit(): void {
    this.layout.setBreadcrumb([
      { label: 'Inicio', url: '/' },
      { label: 'Presupuesto', url: '/presupuesto' },
      { label: 'Carga de la Matriz PDL' },
    ]);
    this.cargarContexto();
  }

  // ── Llamadas ────────────────────────────────────────────────────────────

  /** Una sola petición pinta la línea base, el historial y el borrador
   *  abierto: son lo mismo desde el punto de vista de la pantalla. */
  cargarContexto(): void {
    this.contextoFallo.set(null);
    this.http.get<Contexto>(`${this.base}/`).subscribe({
      next: (r) => this.contexto.set(r),
      error: (e) => {
        this.contexto.set(null);
        this.contextoFallo.set(this.mensajeError(
          e, 'No se pudo consultar el estado del Plan ni las cargas anteriores.'));
      },
    });
  }

  onArchivo(ev: Event): void {
    const input = ev.target as HTMLInputElement;
    this.archivo.set(input.files?.[0] ?? null);
    // Cambiar de archivo invalida todo lo que se veía: el diff, el borrador y
    // el resultado apuntaban a OTRO archivo. La fecha de corte se conserva
    // porque suele ser la misma entre dos intentos del mismo envío.
    this.revision.set(null);
    this.carga.set(null);
    this.aplicado.set(null);
    this.pidiendoNota.set(false);
    this.nota = '';
    this.error.set(null);
  }

  /** Momento 1. No persiste: es el único modo de mirar un archivo sin
   *  comprometer su hash. */
  revisar(): void {
    const f = this.archivo();
    if (!f) return;
    const body = new FormData();
    // Sin fijar Content-Type a mano: Angular pone el boundary multipart, y
    // ponerlo nosotros rompe el parseo de request.FILES en Django.
    body.append('archivo', f);

    this.cargando.set(true);
    this.error.set(null);
    this.http.post<Revision>(`${this.base}/prevalidar/`, body).subscribe({
      next: (r) => {
        this.revision.set(r);
        this.carga.set(null);
        this.aplicado.set(null);
        this.cargando.set(false);
      },
      error: (e) => {
        this.error.set(this.mensajeError(e, 'No se pudo revisar el archivo.'));
        this.cargando.set(false);
      },
    });
  }

  /** Momento 2. Guarda la comparación con su corte; todavía no escribe en
   *  el Plan. */
  crearBorrador(): void {
    const f = this.archivo();
    if (!f || !this.puedeCrearBorrador()) return;
    const body = new FormData();
    body.append('archivo', f);
    body.append('corte_oficial', this.corte);

    this.cargando.set(true);
    this.error.set(null);
    this.http.post<Carga>(`${this.base}/`, body).subscribe({
      next: (c) => {
        this.carga.set(c);
        this.cargando.set(false);
        this.cargarContexto();
      },
      error: (e) => {
        this.error.set(this.mensajeError(e, 'No se pudo crear el borrador.'));
        this.cargando.set(false);
        // Un 409 suele ser «ya hay un borrador abierto»: recargar el contexto
        // hace aparecer el aviso con el botón que lleva a ese borrador, en
        // vez de dejar a la persona con una prohibición y ninguna salida.
        if (e?.status === 409) this.cargarContexto();
      },
    });
  }

  /** Abre una carga existente (el borrador que quedó vivo, o una del
   *  historial). Es lo que reemplaza a una ruta con id. */
  abrirCarga(id: number): void {
    this.cargando.set(true);
    this.error.set(null);
    this.http.get<Carga>(`${this.base}/${id}/`).subscribe({
      next: (c) => {
        this.carga.set(c);
        this.revision.set(null);
        this.aplicado.set(null);
        this.pidiendoNota.set(false);
        this.nota = '';
        this.cargando.set(false);
      },
      error: (e) => {
        this.error.set(this.mensajeError(e, 'No se pudo abrir la carga.'));
        this.cargando.set(false);
      },
    });
  }

  /** Momento 3. El único dato que viaja es el id: reenviar el diff desde el
   *  navegador sería dejar que el cliente decida qué se escribe en el Plan. */
  async aplicar(): Promise<void> {
    const c = this.carga();
    if (!c || !this.puedeAplicar()) return;

    const r = this.resumen();
    const cifras = this.estadoRevision() === 'sin_cambios'
      ? 'No hay nada que escribir en el catálogo: solo queda registrado que este '
        + 'corte se revisó.'
      : `Van a entrar ${r.altas}, corregirse ${r.cambios}, volver `
        + `${r.reactivaciones} y salir ${r.retiros} entradas del catálogo del Plan. `
        + 'Lo que sale se marca inactivo, no se borra.';

    // Sin `danger: true` a propósito: aplicar no destruye nada —todo queda
    // registrado y lo retirado sigue consultable—. El rojo se reserva para
    // descartar, que es lo único irreversible de esta pantalla.
    const ok = await this.confirm.ask({
      title: 'Aplicar la matriz al Plan',
      message: `${cifras} Corte: ${c.corte_oficial}.`,
      confirmText: 'Aplicar',
      cancelText: 'Cancelar',
    });
    if (!ok) return;

    this.cargando.set(true);
    this.error.set(null);
    this.http.post<ResultadoAplicar>(`${this.base}/${c.id}/aplicar/`, {}).subscribe({
      next: (res) => {
        this.aplicado.set(res);
        this.carga.set(res.carga);
        this.cargando.set(false);
        this.toast.success(res.resultado_texto || 'La matriz se aplicó al Plan.');
        this.cargarContexto();
      },
      error: (e) => {
        this.error.set(this.mensajeError(e, 'No se pudo aplicar la carga.'));
        this.cargando.set(false);
      },
    });
  }

  abrirDescarte(): void {
    this.nota = this.carga()?.nota ?? '';
    this.pidiendoNota.set(true);
  }

  /** El motivo se pide ANTES de confirmar: es lo único que queda de una carga
   *  que nunca se aplicó, y el confirm puede entonces citarlo. */
  async descartar(): Promise<void> {
    const c = this.carga();
    const nota = this.nota.trim();
    if (!c || nota.length < 5) return;

    const ok = await this.confirm.ask({
      title: 'Descartar la carga',
      message: `Se va a descartar la carga #${c.id} con el motivo «${nota}». `
        + `El archivo «${c.archivo_nombre}» NO se va a poder volver a subir: el `
        + 'sistema lo reconoce por su contenido y lo rechaza como repetido. Si el '
        + 'corte es el mismo, la ALK tiene que mandar un archivo distinto.',
      danger: true,
      confirmText: 'Descartar',
      cancelText: 'Cancelar',
    });
    if (!ok) return;

    this.cargando.set(true);
    this.error.set(null);
    this.http.post<{ carga: Carga }>(`${this.base}/${c.id}/descartar/`, { nota })
      .subscribe({
        next: (res) => {
          this.carga.set(res.carga);
          this.pidiendoNota.set(false);
          this.cargando.set(false);
          this.toast.info(`La carga #${c.id} quedó descartada.`);
          this.cargarContexto();
        },
        error: (e) => {
          this.error.set(this.mensajeError(e, 'No se pudo descartar la carga.'));
          this.cargando.set(false);
        },
      });
  }

  /** Deja la pantalla como al entrar, sin recargar la ruta. */
  limpiar(): void {
    this.archivo.set(null);
    this.revision.set(null);
    this.carga.set(null);
    this.aplicado.set(null);
    this.pidiendoNota.set(false);
    this.nota = '';
    this.error.set(null);
    if (this.inputArchivo) this.inputArchivo.nativeElement.value = '';
    this.cargarContexto();
  }

  // ── Helpers de presentación ─────────────────────────────────────────────

  /** Cuatro respuestas del servidor NO traen `detail` y hay que redactarlas
   *  acá, o la persona ve el mismo texto de respaldo en casos muy distintos:
   *  el 413 lo corta nginx antes de que Django exista y devuelve su propio
   *  HTML; el 0 es la red; el 504 es el timeout de gunicorn. */
  private mensajeError(e: unknown, respaldo: string): string {
    const err = e as { status?: number; error?: { detail?: string } };
    if (err?.status === 0) {
      return 'No se pudo conectar con el servidor. El archivo no se subió.';
    }
    if (err?.status === 413) {
      return 'El archivo es demasiado grande para enviarlo.';
    }
    if (err?.status === 504) {
      return 'El servidor tardó demasiado leyendo el archivo. No quedó registrado; '
        + 'puede volver a intentarlo.';
    }
    return err?.error?.detail || respaldo;
  }

  /** Respaldo por si el servidor no manda `estado_revision`. No distingue
   *  «no hay cambios» de «no se calculó» —para eso existe el campo—, así que
   *  se queda del lado más informativo y el aviso duro lo da el servidor. */
  private deducir(cambios?: Renglon[]): EstadoRevision {
    return cambios && cambios.length ? 'con_cambios' : 'sin_cambios';
  }

  fecha(iso: string | null | undefined): string {
    if (!iso) return 'sin fecha';
    const d = new Date(iso);
    if (Number.isNaN(d.getTime())) return String(iso);
    return d.toLocaleDateString('es-CO', { day: '2-digit', month: 'short', year: 'numeric' });
  }

  peso(f: File): string {
    const kb = f.size / 1024;
    return kb < 1024 ? `${Math.round(kb)} KB` : `${(kb / 1024).toFixed(1)} MB`;
  }

  valor(v: string | number | null | undefined): string {
    return v === null || v === undefined || v === '' ? '—' : String(v);
  }

  etiquetaEstado(e: EstadoCarga): string {
    if (e === 'borrador') return 'Sin aplicar';
    if (e === 'aplicada') return 'Aplicada';
    return 'Descartada';
  }

  badgeEstado(e: EstadoCarga): string {
    if (e === 'borrador') return 'ui-badge--warning';
    if (e === 'aplicada') return 'ui-badge--success';
    return 'ui-badge--muted';
  }

  varianteAviso(tipo: string): NoticeVariant {
    return VARIANTE_AVISO[tipo] ?? 'warning';
  }

  /** Lo que se pinta es `hecho` —lo que de verdad se escribió—, no los
   *  contadores del borrador. Divergen justo cuando importa: si la base
   *  cambió entre revisar y aplicar, los UPDATE devuelven 0 y `hecho` sale
   *  menor. Si no hay `hecho` (se abrió una carga ya aplicada), se dice
   *  quién y cuándo, que es lo único que se sabe. */
  textoAplicada(c: Carga): string {
    const h = this.aplicado()?.hecho;
    if (!h) {
      const quien = c.aplicado_por ? ` por ${c.aplicado_por}` : '';
      return `Esta carga ya se aplicó el ${this.fecha(c.aplicado_at)}${quien}.`;
    }
    const texto = this.aplicado()?.resultado_texto;
    if (texto) return texto;
    return `Se aplicaron ${h.altas} altas, ${h.cambios} cambios, `
      + `${h.reactivaciones} reactivaciones y ${h.retiros} retiros.`;
  }

  borradorPendiente = computed(() => {
    const b = this.contexto()?.borrador_abierto;
    if (!b) return null;
    // Si ya está abierto en pantalla, el aviso sobra.
    return this.carga()?.id === b.id ? null : b;
  });
}
