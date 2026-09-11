import { CommonModule } from '@angular/common';
import { HttpClient } from '@angular/common/http';
import { Component, OnInit, inject, signal } from '@angular/core';
import { RouterLink } from '@angular/router';
import { firstValueFrom } from 'rxjs';

import { ConfigService } from '../../core/config/config.service';
import { LayoutService } from '../../core/layout/layout.service';
import { enMillones } from './muro/muro-subgrupos.component';

interface EnSecop {
  referencia: string | null; tipo: string | null; estado: string | null;
  objeto: string | null; contratista: string | null; documento: string | null;
  valor: number | null; pagado: number | null; url: string | null; n_filas: number;
}
interface EnBogData {
  no_compromiso: string | null; tipo: string | null; contratista: string | null;
  documentos: string[]; anio: number; comprometido: number | null; girado: number | null;
  rubro: string | null; ejercicio: number | null; por_pagar: boolean; n_crp: number;
}
interface EnInnovaK {
  contrato_id: number | null; valor: number | null; n_proyectos: number;
  proyecto_id: number | null; proyecto_codigo: string | null; proyecto_nombre: string | null;
}
interface Fila {
  numero: number; anio: number; referencia: string;
  secop: EnSecop | null; bogdata: EnBogData | null; innovak: EnInnovaK | null;
  en_el_plan: boolean; clase: string; glosa: string; diferencia: number | null;
}
interface Clase {
  n: number; glosa: string;
  valor_secop: number | null;
  comprometido_bogdata: number | null;
  girado_bogdata: number | null;
}
interface Respuesta {
  items: Fila[]; count: number; page: number; pages: number;
  vigencias: number[];
  resumen: {
    n: number;
    por_clase: Record<string, Clase>;
    cobertura: {
      en_secop: number; en_bogdata: number; en_innovak: number;
      en_el_plan: number; comparables: number; coinciden: number;
    };
    corte_crp: { carga_id: number | null; fecha: string | null; ejercicio: number | null; filas: number | null };
  };
}

/**
 * CONTRATOS POR FUENTE — el mismo contrato visto por SECOP, BogData e innovaK.
 *
 * LO QUE PIDIÓ ALEX, TEXTUAL: «mostrando las diferentes fuentes para saber
 * dónde está el error según la data». Por eso acá no hay una columna «valor»
 * con la cifra que el sistema prefiere: hay una columna por fuente, con el
 * nombre de la fuente encima, y las tres se pueden leer de corrido.
 *
 * LA CELDA VACÍA DICE «NO LO VE», NO «CERO». Es la misma regla de la casa que
 * en el resto del módulo, y acá es más importante que en ninguna otra
 * pantalla: media docena de discrepancias de septiembre salieron de leer el
 * cero de una fuente como una medición. En particular el pagado de SECOP, que
 * nunca llega en nulo aunque nadie lo haya cargado.
 *
 * LA DIFERENCIA SOLO SE PINTA CUANDO SE PUEDE RESTAR. Fuera del ejercicio del
 * corte del CRP, o cuando el contratista no coincide entre las dos fuentes, la
 * columna dice por qué no hay resta en vez de mostrar un número que no
 * significa nada. El motivo lo escribe el servicio, no esta pantalla.
 */
@Component({
  standalone: true,
  selector: 'app-contratos-fuentes',
  imports: [CommonModule, RouterLink],
  template: `
    <div class="page">
      <header class="page__header">
        <h1><i class="fa fa-scale-balanced" aria-hidden="true"></i> Contratos por fuente</h1>
        <p class="page__subtitle">
          El mismo contrato como lo ve SECOP, como lo ve BogData y como lo ve
          innovaK. Donde las cifras no son comparables, la pantalla lo dice en
          vez de restarlas.
        </p>
      </header>

      <!-- ── Filtros ────────────────────────────────────────────────── -->
      <div class="filtros">
        <div class="grupo" role="group" aria-labelledby="vig-rot">
          <span class="rotulo" id="vig-rot">Vigencia</span>
          <button type="button" class="chip" [class.chip--on]="!vigencia()"
                  [attr.aria-pressed]="!vigencia()" (click)="setVigencia(null)">Todas</button>
          @for (v of vigencias(); track v) {
            <button type="button" class="chip" [class.chip--on]="vigencia() === v"
                    [attr.aria-pressed]="vigencia() === v" (click)="setVigencia(v)">{{ v }}</button>
          }
        </div>
        <label class="buscar">
          <span class="ui-sr-only">Buscar por referencia, contratista u objeto</span>
          <i class="fa fa-search" aria-hidden="true"></i>
          <input type="search" placeholder="Referencia, contratista u objeto…"
                 [value]="q()" (change)="buscar($any($event.target).value)">
        </label>
      </div>

      @if (cargando()) {
        <p class="muted">Cargando…</p>
      } @else if (!datos()) {
        <div class="ui-empty-state">
          <i class="fa fa-info-circle" aria-hidden="true"></i>
          <p>No se pudieron leer los contratos.</p>
        </div>
      } @else {
        <!-- ── De cuándo es cada fuente ─────────────────────────────── -->
        <section class="cortes" aria-label="Alcance de cada fuente">
          <div class="corte">
            <span class="corte__f">SECOP II</span>
            <span class="corte__d">{{ cob().en_secop | number }} contratos en el espejo</span>
          </div>
          <div class="corte">
            <span class="corte__f">BogData · CRP</span>
            <span class="corte__d">
              corte {{ fecha(datos()!.resumen.corte_crp.fecha) }} · ejercicio
              {{ datos()!.resumen.corte_crp.ejercicio ?? 'sin declarar' }}
            </span>
          </div>
          <div class="corte">
            <span class="corte__f">innovaK</span>
            <span class="corte__d">{{ cob().en_el_plan | number }} colgados del Plan</span>
          </div>
        </section>

        <p class="alcance">
          <i class="fa fa-circle-info" aria-hidden="true"></i>
          El archivo del CRP es un corte de un solo ejercicio. Para un contrato
          de {{ datos()!.resumen.corte_crp.ejercicio }} su cifra es el compromiso del año y se puede
          poner al lado de SECOP; para uno anterior es solo el saldo que quedó
          como obligación por pagar, y por eso no se resta.
        </p>

        <!-- ── Dónde está cada contrato ─────────────────────────────── -->
        <section class="clases" aria-label="Concordancia entre las fuentes">
          <button type="button" class="clase" [class.clase--on]="!clase()"
                  [attr.aria-pressed]="!clase()" (click)="setClase(null)">
            <span class="clase__n">{{ datos()!.resumen.n | number }}</span>
            <span class="clase__t">Todos</span>
            <span class="clase__g">El universo de las tres fuentes juntas.</span>
          </button>
          @for (c of CLASES; track c) {
            @if (kl(c); as d) {
              <button type="button" class="clase" [class]="'clase clase--' + c"
                      [class.clase--on]="clase() === c" [attr.aria-pressed]="clase() === c"
                      (click)="setClase(c)">
                <span class="clase__n">{{ d.n | number }}</span>
                <span class="clase__t">{{ TITULO[c] }}</span>
                <span class="clase__g">{{ d.glosa }}</span>
                <span class="clase__p">
                  @if (d.valor_secop !== null) { SECOP {{ mm(d.valor_secop) }} }
                  @if (d.comprometido_bogdata !== null) { · BogData {{ mm(d.comprometido_bogdata) }} }
                </span>
              </button>
            }
          }
        </section>

        <p class="conteo">
          {{ datos()!.count | number }} contratos
          @if (clase()) { en «{{ TITULO[clase()!] }}» }
          · de los {{ cob().comparables | number }} comparables,
          {{ cob().coinciden | number }} coinciden al peso.
        </p>

        <!-- ── Fuente por fuente ────────────────────────────────────── -->
        <div class="tabla-wrap">
          <table class="tabla">
            <caption class="ui-sr-only">Cada contrato con lo que dice cada fuente</caption>
            <thead>
              <tr>
                <th scope="col">Contrato</th>
                <th scope="col" class="num">Valor<br><small>SECOP</small></th>
                <th scope="col" class="num">Pagado<br><small>SECOP</small></th>
                <th scope="col" class="num sep">Comprometido<br><small>BogData</small></th>
                <th scope="col" class="num">Girado<br><small>BogData</small></th>
                <th scope="col" class="sep">Plan<br><small>innovaK</small></th>
                <th scope="col" class="num">Diferencia</th>
              </tr>
            </thead>
            <tbody>
              @for (f of datos()!.items; track f.referencia + '-' + f.numero + '-' + f.anio) {
                <tr>
                  <th scope="row" class="ct">
                    <span class="ct__r">{{ f.referencia }}</span>
                    <span class="ct__c">{{ contratista(f) }}</span>
                    <span class="ct__b" [class]="'ct__b ct__b--' + f.clase">{{ TITULO[f.clase] }}</span>
                  </th>
                  <td class="num">{{ mm(f.secop?.valor ?? null) }}</td>
                  <td class="num">
                    {{ mm(f.secop?.pagado ?? null) }}
                    @if (f.secop && f.secop.pagado === 0) {
                      <span class="pista" title="SECOP escribe 0 también cuando nadie cargó el pago">?</span>
                    }
                  </td>
                  <td class="num sep">{{ mm(f.bogdata?.comprometido ?? null) }}</td>
                  <td class="num">{{ mm(f.bogdata?.girado ?? null) }}</td>
                  <td class="sep plan">
                    @if (f.innovak?.proyecto_id) {
                      <a [routerLink]="['/plan/proyectos', f.innovak!.proyecto_id]"
                         [title]="f.innovak!.proyecto_nombre || ''">
                        {{ f.innovak!.proyecto_codigo }}</a>
                    } @else {
                      <span class="muted">No cuelga del Plan</span>
                    }
                  </td>
                  <td class="num">
                    @if (f.diferencia !== null) {
                      <span [class.dif--alta]="esGrande(f.diferencia)">{{ mm(f.diferencia) }}</span>
                    } @else {
                      <span class="nocmp" [title]="f.glosa">No comparable</span>
                    }
                  </td>
                </tr>
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

    .filtros { display: flex; align-items: center; gap: $space-4; margin: $space-3 0; flex-wrap: wrap; }
    .grupo { display: flex; align-items: center; gap: $space-2; flex-wrap: wrap; }
    .rotulo { font-size: $font-size-sm; color: $color-text-muted; }
    .chip { border: 1px solid rgba(0,0,0,.15); background: #fff; border-radius: 999px;
            padding: 2px 12px; font-size: $font-size-sm; cursor: pointer; }
    .chip--on { background: $color-primary; color: #fff; border-color: $color-primary; }
    .buscar { display: flex; align-items: center; gap: $space-2; flex: 1 1 240px;
              border: 1px solid rgba(0,0,0,.15); border-radius: 6px; padding: 2px $space-2; background: #fff;
              i { color: $color-text-muted; }
              input { border: 0; outline: 0; width: 100%; padding: 4px 0; font-size: $font-size-sm; } }

    .cortes { display: flex; gap: $space-4; flex-wrap: wrap; margin-bottom: $space-2;
              padding: $space-2 0; border-bottom: 1px solid rgba(0,0,0,.08); }
    .corte { display: flex; flex-direction: column; }
    .corte__f { font-size: $font-size-sm; font-weight: 600; }
    .corte__d { font-size: $font-size-sm; color: $color-text-muted; }

    .alcance { margin: 0 0 $space-3; font-size: $font-size-sm; color: $color-text-muted;
               i { margin-right: $space-1; } }

    .clases { display: grid; grid-template-columns: repeat(auto-fit, minmax(210px, 1fr));
              gap: $space-2; margin-bottom: $space-3; }
    .clase { text-align: left; cursor: pointer; background: #fff; border: 1px solid rgba(0,0,0,.1);
             border-left: 4px solid rgba(0,0,0,.2); border-radius: 8px; padding: $space-2 $space-3;
             display: flex; flex-direction: column; gap: 2px; }
    .clase--on { box-shadow: 0 0 0 2px rgba(0,0,0,.12) inset; }
    .clase--acuerdo { border-left-color: #15803d; }
    .clase--valor_distinto { border-left-color: #b45309; }
    .clase--identidad_dudosa { border-left-color: #b91c1c; }
    .clase--solo_secop, .clase--solo_bogdata { border-left-color: #0e7490; }
    .clase--fuera_de_corte { border-left-color: rgba(0,0,0,.25); }
    .clase__n { font-size: 1.35rem; font-weight: 700; font-variant-numeric: tabular-nums; }
    .clase__t { font-size: $font-size-sm; font-weight: 600; }
    .clase__g { font-size: $font-size-sm; color: $color-text-muted; }
    .clase__p { font-size: $font-size-sm; color: $color-text-muted; font-variant-numeric: tabular-nums; }

    .conteo { margin: 0 0 $space-2; font-size: $font-size-sm; color: $color-text-muted; }

    .tabla-wrap { overflow-x: auto; }
    .tabla { width: 100%; border-collapse: collapse; font-size: $font-size-sm; }
    .tabla th, .tabla td { padding: $space-2 $space-3; border-bottom: 1px solid rgba(0,0,0,.08);
                           text-align: left; vertical-align: top; }
    .tabla thead th { small { font-weight: 400; color: $color-text-muted; } }
    .tabla th.num, .tabla td.num { text-align: right; font-variant-numeric: tabular-nums; }
    .tabla .sep { border-left: 2px solid rgba(0,0,0,.08); }
    .ct { font-weight: 400; }
    .ct__r { display: block; font-weight: 700; }
    .ct__c { display: block; color: $color-text-muted; }
    .ct__b { display: inline-block; margin-top: 2px; font-size: .72rem; padding: 0 6px;
             border-radius: 999px; background: rgba(0,0,0,.06); }
    .ct__b--acuerdo { background: rgba(21,128,61,.12); }
    .ct__b--valor_distinto { background: rgba(180,83,9,.14); }
    .ct__b--identidad_dudosa { background: rgba(185,28,28,.12); }
    .pista { margin-left: 4px; color: $color-text-muted; cursor: help; }
    .nocmp { color: $color-text-muted; font-style: italic; cursor: help; }
    .dif--alta { font-weight: 700; }
    .plan a { font-weight: 600; }
    .muted { color: $color-text-muted; }

    .pag { display: flex; align-items: center; gap: $space-3; margin-top: $space-3;
           font-size: $font-size-sm;
           button { border: 1px solid rgba(0,0,0,.15); background: #fff; border-radius: 6px;
                    padding: 4px 12px; cursor: pointer; &:disabled { opacity: .45; cursor: default; } } }
  `],
})
export class ContratosFuentesComponent implements OnInit {
  private http = inject(HttpClient);
  private cfg = inject(ConfigService);
  private layout = inject(LayoutService);

  /** El orden en que se leen: primero lo que está de acuerdo, después lo que
   *  hay que mirar, y al final lo que no es comparable. */
  readonly CLASES = ['acuerdo', 'valor_distinto', 'identidad_dudosa',
                     'solo_secop', 'solo_bogdata', 'fuera_de_corte'];

  readonly TITULO: Record<string, string> = {
    acuerdo: 'De acuerdo',
    valor_distinto: 'Cifras distintas',
    identidad_dudosa: 'Identidad dudosa',
    solo_secop: 'Solo en SECOP',
    solo_bogdata: 'Solo en BogData',
    fuera_de_corte: 'Fuera del corte',
  };

  datos = signal<Respuesta | null>(null);
  cargando = signal<boolean>(true);
  vigencia = signal<number | null>(null);
  clase = signal<string | null>(null);
  q = signal<string>('');
  pagina = signal<number>(1);

  /** Los años salen del dato, no de una lista escrita a mano: si mañana entra
   *  un contrato de 2027 aparece solo. */
  vigencias = signal<number[]>([]);

  async ngOnInit(): Promise<void> {
    this.layout.setBreadcrumb([
      { label: 'Plan de Desarrollo', url: '/plan' },
      { label: 'Contratos por fuente' },
    ]);
    await this.cargar();
  }

  setVigencia(v: number | null): void { this.vigencia.set(v); this.pagina.set(1); void this.cargar(); }
  setClase(c: string | null): void { this.clase.set(this.clase() === c ? null : c); this.pagina.set(1); void this.cargar(); }
  buscar(texto: string): void { this.q.set(texto); this.pagina.set(1); void this.cargar(); }
  irA(p: number): void { this.pagina.set(p); void this.cargar(); }

  private async cargar(): Promise<void> {
    this.cargando.set(true);
    const p = new URLSearchParams({ page: String(this.pagina()), por: '25' });
    if (this.vigencia()) p.set('vigencia', String(this.vigencia()));
    if (this.clase()) p.set('clase', this.clase()!);
    if (this.q()) p.set('q', this.q());
    try {
      const r = await firstValueFrom(
        this.http.get<Respuesta>(this.cfg.url(`/presupuesto/api/contratos/fuentes/?${p}`)));
      this.datos.set(r);
      if (r.vigencias?.length) this.vigencias.set(r.vigencias.filter((v) => v >= 2024));
    } catch {
      this.datos.set(null);
    } finally {
      this.cargando.set(false);
    }
  }

  cob() { return this.datos()!.resumen.cobertura; }
  kl(c: string): Clase | null { return this.datos()!.resumen.por_clase[c] ?? null; }

  /** El contratista que se muestra es el de SECOP cuando lo hay, porque SECOP
   *  es la fuente del hecho contractual. Si el contrato solo está en BogData,
   *  se muestra el beneficiario del CRP y así queda claro de dónde salió. */
  contratista(f: Fila): string {
    return f.secop?.contratista || f.bogdata?.contratista || 'Sin contratista declarado';
  }

  mm(v: number | null | undefined): string {
    return v === null || v === undefined ? 'No lo ve' : enMillones(v);
  }

  fecha(iso: string | null): string {
    if (!iso) return 'sin corte declarado';
    return new Date(iso).toLocaleDateString('es-CO', {
      year: 'numeric', month: 'long', day: 'numeric',
    });
  }

  esGrande(d: number | null): boolean {
    return d !== null && Math.abs(d) >= 1e9;
  }
}
