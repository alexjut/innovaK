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
  /** Las señales de la fila. Los borradores NO cuentan como cambios en firme. */
  n_modificaciones: number; n_mod_en_firme: number; n_cesiones: number;
  dias_adicionados: number; fecha_fin: string | null;
  /** Negativo = ya venció. `null` = sin fecha de fin. */
  dias_para_vencer: number | null;
}

/** Un valor de faceta con su conteo. Es lo que pinta cada tag. */
interface Faceta { valor: string; n: number; }

interface Kpis {
  contratos: number; valor_total: number;
  con_pago: number; pct_con_pago: number | null; pago_sin_dato: number;
  denominador_pago: number;
  pct_plata_con_dato: number | null;
  modificados: number; cedidos: number;
  prorrogados: number; dias_adicionados_total: number;
  vencen_30: number;
  enlazados_plan: number; valor_enlazado: number;
  corte: string;
}

/**
 * Las seis cifras sobre el UNIVERSO, para acompañar a las filtradas.
 *
 * Solo seis y no las trece: son las que se pintan. Traer del servidor números
 * que nadie muestra es ancho de banda y una invitación a usarlos mal.
 */
interface Universo {
  contratos: number; valor_total: number; con_pago: number;
  modificados: number; prorrogados: number; vencen_30: number;
  anio_desde: number;
}

/** Los KPIs que además filtran. El `null` es «ninguno», o sea sin filtro. */
type KpiFiltro = 'con_pago' | 'modificados' | 'prorrogados' | 'vencen_30'
               | 'enlazados_plan' | null;

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

      <!-- (A) LOS SEIS KPIs, Y CADA UNO ES UN FILTRO.
           Aplican el MISMO predicado que los cuenta en el servidor: pulsar
           «Prorrogados» deja la lista en los mismos que dice el recuadro. Si
           el front los recalculara, el recuadro diría una cosa y la lista
           otra, y nadie sabria cual creer. -->
      @if (kpis(); as k) {
        <div class="kpis" role="group"
             [attr.aria-label]="hayFiltro()
               ? 'Cifras de los contratos filtrados. Cada una filtra la lista'
               : 'Cifras de los contratos. Cada una filtra la lista'">
          <div class="kpi kpi--quieto">
            <span class="kpi__n">{{ k.contratos | number }}</span>
            <span class="kpi__l">Contratos</span>
            <!-- Con filtro, la cifra grande es la FILTRADA y el total va aquí.
                 Antes la grande era el total mientras la lista mostraba otra
                 cosa: lo reportaron como confusión y tenían razón. -->
            @if (hayFiltro()) {
              <span class="kpi__d kpi__d--filtro">de {{ universo()?.contratos | number }} en total</span>
            } @else {
              <span class="kpi__d">en el espejo de SECOP</span>
            }
          </div>
          <div class="kpi kpi--quieto">
            <span class="kpi__n">{{ enMillones(k.valor_total) }}</span>
            <span class="kpi__l">Valor total</span>
            @if (hayFiltro()) {
              <span class="kpi__d kpi__d--filtro">de {{ enMillones(universo()?.valor_total ?? 0) }} en total</span>
            } @else {
              <span class="kpi__d">suma de lo adjudicado</span>
            }
          </div>

          <button type="button" class="kpi kpi--btn" role="switch"
                  [class.kpi--on]="kpi() === 'con_pago'"
                  [attr.aria-pressed]="kpi() === 'con_pago'"
                  (click)="filtrarKpi('con_pago')">
            <span class="kpi__n">{{ k.pct_con_pago ?? '—' }}%</span>
            <span class="kpi__l">Con pago reportado</span>
            <!-- El denominador NO es decorativo: sin el, un 92 % se lee como
                 «92 % pagado», que es otra cosa y la pantalla no la afirma. -->
            <span class="kpi__d">
              {{ k.con_pago | number }} de {{ k.denominador_pago | number }} con dato
            </span>
          </button>

          <button type="button" class="kpi kpi--btn" role="switch"
                  [class.kpi--on]="kpi() === 'modificados'"
                  [attr.aria-pressed]="kpi() === 'modificados'"
                  (click)="filtrarKpi('modificados')">
            <span class="kpi__n">{{ k.modificados | number }}</span>
            <span class="kpi__l">Modificados</span>
            <span class="kpi__d" [class.kpi__d--filtro]="hayFiltro()">
                {{ k.cedidos | number }} con cesión@if (hayFiltro()) { · de {{ universo()?.modificados | number }} }
              </span>
          </button>

          <button type="button" class="kpi kpi--btn" role="switch"
                  [class.kpi--on]="kpi() === 'prorrogados'"
                  [attr.aria-pressed]="kpi() === 'prorrogados'"
                  (click)="filtrarKpi('prorrogados')">
            <span class="kpi__n">{{ k.prorrogados | number }}</span>
            <span class="kpi__l">Prorrogados</span>
            <span class="kpi__d" [class.kpi__d--filtro]="hayFiltro()">
                {{ k.dias_adicionados_total | number }} días@if (hayFiltro()) { · de {{ universo()?.prorrogados | number }} }
              </span>
          </button>

          <button type="button" class="kpi kpi--btn kpi--aviso" role="switch"
                  [class.kpi--on]="kpi() === 'vencen_30'"
                  [attr.aria-pressed]="kpi() === 'vencen_30'"
                  (click)="filtrarKpi('vencen_30')">
            <span class="kpi__n">{{ k.vencen_30 | number }}</span>
            <span class="kpi__l">Vencen en 30 días</span>
            <span class="kpi__d" [class.kpi__d--filtro]="hayFiltro()">
                al {{ k.corte }}@if (hayFiltro()) { · de {{ universo()?.vencen_30 | number }} }
              </span>
          </button>
        </div>
      }

      <!-- (B) LOS FILTROS, COMO TAGS Y NO COMO DESPLEGABLES.
           Cada tag lleva su conteo, que sale del servidor sobre el universo
           del buscador y NO sobre la página: un número que cambia al pasar de
           página no sirve para decidir por dónde filtrar. Un valor sin filas
           no se ofrece. -->
      @if (facetas(); as f) {
        <section class="filtros" aria-label="Filtros">
          @for (g of GRUPOS; track g.clave) {
            @if (f[g.clave]?.length) {
              <div class="filtros__fila">
                <span class="filtros__rotulo">{{ g.etiqueta }}</span>
                @for (v of f[g.clave]; track v.valor) {
                  <button type="button" class="tag"
                          [class.tag--on]="activo(g.clave) === v.valor"
                          [attr.aria-pressed]="activo(g.clave) === v.valor"
                          (click)="filtrarFaceta(g.clave, v.valor)">
                    {{ v.valor }}<span class="tag__n">{{ v.n | number }}</span>
                  </button>
                }
              </div>
            }
          }

          <div class="filtros__fila">
            <span class="filtros__rotulo">Enlace al Plan</span>
            <button type="button" class="tag tag--plan"
                    [class.tag--on]="kpi() === 'enlazados_plan'"
                    [attr.aria-pressed]="kpi() === 'enlazados_plan'"
                    (click)="filtrarKpi('enlazados_plan')">
              Enlazados al Plan<span class="tag__n">{{ kpis()?.enlazados_plan | number }}</span>
            </button>
          </div>

          <div class="filtros__fila">
            <span class="filtros__rotulo">Orden</span>
            @for (o of ORDENES; track o.clave) {
              <button type="button" class="tag"
                      [class.tag--on]="orden() === o.clave"
                      [attr.aria-pressed]="orden() === o.clave"
                      (click)="ordenarPor(o.clave)">
                {{ o.etiqueta }}
                @if (orden() === o.clave) {
                  <span class="tag__dir">{{ direccion() === 'desc' ? '↓' : '↑' }}</span>
                }
              </button>
            }
          </div>

          <!-- (D) Quitar todo de una. Solo aparece si hay algo puesto. -->
          @if (hayFiltros()) {
            <button type="button" class="limpiar" (click)="limpiar()">
              <i class="fa fa-xmark" aria-hidden="true"></i> Quitar los filtros
            </button>
          }
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

                <!-- (C) LAS SEÑALES. Solo se pintan cuando existen: la fila
                     no se llena de pastillas apagadas. -->
                @if (ct.n_modificaciones) {
                  <span class="sig" [attr.title]="tituloModif(ct)">
                    {{ ct.n_modificaciones }}
                    {{ ct.n_modificaciones === 1 ? 'modificación' : 'modificaciones' }}
                    @if (ct.n_mod_en_firme < ct.n_modificaciones) {
                      <span class="sig__bo">{{ ct.n_modificaciones - ct.n_mod_en_firme }} en trámite</span>
                    }
                  </span>
                }
                @if (ct.dias_adicionados > 0) {
                  <span class="sig sig--plazo"
                        title="El contrato ya no termina cuando se firmó: se le sumaron días">
                    +{{ ct.dias_adicionados | number }} días
                  </span>
                }
                @if (ct.n_cesiones) {
                  <span class="sig sig--ces"
                        title="Cambió quién ejecuta. SECOP no publica el contratista anterior">
                    {{ ct.n_cesiones === 1 ? 'Cedido' : ct.n_cesiones + ' cesiones' }}
                  </span>
                }
                <!-- El aviso de vencimiento sale de la FECHA y no del estado:
                     medido, 1.526 contratos ya pasaron su fecha de fin sin
                     estar declarados cerrados. El estado va atrasado; la
                     fecha, no. -->
                @if (porVencer(ct)) {
                  <span class="sig sig--vence"
                        [title]="'Termina el ' + ct.fecha_fin">
                    Vence en {{ ct.dias_para_vencer }}
                    {{ ct.dias_para_vencer === 1 ? 'día' : 'días' }}
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

    /* ── (A) Los seis KPIs. Los dos primeros son cifra; los cuatro
       siguientes son BOTONES, y se ven como botones a propósito: si filtran,
       hay que poder adivinarlo sin pulsarlos. ── */
    .kpis {
      display: grid; grid-template-columns: repeat(auto-fit, minmax(146px, 1fr));
      gap: $space-2; margin: $space-3 0;
    }
    .kpi {
      background: #fff; border: 1px solid rgba(0,0,0,.1); border-radius: 10px;
      border-top: 2.5px solid rgba(0,0,0,.12);
      padding: $space-2 $space-3; text-align: left; display: flex;
      flex-direction: column; gap: 1px;
    }
    /* La línea de contexto cuando hay filtro. Se distingue de la descripción
       normal para que se lea como una comparación y no como una etiqueta. */
    .kpi__d--filtro { font-variant-numeric: tabular-nums; opacity: .85; }
    .kpis--filtrado .kpi__n { color: var(--acento, #1d4ed8); }

    .kpi__n {
      font-size: 1.32rem; font-weight: 800; line-height: 1.12;
      font-variant-numeric: tabular-nums; color: $color-text;
    }
    .kpi__l { font-size: $font-size-sm; font-weight: 600; color: $color-text; }
    .kpi__d { font-size: 10.5px; color: $color-text-muted; line-height: 1.3; }
    .kpi--quieto { border-top-color: $color-neutral-600; }
    .kpi--btn {
      cursor: pointer; font-family: inherit; border-top-color: #0F766E;
      transition: transform .12s ease, box-shadow .12s ease;
      &:hover { transform: translateY(-1px); box-shadow: 0 3px 10px rgba(0,0,0,.08); }
      &:focus-visible { outline: 3px solid rgba(214,0,28,.55); outline-offset: 2px; }
    }
    .kpi--btn .kpi__n { color: #0F766E; }
    .kpi--aviso { border-top-color: $color-warning-hondo; }
    .kpi--aviso .kpi__n { color: $color-warning-hondo; }
    .kpi--on {
      background: rgba(13,148,136,.07);
      box-shadow: 0 0 0 2px #0F766E inset;
    }
    .kpi--aviso.kpi--on { background: rgba(245,158,11,.1); box-shadow: 0 0 0 2px $color-warning-hondo inset; }

    /* ── (B) Los filtros como TAGS. Cada uno lleva su conteo; pulsar el
       activo lo quita, que es lo que se espera de un tag. ── */
    .filtros { margin: $space-3 0; display: flex; flex-direction: column; gap: $space-2; }
    .filtros__fila { display: flex; align-items: baseline; gap: 6px; flex-wrap: wrap; }
    .filtros__rotulo {
      flex: 0 0 5.6rem; font-size: 10px; font-weight: $font-weight-semibold;
      letter-spacing: .06em; text-transform: uppercase; color: $color-neutral-600;
    }
    .tag {
      display: inline-flex; align-items: baseline; gap: 5px;
      padding: 3px 10px; border-radius: 9999px; cursor: pointer;
      font-size: $font-size-sm; font-family: inherit;
      background: #fff; color: $color-neutral-800;
      border: 1px solid $color-border-strong;
      &:hover { border-color: #0F766E; color: #0F766E; }
      &:focus-visible { outline: 3px solid rgba(214,0,28,.55); outline-offset: 2px; }
    }
    .tag--on { background: #0F766E; color: #fff; border-color: #0F766E; }
    .tag__n {
      font-size: 10px; font-weight: $font-weight-bold;
      font-variant-numeric: tabular-nums; opacity: .72;
    }
    .tag--on .tag__n { opacity: .9; }
    .tag__dir { font-size: 11px; font-weight: 700; }
    .tag--plan { border-color: rgba(13,148,136,.4); }
    .limpiar {
      align-self: flex-start; margin-top: 2px;
      background: transparent; border: 0; cursor: pointer; font-family: inherit;
      font-size: $font-size-sm; color: $color-primary; padding: 2px 0;
      i { margin-right: 4px; }
      &:hover { text-decoration: underline; }
    }

    /* ── (C) Las señales de la fila ── */
    .sig {
      display: inline-flex; align-items: baseline; gap: 5px;
      border-radius: 999px; padding: 1px 9px; font-size: .72rem; white-space: nowrap;
      background: rgba(0,0,0,.055); color: $color-neutral-800; cursor: help;
    }
    .sig__bo {
      font-size: 9.5px; font-style: italic; color: $color-warning-hondo;
    }
    .sig--plazo { background: rgba(124,58,237,.11); color: #5b21b6; }
    .sig--ces { background: rgba(14,116,144,.12); color: #0e7490; }
    .sig--vence { background: rgba(245,158,11,.16); color: #92400e; font-weight: 600; }

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

  kpis = signal<Kpis | null>(null);
  facetas = signal<Record<string, Faceta[]> | null>(null);

  /**
   * El universo y la bandera de filtro, los dos del SERVIDOR.
   *
   * `hayFiltro` podría deducirse de las cinco señales locales, pero entonces la
   * pantalla y el servidor podrían discrepar —el servidor ignora un filtro que
   * no reconoce, y la pantalla seguiría creyéndolo activo—. Manda el servidor,
   * que es el que contó.
   */
  universo = signal<Universo | null>(null);
  hayFiltro = signal<boolean>(false);

  /** El KPI activo. Es un filtro, no una pestaña: solo uno a la vez. */
  kpi = signal<KpiFiltro>(null);
  anio = signal<string | null>(null);
  estado = signal<string | null>(null);
  modalidad = signal<string | null>(null);
  orden = signal<string>('valor');
  direccion = signal<'asc' | 'desc'>('desc');

  readonly GRUPOS = [
    { clave: 'anio', etiqueta: 'Año' },
    { clave: 'estado', etiqueta: 'Estado' },
    { clave: 'modalidad', etiqueta: 'Modalidad' },
  ];
  readonly ORDENES = [
    { clave: 'valor', etiqueta: 'Valor' },
    { clave: 'fin', etiqueta: 'Fecha de fin' },
    { clave: 'dias', etiqueta: 'Días adicionados' },
    { clave: 'firma', etiqueta: 'Fecha de firma' },
  ];

  buscar(): void { this.ir(1); }

  activo(clave: string): string | null {
    return clave === 'anio' ? this.anio()
         : clave === 'estado' ? this.estado()
         : clave === 'modalidad' ? this.modalidad() : null;
  }

  /** Pulsar el tag activo lo quita. Es lo que la gente espera de un tag. */
  filtrarFaceta(clave: string, valor: string): void {
    const sig = clave === 'anio' ? this.anio
              : clave === 'estado' ? this.estado : this.modalidad;
    sig.set(sig() === valor ? null : valor);
    this.ir(1);
  }

  filtrarKpi(k: Exclude<KpiFiltro, null>): void {
    this.kpi.set(this.kpi() === k ? null : k);
    this.ir(1);
  }

  /** Dos pulsaciones sobre el mismo orden invierten la dirección. */
  ordenarPor(o: string): void {
    if (this.orden() === o) {
      this.direccion.set(this.direccion() === 'desc' ? 'asc' : 'desc');
    } else {
      this.orden.set(o);
      this.direccion.set('desc');
    }
    this.ir(1);
  }

  hayFiltros(): boolean {
    return !!(this.kpi() || this.anio() || this.estado() || this.modalidad()
              || this.naturaleza() || this.q);
  }

  limpiar(): void {
    this.kpi.set(null); this.anio.set(null); this.estado.set(null);
    this.modalidad.set(null); this.naturaleza.set(null); this.q = '';
    this.orden.set('valor'); this.direccion.set('desc');
    this.ir(1);
  }

  /** Los borradores se dicen, no se suman: «En Edición» no es un cambio hecho. */
  tituloModif(c: Contrato): string {
    const base = `${c.n_mod_en_firme} en firme de ${c.n_modificaciones}`;
    return c.n_mod_en_firme < c.n_modificaciones
      ? `${base}. Las que faltan son borradores o trámites que SECOP publica: no son cambios hechos.`
      : base;
  }

  /** La ventana de aviso. Un contrato ya vencido no «vence en N días». */
  porVencer(c: Contrato): boolean {
    const d = c.dias_para_vencer;
    return d !== null && d >= 0 && d <= 30;
  }

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
      const par = new URLSearchParams({
        page: String(p), q: this.q,
        orden: this.orden(), direccion: this.direccion(),
      });
      for (const [k, v] of Object.entries({
        naturaleza: this.naturaleza(), anio: this.anio(),
        estado: this.estado(), modalidad: this.modalidad(), kpi: this.kpi(),
      })) {
        if (v) par.set(k, String(v));
      }
      const url = `/dashboard/api/v2/presupuesto/contratos-oficiales/?${par}`;
      const r: any = await firstValueFrom(this.http.get(this.cfg.url(url)));
      this.items.set(r?.items ?? []);
      this.count.set(r?.count ?? 0);
      this.page.set(r?.page ?? 1);
      this.pages.set(r?.pages ?? 1);
      // Los KPIs vienen sobre LO FILTRADO, para que la cifra grande coincida
      // con la lista. El universo viene al lado y se pinta como contexto.
      //
      // Hasta el 2026-10-15 venían solo sobre el universo, a propósito: «un
      // recuadro que cambia al filtrar no sirve para decidir por dónde
      // filtrar». El argumento seguía siendo bueno y la consecuencia en uso
      // fue peor: el recuadro decía 3.203 sobre una lista de 1.135 y nadie
      // sabía cuál de los dos creer. Lo reportaron como confusión.
      if (r?.kpis) this.kpis.set(r.kpis);
      if (r?.universo) this.universo.set(r.universo);
      this.hayFiltro.set(!!r?.hay_filtro);
      // Las facetas siguen sobre el universo: su conteo es lo que dice cuántos
      // hay si uno pulsa ese tag, así que no puede depender de lo ya filtrado.
      if (r?.facetas) this.facetas.set(r.facetas);
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
