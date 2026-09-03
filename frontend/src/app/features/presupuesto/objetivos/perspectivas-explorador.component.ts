import { CommonModule } from '@angular/common';
import { HttpClient } from '@angular/common/http';
import { Component, Input, OnChanges, OnDestroy, SimpleChanges, computed, inject, signal } from '@angular/core';
import { catchError, of } from 'rxjs';
import { ConfigService } from '../../../core/config/config.service';
import { formatMoneda, formatNumero } from '../../../shared/format/format.util';
import { ExpedienteProyectoComponent } from '../expediente/expediente-proyecto.component';
import { enMillones } from '../muro/muro-subgrupos.component';
import {
  ALERTAS, AlertaCumplimiento, ObjetivoEstrategico, ObjetivoPrograma, ProyectoLista,
  comprometidoDe, giradoDe, peorAlerta, saldoPorGirar,
} from './objetivos.types';

/** Los 3 baldes en los que cae cada una de las 5 alertas, para el semáforo y
 *  la barra apilada. Es una SIMPLIFICACIÓN visual de las 5 categorías reales
 *  —nunca se pierde el detalle: el badge de cada proyecto/meta sigue
 *  mostrando la alerta completa, esto solo agrupa color. */
const BALDE: Record<AlertaCumplimiento, 'rojo' | 'amarillo' | 'verde'> = {
  'Crítico': 'rojo', 'Desierta': 'rojo', 'Sin magnitud contratada': 'rojo',
  'En ejecución de acuerdo a cronograma': 'amarillo',
  'Ejecutada': 'verde',
};
const TEXTO_BALDE: Record<'rojo' | 'amarillo' | 'verde', string> = {
  rojo: 'Crítico', amarillo: 'En progreso', verde: 'En meta',
};

interface PerspectivaCard {
  numero: string;
  nombre: string;
  balde: 'rojo' | 'amarillo' | 'verde' | 'gris';
  pctRojo: number; pctAmarillo: number; pctVerde: number;
  nMetas: number;
  avancePct: number | null;
  presupuestoProgramado: number;
}

interface MetaLigera {
  meta_proyecto_id: number;
  nombre: string | null;
  avance_pct: number | null;
  n_indicadores: number;
  indicadores_con_avance: number;
}

/** Un proyecto ya resuelto para pintar en Nivel 3, con la plata «real → si
 *  no, oficial» ya calculada — la plantilla no vuelve a decidir la fuente. */
interface ProyectoResuelto {
  p: ProyectoLista;
  comprometido: { valor: number | null; esOficial: boolean };
  girado: { valor: number | null; esOficial: boolean };
  saldo: number | null;
}

interface ProgramaResuelto extends ObjetivoPrograma {
  proyectosFiltrados: ProyectoResuelto[];
  peorAlerta: AlertaCumplimiento | null;
  balde: 'rojo' | 'amarillo' | 'verde' | 'gris';
}

/**
 * Explorador jerárquico Perspectiva → Programa → Proyecto → Meta.
 *
 * Reemplaza al Explorador 360° plano (búsqueda + lista sin jerarquía): acá
 * el punto de partida es SIEMPRE elegir la perspectiva primero. Los filtros
 * (búsqueda, área, subgrupo, alerta) acotan lo que se ve dentro de la
 * perspectiva activa, nunca reemplazan la jerarquía.
 *
 * No pide el árbol por su cuenta: lo recibe del padre (mismo
 * `/objetivos-estrategicos/` que ya se usaba para el chip de Objetivo), así
 * que esta pantalla y el resto del dashboard nunca pueden mostrar números
 * distintos del mismo dato.
 */
@Component({
  standalone: true,
  selector: 'app-perspectivas-explorador',
  imports: [CommonModule, ExpedienteProyectoComponent],
  templateUrl: './perspectivas-explorador.component.html',
  styleUrl: './perspectivas-explorador.component.scss',
})
export class PerspectivasExploradorComponent implements OnChanges, OnDestroy {
  @Input() objetivos: ObjetivoEstrategico[] = [];

  /**
   * Id de un proyecto a abrir de un salto — lo usa la pestaña «Metas» del
   * dashboard («abrirProyectoDeMeta») para saltar acá desde el panorama de
   * metas. Encuentra su perspectiva/programa dentro del árbol y los abre;
   * si el id no aparece en NINGÚN programa (proyecto sin objetivo
   * estratégico cargado — 1 de 31 hoy), no hace nada: no hay a dónde
   * saltar sin inventar una ubicación.
   */
  @Input() abrirProyectoId: number | null = null;

  private http = inject(HttpClient);
  private cfg = inject(ConfigService);

  readonly ALERTAS = ALERTAS;
  readonly TEXTO_BALDE = TEXTO_BALDE;
  formatMoneda = formatMoneda;
  formatNumero = formatNumero;
  enMillones = enMillones;

  private datos = signal<ObjetivoEstrategico[]>([]);

  // ── Nivel 1: siempre la foto COMPLETA, sin filtrar — elegir un eje no
  // debe cambiar cómo se ven los otros 4. ──
  perspectivaCards = computed<PerspectivaCard[]>(() => this.datos().map((o, i) => {
    const proyectos = this.proyectosDe(o);
    const conteo = this.conteoAlertaDe(proyectos);
    const total = Object.values(conteo).reduce((s, n) => s + n, 0);
    const rojo = (conteo['Crítico'] ?? 0) + (conteo['Desierta'] ?? 0) + (conteo['Sin magnitud contratada'] ?? 0);
    const amarillo = conteo['En ejecución de acuerdo a cronograma'] ?? 0;
    const verde = conteo['Ejecutada'] ?? 0;
    const peor = peorAlerta(proyectos.map(p => p.alerta));
    return {
      numero: String(i + 1),
      nombre: o.nombre.replace(/^\d+\s*-\s*/, ''),
      balde: peor ? BALDE[peor] : 'gris',
      pctRojo: total ? (rojo / total) * 100 : 0,
      pctAmarillo: total ? (amarillo / total) * 100 : 0,
      pctVerde: total ? (verde / total) * 100 : 0,
      nMetas: total,
      avancePct: this.avancePonderado(proyectos),
      presupuestoProgramado: proyectos.reduce((s, p) => s + (p.programado_oficial ?? 0), 0),
    };
  }));

  // ── Selección de perspectiva (Nivel 1) ──
  perspectivaSel = signal<string>('');
  perspectivaActiva = computed<ObjetivoEstrategico | undefined>(() =>
    this.datos().find(o => o.nombre === this.perspectivaSel()));

  seleccionarPerspectiva(nombre: string): void {
    this.perspectivaSel.set(this.perspectivaSel() === nombre ? '' : nombre);
    this.limpiarFiltros();
  }

  // ── Filtros — SIEMPRE dentro de la perspectiva activa ──
  busqueda = signal<string>('');
  private busquedaTimer?: ReturnType<typeof setTimeout>;
  areaSel = signal<string>('');
  subgrupoSel = signal<number | null>(null);
  alertaSel = signal<string>('');

  /** Debounce de 300ms: no se recalcula ni se re-renderiza en cada tecla. */
  cambiarBusqueda(ev: Event): void {
    const valor = (ev.target as HTMLInputElement).value || '';
    clearTimeout(this.busquedaTimer);
    this.busquedaTimer = setTimeout(() => this.busqueda.set(valor), 300);
  }

  setArea(v: string): void { this.areaSel.set(this.areaSel() === v ? '' : v); }
  setSubgrupo(ev: Event): void {
    const v = (ev.target as HTMLSelectElement).value;
    this.subgrupoSel.set(v ? Number(v) : null);
  }
  setAlerta(v: string): void { this.alertaSel.set(this.alertaSel() === v ? '' : v); }

  hayFiltro = computed(() =>
    !!this.busqueda().trim() || !!this.areaSel() || this.subgrupoSel() != null || !!this.alertaSel());

  limpiarFiltros(): void {
    this.busqueda.set(''); this.areaSel.set(''); this.subgrupoSel.set(null); this.alertaSel.set('');
  }

  claseAlerta(alerta: AlertaCumplimiento): string {
    return this.ALERTAS.find(a => a.valor === alerta)?.clase ?? '';
  }
  baldeDe(alerta: AlertaCumplimiento | null): 'rojo' | 'amarillo' | 'verde' | 'gris' {
    return alerta ? BALDE[alerta] : 'gris';
  }

  private plano(t: string | null): string {
    return (t || '').normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase();
  }

  /** Área, subgrupo y búsqueda — sin la alerta. Separado para que el
   *  conteo del chip de alerta descuente los otros filtros pero nunca a sí
   *  mismo (mismo patrón que ya usa el dashboard para el chip de alerta). */
  private pasaSinAlerta(p: ProyectoLista): boolean {
    if (this.areaSel() && p.dependencia !== this.areaSel()) return false;
    if (this.subgrupoSel() != null && p.subgrupo_id !== this.subgrupoSel()) return false;
    const q = this.plano(this.busqueda().trim());
    if (q && !this.plano(p.nombre).includes(q) && !this.plano(p.codigo).includes(q)
        && !this.plano(p.subgrupo).includes(q) && !this.plano(p.dependencia).includes(q)) return false;
    return true;
  }
  private pasaFiltro(p: ProyectoLista): boolean {
    if (!this.pasaSinAlerta(p)) return false;
    if (this.alertaSel() && p.alerta !== this.alertaSel()) return false;
    return true;
  }

  /** Proyectos de la perspectiva activa, sin deduplicar entre programas —
   *  cada aparición es la del programa al que pertenece. */
  private proyectosPerspectivaActiva = computed<ProyectoLista[]>(() => {
    const obj = this.perspectivaActiva();
    if (!obj) return [];
    return this.proyectosDe(obj);
  });

  areasDisponibles = computed<Array<{ nombre: string; conteo: number }>>(() => {
    const m = new Map<string, number>();
    for (const p of this.proyectosPerspectivaActiva()) {
      if (!p.dependencia) continue;
      if (!this.pasaSinAlertaSinArea(p)) continue;
      m.set(p.dependencia, (m.get(p.dependencia) ?? 0) + 1);
    }
    return [...m.entries()].map(([nombre, conteo]) => ({ nombre, conteo }))
      .sort((a, b) => a.nombre.localeCompare(b.nombre, 'es'));
  });
  private pasaSinAlertaSinArea(p: ProyectoLista): boolean {
    if (this.subgrupoSel() != null && p.subgrupo_id !== this.subgrupoSel()) return false;
    const q = this.plano(this.busqueda().trim());
    if (q && !this.plano(p.nombre).includes(q) && !this.plano(p.codigo).includes(q)) return false;
    return true;
  }

  subgruposDisponibles = computed<Array<{ id: number; nombre: string; conteo: number }>>(() => {
    const m = new Map<number, { nombre: string; conteo: number }>();
    for (const p of this.proyectosPerspectivaActiva()) {
      if (p.subgrupo_id == null || !p.subgrupo) continue;
      if (this.areaSel() && p.dependencia !== this.areaSel()) continue;
      const cur = m.get(p.subgrupo_id) ?? { nombre: p.subgrupo, conteo: 0 };
      cur.conteo++;
      m.set(p.subgrupo_id, cur);
    }
    return [...m.entries()].map(([id, v]) => ({ id, ...v }))
      .sort((a, b) => a.nombre.localeCompare(b.nombre, 'es'));
  });

  /** Conteo por alerta, descontando búsqueda/área/subgrupo pero NO la
   *  alerta misma — para que el número del chip coincida siempre con lo
   *  que el clic va a mostrar. */
  alertaConteo = computed<Partial<Record<string, number>>>(() => {
    const out: Partial<Record<string, number>> = {};
    for (const p of this.proyectosPerspectivaActiva()) {
      if (!p.alerta || !this.pasaSinAlerta(p)) continue;
      out[p.alerta] = (out[p.alerta] ?? 0) + 1;
    }
    return out;
  });

  // ── Nivel 2/3: programas de la perspectiva activa, con sus proyectos ya
  // filtrados. Un programa sin proyectos que pasen el filtro no se muestra. ──
  programasVisibles = computed<ProgramaResuelto[]>(() => {
    const obj = this.perspectivaActiva();
    if (!obj) return [];
    return obj.programas
      .map(prog => {
        const proyectosFiltrados = prog.proyectos
          .filter(p => this.pasaFiltro(p))
          .map(p => this.resolverProyecto(p));
        const peor = peorAlerta(prog.proyectos.map(p => p.alerta));
        return {
          ...prog,
          proyectosFiltrados,
          peorAlerta: peor,
          balde: peor ? BALDE[peor] : 'gris',
        } as ProgramaResuelto;
      })
      .filter(p => p.proyectosFiltrados.length > 0)
      .sort((a, b) => a.nombre.localeCompare(b.nombre, 'es'));
  });

  private resolverProyecto(p: ProyectoLista): ProyectoResuelto {
    return { p, comprometido: comprometidoDe(p), girado: giradoDe(p), saldo: saldoPorGirar(p) };
  }

  // ── Acordeones (Set = varios abiertos a la vez) ──
  programasAbiertos = signal<Set<string>>(new Set());
  proyectosAbiertos = signal<Set<string>>(new Set());
  expedientesAbiertos = signal<Set<string>>(new Set());

  toggleProg(nombre: string): void {
    this.programasAbiertos.update(s => this.toggled(s, nombre));
  }
  toggleProy(codigo: string): void {
    this.proyectosAbiertos.update(s => this.toggled(s, codigo));
    if (this.proyectosAbiertos().has(codigo) && !this.metasPorProyecto()[codigo]) {
      this.cargarMetasLigeras(codigo);
    }
  }
  toggleExpediente(codigo: string): void {
    this.expedientesAbiertos.update(s => this.toggled(s, codigo));
  }
  private toggled(s: Set<string>, v: string): Set<string> {
    const n = new Set(s);
    n.has(v) ? n.delete(v) : n.add(v);
    return n;
  }

  // ── Nivel 4: metas de un proyecto, carga perezosa al abrir su tarjeta ──
  //
  // NO trae sector/alerta/girado POR META: el endpoint de hoy
  // (`/proyectos/<id>/expediente/`) no expone esos tres campos a ese nivel
  // —solo a nivel de proyecto entero—. Se declara así en la fila, no se
  // rellena con el dato del proyecto disfrazado de dato de la meta.
  metasPorProyecto = signal<Record<string, 'cargando' | 'error' | MetaLigera[]>>({});

  private cargarMetasLigeras(codigo: string): void {
    const proy = this.proyectosPerspectivaActiva().find(p => p.codigo === codigo);
    if (!proy) return;
    this.metasPorProyecto.update(m => ({ ...m, [codigo]: 'cargando' }));
    this.http.get<any>(this.cfg.url(`/presupuesto/api/proyectos/${proy.id}/expediente/`))
      .pipe(catchError(() => of(null)))
      .subscribe(d => {
        const metas: MetaLigera[] = Array.isArray(d?.metas) ? d.metas.map((m: any) => ({
          meta_proyecto_id: m.meta_proyecto_id,
          nombre: m.nombre ?? m.descripcion ?? null,
          avance_pct: m.avance_pct ?? null,
          n_indicadores: m.n_indicadores ?? 0,
          indicadores_con_avance: m.indicadores_con_avance ?? 0,
        })) : null;
        this.metasPorProyecto.update(mp => ({ ...mp, [codigo]: metas ?? 'error' }));
      });
  }

  // ── Helpers de agregación, compartidos por Nivel 1 y las cabeceras de
  // programa/proyecto ──
  private proyectosDe(o: ObjetivoEstrategico): ProyectoLista[] {
    const vistos = new Map<number, ProyectoLista>();
    for (const prog of o.programas) for (const p of prog.proyectos) vistos.set(p.id, p);
    return [...vistos.values()];
  }
  private conteoAlertaDe(proyectos: ProyectoLista[]): Record<string, number> {
    const out: Record<string, number> = {};
    for (const p of proyectos) {
      for (const [a, n] of Object.entries(p.alerta_conteo ?? {})) out[a] = (out[a] ?? 0) + n;
    }
    return out;
  }
  /** Promedio de `avance_pct` ponderado por `n_metas`. Es el mismo avance
   *  (KPI de innovaK) que ya se ve en cada proyecto — no es el
   *  «% cumplimiento entregado» de la hoja Alertas, que hoy no se expone
   *  por meta; se llama «avance» en pantalla a propósito, para no prometer
   *  una precisión que la fuente todavía no da. */
  private avancePonderado(proyectos: ProyectoLista[]): number | null {
    let sumaPeso = 0, sumaVal = 0;
    for (const p of proyectos) {
      if (p.avance_pct == null || !p.n_metas) continue;
      sumaPeso += p.n_metas; sumaVal += p.avance_pct * p.n_metas;
    }
    return sumaPeso ? Math.round((sumaVal / sumaPeso) * 10) / 10 : null;
  }

  ngOnChanges(changes: SimpleChanges): void {
    if (changes['objetivos']) this.datos.set(this.objetivos ?? []);
    if (changes['abrirProyectoId'] && this.abrirProyectoId != null) this.saltarAProyecto(this.abrirProyectoId);
  }
  ngOnDestroy(): void { clearTimeout(this.busquedaTimer); }

  private saltarAProyecto(id: number): void {
    for (const obj of this.datos()) {
      for (const prog of obj.programas) {
        const p = prog.proyectos.find(x => x.id === id);
        if (!p) continue;
        this.perspectivaSel.set(obj.nombre);
        this.limpiarFiltros();
        this.programasAbiertos.update(s => new Set(s).add(prog.nombre));
        this.proyectosAbiertos.update(s => new Set(s).add(p.codigo || ''));
        if (p.codigo && !this.metasPorProyecto()[p.codigo]) this.cargarMetasLigeras(p.codigo);
        return;
      }
    }
  }
}
