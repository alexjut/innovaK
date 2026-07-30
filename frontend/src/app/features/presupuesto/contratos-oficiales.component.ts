import { CommonModule } from '@angular/common';
import { Component, OnInit, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { HttpClient } from '@angular/common/http';
import { RouterLink } from '@angular/router';
import { firstValueFrom } from 'rxjs';
import { ConfigService } from '../../core/config/config.service';
import { LayoutService } from '../../core/layout/layout.service';

interface Contrato {
  referencia: string; estado: string; tipo: string; modalidad: string; objeto: string;
  proveedor: string; valor: number; pagado: number; fecha_firma: string; anio: number | null;
  url_proceso: string; en_innovak: boolean;
}

interface Resumen {
  total: number; en_innovak: number; faltantes: number; pct_conciliado: number;
  valor_total: number; valor_conciliado: number; valor_faltante: number;
}

type Filtro = 'todos' | 'en_innovak' | 'faltantes';

/**
 * Lista general de contratos ADJUDICADOS de Kennedy (SECOP II), paginada en
 * servidor (miles de filas) con buscador. Enlace directo a SECOP. JWT-first.
 */
@Component({
  standalone: true,
  selector: 'app-contratos-oficiales',
  imports: [CommonModule, FormsModule, RouterLink],
  template: `
    <div class="page">
      <header class="page__header">
        <h1><i class="fa fa-file-signature"></i> Contratos <span class="of">· oficial (SECOP)</span></h1>
        <p class="page__subtitle">
          Contratos adjudicados de la Alcaldía Local de Kennedy en SECOP II, conciliados
          contra los contratos internos de innovaK. Clic en el número abre el proceso en SECOP.
        </p>
      </header>

      <!-- Panel de conciliación -->
      @if (resumen(); as r) {
        <div class="kpis">
          <div class="kpi">
            <span class="kpi__n">{{ r.total | number }}</span>
            <span class="kpi__l">Contratos en SECOP</span>
          </div>
          <div class="kpi kpi--ok">
            <span class="kpi__n">{{ r.en_innovak | number }}</span>
            <span class="kpi__l">Ya en innovaK</span>
          </div>
          <div class="kpi kpi--warn">
            <span class="kpi__n">{{ r.faltantes | number }}</span>
            <span class="kpi__l">Faltan por cargar</span>
          </div>
          <div class="kpi kpi--pct">
            <span class="kpi__n">{{ r.pct_conciliado }}%</span>
            <span class="kpi__l">Conciliado</span>
            <div class="kpi__bar"><span [style.width.%]="r.pct_conciliado"></span></div>
          </div>
          <div class="kpi kpi--money">
            <span class="kpi__n">{{ money(r.valor_total) }}</span>
            <span class="kpi__l">Valor total · faltan {{ money(r.valor_faltante) }}</span>
          </div>
        </div>
      }

      <div class="barra">
        <div class="chips" role="tablist" aria-label="Filtrar contratos">
          <button class="chip" [class.chip--on]="solo() === 'todos'" (click)="filtrar('todos')">Todos</button>
          <button class="chip" [class.chip--on]="solo() === 'en_innovak'" (click)="filtrar('en_innovak')">En innovaK</button>
          <button class="chip chip--warn" [class.chip--on]="solo() === 'faltantes'" (click)="filtrar('faltantes')">Faltan por cargar</button>
        </div>
        <input class="buscador" type="search" [(ngModel)]="q"
               (keyup.enter)="buscar()" placeholder="Buscar referencia, objeto o proveedor… (Enter)" />
        <button class="btn" (click)="buscar()">Buscar</button>
        <span class="conteo">{{ count() | number }} en la lista</span>
      </div>

      @if (cargando()) {
        <p class="muted">Cargando…</p>
      } @else if (!items().length) {
        <div class="ui-empty-state"><i class="fa fa-info-circle"></i><p>Sin resultados.</p></div>
      } @else {
        <div class="lista">
          @for (ct of items(); track ct.referencia) {
            <article class="cc">
              <div class="cc__head">
                @if (ct.url_proceso) {
                  <a class="ref" [href]="ct.url_proceso" target="_blank" rel="noopener">{{ ct.referencia }} ↗</a>
                } @else { <span class="ref">{{ ct.referencia }}</span> }
                <span class="estado" [class]="'e-' + slug(ct.estado)">{{ ct.estado }}</span>
                @if (ct.en_innovak) {
                  <span class="badge badge--ok"><i class="fa fa-check"></i> en innovaK</span>
                } @else {
                  <span class="badge badge--warn"><i class="fa fa-triangle-exclamation"></i> falta cargar</span>
                }
              </div>
              <p class="cc__obj">{{ ct.objeto }}</p>
              <div class="cc__stats">
                <div class="st"><span class="st__n">\${{ ct.valor | number:'1.0-0' }}</span><span class="st__l">Valor</span></div>
                <div class="st"><span class="st__n">\${{ ct.pagado | number:'1.0-0' }}</span><span class="st__l">Pagado</span></div>
                <div class="st"><span class="st__n">{{ ct.anio || '—' }}</span><span class="st__l">Año</span></div>
                <div class="st st--prov"><span class="st__n">{{ ct.proveedor || '—' }}</span><span class="st__l">{{ ct.modalidad }}</span></div>
              </div>
            </article>
          }
        </div>

        <div class="pager">
          <button (click)="ir(page() - 1)" [disabled]="page() === 1">← Anterior</button>
          <span>Página {{ page() }} de {{ pages() }}</span>
          <button (click)="ir(page() + 1)" [disabled]="page() >= pages()">Siguiente →</button>
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
    /* Panel de conciliación */
    .kpis { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: $space-3; margin-bottom: $space-4; }
    .kpi { background: #fff; border: 1px solid rgba(0,0,0,.1); border-radius: 12px; padding: $space-3; position: relative; }
    .kpi__n { display: block; font-size: 1.5rem; font-weight: 800; color: $color-text; font-variant-numeric: tabular-nums; line-height: 1.1; }
    .kpi__l { font-size: .74rem; color: $color-text-muted; }
    .kpi--ok { border-left: 4px solid #16a34a; }
    .kpi--ok .kpi__n { color: #166534; }
    .kpi--warn { border-left: 4px solid #d97706; }
    .kpi--warn .kpi__n { color: #92400e; }
    .kpi--pct { border-left: 4px solid $color-primary; }
    .kpi--money .kpi__n { font-size: 1.15rem; }
    .kpi__bar { margin-top: $space-1; height: 6px; border-radius: 999px; background: rgba(0,0,0,.08); overflow: hidden; }
    .kpi__bar span { display: block; height: 100%; background: $color-primary; border-radius: 999px; transition: width .4s ease; }
    /* Chips de filtro */
    .chips { display: inline-flex; gap: $space-1; background: rgba(0,0,0,.04); padding: 3px; border-radius: 10px; }
    .chip { border: 0; background: transparent; padding: $space-1 $space-3; border-radius: 8px; cursor: pointer; font-size: $font-size-sm; color: $color-text-muted; }
    .chip--on { background: #fff; color: $color-text; font-weight: 700; box-shadow: 0 1px 3px rgba(0,0,0,.12); }
    .chip--warn.chip--on { color: #92400e; }
    .barra { display: flex; align-items: center; gap: $space-2; margin-bottom: $space-3; flex-wrap: wrap; }
    .buscador { flex: 1; min-width: 220px; max-width: 460px; padding: $space-2 $space-3; border: 1px solid rgba(0,0,0,.15); border-radius: 8px; }
    .btn { padding: $space-2 $space-3; border: 1px solid $color-primary; background: $color-primary; color: #fff; border-radius: 8px; cursor: pointer; }
    .conteo { color: $color-text-muted; font-size: $font-size-sm; }
    .lista { display: flex; flex-direction: column; gap: $space-3; }
    .cc { border: 1px solid rgba(0,0,0,.1); border-radius: 12px; padding: $space-3 $space-4; background: #fff; }
    .cc__head { display: flex; align-items: center; gap: $space-2; flex-wrap: wrap; }
    .ref { font-weight: 700; color: $color-primary; text-decoration: none; }
    .estado { border-radius: 999px; padding: 1px 9px; font-size: .72rem; background: rgba(0,0,0,.08); white-space: nowrap; }
    .e-en-ejecucion { background: #dbeafe; color: #1e40af; }
    .e-terminado, .e-cerrado { background: #dcfce7; color: #166534; }
    .e-modificado { background: #fef3c7; color: #92400e; }
    .cc__obj { margin: $space-1 0 $space-3; color: $color-text; font-size: $font-size-sm; }
    .cc__stats { display: grid; grid-template-columns: repeat(auto-fit, minmax(120px, 1fr)); gap: $space-2; }
    .st { background: rgba(0,0,0,.03); border-radius: 8px; padding: $space-2; text-align: center; }
    .st--prov { text-align: left; }
    .st__n { display: block; font-weight: 700; font-variant-numeric: tabular-nums; color: $color-text; font-size: $font-size-sm; }
    .st--prov .st__n { font-weight: 600; }
    .st__l { font-size: .72rem; color: $color-text-muted; }
    .badge { border-radius: 999px; padding: 1px 9px; font-size: .72rem; i { margin-right: 3px; } }
    .badge--ok { background: #dcfce7; color: #166534; }
    .badge--warn { background: #fef3c7; color: #92400e; }
    .pager { display: flex; align-items: center; gap: $space-3; margin-top: $space-4; justify-content: center; flex-wrap: wrap; }
    .pager button { padding: $space-1 $space-3; border: 1px solid rgba(0,0,0,.15); border-radius: 8px; background: #fff; cursor: pointer; }
    .pager button:disabled { opacity: .4; cursor: default; }
    .ui-back-link { display: inline-block; margin-top: $space-4; color: $color-primary; }
  `],
})
export class ContratosOficialesComponent implements OnInit {
  private http = inject(HttpClient);
  private cfg = inject(ConfigService);
  private layout = inject(LayoutService);

  items = signal<Contrato[]>([]);
  count = signal<number>(0);
  page = signal<number>(1);
  pages = signal<number>(1);
  resumen = signal<Resumen | null>(null);
  solo = signal<Filtro>('todos');
  cargando = signal<boolean>(true);
  q = '';

  buscar(): void { this.ir(1); }

  filtrar(f: Filtro): void {
    if (this.solo() === f) return;
    this.solo.set(f);
    this.ir(1);
  }

  async ir(p: number): Promise<void> {
    if (p < 1 || (this.pages() && p > this.pages())) return;
    this.cargando.set(true);
    try {
      const url = `/dashboard/api/v2/presupuesto/contratos-oficiales/`
        + `?page=${p}&q=${encodeURIComponent(this.q)}&solo=${this.solo()}`;
      const r: any = await firstValueFrom(this.http.get(this.cfg.url(url)));
      this.items.set(r?.items ?? []);
      this.count.set(r?.count ?? 0);
      this.page.set(r?.page ?? 1);
      this.pages.set(r?.pages ?? 1);
      if (r?.resumen) this.resumen.set(r.resumen);
    } catch {
      this.items.set([]);
    } finally {
      this.cargando.set(false);
    }
  }

  slug(s: string): string {
    return (s || '').toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g, '').replace(/\s+/g, '-');
  }

  /** Pesos en formato compacto: $1.234 M / $12,3 mil M. */
  money(v: number): string {
    const n = Math.abs(v || 0);
    if (n >= 1e9) return `$${(v / 1e9).toLocaleString('es-CO', { maximumFractionDigits: 1 })} mil M`;
    if (n >= 1e6) return `$${(v / 1e6).toLocaleString('es-CO', { maximumFractionDigits: 1 })} M`;
    return `$${(v || 0).toLocaleString('es-CO', { maximumFractionDigits: 0 })}`;
  }

  ngOnInit(): void {
    this.layout.setBreadcrumb([
      { label: 'Inicio', url: '/' },
      { label: 'Presupuesto', url: '/presupuesto' },
      { label: 'Contratos' },
    ]);
    this.ir(1);
  }
}
