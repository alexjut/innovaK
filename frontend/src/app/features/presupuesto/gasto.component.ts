import { CommonModule } from '@angular/common';
import { HttpClient } from '@angular/common/http';
import { Component, OnInit, inject, signal } from '@angular/core';
import { firstValueFrom } from 'rxjs';

import { ConfigService } from '../../core/config/config.service';
import { LayoutService } from '../../core/layout/layout.service';
import { enMillones } from './muro/muro-subgrupos.component';
import { errorDeCarga, ErrorDeCarga } from './estado-carga';

interface Eje { clave: string; titulo: string; pregunta: string; columna: string }
interface Grupo {
  grupo: string; compromisos: number; n_crp: number; cdps: number; terceros: number;
  comprometido: number | null; girado: number | null; sin_autorizar: number | null;
  juridicas: number; naturales: number; pct: number | null;
}
interface Respuesta {
  eje: string; ejes: Eje[]; vigencia: number | null; items: Grupo[];
  totales: {
    grupos: number; compromisos: number | null; comprometido: number | null;
    girado: number | null; sin_autorizar: number | null;
  };
  corte_crp: { carga_id: number | null; fecha: string | null; ejercicio: number | null; filas: number | null };
  /** Qué universo del CRP se está mirando. Cuatro pantallas leen la misma
   *  tabla con tres recortes distintos; declararlo evita que dos cifras
   *  legítimas se lean como un descuadre. */
  alcance: {
    filas: number; valor: number;
    filas_vigencias_anteriores: number; valor_vigencias_anteriores: number;
    texto: string;
  };
  vigencias: number[];
}

/**
 * EN QUÉ SE GASTA — el gasto del Fondo por tipo, modalidad o rubro.
 *
 * QUÉ REEMPLAZA. `/plan/conceptos` servía la tabla interna `concepto_gasto`,
 * que tiene UNA fila y es una prueba: «prueba concepto», «pruebas de
 * concepto». Nada la referencia —las 15 filas de `contrato_actividad_plan`
 * traen `concepto_gasto_id` en NULL—, así que era un CRUD sobre un dato de
 * ensayo.
 *
 * Y EL «CONCEPTO DE GASTO» DEL ARCHIVO TAMPOCO SIRVE: solo tiene cuatro
 * valores en 2.630 filas y es el mismo corte que ya hace el rubro, con menos
 * detalle. Lo que sí responde «en qué se gasta» es el tipo de compromiso, y
 * por eso es el eje que abre.
 *
 * TRES EJES PORQUE SON TRES PREGUNTAS:
 *
 *     tipo ....... en qué se gasta        contrato de obra, convenio, CPS…
 *     modalidad .. cómo se contrató       directa, licitación, concurso…
 *     rubro ...... de dónde sale          el proyecto o la bolsa contable
 *
 * NINGUNA DE LAS TRES CIFRAS ES «GASTO EJECUTADO». Comprometido es lo afectado
 * a un contrato, girado es lo AUTORIZADO a girar y la diferencia es lo que
 * todavía no tiene autorización. El pago efectivo no viene en el archivo.
 */
@Component({
  standalone: true,
  selector: 'app-gasto',
  imports: [CommonModule],
  template: `
    <div class="page">
      <header class="page__header">
        <h1><i class="fa fa-tags" aria-hidden="true"></i> En qué se gasta</h1>
        <p class="page__subtitle">
          El gasto del Fondo visto por tipo de compromiso, por modalidad de
          selección o por rubro. Sale del CRP de BogData, no se escribe a mano.
        </p>
      </header>

      @if (cargando()) {
        <p class="muted">Cargando…</p>
      } @else if (!datos()) {
        <div class="ui-empty-state">
          <i class="fa fa-info-circle" aria-hidden="true"></i>
          <p><strong>{{ error()?.titulo || 'No se pudo leer el gasto' }}</strong></p>
          @if (error(); as err) { <p class="muted">{{ err.detalle }}</p> }
        </div>
      } @else {
        <!-- ── Los tres ejes ────────────────────────────────────────── -->
        <div class="ejes" role="tablist">
          @for (e of datos()!.ejes; track e.clave) {
            <button type="button" role="tab" class="eje"
                    [class.eje--on]="datos()!.eje === e.clave"
                    [attr.aria-selected]="datos()!.eje === e.clave"
                    (click)="setEje(e.clave)">
              <span class="eje__t">{{ e.titulo }}</span>
              <span class="eje__p">{{ e.pregunta }}</span>
            </button>
          }
        </div>

        <div class="vigencia" role="group" aria-labelledby="vig-rot">
          <span class="rotulo" id="vig-rot">Año del compromiso</span>
          <button type="button" class="chip" [class.chip--on]="!vigencia()"
                  [attr.aria-pressed]="!vigencia()" (click)="setVigencia(null)">Todos</button>
          @for (v of datos()!.vigencias; track v) {
            <button type="button" class="chip" [class.chip--on]="vigencia() === v"
                    [attr.aria-pressed]="vigencia() === v" (click)="setVigencia(v)">{{ v }}</button>
          }
        </div>

        <!-- ── Los totales, con el rótulo de la cadena ──────────────── -->
        <section class="tot" aria-label="Totales">
          <div class="t"><span class="t__n">{{ datos()!.totales.compromisos | number }}</span>
            <span class="t__l">Compromisos</span></div>
          <div class="t"><span class="t__n">{{ mm(datos()!.totales.comprometido) }}</span>
            <span class="t__l">Comprometido</span></div>
          <div class="t"><span class="t__n">{{ mm(datos()!.totales.girado) }}</span>
            <span class="t__l">Giro autorizado</span></div>
          <div class="t"><span class="t__n">{{ mm(datos()!.totales.sin_autorizar) }}</span>
            <span class="t__l">Sin autorizar</span></div>
        </section>

        <p class="alcance">
          <i class="fa fa-circle-info" aria-hidden="true"></i>
          Comprometido es lo que quedó afectado a un contrato. El giro está
          <strong>autorizado</strong>, que no es el pago hecho: ese eslabón no
          viene en el archivo. Corte del CRP:
          {{ fecha(datos()!.corte_crp.fecha) }}.
        </p>

        <!--
          QUÉ SE ESTÁ MIRANDO. Sin esta línea, esta pantalla dice $226.745 M y
          /plan/fuentes dice $184.839 M del mismo archivo, y la diferencia
          parece un descuadre contable cuando es un filtro de año.
        -->
        <p class="alcance alcance--universo">
          <i class="fa fa-layer-group" aria-hidden="true"></i>
          <span>
            <strong>{{ datos()!.alcance.filas | number }} compromisos</strong>
            por {{ mm(datos()!.alcance.valor) }}.
            {{ datos()!.alcance.texto }}
            @if (datos()!.alcance.filas_vigencias_anteriores) {
              De ese total, {{ mm(datos()!.alcance.valor_vigencias_anteriores) }}
              son de vigencias anteriores al Plan.
            }
          </span>
        </p>

        <!-- ── El desglose ──────────────────────────────────────────── -->
        <div class="tabla-wrap">
          <table class="tabla">
            <caption class="ui-sr-only">Gasto por {{ tituloEje() }}</caption>
            <thead>
              <tr>
                <th scope="col">{{ tituloEje() }}</th>
                <th scope="col" class="num">Compromisos</th>
                <th scope="col" class="num">Comprometido</th>
                <th scope="col" class="peso">Peso</th>
                <th scope="col" class="num">Giro autorizado</th>
                <th scope="col" class="num">Sin autorizar</th>
                <th scope="col">Contratistas</th>
              </tr>
            </thead>
            <tbody>
              @for (g of datos()!.items; track g.grupo) {
                <tr>
                  <th scope="row" class="gr">{{ g.grupo }}</th>
                  <td class="num">{{ g.compromisos | number }}</td>
                  <td class="num">{{ mm(g.comprometido) }}</td>
                  <td class="peso">
                    @if (g.pct !== null) {
                      <span class="peso__v">{{ g.pct }} %</span>
                      <span class="barra" aria-hidden="true">
                        <span class="barra__f" [style.width.%]="g.pct"></span>
                      </span>
                    } @else {
                      <span class="muted">Sin dato</span>
                    }
                  </td>
                  <td class="num">{{ mm(g.girado) }}</td>
                  <td class="num">{{ mm(g.sin_autorizar) }}</td>
                  <td class="qn">
                    @if (g.juridicas) { <span class="q q--j">{{ g.juridicas }} jurídicas</span> }
                    @if (g.naturales) { <span class="q q--n">{{ g.naturales }} naturales</span> }
                    @if (!g.juridicas && !g.naturales) { <span class="muted">Sin clasificar</span> }
                  </td>
                </tr>
              }
            </tbody>
          </table>
        </div>
      }
    </div>
  `,
  styles: [`
    @use '../../../styles/tokens' as *;
    .page__header h1 { margin: 0; color: $color-primary; i { margin-right: $space-2; } }

    .ejes { display: grid; grid-template-columns: repeat(auto-fit, minmax(190px, 1fr));
            gap: $space-2; margin: $space-3 0 $space-2; }
    .eje { text-align: left; cursor: pointer; background: #fff; border: 1px solid rgba(0,0,0,.1);
           border-bottom: 3px solid rgba(0,0,0,.15); border-radius: 8px;
           padding: $space-2 $space-3; display: flex; flex-direction: column; gap: 2px; }
    .eje--on { border-bottom-color: $color-primary; box-shadow: 0 0 0 2px rgba(0,0,0,.08) inset; }
    .eje__t { font-weight: 700; font-size: $font-size-sm; }
    .eje__p { font-size: $font-size-sm; color: $color-text-muted; }

    .vigencia { display: flex; align-items: center; gap: $space-2; margin: $space-2 0;
                flex-wrap: wrap; }
    .rotulo { font-size: $font-size-sm; color: $color-text-muted; }
    .chip { border: 1px solid rgba(0,0,0,.15); background: #fff; border-radius: 999px;
            padding: 2px 12px; font-size: $font-size-sm; cursor: pointer; }
    .chip--on { background: $color-primary; color: #fff; border-color: $color-primary; }

    .tot { display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
           gap: $space-2; margin-bottom: $space-2; }
    .t { border: 1px solid rgba(0,0,0,.1); border-radius: 8px; padding: $space-2 $space-3;
         display: flex; flex-direction: column; }
    .t__n { font-size: 1.2rem; font-weight: 700; font-variant-numeric: tabular-nums; }
    .t__l { font-size: $font-size-sm; color: $color-text-muted; }

    .alcance { margin: 0 0 $space-3; font-size: $font-size-sm; color: $color-text-muted;
               i { margin-right: $space-1; } }
    // QUÉ universo se está mirando. Va con marco porque es la línea que evita
    // que dos cifras legítimas de la misma tabla se lean como un descuadre.
    .alcance--universo {
      display: flex; gap: $space-2; align-items: flex-start;
      padding: $space-2 $space-3; border-radius: $radius-sm;
      background: $color-bg-subtle; border-left: 3px solid $color-border;
      i { margin: 2px 0 0; }
      strong { color: $color-text; }
    }

    .tabla-wrap { overflow-x: auto; }
    .tabla { width: 100%; border-collapse: collapse; font-size: $font-size-sm; }
    .tabla th, .tabla td { padding: $space-2 $space-3; border-bottom: 1px solid rgba(0,0,0,.08);
                           text-align: left; vertical-align: top; }
    .tabla th.num, .tabla td.num { text-align: right; font-variant-numeric: tabular-nums; }
    .gr { font-weight: 600; max-width: 320px; }
    .peso { min-width: 110px; }
    .peso__v { font-variant-numeric: tabular-nums; }
    .barra { display: block; height: 6px; border-radius: 999px; margin-top: 4px;
             background: rgba(0,0,0,.08); overflow: hidden; }
    .barra__f { display: block; height: 100%; background: $color-primary; }
    .qn { white-space: nowrap; }
    .q { display: block; font-size: .72rem; }
    .q--j { color: #7c3aed; }
    .q--n { color: #0e7490; }
    .muted { color: $color-text-muted; }
  `],
})
export class GastoComponent implements OnInit {
  private http = inject(HttpClient);
  private cfg = inject(ConfigService);
  private layout = inject(LayoutService);

  datos = signal<Respuesta | null>(null);
  cargando = signal<boolean>(true);
  error = signal<ErrorDeCarga | null>(null);
  eje = signal<string>('tipo');
  vigencia = signal<number | null>(null);

  async ngOnInit(): Promise<void> {
    this.layout.setBreadcrumb([
      { label: 'Plan de Desarrollo', url: '/plan' },
      { label: 'En qué se gasta' },
    ]);
    await this.cargar();
  }

  setEje(e: string): void { this.eje.set(e); void this.cargar(); }
  setVigencia(v: number | null): void { this.vigencia.set(v); void this.cargar(); }

  tituloEje(): string {
    return this.datos()!.ejes.find((e) => e.clave === this.datos()!.eje)?.titulo ?? '';
  }

  private async cargar(): Promise<void> {
    this.cargando.set(true);
    const p = new URLSearchParams({ eje: this.eje() });
    if (this.vigencia()) p.set('vigencia', String(this.vigencia()));
    try {
      this.datos.set(await firstValueFrom(
        this.http.get<Respuesta>(this.cfg.url(`/presupuesto/api/gasto/?${p}`))));
    } catch (e: any) {
      this.datos.set(null);
      // Nombrar el 403: «no se pudo leer» manda a reintentar, y una falta de
      // permiso no la arregla quien mira la pantalla.
      this.error.set(errorDeCarga(e, 'el gasto'));
    } finally {
      this.cargando.set(false);
    }
  }

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
