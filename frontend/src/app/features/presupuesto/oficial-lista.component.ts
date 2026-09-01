import { CommonModule } from '@angular/common';
import { Component, OnInit, inject, signal, computed } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { HttpClient } from '@angular/common/http';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { firstValueFrom } from 'rxjs';
import { ConfigService } from '../../core/config/config.service';
import { LayoutService } from '../../core/layout/layout.service';

const POR_PAGINA = 10;

const META = {
  metas: { titulo: 'Metas', icono: 'fa-flag-checkered',
    subt: 'Metas del Plan de Desarrollo Local (SEGPLAN). Fuente: Distrito.' },
  proyectos: { titulo: 'Proyectos', icono: 'fa-folder-tree',
    subt: 'Proyectos de inversión del Plan (SEGPLAN). Fuente: Distrito.' },
  programas: { titulo: 'Programas', icono: 'fa-diagram-project',
    subt: 'Programas del Plan de Desarrollo (SEGPLAN). Fuente: Distrito.' },
} as const;

type Tipo = keyof typeof META;

/**
 * Lista OFICIAL (metas | proyectos | programas) desde el Plan SEGPLAN, en tarjetas
 * con buscador + paginación de 10. Reemplaza el catálogo interno viejo en la UI.
 * El `tipo` viene de `data.tipo` de la ruta.
 */
@Component({
  standalone: true,
  selector: 'app-oficial-lista',
  imports: [CommonModule, FormsModule, RouterLink],
  template: `
    <div class="page">
      <header class="page__header">
        <h1><i class="fa" [class]="cfgMeta.icono" aria-hidden="true"></i> {{ cfgMeta.titulo }} <span class="of">· oficial</span></h1>
        <p class="page__subtitle">{{ cfgMeta.subt }}</p>
      </header>

      @if (cargando()) {
        <p class="muted">Cargando…</p>
      } @else if (!items().length) {
        <div class="ui-empty-state"><i class="fa fa-info-circle" aria-hidden="true"></i>
          <p>Sin datos oficiales. Corre la ingesta SDP.</p></div>
      } @else {
        <div class="barra">
          <input class="buscador" type="search" [(ngModel)]="busqueda"
                 (ngModelChange)="pagina.set(1)" placeholder="Buscar…" />
          <span class="conteo">{{ filtradas().length }} {{ cfgMeta.titulo.toLowerCase() }}</span>
        </div>

        <div class="lista">
          @for (it of paginaActual(); track it.codigo) {
            <article class="mc">
              <div class="mc__head">
                <span class="chip">{{ it.codigo }}</span>
                <h3 class="mc__title">{{ it.nombre }}</h3>
                @if (tipo !== 'programas') {
                  @if (it.en_innovak) { <span class="badge badge--ok">en innovaK</span> }
                  @else { <span class="badge badge--no">no cargado</span> }
                }
              </div>

              @if (tipo === 'metas') {
                <p class="mc__ruta">{{ it.programa }} <span class="sep">›</span> {{ it.proyecto }}</p>
                <div class="mc__stats">
                  <div class="st"><span class="st__n">{{ it.programado | number:'1.0-0' }}</span><span class="st__l">Meta programada</span></div>
                  <div class="st"><span class="st__n">{{ it.entregado | number:'1.0-0' }}</span><span class="st__l">Entregado</span></div>
                  <div class="st"><span class="st__n" [class]="'p-' + nivel(it.avance_pct)">{{ it.avance_pct }}%</span><span class="st__l">Avance</span></div>
                  <div class="st"><span class="st__n">{{ it.tipo_anualizacion || '—' }}</span><span class="st__l">Anualización</span></div>
                </div>
              } @else if (tipo === 'proyectos') {
                <p class="mc__ruta">{{ it.programa }} <span class="sep">·</span> {{ it.sector }} <span class="sep">·</span> {{ it.estado }}</p>
                <div class="mc__stats">
                  <div class="st"><span class="st__n">{{ it.n_metas }}</span><span class="st__l">Metas</span></div>
                  <div class="st"><span class="st__n">\${{ it.programado | number:'1.0-0' }}</span><span class="st__l">Presupuesto proyectado PDL (M)</span></div>
                  <div class="st"><span class="st__n">\${{ it.comprometido | number:'1.0-0' }}</span><span class="st__l">Comprometido (M)</span></div>
                  <div class="st"><span class="st__n">\${{ it.girado | number:'1.0-0' }}</span><span class="st__l">Girado (M)</span></div>
                </div>
              } @else {
                <div class="mc__stats">
                  <div class="st"><span class="st__n">{{ it.n_objetivos }}</span><span class="st__l">Objetivos</span></div>
                  <div class="st"><span class="st__n">{{ it.n_proyectos }}</span><span class="st__l">Proyectos</span></div>
                  <div class="st"><span class="st__n">{{ it.n_metas }}</span><span class="st__l">Metas</span></div>
                </div>
              }
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
    .page { max-width: 1100px; margin: 0 auto; }
    .page__header h1 { margin: 0; color: $color-primary; i { margin-right: $space-2; } }
    .of { color: $color-text-muted; font-weight: 400; font-size: $font-size-base; }
    .page__subtitle { color: $color-text-muted; margin: $space-1 0 $space-4; }
    .muted { color: $color-text-muted; }
    .barra { display: flex; align-items: center; gap: $space-3; margin-bottom: $space-3; flex-wrap: wrap; }
    .buscador { flex: 1; min-width: 220px; max-width: 460px; padding: $space-2 $space-3; border: 1px solid rgba(0,0,0,.15); border-radius: 8px; }
    .conteo { color: $color-text-muted; font-size: $font-size-sm; }
    .lista { display: flex; flex-direction: column; gap: $space-3; }
    .mc { border: 1px solid rgba(0,0,0,.1); border-radius: 12px; padding: $space-3 $space-4; background: #fff; }
    .mc__head { display: flex; align-items: center; gap: $space-2; flex-wrap: wrap; }
    .mc__title { margin: 0; font-size: $font-size-base; color: $color-text; flex: 1; min-width: 200px; }
    .mc__ruta { margin: $space-1 0 $space-3; color: $color-text-muted; font-size: $font-size-sm; }
    .mc__ruta .sep { opacity: .5; margin: 0 4px; }
    .mc__stats { display: grid; grid-template-columns: repeat(auto-fit, minmax(110px, 1fr)); gap: $space-2; }
    .st { background: rgba(0,0,0,.03); border-radius: 8px; padding: $space-2; text-align: center; }
    .st__n { display: block; font-weight: 700; font-variant-numeric: tabular-nums; color: $color-text; }
    .st__l { font-size: .72rem; color: $color-text-muted; }
    .p-alto { color: #16a34a; } .p-medio { color: #f59e0b; } .p-bajo { color: #dc2626; }
    .chip { border-radius: 999px; padding: 1px 9px; font-size: .75rem; background: $color-primary; color: #fff; font-variant-numeric: tabular-nums; white-space: nowrap; }
    .badge { border-radius: 999px; padding: 1px 9px; font-size: .72rem; white-space: nowrap; }
    .badge--ok { background: #dcfce7; color: #166534; } .badge--no { background: #fee2e2; color: #991b1b; }
    .pager { display: flex; align-items: center; gap: $space-3; margin-top: $space-4; justify-content: center; flex-wrap: wrap; }
    .pager button { padding: $space-1 $space-3; border: 1px solid rgba(0,0,0,.15); border-radius: 8px; background: #fff; cursor: pointer; }
    .pager button:disabled { opacity: .4; cursor: default; }
    .ui-back-link { display: inline-block; margin-top: $space-4; color: $color-primary; }
  `],
})
export class OficialListaComponent implements OnInit {
  private http = inject(HttpClient);
  private cfg = inject(ConfigService);
  private layout = inject(LayoutService);
  private ruta = inject(ActivatedRoute);

  tipo: Tipo = 'metas';
  get cfgMeta() { return META[this.tipo]; }

  items = signal<any[]>([]);
  cargando = signal<boolean>(true);
  busqueda = signal<string>('');
  pagina = signal<number>(1);

  filtradas = computed(() => {
    const q = this.busqueda().trim().toLowerCase();
    if (!q) return this.items();
    return this.items().filter(it =>
      JSON.stringify(it).toLowerCase().includes(q));
  });
  totalPaginas = computed(() => Math.max(1, Math.ceil(this.filtradas().length / POR_PAGINA)));
  paginaActual = computed(() => {
    const ini = (this.pagina() - 1) * POR_PAGINA;
    return this.filtradas().slice(ini, ini + POR_PAGINA);
  });

  prev(): void { if (this.pagina() > 1) this.pagina.update(p => p - 1); }
  next(): void { if (this.pagina() < this.totalPaginas()) this.pagina.update(p => p + 1); }
  nivel(pct: number): 'alto' | 'medio' | 'bajo' { return pct >= 80 ? 'alto' : pct >= 50 ? 'medio' : 'bajo'; }

  async ngOnInit(): Promise<void> {
    this.tipo = (this.ruta.snapshot.data['tipo'] as Tipo) || 'metas';
    this.layout.setBreadcrumb([
      { label: 'Inicio', url: '/' },
      { label: 'Presupuesto', url: '/presupuesto' },
      { label: this.cfgMeta.titulo },
    ]);
    try {
      const r: any = await firstValueFrom(
        this.http.get(this.cfg.url(`/dashboard/api/v2/presupuesto/oficial/${this.tipo}/`)));
      this.items.set(r?.items ?? []);
    } catch {
      this.items.set([]);
    } finally {
      this.cargando.set(false);
    }
  }
}
