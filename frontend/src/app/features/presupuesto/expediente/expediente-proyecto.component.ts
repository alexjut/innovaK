import { CommonModule } from '@angular/common';
import { HttpClient } from '@angular/common/http';
import {
  ChangeDetectionStrategy, Component, Input, computed, inject, signal,
} from '@angular/core';
import { ConfigService } from '../../../core/config/config.service';
import { formatFecha, formatMoneda, formatNumero } from '../../../shared/format/format.util';
import {
  ClaveEtapa, ContratoExpediente, EstadoSemaforo, ExpedienteProyecto,
  IndicadorExpediente, MetaExpediente,
} from './expediente-proyecto.types';

/**
 * Las 4 etapas del expediente contractual, en orden y con su color.
 * Ninguna usa el rojo institucional ($color-primary): si «sancionatorio»
 * llevara el rojo de la marca, la franja se leería «alcaldía» y no «alerta».
 */
export const ETAPAS: Array<{ clave: ClaveEtapa; etiqueta: string }> = [
  { clave: 'formulacion',   etiqueta: 'Formulación' },
  { clave: 'ejecucion',     etiqueta: 'Ejecución' },
  { clave: 'liquidacion',   etiqueta: 'Liquidación' },
  { clave: 'sancionatorio', etiqueta: 'Sancionatorio' },
];

const SEMAFORO_TEXTO: Record<EstadoSemaforo, string> = {
  al_dia: 'Al día',
  atrasado: 'Atrasado',
  critico: 'Crítico',
  incompleto: 'Sin datos para calificar',
};

/** Radio y circunferencia del donut (SVG de 100×100, trazo de 10). */
const DONUT_R = 42;
const DONUT_C = 2 * Math.PI * DONUT_R;

/**
 * EXPEDIENTE DEL PROYECTO — panel derecho del explorador maestro/detalle.
 *
 * Recibe el id por `@Input()` y él mismo carga
 * `GET /presupuesto/api/proyectos/<id>/expediente/`. El contenedor no le pasa
 * datos: así el panel izquierdo (lista de proyectos) no tiene que saber nada
 * del expediente y cambiar de proyecto es cambiar un número.
 *
 * Reglas de pintura que este componente NO negocia:
 *
 *  - `avance_pct === null` → donut APAGADO con la palabra «sin dato». Nunca 0 %.
 *  - Las 4 etapas se pintan siempre APAGADAS mientras `etapa` sea null: la
 *    tabla `contrato` no tiene columna de etapa (18 columnas, ninguna es esa).
 *    No se deduce del estado de SECOP ni de las fechas.
 *  - El plan de pago sale con su encabezado y el motivo del vacío. Cero
 *    trimestres inventados: `crp` y `forma_pago` tienen 0 filas.
 *  - El KPI ejecutado sale de los avances reportados. Sin avances va un guion
 *    y la nota; no un 0 que se leería como «entregó nada».
 *  - El gris de «sin dato» SIEMPRE lleva la palabra escrita al lado: el color
 *    nunca es el único portador del significado (WCAG 1.4.1).
 */
@Component({
  standalone: true,
  selector: 'app-expediente-proyecto',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [CommonModule],
  templateUrl: './expediente-proyecto.component.html',
  styleUrl: './expediente-proyecto.component.scss',
})
export class ExpedienteProyectoComponent {
  private http = inject(HttpClient);
  private cfg = inject(ConfigService);

  /** Id del proyecto a expedientar. `null` = todavía no eligieron ninguno. */
  @Input() set proyectoId(v: number | null | undefined) {
    const id = v == null ? null : Number(v);
    if (id === this._id()) return;          // el mismo id no se recarga
    this._id.set(id);
    this.abiertas.set(new Set<number>());
    this.contratoAbierto.set(null);
    if (id == null) { this.datos.set(null); this.error.set(null); return; }
    this.cargar(id);
  }

  private _id = signal<number | null>(null);

  datos = signal<ExpedienteProyecto | null>(null);
  cargando = signal(false);
  error = signal<string | null>(null);

  /** Metas desplegadas (por `meta_proyecto_id`) y contrato desplegado. */
  abiertas = signal<Set<number>>(new Set<number>());
  contratoAbierto = signal<number | null>(null);

  formatNumero = formatNumero;
  formatMoneda = formatMoneda;
  formatFecha = formatFecha;
  ETAPAS = ETAPAS;
  DONUT_C = DONUT_C;
  DONUT_R = DONUT_R;

  hayProyecto = computed(() => this._id() !== null);

  // ── Carga ───────────────────────────────────────────────────────────────
  private cargar(id: number): void {
    this.cargando.set(true);
    this.error.set(null);
    this.http
      .get<ExpedienteProyecto>(this.cfg.url(`/presupuesto/api/proyectos/${id}/expediente/`))
      .subscribe({
        next: (d) => {
          // Llegó tarde y ya cambiaron de proyecto: se descarta.
          if (this._id() !== id) return;
          this.datos.set(d);
          this.cargando.set(false);
        },
        error: (e) => {
          if (this._id() !== id) return;
          this.datos.set(null);
          this.error.set(this.mensajeError(e, id));
          this.cargando.set(false);
        },
      });
  }

  /**
   * Un mensaje por causa, no uno solo para todo.
   *
   * El anterior decía «el proyecto no existe o no está publicado» ante
   * cualquier fallo, y era demasiado concluyente: la misma frase salía cuando
   * el identificador iba mal, cuando el servicio no respondía y cuando el
   * proyecto simplemente no tenía expediente. Confundir esos casos manda a
   * buscar el problema donde no está.
   *
   * Nota sobre el 404: el identificador canónico del proyecto es `id`, NO
   * `codigo`, y no coinciden — el proyecto de código 2784 tiene id 2802. Lo
   * traicionero es que en el 2788 ambos números SON iguales, así que un bug de
   * identificador se ve intermitente. Por eso el 404 lo menciona.
   */
  private mensajeError(e: any, id: number): string {
    const s = e?.status;
    if (s === 0 || s === undefined) {
      return 'No se pudo contactar el servicio. Revise la conexión y reintente.';
    }
    if (s === 401) return 'La sesión expiró. Vuelva a entrar para ver el expediente.';
    if (s === 403) return 'No tiene permiso para ver el expediente de presupuesto.';
    if (s === 404) {
      return `No hay expediente para el proyecto ${id}. Puede que el proyecto no exista `
           + 'o que se haya pedido con el código en vez del identificador.';
    }
    if (s >= 500) {
      return 'El servidor falló al armar el expediente. Es un error del sistema, '
           + 'no un dato faltante: reintente y avise si persiste.';
    }
    return `No se pudo cargar el expediente (error ${s}).`;
  }

  recargar(): void {
    const id = this._id();
    if (id != null) this.cargar(id);
  }

  // ── Acordeones ──────────────────────────────────────────────────────────
  abierta(m: MetaExpediente): boolean { return this.abiertas().has(m.meta_proyecto_id); }

  alternarMeta(m: MetaExpediente): void {
    const s = new Set(this.abiertas());
    if (s.has(m.meta_proyecto_id)) s.delete(m.meta_proyecto_id);
    else s.add(m.meta_proyecto_id);
    this.abiertas.set(s);
  }

  alternarContrato(c: ContratoExpediente): void {
    this.contratoAbierto.set(this.contratoAbierto() === c.id ? null : c.id);
  }

  // ── Cabecera ────────────────────────────────────────────────────────────
  /** «2780 · Cultura · 4 metas · 15 contratos», sin partes vacías. */
  lineaIdentidad = computed<string>(() => {
    const d = this.datos();
    if (!d) return '';
    const partes: string[] = [];
    if (d.codigo) partes.push(String(d.codigo));
    partes.push(d.area || d.subgrupo?.nombre || 'sin área asignada');
    partes.push(`${d.n_metas} ${d.n_metas === 1 ? 'meta' : 'metas'}`);
    partes.push(`${d.n_contratos} ${d.n_contratos === 1 ? 'contrato' : 'contratos'}`);
    return partes.join('  ·  ');
  });

  semaforoTexto(s: EstadoSemaforo | null): string {
    return s ? SEMAFORO_TEXTO[s] : 'Sin calificar';
  }

  // ── Donut de avance ─────────────────────────────────────────────────────
  /**
   * Trazo del arco. `pct` null nunca llega aquí: el template pinta el donut
   * apagado antes de llamar. Se recorta a 100 para que un sobrecumplimiento
   * no dé la vuelta al círculo y se lea como un avance pequeño.
   */
  arco(pct: number): string {
    const p = Math.max(0, Math.min(pct, 100));
    return `${(DONUT_C * p) / 100} ${DONUT_C}`;
  }

  /** Semáforo de color del avance. Los mismos cortes que usa la página. */
  claseAvance(pct: number | null): string {
    if (pct == null) return 'sin-dato';
    if (pct >= 80) return 'ok';
    if (pct >= 50) return 'medio';
    return 'bajo';
  }

  // ── Metas y KPI ─────────────────────────────────────────────────────────
  /**
   * ¿El KPI tiene avance REPORTADO? `n_aportes` es la respuesta buena; si el
   * backend no lo manda se cae al ejecutado, que solo confunde el caso —raro—
   * de aportes que suman exactamente cero.
   */
  hayEjecutado(k: IndicadorExpediente): boolean {
    if (k.n_aportes != null) return k.n_aportes > 0;
    return k.ejecutado != null && k.ejecutado !== 0;
  }

  /** «3 eventos» — la unidad NO se inventa cuando el indicador no la trae. */
  magnitud(valor: number | null, unidad: string | null): string {
    if (valor == null) return '—';
    return unidad ? `${formatNumero(valor)} ${unidad}` : formatNumero(valor);
  }

  contratosDeMeta(m: MetaExpediente): ContratoExpediente[] {
    const idx = this.indiceContratos();
    return (m.contratos_ids ?? [])
      .map((id) => idx.get(id))
      .filter((c): c is ContratoExpediente => !!c);
  }

  private indiceContratos = computed<Map<number, ContratoExpediente>>(() => {
    const m = new Map<number, ContratoExpediente>();
    for (const c of this.datos()?.contratos ?? []) m.set(c.id, c);
    return m;
  });

  // ── Contratos sin meta ──────────────────────────────────────────────────
  /** El backend puede mandar lista de ids u objeto anotado: se normaliza. */
  private sinMeta = computed<{ ids: number[]; motivo: string | null }>(() => {
    const v = this.datos()?.contratos_sin_meta;
    if (!v) return { ids: [], motivo: null };
    if (Array.isArray(v)) return { ids: v, motivo: null };
    return { ids: v.ids ?? [], motivo: v.motivo ?? null };
  });

  contratosSinMeta = computed<ContratoExpediente[]>(() => {
    const idx = this.indiceContratos();
    return this.sinMeta().ids
      .map((id) => idx.get(id))
      .filter((c): c is ContratoExpediente => !!c);
  });

  motivoSinMeta = computed<string>(() =>
    this.sinMeta().motivo
    ?? this.datos()?.contratos_sin_meta_motivo
    ?? 'Llegan al proyecto por `contrato_proyecto`, que no pasa por ninguna meta.');

  /**
   * Por qué NUNCA llega el contratista. Medido hoy contra la BD: la tabla
   * `proveedor` tiene 0 filas y los 25 contratos tienen `proveedor_id` NULL.
   * El nombre existe en el espejo de SECOP, que todavía no se cruza para esto.
   */
  motivoContratista(c: ContratoExpediente): string {
    return c.contratista_motivo
      ?? 'la tabla proveedor está vacía y ningún contrato tiene proveedor_id; '
       + 'el nombre está en el espejo de SECOP, sin enganchar todavía';
  }

  /**
   * El backend nombra las etapas con otro vocabulario del que pide el encargo
   * (manda `planeacion`/`contratacion`; acá se pintan Formulación, Ejecución,
   * Liquidación y Sancionatorio). `planeacion` y `formulacion` son la misma
   * etapa con dos nombres, así que se alinean. `contratacion` NO se dobla
   * dentro de ninguna de las cuatro: doblarla sería decidir por el área.
   *
   * Hoy da igual —los 25 contratos tienen `etapa: null`— pero el día que entre
   * el DDL esto evita que el stepper se quede mudo sin que nadie se entere.
   */
  private static readonly SINONIMOS: Record<string, ClaveEtapa> = {
    planeacion: 'formulacion',
    formulacion: 'formulacion',
    ejecucion: 'ejecucion',
    liquidacion: 'liquidacion',
    sancionatorio: 'sancionatorio',
  };

  /** ¿Este paso es el vigente del contrato? */
  esPasoActivo(c: ContratoExpediente, clave: ClaveEtapa): boolean {
    if (!c.etapa) return false;
    return ExpedienteProyectoComponent.SINONIMOS[String(c.etapa).toLowerCase()] === clave;
  }

  /** El contrato trae etapa, pero con un nombre que este panel no sabe pintar. */
  etapaDesconocida(c: ContratoExpediente): boolean {
    if (!c.etapa) return false;
    return !(String(c.etapa).toLowerCase() in ExpedienteProyectoComponent.SINONIMOS);
  }

  // ── Dinero del contrato ─────────────────────────────────────────────────
  /**
   * Saldo por girar del contrato. Se calcula SOLO si hay valor y hay girado
   * creíble: sin conciliar con SECOP el girado no se conoce, y restar cero
   * daría un saldo igual al valor del contrato — plausible y falso.
   */
  saldoContrato(c: ContratoExpediente): number | null {
    if (c.saldo != null) return c.saldo;
    if (c.valor == null) return null;
    if (!c.conciliado_secop || c.girado == null) return null;
    return c.valor - c.girado;
  }

  motivoSaldo(c: ContratoExpediente): string {
    if (c.valor == null) return 'el contrato no tiene valor cargado';
    if (!c.conciliado_secop) return 'el contrato no cruza con el espejo de SECOP';
    return 'no hay girado registrado';
  }

  /** Gauge financiero: girado sobre valor. Null cuando no hay de dónde. */
  pctFinanciero(c: ContratoExpediente): number | null {
    if (!c.conciliado_secop || c.girado == null || c.valor == null || c.valor <= 0) return null;
    return Math.round((c.girado / c.valor) * 1000) / 10;
  }

  /** Gauge técnico: `contrato.ejecucion`. Medido: 4 no nulos de 25 → 21 grises. */
  pctTecnico(c: ContratoExpediente): number | null {
    return c.ejecucion == null ? null : Number(c.ejecucion);
  }

  estadoContrato(c: ContratoExpediente): string {
    if (c.estado_secop) return c.estado_secop;
    return c.conciliado_secop ? 'Conciliado con SECOP' : 'Sin conciliar';
  }

  viaTexto(v: string | null | undefined): string {
    return ({
      contrato_proyecto: 'vinculado al proyecto',
      contrato_actividad_plan: 'vinculado por actividad del plan',
    } as Record<string, string>)[v ?? ''] ?? 'vía de atribución no declarada';
  }
}
