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
        <div class="ui-empty-state"><i class="fa fa-info-circle"></i>
          <p>Sin estructura oficial aún. Aplica el ALTER 009 y re-corre la ingesta SDP.</p></div>
      } @else {
        <div class="barra">
          <input class="buscador" type="search" [(ngModel)]="busqueda"
                 (ngModelChange)="pagina.set(1)"
                 placeholder="Buscar programa, objetivo, proyecto o meta…" />
          <span class="conteo">{{ filtradas().length }} metas</span>
        </div>

        <div class="tabla-wrap">
          <table class="tabla">
            <thead>
              <tr>
                <th>Programa</th><th>Objetivo</th><th>Proyecto</th>
                <th>SEGPLAN</th><th>Meta</th>
                <th class="num">Programado</th><th class="num">Entregado</th><th class="num">%</th>
                <th>En innovaK</th>
              </tr>
            </thead>
            <tbody>
              @for (f of paginaActual(); track f.codigo_meta) {
                <tr>
                  <td class="mut">{{ f.programa }}</td>
                  <td class="mut">{{ f.objetivo }}</td>
                  <td><span class="chip">{{ f.proyecto_codigo }}</span> {{ f.proyecto_nombre }}</td>
                  <td><span class="chip chip--meta">{{ f.codigo_meta }}</span></td>
                  <td>{{ f.meta }}</td>
                  <td class="num">{{ f.programado | number:'1.0-0' }}</td>
                  <td class="num">{{ f.entregado | number:'1.0-0' }}</td>
                  <td class="num"><strong>{{ f.avance_pct }}%</strong></td>
                  <td>@if (f.interno) { <span class="badge badge--ok">sí</span> }
                      @else { <span class="badge badge--no">no</span> }</td>
                </tr>
              }
            </tbody>
          </table>
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
    .barra { display: flex; align-items: center; gap: $space-3; margin-bottom: $space-3; }
    .buscador { flex: 1; max-width: 460px; padding: $space-2 $space-3; border: 1px solid rgba(0,0,0,.15); border-radius: 8px; }
    .conteo { color: $color-text-muted; font-size: $font-size-sm; }
    .tabla-wrap { overflow-x: auto; }
    .tabla { width: 100%; border-collapse: collapse; font-size: $font-size-sm; }
    .tabla th, .tabla td { padding: $space-2 $space-3; border-bottom: 1px solid rgba(0,0,0,.08); text-align: left; vertical-align: top; }
    .tabla th.num, .tabla td.num { text-align: right; font-variant-numeric: tabular-nums; }
    .tabla td.mut { color: $color-text-muted; max-width: 160px; }
    .chip { border-radius: 999px; padding: 1px 8px; font-size: .75rem; background: $color-primary; color: #fff; font-variant-numeric: tabular-nums; }
    .chip--meta { background: #64748b; }
    .badge { border-radius: 999px; padding: 1px 8px; font-size: .72rem; }
    .badge--ok { background: #dcfce7; color: #166534; } .badge--no { background: #fee2e2; color: #991b1b; }
    .pager { display: flex; align-items: center; gap: $space-3; margin-top: $space-3; justify-content: center; }
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
