import { CommonModule } from '@angular/common';
import { HttpClient } from '@angular/common/http';
import {
  ChangeDetectionStrategy, Component, Input, computed, inject, signal,
} from '@angular/core';
import { AuthService } from '../../../core/auth/auth.service';
import { ConfigService } from '../../../core/config/config.service';
import { formatFecha, formatMoneda, formatNumero } from '../../../shared/format/format.util';
import {
  ContratoExpediente, EjecucionPresupuestalContrato, EstadoEtapaContrato,
  EstadoSemaforo, EtapaCatalogo, ExpedienteProyecto, FilaPlanPago,
  IndicadorExpediente, MetaExpediente,
} from './expediente-proyecto.types';

/** Módulo que gobierna presupuesto. El PATCH de etapa exige este mismo. */
const MODULO_PRESUPUESTO = 'presupuesto_proyectos';

const SEMAFORO_TEXTO: Record<EstadoSemaforo, string> = {
  al_dia: 'Al día',
  atrasado: 'Atrasado',
  critico: 'Crítico',
  incompleto: 'Sin datos para calificar',
};

/** Radio y circunferencia del donut (SVG de 100×100, trazo de 10). */
const DONUT_R = 42;
const DONUT_C = 2 * Math.PI * DONUT_R;

/** Un nodo del stepper, ya resuelto: el template no calcula nada. */
export interface PasoEtapa {
  codigo: number;
  etiqueta: string;
  descripcion: string | null;
  /** `completada` · `actual` · `futura` · `neutra` (sin etapa registrada). */
  estado: 'completada' | 'actual' | 'futura' | 'neutra';
  /** ¿El tramo que LLEGA a este nodo está recorrido? Decide si se anima. */
  tramoRecorrido: boolean;
  /** Retardo de la animación del tramo, en ms. Solo en tramos recorridos. */
  retardoMs: number;
  ultimo: boolean;
}

/** Una celda del módulo financiero del contrato. */
export interface CeldaPlata {
  rotulo: string;
  valor: number | null;
  /** Fuente en letra pequeña bajo la cifra (de dónde salió). */
  fuente: string | null;
  /** Por qué está vacía. Solo cuando `valor` es null. */
  motivo: string | null;
  /** El saldo lleva realce cuando hay algo que destacar. */
  destacada: boolean;
}

/** Una fila del plan de pago ya preparada para pintar. */
export interface FilaPago extends FilaPlanPago {
  /** Etiqueta del periodo, solo en la primera fila de cada grupo. */
  rotuloPeriodo: string | null;
  /** Primera fila de su periodo: lleva la separación gruesa. */
  abrePeriodo: boolean;
}

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
 *  - **$0 y «sin dato» se ven distinto.** Un cero es un hecho («no se giró»);
 *    un null es una ignorancia («no sabemos si se giró»). Confundirlos es el
 *    error que Alex marcó como el más grave del tablero.
 *  - El stepper de etapa nace NEUTRO y quieto mientras `etapa` sea null:
 *    medido hoy, los 25 contratos están así porque nadie la ha registrado.
 *    NO se deduce del estado de SECOP («Modificado» en 20 de 25 significa que
 *    hubo otrosí, no que el contrato esté en tal etapa).
 *  - Solo se anima el tramo YA RECORRIDO, una vez y al abrir. Un tramo futuro
 *    animado prometería un avance que no ocurrió.
 *  - El plan de pago pinta los periodos que TRAE el dato. Cero trimestres
 *    inventados.
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
  private auth = inject(AuthService);

  /** Id del proyecto a expedientar. `null` = todavía no eligieron ninguno. */
  @Input() set proyectoId(v: number | null | undefined) {
    const id = v == null ? null : Number(v);
    if (id === this._id()) return;          // el mismo id no se recarga
    this._id.set(id);
    this.abiertas.set(new Set<number>());
    this.contratoAbierto.set(null);
    this.cerrarRegistroEtapa();
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

  /**
   * Catálogo de etapas, SIEMPRE el del servidor.
   *
   * Antes había una copia a mano acá (`CATALOGO_RESPALDO`) con las cuatro
   * filas de `etapa_contrato` transcritas. Estaba borrada de nacimiento: una
   * copia que nadie sincroniza es una mentira esperando a que alguien
   * renombre una etapa en la tabla. Se borró.
   *
   * El detalle del expediente no trae el catálogo —medido: las claves que
   * devuelve `expediente_proyecto()` no incluyen `etapas_catalogo`; ese viaja
   * en la CABECERA de la vista de lista, que este componente no pide—, así
   * que se pide una sola vez a `GET /presupuesto/api/contratos/<id>/etapa/`,
   * que lo publica entero junto con el estado del contrato.
   *
   * Arranca vacío: mientras no llegue no se dibuja el stepper. Unos pasos
   * inventados que resulten no ser los de la base son peor que ninguno. Y son
   * cinco desde el 2026-08-26 —entró «En elaboración»—, prueba de que el
   * número no se puede escribir en ninguna parte del código.
   */
  catalogoEtapas = signal<EtapaCatalogo[]>([]);
  private catalogoPedido = false;

  /** Contrato cuyo selector de etapa está abierto. */
  registrando = signal<number | null>(null);
  guardandoEtapa = signal(false);
  errorEtapa = signal<string | null>(null);

  formatNumero = formatNumero;
  formatMoneda = formatMoneda;
  formatFecha = formatFecha;
  DONUT_C = DONUT_C;
  DONUT_R = DONUT_R;

  hayProyecto = computed(() => this._id() !== null);

  /**
   * ¿Puede el usuario registrar la etapa? El backend pone DOS candados —el
   * módulo y el scope por subgrupo (`ContratoEtapaView._puede_tocar`)— y el
   * segundo NO se puede evaluar acá.
   *
   * Medido el 2026-08-23, buscando justamente ese permiso en el payload:
   *
   *   · `expediente_proyecto(pk)` devuelve 36 claves y ninguna es de permiso
   *     (tampoco trae `cabecera`: eso viaja sólo en la vista de lista).
   *   · cada contrato del expediente trae 24 claves —`etapa`, `etapa_motivo`,
   *     `via_atribucion`, `plan_pago`…— y ninguna dice si se puede tocar.
   *   · `GET /presupuesto/api/contratos/<id>/etapa/` devuelve 8 claves y
   *     tampoco.
   *
   * Así que el botón sigue mostrándose con el módulo solamente, y un usuario
   * de otra área se come un 403 al pulsarlo. Se deja así A PROPÓSITO: la regla
   * de scope vive en el backend, y reimplementarla acá —«los subgrupos del
   * usuario contra los subgrupos del contrato»— crearía una segunda fuente de
   * verdad que se desincroniza en cuanto cambie una de las dos vías de
   * atribución. Lo que falta es que el backend publique el permiso por
   * contrato; el día que lo mande, esto pasa a leerlo y nada más.
   *
   * Mientras tanto el 403 no deja al usuario a ciegas: su mensaje del servidor
   * («Este contrato pertenece a otra área.») se muestra tal cual bajo el
   * stepper.
   */
  /** Lo que el backend responde en `puede_registrar_etapa`. `null` = sin pedir. */
  permisoEtapa = signal<boolean | null>(null);
  permisoEtapaMotivo = signal<string | null>(null);

  /**
   * ¿Se pinta el botón de registrar etapa?
   *
   * Dos candados, el mismo orden que el servidor: primero el módulo (barato,
   * local) y después el **scope por área**, que solo el backend sabe resolver.
   * Mientras su respuesta no llegue, `permisoEtapa` es `null` y el botón NO se
   * muestra: es preferible que aparezca un instante después a ofrecérselo a
   * alguien que se va a comer un 403 al pulsarlo.
   */
  puedeRegistrarEtapa = computed(() =>
    this.auth.hasModule(MODULO_PRESUPUESTO) && this.permisoEtapa() === true);

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
          this.pedirCatalogoEtapas(d);
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
   * Trae el catálogo real usando cualquier contrato del expediente. Es un GET
   * y no escribe nada; si falla, el stepper no se dibuja y el contrato sigue
   * mostrando su etapa —que sale del dato, no del catálogo—, así que no se
   * interrumpe al usuario con un error que no le impide nada.
   */
  private pedirCatalogoEtapas(d: ExpedienteProyecto): void {
    if (this.catalogoPedido) return;
    const primero = d.contratos?.[0]?.id;
    if (primero == null) return;
    this.catalogoPedido = true;
    this.http
      .get<EstadoEtapaContrato>(this.cfg.url(`/presupuesto/api/contratos/${primero}/etapa/`))
      .subscribe({
        next: (r) => {
          if (r?.etapas_catalogo?.length) this.catalogoEtapas.set(r.etapas_catalogo);
          // El permiso lo decide el BACKEND y viaja en el payload. No se
          // reimplementa acá: la atribución contrato→área usa dos vías, y una
          // copia en TypeScript se desincronizaría sin que nadie se entere.
          if (r?.puede_registrar_etapa !== undefined) {
            this.permisoEtapa.set(!!r.puede_registrar_etapa);
            this.permisoEtapaMotivo.set(r.puede_registrar_etapa_motivo ?? null);
          }
        },
        error: () => { /* el respaldo ya está pintado */ },
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
    const abierto = this.contratoAbierto() === c.id;
    this.contratoAbierto.set(abierto ? null : c.id);
    this.cerrarRegistroEtapa();
  }

  // ── Cabecera ────────────────────────────────────────────────────────────
  /**
   * «Cultura · 4 metas · 15 contratos», sin partes vacías. El CÓDIGO no va
   * aquí: la cabecera lo pinta como chip aparte y repetirlo lo diluiría.
   */
  lineaIdentidad = computed<string>(() => {
    const d = this.datos();
    if (!d) return '';
    const partes: string[] = [];
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

  /** Ancho de barra, recortado a 100 por la misma razón que el arco. */
  ancho(pct: number | null): number {
    if (pct == null) return 0;
    return Math.max(0, Math.min(pct, 100));
  }

  /**
   * Saldo por girar de la Matriz PDL, SOLO cuando no hay contrato en
   * innovaK (`saldo_por_girar` ya cubre ese caso con datos propios). Resta
   * comprometido_oficial − girado_oficial: es válida porque las dos vienen
   * de la MISMA fuente y las mismas filas — no es la resta entre universos
   * que el ledger del cockpit evita a propósito (programado vs. comprometido).
   */
  saldoOficial(d: ExpedienteProyecto): number | null {
    if (d.saldo_por_girar != null) return null;
    if (d.comprometido_oficial == null || d.girado_oficial == null) return null;
    return d.comprometido_oficial - d.girado_oficial;
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

  /**
   * «5 de 1.000 personas» — el avance del KPI en una sola frase. Es la lectura
   * que pidió Alex (N de M) y sale de los dos números que ya vienen; si falta
   * cualquiera de los dos, no se compone una frase a medias.
   */
  avanceNdeM(k: IndicadorExpediente): string | null {
    if (k.programado == null) return null;
    if (!this.hayEjecutado(k)) return null;
    const n = formatNumero(k.ejecutado);
    const m = formatNumero(k.programado);
    return k.unidad ? `${n} de ${m} ${k.unidad}` : `${n} de ${m}`;
  }

  /**
   * Cadena real del KPI: actividades → eventos → beneficiarios.
   *
   * Se pinta SOLO lo que el backend manda. Medido contra la base el
   * 2026-08-23: la cadena existe hasta el evento —`actividad_indicador` cubre
   * 20 de los 23 indicadores y `evento.actividad_plan_id` engancha 23
   * eventos— pero se corta ahí: esos 23 eventos tienen CERO filas en
   * `participante_evento` (los 2.545 participantes cuelgan de los otros 32
   * eventos, ninguno atado a una actividad del plan). Por eso el renglón de
   * beneficiarios no se dibuja aunque el de eventos sí: la diferencia es real
   * y no se maquilla.
   */
  hayCadena(k: IndicadorExpediente): boolean {
    return !!(k.actividades?.length || k.eventos?.length
              || (k.beneficiarios != null && k.beneficiarios > 0));
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
    ?? 'Estos contratos llegan al proyecto sin pasar por ninguna meta.');

  /**
   * Por qué no llega el contratista, cuando no llega.
   *
   * Ya no es lo normal: la precarga desde SECOP lo puso en 23 de 25. Los dos
   * que faltan tienen motivo propio —uno es anterior a la ventana que publica
   * SECOP y el otro tiene un empate dudoso— y el backend lo explica en
   * `contratista_motivo`. El respaldo de acá es sólo por si el payload es
   * viejo.
   */
  motivoContratista(c: ContratoExpediente): string {
    return c.contratista_motivo
      ?? 'no hay contratista registrado en el contrato';
  }

  // ─────────────────────────────────────────────────────────────────────────
  // 1. ETAPA DEL CONTRATO
  // ─────────────────────────────────────────────────────────────────────────

  /**
   * Los nodos del stepper —tantos como etapas haya— con su estado ya resuelto.
   *
   * Sin etapa registrada, TODOS salen `neutra`: ni uno completado, ni uno
   * actual. Es la diferencia entre «no ha empezado» y «no sabemos» y es la
   * única lectura honesta hoy.
   */
  pasos(c: ContratoExpediente): PasoEtapa[] {
    const cat = [...this.catalogoEtapas()].sort((a, b) => a.orden - b.orden);
    const actual = c.etapa?.orden ?? null;
    return cat.map((e, i) => {
      const estado: PasoEtapa['estado'] =
        actual == null ? 'neutra'
        : e.orden < actual ? 'completada'
        : e.orden === actual ? 'actual'
        : 'futura';
      // El tramo se dibuja a la DERECHA del nodo, así que el que llega al
      // nodo `actual` es el del nodo anterior. Un tramo solo se considera
      // recorrido si su nodo de destino ya se alcanzó.
      const recorrido = actual != null && e.orden < actual;
      return {
        codigo: e.codigo,
        etiqueta: e.nombre,
        descripcion: e.descripcion ?? null,
        estado,
        tramoRecorrido: recorrido,
        // Escalonado corto: los tramos se encadenan en vez de dispararse a la
        // vez, que es lo que hace que se lea como un recorrido y no como un
        // parpadeo. Total ≤ 1.000 ms aunque estén los tres tramos recorridos.
        retardoMs: recorrido ? i * 160 : 0,
        ultimo: i === cat.length - 1,
      };
    });
  }

  /** Texto de la etapa registrada, con quién y cuándo si el dato existe. */
  etapaPie(c: ContratoExpediente): string | null {
    if (!c.etapa) return null;
    const partes: string[] = [];
    if (c.etapa_fecha) partes.push(`registrada el ${formatFecha(c.etapa_fecha)}`);
    if (c.etapa_registrada_por?.nombre) partes.push(`por ${c.etapa_registrada_por.nombre}`);
    return partes.length ? partes.join(' ') : null;
  }

  // ── Registro de etapa (el único punto de escritura del expediente) ──────
  abrirRegistroEtapa(c: ContratoExpediente): void {
    this.errorEtapa.set(null);
    this.registrando.set(this.registrando() === c.id ? null : c.id);
  }

  cerrarRegistroEtapa(): void {
    this.registrando.set(null);
    this.errorEtapa.set(null);
    this.guardandoEtapa.set(false);
  }

  /** ¿Es esta la etapa que ya tiene el contrato? Se marca, no se repite. */
  etapaElegida(c: ContratoExpediente, codigo: number): boolean {
    return c.etapa?.codigo === codigo;
  }

  /**
   * PATCH de la etapa. `codigo === null` la borra (corregir un registro
   * equivocado es tan necesario como ponerlo). La respuesta trae el estado
   * canónico y se copia sobre el contrato en memoria: recargar el expediente
   * entero por un campo cerraría todos los acordeones abiertos.
   */
  guardarEtapa(c: ContratoExpediente, codigo: number | null): void {
    if (!this.puedeRegistrarEtapa()) return;
    this.guardandoEtapa.set(true);
    this.errorEtapa.set(null);
    this.http
      .patch<EstadoEtapaContrato>(
        this.cfg.url(`/presupuesto/api/contratos/${c.id}/etapa/`),
        { etapa_codigo: codigo })
      .subscribe({
        next: (r) => {
          c.etapa = r.etapa;
          c.etapa_fecha = r.etapa_fecha;
          c.etapa_registrada_por = r.etapa_registrada_por;
          c.etapa_motivo = r.etapa_motivo;
          if (r.etapas_catalogo?.length) this.catalogoEtapas.set(r.etapas_catalogo);
          // El dato del contrato cambió pero el objeto es el mismo: se
          // reemplaza la señal para que OnPush vuelva a pintar.
          const d = this.datos();
          if (d) this.datos.set({ ...d });
          this.guardandoEtapa.set(false);
          this.registrando.set(null);
        },
        error: (e) => {
          this.guardandoEtapa.set(false);
          // El backend redacta sus 403 y 400 en castellano de pantalla («Este
          // contrato pertenece a otra área»): se muestran tal cual, que dicen
          // más que cualquier frase genérica que se pudiera poner acá.
          this.errorEtapa.set(
            e?.error?.detail
            ?? (e?.status === 401
                  ? 'La sesión expiró. Vuelva a entrar para registrar la etapa.'
                  : 'No se pudo guardar la etapa. Reintente.'));
        },
      });
  }

  // ─────────────────────────────────────────────────────────────────────────
  // 2. EJECUCIÓN PRESUPUESTAL DEL CONTRATO
  // ─────────────────────────────────────────────────────────────────────────

  /**
   * Las cuatro celdas del módulo financiero, en el orden fijo del encargo:
   * PROGRAMADO · COMPROMETIDO · GIRADO/PAGADO · SALDO.
   *
   * Si el backend manda `ejecucion_presupuestal` se usa ESE bloque, que trae
   * cada motivo distinguido en el origen. Si no llega —expedientes servidos
   * por una versión anterior— se recompone con lo que hay en el contrato,
   * pero sin inventar el saldo: restar un comprometido de innovaK menos un
   * girado sin conciliar da una cifra plausible y falsa.
   */
  celdasPlata(c: ContratoExpediente): CeldaPlata[] {
    const e = c.ejecucion_presupuestal ?? this.ejecucionDeRespaldo(c);
    return [
      {
        rotulo: 'Programado (CDP)',
        valor: e.programado,
        fuente: e.programado_origen ?? null,
        motivo: e.programado == null
          ? (e.programado_motivo ?? 'no hay programación registrada para este contrato')
          : null,
        destacada: false,
      },
      {
        rotulo: 'Comprometido',
        valor: e.comprometido,
        fuente: e.comprometido != null ? 'valor del contrato' : null,
        motivo: e.comprometido == null
          ? (e.comprometido_motivo ?? 'el contrato no tiene valor cargado')
          : null,
        destacada: false,
      },
      {
        rotulo: 'Girado / pagado',
        valor: e.girado,
        fuente: e.girado != null ? (e.girado_origen ?? null) : null,
        motivo: e.girado == null
          ? (e.girado_motivo ?? 'el contrato no cruza con el espejo de SECOP')
          : null,
        destacada: false,
      },
      {
        rotulo: 'Saldo',
        valor: e.saldo,
        fuente: e.saldo != null ? 'comprometido menos girado' : null,
        motivo: e.saldo == null ? (e.saldo_motivo ?? this.motivoSaldo(c)) : null,
        // El realce es para el saldo que queda VIVO. Un saldo en cero es una
        // buena noticia y no necesita que se le grite.
        destacada: e.saldo != null && e.saldo > 0,
      },
    ];
  }

  /** Reconstrucción conservadora cuando el backend no manda el bloque. */
  private ejecucionDeRespaldo(c: ContratoExpediente): EjecucionPresupuestalContrato {
    const girado = (c.conciliado_secop && c.girado != null) ? c.girado : null;
    return {
      programado: null,
      programado_motivo: 'este expediente no trae la programación del contrato',
      comprometido: c.valor,
      girado,
      girado_origen: girado != null ? 'SECOP II' : null,
      saldo: (c.valor != null && girado != null) ? c.valor - girado : null,
    };
  }

  motivoSaldo(c: ContratoExpediente): string {
    if (c.valor == null) return 'sin valor del contrato no hay saldo que calcular';
    if (!c.conciliado_secop) return 'el contrato no cruza con el espejo de SECOP';
    return 'no hay girado registrado contra el cual restar';
  }

  /** Saldo del contrato para la fila resumen (la que se ve plegada). */
  saldoContrato(c: ContratoExpediente): number | null {
    const e = c.ejecucion_presupuestal;
    if (e) return e.saldo;
    return this.ejecucionDeRespaldo(c).saldo;
  }

  // ─────────────────────────────────────────────────────────────────────────
  // 3. EJECUCIÓN TÉCNICA Y FINANCIERA
  // ─────────────────────────────────────────────────────────────────────────

  /** Gauge financiero: girado sobre comprometido. Null cuando no hay de dónde. */
  pctFinanciero(c: ContratoExpediente): number | null {
    const e = c.ejecucion_presupuestal;
    if (e?.pct_girado != null) return e.pct_girado;
    if (!c.conciliado_secop || c.girado == null || c.valor == null || c.valor <= 0) return null;
    return Math.round((c.girado / c.valor) * 1000) / 10;
  }

  /** Gauge técnico: `contrato.ejecucion`. Medido: 4 no nulos de 25 → 21 grises. */
  pctTecnico(c: ContratoExpediente): number | null {
    return c.ejecucion == null ? null : Number(c.ejecucion);
  }

  viaTexto(c: ContratoExpediente): string {
    if (c.via_atribucion_texto) return c.via_atribucion_texto;
    return ({
      contrato_proyecto: 'Asociado directamente al proyecto',
      contrato_actividad_plan: 'Asociado a través de una actividad del plan',
    } as Record<string, string>)[c.via_atribucion ?? ''] ?? 'Vía de atribución no declarada';
  }

  /** La cadena por la que llegó a la meta, ya redactada y sin duplicados. */
  viaMetaTexto(c: ContratoExpediente): string | null {
    const v = c.via_meta_texto ?? null;
    if (!v) return null;
    const lista = Array.isArray(v) ? v : [v];
    const limpias = [...new Set(lista.filter(Boolean))];
    return limpias.length ? limpias.join(' · ') : null;
  }

  // ─────────────────────────────────────────────────────────────────────────
  // 4. PLAN DE PAGO
  // ─────────────────────────────────────────────────────────────────────────

  /**
   * Las filas del plan tal como vienen, agrupadas por el periodo QUE TRAE EL
   * DATO. No se completan meses faltantes ni se asumen cuatro trimestres: si
   * SECOP publicó pagos en cinco meses salteados, se ven cinco.
   *
   * El periodo se repite en el dato (un mes puede tener dos pagos), así que
   * la etiqueta se escribe una sola vez por grupo y el resto de filas del
   * grupo la dejan vacía: la tabla se lee como un plan y no como un listado.
   */
  filasPago(c: ContratoExpediente): FilaPago[] {
    let anterior: string | null | undefined;
    return (c.plan_pago ?? []).map((f) => {
      const abre = f.periodo !== anterior;
      anterior = f.periodo;
      return {
        ...f,
        abrePeriodo: abre,
        rotuloPeriodo: abre ? this.periodoTexto(f.periodo) : null,
      };
    });
  }

  /**
   * «2025-05» → «Mayo 2025». Es FORMATO, no invención: el periodo sale del
   * dato y si no tiene la forma de un mes se muestra tal cual llegó, sin
   * forzarlo a un calendario que nadie reportó.
   */
  periodoTexto(p: string | null): string {
    if (!p) return 'Periodo sin fecha';
    const m = /^(\d{4})-(\d{2})$/.exec(p);
    if (!m) return p;
    const fecha = new Date(Number(m[1]), Number(m[2]) - 1, 1);
    if (isNaN(fecha.getTime())) return p;
    const txt = fecha.toLocaleDateString('es-CO', { month: 'long', year: 'numeric' });
    return txt.charAt(0).toUpperCase() + txt.slice(1);
  }

  /** Suma de una columna del plan. Null si NINGUNA fila trae ese número. */
  private totalPago(c: ContratoExpediente, campo: 'programado' | 'pagado'): number | null {
    const filas = c.plan_pago ?? [];
    const conDato = filas.filter((f) => f[campo] != null);
    if (!conDato.length) return null;
    return conDato.reduce((s, f) => s + Number(f[campo]), 0);
  }

  totalProgramado(c: ContratoExpediente): number | null { return this.totalPago(c, 'programado'); }
  totalPagado(c: ContratoExpediente): number | null { return this.totalPago(c, 'pagado'); }

  /** El total solo aporta si hay más de una fila que sumar. */
  hayTotal(c: ContratoExpediente): boolean { return (c.plan_pago?.length ?? 0) > 1; }

  /**
   * Estado del pago normalizado a clase CSS. Los valores reales de SECOP son
   * cinco: Pagado · Aprobado · Enviado Por Proveedor · Rechazado ·
   * Pendiente Registro. Cualquier otro cae en neutro y se muestra su texto:
   * el estado desconocido se lee, no se esconde.
   */
  clasePago(estado: string | null | undefined): string {
    const e = (estado ?? '').toLowerCase();
    if (e.startsWith('pagado')) return 'ok';
    if (e.startsWith('aprobado')) return 'medio';
    if (e.startsWith('rechazado')) return 'malo';
    if (e) return 'neutro';
    return 'neutro';
  }
}
