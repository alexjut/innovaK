import { CommonModule } from '@angular/common';
import { HttpClient } from '@angular/common/http';
import { Component, OnInit, inject, signal } from '@angular/core';
import { RouterLink } from '@angular/router';
import { firstValueFrom } from 'rxjs';

import { ConfigService } from '../../core/config/config.service';
import { LayoutService } from '../../core/layout/layout.service';
import { enMillones } from './muro/muro-subgrupos.component';
import { errorDeCarga, ErrorDeCarga } from './estado-carga';

interface EnBogData {
  n_interno: number | null; n_posiciones: number;
  comprometido: number | null; girado: number | null;
  n_crp: number; n_compromisos: number; ejercicio: number | null;
  fecha: string | null; proyecto_id: number | null; proyecto_texto: string | null;
  n_proyectos: number; rubro: string | null; por_pagar: boolean;
}
interface EnInnovaK {
  cdp_id: number; numero: number | null; valor: number | null; fecha: string | null;
  descripcion: string | null; proyecto_id: number | null;
  proyecto_codigo: string | null; proyecto_nombre: string | null;
  n_contratos: number; valor_contratos: number | null;
}
interface Fila {
  numero: number | null; bogdata: EnBogData | null; innovak: EnInnovaK | null;
  clase: string; glosa: string; saldo: number | null;
}
interface Clase {
  n: number; glosa: string;
  expedido_innovak: number | null; comprometido_bogdata: number | null;
  girado_bogdata: number | null; saldo: number | null;
}
interface Paso {
  paso: string; que: string; fuente: string;
  valor: number | null; medido: boolean;
}
interface Respuesta {
  items: Fila[]; count: number; page: number; pages: number;
  /** Qué recorte del CRP mira esta pantalla. Ver el comentario del template. */
  alcance: {
    filas: number; valor: number;
    filas_vigencias_anteriores: number; valor_vigencias_anteriores: number;
    texto: string;
  };
  resumen: {
    n: number; por_clase: Record<string, Clase>;
    cobertura: { en_bogdata: number; en_innovak: number; con_saldo: number; con_proyecto: number };
    corte_crp: { carga_id: number | null; fecha: string | null; ejercicio: number | null; filas: number | null };
    cadena: Paso[];
    archivo: { cdps: number; expedido: number | null; anulaciones: number | null;
               comprometido: number | null; girado: number | null; sin_autorizar: number | null };
  };
}
interface Crp {
  numero_crp: number | null; no_compromiso: string | null;
  compromiso_numero: number | null; compromiso_anio: number | null;
  tipo: string | null; beneficiario: string | null; objeto: string | null;
  valor_crp: number | null; anulaciones: number | null;
  comprometido: number | null; girado: number | null; sin_autorizar: number | null;
  rubro: string | null; concepto_gasto: string | null; proyecto_texto: string | null;
  fecha_registro: string | null; por_pagar: boolean; en_el_plan: boolean;
  innovak: { contrato_id: number; valor: number | null } | null;
}
interface Detalle {
  numero_cdp: number; items: Crp[];
  totales: {
    n: number; valor_crp: number | null; anulaciones: number | null;
    comprometido: number | null; girado: number | null;
    sin_autorizar: number | null; en_el_plan: number;
  };
}

/**
 * CDP — la reserva de plata, y los CRP que salen de ella.
 *
 * QUÉ REEMPLAZA. Esta pantalla mostraba CINCO filas y cuatro eran cáscaras sin
 * número, sin fecha y sin valor, creadas solo para poder colgar un contrato.
 * Encima la tabla pedía una columna `proyecto_nombre` que el endpoint nunca
 * mandó, así que Proyecto salía en blanco siempre. Los CDP de verdad son
 * 2.173 y están en BogData, que es quien los expide.
 *
 * LA CADENA, EN SU ORDEN. El CRP va DESPUÉS del contrato, no antes: el CDP
 * reserva, el contrato se firma contra esa reserva y solo entonces el CRP
 * compromete la apropiación.
 *
 *     Apropiación → CDP → proceso → Contrato → CRP → ejecución
 *                 → obligación → giro
 *
 * Se abre una fila y se ve a quién se le comprometió esa plata, por cuánto,
 * cuánto se autorizó girar y si ese compromiso es un contrato que el Plan ya
 * conoce. El CRP es COMPROMISO y no gasto: comprometido, ejecutado, obligado
 * y girado son cuatro cifras distintas y casi nunca coinciden.
 *
 * NO ES 1 A 1. Un CDP puede tener varios CRP (248 los tienen, uno llega a 36)
 * y un contrato puede financiarse desde varios CDP (172 lo hacen, uno desde
 * 13). La pantalla nunca afirma que una fila sea un contrato.
 *
 * EL SALDO SOLO EXISTE CON LAS DOS FUENTES. El archivo del CRP no trae por
 * cuánto se expidió el CDP, solo lo que se comprometió contra él. Así que
 * «cuánto queda libre» no sale de BogData sola ni de innovaK sola. Donde no
 * están las dos, la celda dice que no se puede calcular — que es distinto de
 * decir cero. Y donde sí, la columna se llama «libre» y no «diferencia»: que
 * un CDP de $52 M tenga $2,6 M comprometidos es un CDP con saldo, no un
 * descuadre.
 */
@Component({
  standalone: true,
  selector: 'app-cdps-fuentes',
  imports: [CommonModule, RouterLink],
  template: `
    <div class="page">
      <header class="page__header">
        <h1><i class="fa fa-file-invoice-dollar" aria-hidden="true"></i> CDP</h1>
        <p class="page__subtitle">
          La plata reservada, y los compromisos que salieron de cada reserva.
          Abre un CDP para ver sus CRP y a qué contrato del Plan llegan.
        </p>
      </header>

      <div class="filtros">
        <label class="buscar">
          <span class="ui-sr-only">Buscar por número, proyecto o rubro</span>
          <i class="fa fa-search" aria-hidden="true"></i>
          <input type="search" placeholder="Número de CDP, proyecto, rubro…"
                 [value]="q()" (change)="buscar($any($event.target).value)">
        </label>
      </div>

      @if (cargando()) {
        <p class="muted">Cargando…</p>
      } @else if (!datos()) {
        <div class="ui-empty-state">
          <i class="fa fa-info-circle" aria-hidden="true"></i>
          <p><strong>{{ error()?.titulo || 'No se pudieron leer los CDP' }}</strong></p>
          @if (error(); as err) { <p class="muted">{{ err.detalle }}</p> }
        </div>
      } @else {
        <section class="cortes" aria-label="Alcance de cada fuente">
          <div class="corte">
            <span class="corte__f">BogData · CRP</span>
            <span class="corte__d">
              corte {{ fecha(datos()!.resumen.corte_crp.fecha) }} · ejercicio
              {{ datos()!.resumen.corte_crp.ejercicio ?? 'sin declarar' }} ·
              {{ cob().en_bogdata | number }} CDP
            </span>
          </div>
          <div class="corte">
            <span class="corte__f">innovaK</span>
            <span class="corte__d">
              {{ cob().en_innovak | number }} registrados ·
              {{ cob().con_saldo | number }} con saldo calculable
            </span>
          </div>
        </section>

        <!--
          QUÉ UNIVERSO SE ESTÁ MIRANDO. Esta pantalla y «En qué se gasta»
          publican los mismos $226.745 M; «Fuentes» publica $184.839 M del
          MISMO archivo con otro recorte. Las tres cifras son correctas y lo
          que faltaba era que cada una declarara la suya: sin esto, dos
          pestañas abiertas en el mismo comité parecen un descuadre contable
          de $41.906 M que en realidad es un filtro de año.
        -->
        @if (datos()!.alcance; as al) {
          <p class="universo">
            <i class="fa fa-layer-group" aria-hidden="true"></i>
            <span>
              <strong>{{ al.filas | number }} compromisos</strong> por
              {{ mm(al.valor) }}. {{ al.texto }}
              @if (al.filas_vigencias_anteriores) {
                De ese total, {{ mm(al.valor_vigencias_anteriores) }} son de
                vigencias anteriores al Plan.
              }
            </span>
          </p>
        }

        <!-- La cadena, en su orden. Los escalones sin cifra NO se pintan en
             cero: se dice que este archivo no los trae. -->
        <section class="cadena" aria-label="La cadena de ejecución presupuestal">
          <h2 class="cadena__t">La cadena, en su orden</h2>
          <ol class="pasos">
            @for (p of datos()!.resumen.cadena; track p.paso) {
              <li class="paso" [class.paso--gris]="!p.medido">
                <span class="paso__n">{{ p.paso }}</span>
                <span class="paso__q">{{ p.que }}</span>
                @if (p.medido) {
                  <span class="paso__v">{{ p.paso === 'CDP' ? (p.valor | number) + ' CDP' : mm(p.valor) }}</span>
                } @else {
                  <span class="paso__v paso__v--no">No está en este archivo</span>
                }
                <span class="paso__f">{{ p.fuente }}</span>
              </li>
            }
          </ol>
          <p class="cadena__n">
            El CRP va <strong>después</strong> del contrato: el CDP reserva, el
            contrato se firma contra esa reserva y solo entonces el CRP
            compromete. Y comprometer no es pagar: de los
            {{ mm(datos()!.resumen.archivo.comprometido) }} comprometidos,
            {{ mm(datos()!.resumen.archivo.sin_autorizar) }} todavía no tienen
            giro autorizado.
          </p>
        </section>

        <p class="alcance">
          <i class="fa fa-circle-info" aria-hidden="true"></i>
          El archivo del CRP no trae por cuánto se expidió el CDP, solo lo
          comprometido contra él. Por eso el saldo aparece nada más donde
          alguien registró el CDP en innovaK. Un saldo en blanco no es cero.
        </p>

        <section class="clases" aria-label="Dónde está cada CDP">
          <button type="button" class="clase" [class.clase--on]="!clase()"
                  [attr.aria-pressed]="!clase()" (click)="setClase(null)">
            <span class="clase__n">{{ datos()!.resumen.n | number }}</span>
            <span class="clase__t">Todos</span>
            <span class="clase__g">El universo de las dos fuentes juntas.</span>
          </button>
          @for (c of CLASES; track c) {
            @if (kl(c); as d) {
              <button type="button" [class]="'clase clase--' + c"
                      [class.clase--on]="clase() === c" [attr.aria-pressed]="clase() === c"
                      (click)="setClase(c)">
                <span class="clase__n">{{ d.n | number }}</span>
                <span class="clase__t">{{ TITULO[c] }}</span>
                <span class="clase__g">{{ d.glosa }}</span>
                <span class="clase__p">
                  @if (d.comprometido_bogdata !== null) { Comprometido {{ mm(d.comprometido_bogdata) }} }
                  @if (d.saldo !== null) { · libre {{ mm(d.saldo) }} }
                </span>
              </button>
            }
          }
        </section>

        <p class="conteo">
          {{ datos()!.count | number }} CDP
          @if (clase()) { en «{{ TITULO[clase()!] }}» }
        </p>

        <div class="tabla-wrap">
          <table class="tabla">
            <caption class="ui-sr-only">CDP con lo que dice cada fuente</caption>
            <thead>
              <tr>
                <th scope="col" class="w1"><span class="ui-sr-only">Abrir</span></th>
                <th scope="col">CDP</th>
                <th scope="col">Proyecto / rubro</th>
                <th scope="col" class="num">Expedido<br><small>innovaK</small></th>
                <th scope="col" class="num sep">Comprometido<br><small>BogData</small></th>
                <th scope="col" class="num">Girado<br><small>BogData</small></th>
                <th scope="col" class="num sep">Libre</th>
              </tr>
            </thead>
            <tbody>
              @for (f of datos()!.items; track llave(f)) {
                <tr [class.fila--abierta]="abierto() === f.numero">
                  <td class="w1">
                    @if (f.numero !== null && f.bogdata) {
                      <button type="button" class="abrir" (click)="alternar(f.numero)"
                              [attr.aria-expanded]="abierto() === f.numero"
                              [attr.aria-label]="'Ver los CRP del CDP ' + f.numero">
                        <i class="fa" [class.fa-chevron-down]="abierto() === f.numero"
                           [class.fa-chevron-right]="abierto() !== f.numero" aria-hidden="true"></i>
                      </button>
                    }
                  </td>
                  <th scope="row" class="ct">
                    <span class="ct__r">{{ f.numero ?? 'Sin número' }}</span>
                    <span class="ct__b" [class]="'ct__b ct__b--' + f.clase">{{ TITULO[f.clase] }}</span>
                    @if (f.bogdata) {
                      <span class="ct__c">{{ f.bogdata.n_crp }} CRP</span>
                    }
                  </th>
                  <td class="proy">
                    @if (f.innovak?.proyecto_id) {
                      <a [routerLink]="['/plan/proyectos', f.innovak!.proyecto_id]">
                        {{ f.innovak!.proyecto_codigo }} {{ f.innovak!.proyecto_nombre }}</a>
                    } @else if (f.bogdata?.proyecto_texto) {
                      <span>{{ f.bogdata!.proyecto_texto }}</span>
                    } @else {
                      <span class="muted">Sin proyecto</span>
                    }
                    @if (f.bogdata?.rubro) {
                      <span class="rubro">{{ f.bogdata!.rubro }}</span>
                    }
                    @if (f.innovak?.descripcion && !f.bogdata) {
                      <span class="rubro">{{ f.innovak!.descripcion }}</span>
                    }
                  </td>
                  <td class="num">{{ mm(f.innovak?.valor ?? null) }}</td>
                  <td class="num sep">{{ mm(f.bogdata?.comprometido ?? null) }}</td>
                  <td class="num">{{ mm(f.bogdata?.girado ?? null) }}</td>
                  <td class="num sep">
                    @if (f.saldo !== null) {
                      <span [class.saldo--neg]="f.saldo < 0">{{ mm(f.saldo) }}</span>
                    } @else {
                      <span class="nocmp" [title]="f.glosa">No se puede calcular</span>
                    }
                  </td>
                </tr>

                @if (abierto() === f.numero) {
                  <tr class="detalle">
                    <td colspan="7">
                      @if (cargandoDetalle()) {
                        <p class="muted">Cargando los CRP…</p>
                      } @else {
                      @if (detalle(); as d) {
                        <p class="det__t">
                          {{ d.totales.n }} compromisos ·
                          comprometido {{ mm(d.totales.comprometido) }} ·
                          girado {{ mm(d.totales.girado) }}
                          @if (d.totales.sin_autorizar) { · sin autorizar {{ mm(d.totales.sin_autorizar) }} }
                          · {{ d.totales.en_el_plan }} en el Plan
                        </p>
                        <table class="sub">
                          <thead>
                            <tr>
                              <th scope="col">Compromiso</th>
                              <th scope="col">Beneficiario</th>
                              <th scope="col">Objeto</th>
                              <th scope="col" class="num">Comprometido</th>
                              <th scope="col" class="num">Girado</th>
                              <th scope="col">En el Plan</th>
                            </tr>
                          </thead>
                          <tbody>
                            @for (r of d.items; track r.numero_crp) {
                              <tr>
                                <td>
                                  <span class="cp">{{ r.no_compromiso || '—' }}</span>
                                  <span class="cp__t">{{ r.tipo }}</span>
                                  @if (r.por_pagar) { <span class="cp__o">obligación por pagar</span> }
                                </td>
                                <td>{{ r.beneficiario || 'Sin beneficiario' }}</td>
                                <td class="obj" [title]="r.objeto || ''">{{ r.objeto || '' }}</td>
                                <td class="num">{{ mm(r.comprometido) }}</td>
                                <td class="num">{{ mm(r.girado) }}</td>
                                <td>
                                  @if (r.en_el_plan) {
                                    <a [routerLink]="['/plan/contratos', r.innovak!.contrato_id]">Sí, ver contrato</a>
                                  } @else {
                                    <span class="muted">No está</span>
                                  }
                                </td>
                              </tr>
                            }
                          </tbody>
                        </table>
                      } @else {
                        <p class="muted">Este CDP no tiene CRP en el corte cargado.</p>
                      }
                      }
                    </td>
                  </tr>
                }
              }
            </tbody>
          </table>
        </div>

        @if (datos()!.pages > 1) {
          <nav class="pag" aria-label="Paginación">
            <button type="button" (click)="irA(datos()!.page - 1)" [disabled]="datos()!.page <= 1">Anterior</button>
            <span>Página {{ datos()!.page }} de {{ datos()!.pages }}</span>
            <button type="button" (click)="irA(datos()!.page + 1)" [disabled]="datos()!.page >= datos()!.pages">Siguiente</button>
          </nav>
        }
      }
    </div>
  `,
  styles: [`
    @use '../../../styles/tokens' as *;
    .page__header h1 { margin: 0; color: $color-primary; i { margin-right: $space-2; } }

    .filtros { display: flex; gap: $space-4; margin: $space-3 0; flex-wrap: wrap; }
    .buscar { display: flex; align-items: center; gap: $space-2; flex: 1 1 260px; max-width: 420px;
              border: 1px solid rgba(0,0,0,.15); border-radius: 6px; padding: 2px $space-2; background: #fff;
              i { color: $color-text-muted; }
              input { border: 0; outline: 0; width: 100%; padding: 4px 0; font-size: $font-size-sm; } }

    .cortes { display: flex; gap: $space-4; flex-wrap: wrap; margin-bottom: $space-2;
              padding: $space-2 0; border-bottom: 1px solid rgba(0,0,0,.08); }
    .corte { display: flex; flex-direction: column; }
    .corte__f { font-size: $font-size-sm; font-weight: 600; }
    .corte__d { font-size: $font-size-sm; color: $color-text-muted; }

    .universo {
      display: flex; gap: $space-2; align-items: flex-start;
      margin: 0 0 $space-3; padding: $space-2 $space-3;
      font-size: $font-size-sm; color: $color-text-muted;
      background: $color-bg-subtle; border-left: 3px solid $color-border;
      border-radius: $radius-sm;
      i { margin: 2px 0 0; }
      strong { color: $color-text; }
    }
    .alcance { margin: 0 0 $space-3; font-size: $font-size-sm; color: $color-text-muted;
               i { margin-right: $space-1; } }

    .cadena { margin: $space-3 0; }
    .cadena__t { margin: 0 0 $space-2; font-size: $font-size-base; }
    .pasos { list-style: none; display: flex; gap: $space-2; margin: 0; padding: 0;
             overflow-x: auto; }
    .paso { flex: 1 0 150px; border: 1px solid rgba(0,0,0,.1); border-radius: 8px;
            padding: $space-2; display: flex; flex-direction: column; gap: 2px;
            border-top: 3px solid $color-primary; background: #fff; }
    .paso--gris { border-top-color: rgba(0,0,0,.18); background: rgba(0,0,0,.02); }
    .paso__n { font-weight: 700; font-size: $font-size-sm; }
    .paso__q { font-size: .72rem; color: $color-text-muted; }
    .paso__v { font-weight: 600; font-variant-numeric: tabular-nums; margin-top: 2px; }
    .paso__v--no { font-weight: 400; font-style: italic; color: $color-text-muted;
                   font-size: .72rem; }
    .paso__f { font-size: .72rem; color: $color-text-muted; }
    .cadena__n { margin: $space-2 0 0; font-size: $font-size-sm; color: $color-text-muted; }

    .clases { display: grid; grid-template-columns: repeat(auto-fit, minmax(210px, 1fr));
              gap: $space-2; margin-bottom: $space-3; }
    .clase { text-align: left; cursor: pointer; background: #fff; border: 1px solid rgba(0,0,0,.1);
             border-left: 4px solid rgba(0,0,0,.2); border-radius: 8px; padding: $space-2 $space-3;
             display: flex; flex-direction: column; gap: 2px; }
    .clase--on { box-shadow: 0 0 0 2px rgba(0,0,0,.12) inset; }
    .clase--con_respaldo { border-left-color: #15803d; }
    .clase--solo_bogdata { border-left-color: #0e7490; }
    .clase--solo_innovak { border-left-color: #b45309; }
    .clase--sin_numero { border-left-color: #b91c1c; }
    .clase__n { font-size: 1.35rem; font-weight: 700; font-variant-numeric: tabular-nums; }
    .clase__t { font-size: $font-size-sm; font-weight: 600; }
    .clase__g, .clase__p { font-size: $font-size-sm; color: $color-text-muted; }

    .conteo { margin: 0 0 $space-2; font-size: $font-size-sm; color: $color-text-muted; }

    .tabla-wrap { overflow-x: auto; }
    .tabla { width: 100%; border-collapse: collapse; font-size: $font-size-sm; }
    .tabla th, .tabla td { padding: $space-2 $space-3; border-bottom: 1px solid rgba(0,0,0,.08);
                           text-align: left; vertical-align: top; }
    .tabla thead th { small { font-weight: 400; color: $color-text-muted; } }
    .tabla th.num, .tabla td.num { text-align: right; font-variant-numeric: tabular-nums; }
    .tabla .sep { border-left: 2px solid rgba(0,0,0,.08); }
    .w1 { width: 32px; padding-right: 0 !important; }
    .abrir { border: 0; background: none; cursor: pointer; color: $color-text-muted; padding: 2px 4px; }
    .fila--abierta { background: rgba(0,0,0,.02); }
    .ct { font-weight: 400; }
    .ct__r { display: block; font-weight: 700; }
    .ct__c { display: block; color: $color-text-muted; }
    .ct__b { display: inline-block; margin-top: 2px; font-size: .72rem; padding: 0 6px;
             border-radius: 999px; background: rgba(0,0,0,.06); }
    .ct__b--con_respaldo { background: rgba(21,128,61,.12); }
    .ct__b--sin_numero { background: rgba(185,28,28,.12); }
    .proy a { font-weight: 600; }
    .rubro { display: block; color: $color-text-muted; }
    .saldo--neg { color: #b91c1c; font-weight: 700; }
    .nocmp { color: $color-text-muted; font-style: italic; cursor: help; }
    .muted { color: $color-text-muted; }

    .detalle > td { background: rgba(0,0,0,.02); }
    .det__t { margin: 0 0 $space-2; font-size: $font-size-sm; font-weight: 600; }
    .sub { width: 100%; border-collapse: collapse; font-size: $font-size-sm; }
    .sub th, .sub td { padding: 4px $space-2; border-bottom: 1px solid rgba(0,0,0,.06);
                       text-align: left; vertical-align: top; }
    .sub th.num, .sub td.num { text-align: right; font-variant-numeric: tabular-nums; }
    .obj { max-width: 340px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
    .cp { display: block; font-weight: 600; }
    .cp__t, .cp__o { display: block; color: $color-text-muted; font-size: .72rem; }

    .pag { display: flex; align-items: center; gap: $space-3; margin-top: $space-3;
           font-size: $font-size-sm;
           button { border: 1px solid rgba(0,0,0,.15); background: #fff; border-radius: 6px;
                    padding: 4px 12px; cursor: pointer; &:disabled { opacity: .45; cursor: default; } } }
  `],
})
export class CdpsFuentesComponent implements OnInit {
  private http = inject(HttpClient);
  private cfg = inject(ConfigService);
  private layout = inject(LayoutService);

  readonly CLASES = ['con_respaldo', 'solo_bogdata', 'solo_innovak', 'sin_numero'];

  readonly TITULO: Record<string, string> = {
    con_respaldo: 'Con respaldo',
    solo_bogdata: 'Solo en BogData',
    solo_innovak: 'Solo en innovaK',
    sin_numero: 'Sin número',
  };

  datos = signal<Respuesta | null>(null);
  cargando = signal<boolean>(true);
  error = signal<ErrorDeCarga | null>(null);
  clase = signal<string | null>(null);
  q = signal<string>('');
  pagina = signal<number>(1);

  abierto = signal<number | null>(null);
  detalle = signal<Detalle | null>(null);
  cargandoDetalle = signal<boolean>(false);

  async ngOnInit(): Promise<void> {
    this.layout.setBreadcrumb([
      { label: 'Plan de Desarrollo', url: '/plan' },
      { label: 'CDP' },
    ]);
    await this.cargar();
  }

  setClase(c: string | null): void {
    this.clase.set(this.clase() === c ? null : c);
    this.pagina.set(1); this.cerrar(); void this.cargar();
  }
  buscar(texto: string): void { this.q.set(texto); this.pagina.set(1); this.cerrar(); void this.cargar(); }
  irA(p: number): void { this.pagina.set(p); this.cerrar(); void this.cargar(); }

  /** Las cáscaras no tienen número, así que el número no sirve de llave para
   *  `track`. Se usa el id interno cuando lo hay. */
  llave(f: Fila): string {
    return f.numero !== null ? `n${f.numero}` : `i${f.innovak?.cdp_id}`;
  }

  private cerrar(): void { this.abierto.set(null); this.detalle.set(null); }

  async alternar(numero: number): Promise<void> {
    if (this.abierto() === numero) { this.cerrar(); return; }
    this.abierto.set(numero);
    this.detalle.set(null);
    this.cargandoDetalle.set(true);
    try {
      this.detalle.set(await firstValueFrom(
        this.http.get<Detalle>(this.cfg.url(`/presupuesto/api/cdps/fuentes/${numero}/`))));
    } catch {
      this.detalle.set(null);
    } finally {
      this.cargandoDetalle.set(false);
    }
  }

  private async cargar(): Promise<void> {
    this.cargando.set(true);
    const p = new URLSearchParams({ page: String(this.pagina()), por: '25' });
    if (this.clase()) p.set('clase', this.clase()!);
    if (this.q()) p.set('q', this.q());
    try {
      this.datos.set(await firstValueFrom(
        this.http.get<Respuesta>(this.cfg.url(`/presupuesto/api/cdps/fuentes/?${p}`))));
    } catch (e: any) {
      this.datos.set(null);
      this.error.set(errorDeCarga(e, 'los CDP'));
    } finally {
      this.cargando.set(false);
    }
  }

  cob() { return this.datos()!.resumen.cobertura; }
  kl(c: string): Clase | null { return this.datos()!.resumen.por_clase[c] ?? null; }

  /** `null` es «esta fuente no lo cubre», nunca «$0». */
  mm(v: number | null | undefined): string {
    return v === null || v === undefined ? 'Sin dato' : enMillones(v);
  }

  fecha(iso: string | null): string {
    if (!iso) return 'sin corte declarado';
    return new Date(iso).toLocaleDateString('es-CO', {
      year: 'numeric', month: 'long', day: 'numeric',
    });
  }
}
