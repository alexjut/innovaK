import { CommonModule } from '@angular/common';
import { Component, OnInit, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { HttpClient } from '@angular/common/http';
import { RouterLink } from '@angular/router';
import { firstValueFrom } from 'rxjs';
import { ConfigService } from '../../core/config/config.service';
import { LayoutService } from '../../core/layout/layout.service';
import { enMillones } from './muro/muro-subgrupos.component';

interface Contrato {
  /** Identidad estable del contrato en SECOP (`CO1.PCCNTR.…`). Es la clave de
   *  `track`: `referencia` se repite —CPS-134-2024 y CPS-653-2024 están dos
   *  veces en el espejo— y con una clave repetida Angular lanza NG0955. */
  id_contrato: string;
  referencia: string; estado: string; tipo: string; modalidad: string; objeto: string;
  proveedor: string; valor: number; fecha_firma: string; anio: number | null;
  url_proceso: string; en_innovak: boolean;
  /** `null` cuando SECOP no lo mide. NUNCA 0: ver `pagado_motivo`. */
  pagado: number | null; pagado_motivo: string | null;
  naturaleza: string | null; naturaleza_fuente: string | null;
  /** La cadena: a qué actividad del plan llega y a cuántas metas aporta. */
  actividad: string | null; n_actividades: number | null; n_metas: number | null;
}

interface Naturaleza {
  n: number; valor: number; de_bogdata: number; inferidos: number; etiqueta: string;
}

/**
 * Los contratos adjudicados de Kennedy en SECOP II, paginados en servidor.
 *
 * ## Esta pantalla dejó de hablar de nosotros
 *
 * Hasta hoy sus cuatro recuadros más grandes decían «24 en innovaK · 3.165
 * faltan · 0,8 % conciliado». Ese 0,8 % **no es una propiedad del contrato**:
 * cuenta cuántos de los 3.189 de SECOP tienen además una fila en nuestra tabla
 * interna. Quien abría la pantalla leía que el módulo estaba vacío o que la
 * Alcaldía no ejecuta, y ninguna de las dos es cierta — y de paso empujaba a
 * cargar 3.165 contratos a mano, tarea que nadie iba a hacer y que ya no hace
 * falta porque el espejo los trae todos, con más campos de los que el
 * formulario interno pide.
 *
 * Por eso salieron los recuadros, los chips «En innovaK / Faltan por cargar»,
 * la columna «N por completar» y la barra de áreas con sus pendientes. **Y con
 * ellos la palabra «falta»**: un contrato que está en SECOP y no en nuestra
 * tabla no está incompleto, está completo en su fuente.
 *
 * Lo que SÍ se conserva es el enganche con el Plan —la cadena contrato →
 * actividad → meta—, que no es conciliación: es lo único que Kennedy tiene y
 * SECOP no. Son 24 contratos, pero valen $40.567 M de $326.688 M: el 12,4 % de
 * la plata.
 *
 * ## «$0» no es «no se pagó»
 *
 * `secop_contrato` no tiene una sola fila con `valor_pagado` en NULL, así que
 * el cero y el «nadie lo reportó» son el mismo dato. La columna Pagado dice
 * **«Sin dato»** con su motivo, no «$0». Es la misma regla del expediente y de
 * la API pública, y el motivo viaja desde el servidor para que las tres
 * puertas expliquen el hueco con las mismas palabras.
 *
 * Solo lectura: es el espejo de SECOP.
 */
@Component({
  standalone: true,
  selector: 'app-contratos-oficiales',
  imports: [CommonModule, FormsModule, RouterLink],
  template: `
    <div class="page">
      <header class="page__header">
        <h1>
          <i class="fa fa-file-signature" aria-hidden="true"></i>
          Contratos <span class="of">· SECOP II</span>
        </h1>
        <p class="page__subtitle">
          Los contratos adjudicados por la Alcaldía Local de Kennedy, tal como
          los publica SECOP II. Acá manda SECOP y las cifras son las suyas;
          clic en el número abre el proceso en el portal.
        </p>
        <p class="page__subtitle">
          Esta lista es <strong>solo lectura</strong>. Para ver el mismo
          contrato con lo que dice además BogData —el comprometido y el girado
          del presupuesto— y dónde no coinciden,
          <a routerLink="/plan/contratos-fuentes">contratos por fuente</a>.
          Los contratos que se operan desde innovaK, con su CDP y las
          actividades que financian, viven en
          <a routerLink="/plan/contratos-internos">contratos internos</a>.
        </p>
      </header>

      <!-- ── Quién contrata ────────────────────────────────────────────
           La lista entera son miles de filas y las personas naturales la
           inundan: son 9 de cada 10 contratos y una tercera parte del valor.
           Partirla deja ver los pocos contratos que mueven la plata. -->
      @if (naturalezas(); as nn) {
        <section class="natur" aria-label="Personas naturales y jurídicas">
          <div class="tabs" role="tablist">
            <button type="button" role="tab" class="tab" [class.tab--on]="!naturaleza()"
                    [attr.aria-selected]="!naturaleza()" (click)="filtrarNaturaleza(null)">
              <span class="tab__n">{{ total(nn) | number }}</span>
              <span class="tab__l">General</span>
              <!-- El valor total vivía en los recuadros de conciliación que se
                   retiraron. Se queda acá: es la cifra de la pantalla. -->
              <span class="tab__d">{{ enMillones(totalValor(nn)) }}</span>
            </button>
            @for (k of NATURALEZAS; track k) {
              @if (nn[k]; as d) {
                <button type="button" role="tab" [class]="'tab tab--' + k"
                        [class.tab--on]="naturaleza() === k"
                        [attr.aria-selected]="naturaleza() === k"
                        (click)="filtrarNaturaleza(k)">
                  <span class="tab__n">{{ d.n | number }}</span>
                  <span class="tab__l">{{ d.etiqueta }}</span>
                  <span class="tab__d">{{ enMillones(d.valor) }}</span>
                  @if (d.inferidos) {
                    <span class="tab__i">{{ d.inferidos | number }} por la forma del documento</span>
                  }
                </button>
              }
            }
          </div>
          <p class="natur__n">
            Sale del tipo de documento del catálogo de BogData. Para los que
            solo están en SECOP se infiere del número —un NIT de empresa tiene
            nueve dígitos y empieza por 8 o 9— y la fila lo dice.
          </p>
        </section>
      }

      <div class="barra">
        <input class="buscador" type="search" [(ngModel)]="q"
               (keyup.enter)="buscar()" placeholder="Buscar referencia, objeto o proveedor… (Enter)" />
        <button class="btn" (click)="buscar()">Buscar</button>
        <span class="conteo">{{ count() | number }} en la lista</span>
      </div>

      @if (cargando()) {
        <p class="muted">Cargando…</p>
      } @else if (!items().length) {
        <div class="ui-empty-state"><i class="fa fa-info-circle" aria-hidden="true"></i><p>Sin resultados.</p></div>
      } @else {
        <div class="lista">
          @for (ct of items(); track ct.id_contrato) {
            <article class="cc">
              <div class="cc__head">
                @if (ct.url_proceso) {
                  <a class="ref" [href]="ct.url_proceso" target="_blank" rel="noopener">{{ ct.referencia }} ↗</a>
                } @else { <span class="ref">{{ ct.referencia }}</span> }
                <span class="estado" [class]="'e-' + slug(ct.estado)">{{ ct.estado }}</span>

                <!-- El enganche con el Plan, y SOLO cuando existe. No hay
                     contraparte negativa: un contrato sin cadena interna no
                     está incompleto, está completo en SECOP. -->
                @if (ct.en_innovak) {
                  <span class="plan" title="Este contrato está enganchado a una actividad del Plan">
                    <i class="fa fa-link" aria-hidden="true"></i> Enlazado al Plan
                  </span>
                }
              </div>

              <!-- LA CADENA: a qué le sirve el contrato. Solo se pinta cuando
                   la hay; lo que no existe no se anuncia. -->
              @if (ct.actividad) {
                <p class="cadena">
                  <span class="cad__l">Actividad</span>
                  <span class="cad__v">{{ ct.actividad }}</span>
                  @if (ct.n_actividades && ct.n_actividades > 1) {
                    <span class="cad__mas">+{{ ct.n_actividades - 1 }} más</span>
                  }
                  @if (ct.n_metas) {
                    <span class="cad__m">{{ ct.n_metas }} meta{{ ct.n_metas === 1 ? '' : 's' }}</span>
                  }
                </p>
              }
              <p class="cc__obj">{{ ct.objeto }}</p>
              <div class="cc__stats">
                <div class="st"><span class="st__n">{{ enMillones(ct.valor) }}</span><span class="st__l">Valor</span></div>
                <!-- «Sin dato» y no «$0»: 240 contratos traen cero y en SECOP
                     ese cero no distingue «no se giró» de «no se reportó». -->
                <div class="st" [class.st--sindato]="ct.pagado === null">
                  <span class="st__n" [attr.title]="ct.pagado_motivo">{{ plata(ct.pagado) }}</span>
                  <span class="st__l">Pagado</span>
                </div>
                <div class="st"><span class="st__n">{{ ct.anio || '—' }}</span><span class="st__l">Año</span></div>
                <div class="st st--prov">
                  <span class="st__n">{{ ct.proveedor || '—' }}</span>
                  <span class="st__l">
                    {{ ct.modalidad }}
                    @if (ct.naturaleza) {
                      <span class="nat" [class]="'nat nat--' + ct.naturaleza"
                            [class.nat--inf]="ct.naturaleza_fuente === 'documento'"
                            [title]="ct.naturaleza_fuente === 'documento'
                                     ? 'Inferido de la forma del documento'
                                     : 'Tipo de documento del catálogo de BogData'">
                        {{ ct.naturaleza === 'juridica' ? 'Jurídica' : 'Natural' }}</span>
                    }
                  </span>
                </div>
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

      <a routerLink="/plan/gestion" class="ui-back-link">← Volver a Gestión del Plan</a>
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

    .natur { margin: $space-3 0; }
    .tabs { display: grid; grid-template-columns: repeat(auto-fit, minmax(190px, 1fr));
            gap: $space-2; }
    .tab { text-align: left; cursor: pointer; background: #fff; border: 1px solid rgba(0,0,0,.1);
           border-bottom: 3px solid rgba(0,0,0,.15); border-radius: 8px;
           padding: $space-2 $space-3; display: flex; flex-direction: column; gap: 2px; }
    .tab--on { border-bottom-color: $color-primary; box-shadow: 0 0 0 2px rgba(0,0,0,.08) inset; }
    .tab--natural { border-bottom-color: #0e7490; }
    .tab--juridica { border-bottom-color: #7c3aed; }
    .tab--sin_clasificar { border-bottom-color: rgba(0,0,0,.25); }
    .tab__n { font-size: 1.3rem; font-weight: 700; font-variant-numeric: tabular-nums; }
    .tab__l { font-size: $font-size-sm; font-weight: 600; }
    .tab__d, .tab__i { font-size: $font-size-sm; color: $color-text-muted; }
    .tab__i { font-style: italic; }
    .natur__n { margin: $space-2 0 0; font-size: $font-size-sm; color: $color-text-muted; }

    .nat { display: inline-block; font-size: .72rem; padding: 0 6px; border-radius: 999px;
           background: rgba(14,116,144,.12); cursor: help; }
    .nat--juridica { background: rgba(124,58,237,.12); }
    .nat--inf { font-style: italic; background: rgba(0,0,0,.05); }

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

    /* El enganche con el Plan. Discreto a propósito: informa, no reclama. */
    .plan {
      border-radius: 999px; padding: 1px 9px; font-size: .72rem; white-space: nowrap;
      background: rgba(13, 148, 136, .10); color: #0F766E;
      i { margin-right: 3px; }
    }

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
    /* Un hueco se ve como hueco: ni negrita de cifra ni color de dato medido. */
    .st--sindato .st__n { font-weight: 400; font-style: italic; color: $color-text-muted; cursor: help; }
    .st__l { font-size: .72rem; color: $color-text-muted; }
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
  cargando = signal<boolean>(true);
  q = '';

  buscar(): void { this.ir(1); }

  /** Las jurídicas primero: son muchas menos y llevan la plata. */
  readonly NATURALEZAS = ['juridica', 'natural', 'sin_clasificar'];

  naturaleza = signal<string | null>(null);
  naturalezas = signal<Record<string, Naturaleza> | null>(null);

  filtrarNaturaleza(k: string | null): void {
    this.naturaleza.set(this.naturaleza() === k ? null : k);
    this.ir(1);
  }

  total(nn: Record<string, Naturaleza>): number {
    return Object.values(nn).reduce((a, d) => a + (d?.n || 0), 0);
  }

  totalValor(nn: Record<string, Naturaleza>): number {
    return Object.values(nn).reduce((a, d) => a + (d?.valor || 0), 0);
  }

  async ir(p: number): Promise<void> {
    if (p < 1 || (this.pages() && p > this.pages())) return;
    this.cargando.set(true);
    try {
      const url = `/dashboard/api/v2/presupuesto/contratos-oficiales/`
        + `?page=${p}&q=${encodeURIComponent(this.q)}`
        + (this.naturaleza() ? `&naturaleza=${this.naturaleza()}` : '');
      const r: any = await firstValueFrom(this.http.get(this.cfg.url(url)));
      this.items.set(r?.items ?? []);
      this.count.set(r?.count ?? 0);
      this.page.set(r?.page ?? 1);
      this.pages.set(r?.pages ?? 1);
      // El panel general viene siempre con las dos, filtre lo que filtre.
      if (r?.por_naturaleza) this.naturalezas.set(r.por_naturaleza);
    } catch {
      this.items.set([]);
    } finally {
      this.cargando.set(false);
    }
  }

  slug(s: string): string {
    return (s || '').toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g, '').replace(/\s+/g, '-');
  }

  /** El formato del módulo: es-CO, en millones. */
  enMillones = enMillones;

  /**
   * Plata que PUEDE no existir.
   *
   * `enMillones` pinta un 0 como «$0», que es correcto cuando el cero está
   * medido. Acá no lo está: `null` significa que SECOP no lo reporta, y
   * decirlo con palabras es la única forma de no afirmar que no se pagó algo
   * que sí se pagó.
   */
  plata(v: number | null | undefined): string {
    return v === null || v === undefined ? 'Sin dato' : enMillones(v);
  }

  ngOnInit(): void {
    this.layout.setBreadcrumb([
      { label: 'Inicio', url: '/' },
      { label: 'Plan de Desarrollo', url: '/plan' },
      { label: 'Gestión', url: '/plan/gestion' },
      { label: 'Contratos' },
    ]);
    this.ir(1);
  }
}
