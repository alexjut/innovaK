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
  // Sólo vienen si el contrato es NUESTRO. Es el salto de este espejo al
  // expediente interno: se ve el contrato en SECOP y se va a completarlo.
  contrato_id: number | null; area_slug: string | null;
  area_nombre: string | null; n_faltantes: number | null;
  /** La cadena: a qué actividad del plan llega y a cuántas metas aporta. */
  actividad: string | null; n_actividades: number | null; n_metas: number | null;
}

/** Una fila del resumen por subgrupo: de quién es cada contrato y cuánto le falta. */
interface AreaResumen {
  slug: string; nombre: string;
  n_contratos: number; n_faltantes: number; pct: number | null;
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
        <h1><i class="fa fa-file-signature" aria-hidden="true"></i> Contratos <span class="of">· oficial (SECOP)</span></h1>
        <p class="page__subtitle">
          Contratos adjudicados de la Alcaldía Local de Kennedy en SECOP II, conciliados
          contra los contratos internos de innovaK. Clic en el número abre el proceso en SECOP.
        </p>
        <p class="page__subtitle">
          Esta lista es <strong>solo lectura</strong>: es el espejo de SECOP.
          Para registrar el valor de un contrato, su CDP y las actividades que
          financia, vaya a
          <a routerLink="/presupuesto/contratos-internos">contratos internos</a>.
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

      <!-- POR SUBGRUPO. Saber de quién es cada contrato y poder quedarse con
           los de un área. Los que más deben van primero: es el orden en que
           conviene atacarlos. Los conteos son sobre el UNIVERSO de contratos
           nuestros, no sobre la página — un número que cambia al pasar de
           página no sirve para decidir por dónde empezar. -->
      @if (areas().length) {
        <div class="areas" role="group" aria-label="Filtrar por subgrupo">
          <button type="button" class="ab" [class.ab--on]="!area()"
                  (click)="filtrarArea(null)">Todos los subgrupos</button>
          @for (a of areas(); track a.slug) {
            <button type="button" class="ab" [class.ab--on]="area() === a.slug"
                    (click)="filtrarArea(a.slug)"
                    [title]="a.nombre + ': ' + a.n_contratos + ' contratos, ' + a.n_faltantes + ' datos pendientes'">
              {{ a.nombre }}
              <span class="ab__n">{{ a.n_contratos }}</span>
              @if (a.n_faltantes) {
                <span class="ab__f">{{ a.n_faltantes }} pend.</span>
              } @else {
                <span class="ab__f ab__f--ok">al día</span>
              }
            </button>
          }
        </div>
      }

      @if (cargando()) {
        <p class="muted">Cargando…</p>
      } @else if (!items().length) {
        <div class="ui-empty-state"><i class="fa fa-info-circle" aria-hidden="true"></i><p>Sin resultados.</p></div>
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
                  <span class="badge badge--ok"><i class="fa fa-check" aria-hidden="true"></i> en innovaK</span>
                } @else {
                  <span class="badge badge--warn"><i class="fa fa-triangle-exclamation" aria-hidden="true"></i> falta cargar</span>
                }

                <!-- El salto al expediente. Sólo aparece si el contrato es
                     nuestro Y sabemos de qué área es: un enlace que no lleva a
                     ninguna parte es peor que ninguno. -->
                @if (ct.area_slug && ct.contrato_id) {
                  <a class="completar"
                     [class.completar--ok]="!ct.n_faltantes"
                     [routerLink]="['/mi-area', ct.area_slug]"
                     [queryParams]="{ contrato: ct.contrato_id }"
                     [title]="'Ir al expediente en ' + ct.area_nombre">
                    @if (ct.n_faltantes) {
                      {{ ct.n_faltantes }} por completar →
                    } @else {
                      Expediente completo →
                    }
                  </a>
                  <span class="area">{{ ct.area_nombre }}</span>
                }
              </div>

              <!-- LA CADENA: de quién es y a qué le sirve. Un contrato sin
                   actividad se dice con esas palabras, no se deja en blanco:
                   es el eslabón que hay que enganchar. -->
              @if (ct.en_innovak && ct.area_slug) {
                <p class="cadena">
                  @if (ct.actividad) {
                    <span class="cad__l">Actividad</span>
                    <span class="cad__v">{{ ct.actividad }}</span>
                    @if (ct.n_actividades && ct.n_actividades > 1) {
                      <span class="cad__mas">+{{ ct.n_actividades - 1 }} más</span>
                    }
                    @if (ct.n_metas) {
                      <span class="cad__m">{{ ct.n_metas }} meta{{ ct.n_metas === 1 ? '' : 's' }}</span>
                    }
                  } @else {
                    <span class="cad__falta">Sin actividad del plan — no le suma a ninguna meta</span>
                  }
                </p>
              }
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
    .cadena {
      display: flex; align-items: baseline; gap: 8px; flex-wrap: wrap;
      margin: 4px 0 0; font-size: $font-size-xs;
    }
    .cad__l {
      font-size: 10px; font-weight: $font-weight-semibold; letter-spacing: 0.06em;
      text-transform: uppercase; color: $color-neutral-600;
    }
    .cad__v { color: $color-neutral-800; }
    .cad__mas, .cad__m {
      padding: 1px 7px; border-radius: 9999px; font-size: 10px;
      font-weight: $font-weight-semibold;
      background: rgba(13, 148, 136, .10); color: #0F766E;
    }
    .cad__falta { color: $color-warning-hondo; font-style: italic; }

    .areas { display: flex; gap: 0.375rem; flex-wrap: wrap; margin-bottom: $space-3; }
    .ab {
      display: inline-flex; align-items: baseline; gap: 6px;
      padding: 4px 12px; border-radius: 9999px;
      font-size: $font-size-sm; cursor: pointer;
      background: #fff; color: $color-neutral-600; border: 1px solid $color-border-strong;
    }
    .ab:hover { border-color: #0F766E; color: #0F766E; }
    .ab--on { background: #0F766E; color: #fff; border-color: #0F766E; }
    .ab__n { font-size: 11px; font-weight: $font-weight-bold; font-variant-numeric: tabular-nums; }
    .ab__f { font-size: 10px; color: $color-warning-hondo; }
    .ab--on .ab__f { color: #fff; }
    .ab__f--ok { color: $color-success-hondo; }
    .ab--on .ab__f--ok { color: #fff; }

    .completar {
      margin-left: auto; padding: 3px 11px; border-radius: 9999px;
      font-size: 11px; font-weight: 600; text-decoration: none;
      background: rgba(245, 158, 11, .14); color: #92400E;
      border: 1px solid rgba(245, 158, 11, .26); white-space: nowrap;
    }
    .completar:hover { background: rgba(245, 158, 11, .22); }
    .completar:focus-visible { outline: 3px solid rgba(214,0,28,.55); outline-offset: 2px; }
    .completar--ok {
      background: rgba(22, 163, 74, .10); color: #166534;
      border-color: rgba(22, 163, 74, .22);
    }
    .area { font-size: 11px; color: #4B5563; white-space: nowrap; }

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
  /** Resumen por subgrupo: de quién es cada contrato y cuánto le falta. */
  areas = signal<AreaResumen[]>([]);
  /** El subgrupo elegido, o `null` para verlos todos. */
  area = signal<string | null>(null);
  cargando = signal<boolean>(true);
  q = '';

  buscar(): void { this.ir(1); }

  filtrar(f: Filtro): void {
    if (this.solo() === f) return;
    this.solo.set(f);
    this.ir(1);
  }

  filtrarArea(slug: string | null): void {
    if (this.area() === slug) return;
    this.area.set(slug);
    // Al elegir un subgrupo se pasa a «En innovaK»: los contratos que aún no
    // están cargados no pertenecen a ninguna área todavía, así que mezclarlos
    // daría una lista donde el filtro parece no funcionar.
    if (slug && this.solo() === 'todos') this.solo.set('en_innovak');
    this.ir(1);
  }

  async ir(p: number): Promise<void> {
    if (p < 1 || (this.pages() && p > this.pages())) return;
    this.cargando.set(true);
    try {
      const url = `/dashboard/api/v2/presupuesto/contratos-oficiales/`
        + `?page=${p}&q=${encodeURIComponent(this.q)}&solo=${this.solo()}`
        + (this.area() ? `&area=${encodeURIComponent(this.area()!)}` : '');
      const r: any = await firstValueFrom(this.http.get(this.cfg.url(url)));
      this.items.set(r?.items ?? []);
      this.count.set(r?.count ?? 0);
      this.page.set(r?.page ?? 1);
      this.pages.set(r?.pages ?? 1);
      if (r?.resumen) this.resumen.set(r.resumen);
      if (r?.areas) this.areas.set(r.areas);
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
