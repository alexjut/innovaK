import { CommonModule } from '@angular/common';
import { Component, OnInit, inject, signal, computed } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { HttpClient } from '@angular/common/http';
import { RouterLink } from '@angular/router';
import { firstValueFrom } from 'rxjs';
import { ConfigService } from '../../core/config/config.service';
import { LayoutService } from '../../core/layout/layout.service';

interface MetaOf { codigo_meta: string; nombre: string; programado_cuatrienio: number; entregado_cuatrienio: number; avance_pct: number; tipo_anualizacion: string | null; }
interface ProyOf { codigo: string; nombre: string; interno: boolean; metas: MetaOf[]; }
interface ObjOf { codigo: string; nombre: string; proyectos: ProyOf[]; }
interface ProgOf { codigo: string; nombre: string; objetivos: ObjOf[]; }

/** Fila plana: una meta oficial con todo su contexto del Plan. */
interface Fila {
  programa: string; objetivo: string; proyecto_codigo: string; proyecto_nombre: string;
  interno: boolean; codigo_meta: string; meta: string;
  programado: number; entregado: number; avance_pct: number; tipo: string | null;
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
          Metas del Plan de Desarrollo Local de Kennedy (SEGPLAN), con su programa, objetivo y
          proyecto. Marca cuáles ya están en innovaK. Fuente: Distrito.
        </p>
      </header>

      @if (cargando()) {
        <p class="muted">Cargando…</p>
      } @else if (!filas().length) {
        <div class="ui-empty-state"><i class="fa fa-info-circle" aria-hidden="true"></i>
          <p>Sin estructura oficial aún. Aplica el ALTER 009 y re-corre la ingesta SDP.</p></div>
      } @else {
        <div class="barra">
          <input class="buscador" type="search" [(ngModel)]="busqueda"
                 (ngModelChange)="pagina.set(1)"
                 placeholder="Buscar programa, objetivo, proyecto o meta…" />
          <span class="conteo">{{ filtradas().length }} metas</span>
        </div>

        <div class="lista">
          @for (f of paginaActual(); track f.codigo_meta) {
            <article class="mc">
              <div class="mc__head">
                <span class="chip chip--meta">{{ f.codigo_meta }}</span>
                <h3 class="mc__title">{{ f.meta }}</h3>
                @if (f.interno) { <span class="badge badge--ok">en innovaK</span> }
                @else { <span class="badge badge--no">no cargado</span> }
              </div>
              <p class="mc__ruta">
                <span>{{ f.programa }}</span>
                <span class="sep">›</span><span>{{ f.objetivo }}</span>
                <span class="sep">›</span><span class="proy"><b>{{ f.proyecto_codigo }}</b> {{ f.proyecto_nombre }}</span>
              </p>
              <div class="mc__stats">
                <div class="st"><span class="st__n">{{ f.programado | number:'1.0-0' }}</span><span class="st__l">Programado</span></div>
                <div class="st"><span class="st__n">{{ f.entregado | number:'1.0-0' }}</span><span class="st__l">Entregado</span></div>
                <div class="st"><span class="st__n st__pct" [class]="'st__pct--' + nivel(f.avance_pct)">{{ f.avance_pct }}%</span><span class="st__l">Avance</span></div>
                <div class="st"><span class="st__n">{{ f.tipo || '—' }}</span><span class="st__l">Anualización</span></div>
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
    .st__pct--alto { color: #16a34a; } .st__pct--medio { color: #f59e0b; } .st__pct--bajo { color: #dc2626; }
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

  nivel(pct: number): 'alto' | 'medio' | 'bajo' {
    return pct >= 80 ? 'alto' : pct >= 50 ? 'medio' : 'bajo';
  }

  async ngOnInit(): Promise<void> {
    this.layout.setBreadcrumb([
      { label: 'Inicio', url: '/' },
      { label: 'Presupuesto', url: '/presupuesto' },
      { label: 'Plan oficial' },
    ]);
    try {
      const r: any = await firstValueFrom(
        this.http.get(this.cfg.url('/dashboard/api/v2/presupuesto/plan-oficial/')));
      const filas: Fila[] = [];
      for (const prog of (r?.programas ?? []) as ProgOf[]) {
        for (const obj of prog.objetivos) {
          for (const py of obj.proyectos) {
            for (const m of py.metas) {
              filas.push({
                programa: prog.nombre, objetivo: obj.nombre,
                proyecto_codigo: py.codigo, proyecto_nombre: py.nombre, interno: py.interno,
                codigo_meta: m.codigo_meta, meta: m.nombre,
                programado: m.programado_cuatrienio, entregado: m.entregado_cuatrienio,
                avance_pct: m.avance_pct, tipo: m.tipo_anualizacion,
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
