import { CommonModule } from '@angular/common';
import { Component, OnInit, inject, signal, computed } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { HttpClient } from '@angular/common/http';
import { RouterLink } from '@angular/router';
import { firstValueFrom } from 'rxjs';
import { ConfigService } from '../../core/config/config.service';
import { LayoutService } from '../../core/layout/layout.service';

interface MetaOf {
  codigo_meta: string; nombre: string;
  apropiacion_poai: number | null; comprometido: number | null; girado: number | null;
  alerta: string | null;
  espejo: { programado: number | null; entregado: number | null;
            tipo_anualizacion: string | null } | null;
}
interface ProyOf { codigo: string; nombre: string; en_innovak: boolean; metas: MetaOf[]; }
interface ProgOf { codigo: string; nombre: string; proyectos: ProyOf[]; }
interface ObjOf { codigo: string; nombre: string; programas: ProgOf[]; }

/** Fila plana: una meta del Plan con todo su contexto. */
interface Fila {
  objetivo: string; programa: string;
  proyecto_codigo: string; proyecto_nombre: string; en_innovak: boolean;
  codigo_meta: string; meta: string;
  apropiacion: number | null; comprometido: number | null; girado: number | null;
  alerta: string | null; en_espejo: boolean;
}

const POR_PAGINA = 10;

/**
 * Plan oficial (SEGPLAN) — tabla plana y detallada, una fila por meta oficial con
 * su Programa→Objetivo→Proyecto. Buscador + paginación de 10. JWT-first.
 */
@Component({
  standalone: true,
  selector: 'app-plan-oficial',
  imports: [CommonModule, FormsModule, RouterLink],
  template: `
    <div class="page">
      <header class="page__header">
        <h1><i class="fa fa-sitemap" aria-hidden="true"></i> Plan oficial</h1>
        <p class="page__subtitle">
          Metas del Plan de Desarrollo Local de Kennedy con su objetivo estratégico,
          programa y proyecto. Fuente: Matriz de Seguimiento PDL de la Alcaldía Local;
          se marca la que no tiene par en Datos Abiertos del Distrito.
        </p>
      </header>

      @if (cargando()) {
        <p class="muted">Cargando…</p>
      } @else if (!filas().length) {
        <div class="ui-empty-state"><i class="fa fa-info-circle" aria-hidden="true"></i>
          <p>Todavía no hay Plan cargado. Entra con la Matriz PDL.</p></div>
      } @else {
        <div class="barra">
          <input class="buscador" type="search" [(ngModel)]="busqueda"
                 (ngModelChange)="pagina.set(1)"
                 placeholder="Buscar objetivo, programa, proyecto o meta…" />
          <span class="conteo">{{ filtradas().length }} metas</span>
        </div>

        <div class="lista">
          @for (f of paginaActual(); track f.codigo_meta) {
            <article class="mc">
              <div class="mc__head">
                <span class="chip chip--meta">{{ f.codigo_meta }}</span>
                <h3 class="mc__title">{{ f.meta }}</h3>
                @if (!f.en_innovak) { <span class="badge badge--no">no cargado en innovaK</span> }
                @if (!f.en_espejo) {
                  <span class="badge badge--no"
                        title="Está en la Matriz de la ALK pero no en Datos Abiertos del Distrito">sin par en SDP</span>
                }
              </div>
              <!-- Objetivo primero: es el nivel de arriba del Plan. Antes esta
                   ruta empezaba por el programa, porque el espejo no tenía la
                   relación y la pantalla la inventaba al revés. -->
              <p class="mc__ruta">
                <span>{{ f.objetivo }}</span>
                <span class="sep">›</span><span>{{ f.programa }}</span>
                <span class="sep">›</span><span class="proy"><b>{{ f.proyecto_codigo }}</b> {{ f.proyecto_nombre }}</span>
              </p>
              <div class="mc__stats">
                <div class="st"><span class="st__n">{{ mill(f.apropiacion) }}</span><span class="st__l">Apropiación POAI</span></div>
                <div class="st"><span class="st__n">{{ mill(f.comprometido) }}</span><span class="st__l">Comprometido</span></div>
                <div class="st"><span class="st__n">{{ mill(f.girado) }}</span><span class="st__l">Girado</span></div>
                <div class="st"><span class="st__n st__txt">{{ f.alerta || 'Sin alerta' }}</span><span class="st__l">Avance de metas</span></div>
              </div>
            </article>
          }
        </div>

        <div class="pager">
          <button (click)="prev()" [disabled]="pagina() === 1">← Anterior</button>
          <span>Página {{ pagina() }} de {{ totalPaginas() }}</span>
          <button (click)="next()" [disabled]="pagina() >= totalPaginas()">Siguiente →</button>
        </div>
      }

      <a routerLink="/presupuesto" class="ui-back-link">← Volver a Presupuesto</a>
    </div>
  `,
  styles: [`
    @use '../../../styles/tokens' as *;
    :host { display: block; }
    .page { max-width: 1200px; margin: 0 auto; }
    .page__header h1 { margin: 0; color: $color-primary; i { margin-right: $space-2; } }
    .page__subtitle { color: $color-text-muted; margin: $space-1 0 $space-4; }
    .muted { color: $color-text-muted; }
    .barra { display: flex; align-items: center; gap: $space-3; margin-bottom: $space-3; flex-wrap: wrap; }
    .buscador { flex: 1; min-width: 220px; max-width: 460px; padding: $space-2 $space-3; border: 1px solid rgba(0,0,0,.15); border-radius: 8px; }
    .conteo { color: $color-text-muted; font-size: $font-size-sm; }
    .lista { display: flex; flex-direction: column; gap: $space-3; }
    .mc { border: 1px solid rgba(0,0,0,.1); border-radius: 12px; padding: $space-3 $space-4; background: #fff; }
    .mc__head { display: flex; align-items: center; gap: $space-2; flex-wrap: wrap; }
    .mc__title { margin: 0; font-size: $font-size-base; color: $color-text; flex: 1; min-width: 200px; }
    .mc__ruta { margin: $space-1 0 $space-3; color: $color-text-muted; font-size: $font-size-sm; display: flex; flex-wrap: wrap; gap: 4px 6px; align-items: baseline; }
    .mc__ruta .sep { opacity: .5; }
    .mc__ruta .proy { color: $color-text; }
    .mc__stats { display: grid; grid-template-columns: repeat(auto-fit, minmax(110px, 1fr)); gap: $space-2; }
    .st { background: rgba(0,0,0,.03); border-radius: 8px; padding: $space-2; text-align: center; }
    .st__n { display: block; font-weight: 700; font-variant-numeric: tabular-nums; color: $color-text; }
    .st__l { font-size: .72rem; color: $color-text-muted; }
    /* La alerta es una frase, no una cifra: no hereda el cuerpo de un número. */
    .st__txt { font-size: $font-size-sm; line-height: 1.25; }
    .chip { border-radius: 999px; padding: 1px 9px; font-size: .75rem; background: #64748b; color: #fff; font-variant-numeric: tabular-nums; white-space: nowrap; }
    .badge { border-radius: 999px; padding: 1px 9px; font-size: .72rem; white-space: nowrap; }
    .badge--ok { background: #dcfce7; color: #166534; } .badge--no { background: #fee2e2; color: #991b1b; }
    .pager { display: flex; align-items: center; gap: $space-3; margin-top: $space-4; justify-content: center; flex-wrap: wrap; }
    .pager button { padding: $space-1 $space-3; border: 1px solid rgba(0,0,0,.15); border-radius: 8px; background: #fff; cursor: pointer; }
    .pager button:disabled { opacity: .4; cursor: default; }
    .ui-back-link { display: inline-block; margin-top: $space-4; color: $color-primary; }
  `],
})
export class PlanOficialComponent implements OnInit {
  private http = inject(HttpClient);
  private cfg = inject(ConfigService);
  private layout = inject(LayoutService);

  filas = signal<Fila[]>([]);
  cargando = signal<boolean>(true);
  busqueda = signal<string>('');
  pagina = signal<number>(1);

  filtradas = computed(() => {
    const q = this.busqueda().trim().toLowerCase();
    if (!q) return this.filas();
    return this.filas().filter(f =>
      (f.programa + ' ' + f.objetivo + ' ' + f.proyecto_codigo + ' ' + f.proyecto_nombre + ' '
        + f.codigo_meta + ' ' + f.meta).toLowerCase().includes(q));
  });
  totalPaginas = computed(() => Math.max(1, Math.ceil(this.filtradas().length / POR_PAGINA)));
  paginaActual = computed(() => {
    const ini = (this.pagina() - 1) * POR_PAGINA;
    return this.filtradas().slice(ini, ini + POR_PAGINA);
  });

  prev(): void { if (this.pagina() > 1) this.pagina.update(p => p - 1); }
  next(): void { if (this.pagina() < this.totalPaginas()) this.pagina.update(p => p + 1); }

  /** Pesos a «$N M». La Matriz los trae en PESOS; el espejo venía en millones.
   *  `null` no es 0: una meta sin apropiación reportada no apropió cero. */
  mill(v: number | null | undefined): string {
    if (v == null) return 'Sin dato';
    return `$${(v / 1e6).toLocaleString('es-CO', { maximumFractionDigits: 0 })} M`;
  }

  async ngOnInit(): Promise<void> {
    this.layout.setBreadcrumb([
      { label: 'Inicio', url: '/' },
      { label: 'Plan de Desarrollo', url: '/presupuesto' },
      { label: 'Plan oficial' },
    ]);
    try {
      const r: any = await firstValueFrom(
        this.http.get(this.cfg.url('/dashboard/api/v2/presupuesto/plan-oficial/')));
      // Objetivo → Programa → Proyecto → Meta. El orden importa: el espejo
      // traía programa y objetivo como campos sueltos y esta pantalla los
      // anidaba al revés, como si un programa agrupara objetivos.
      const filas: Fila[] = [];
      for (const obj of (r?.objetivos ?? []) as ObjOf[]) {
        for (const prog of obj.programas) {
          for (const py of prog.proyectos) {
            for (const m of py.metas) {
              filas.push({
                objetivo: obj.nombre, programa: prog.nombre,
                proyecto_codigo: py.codigo, proyecto_nombre: py.nombre,
                en_innovak: py.en_innovak,
                codigo_meta: m.codigo_meta, meta: m.nombre,
                apropiacion: m.apropiacion_poai, comprometido: m.comprometido,
                girado: m.girado, alerta: m.alerta, en_espejo: !!m.espejo,
              });
            }
          }
        }
      }
      this.filas.set(filas);
    } catch {
      this.filas.set([]);
    } finally {
      this.cargando.set(false);
    }
  }
}
