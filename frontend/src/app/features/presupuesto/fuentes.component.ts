import { CommonModule } from '@angular/common';
import { HttpClient } from '@angular/common/http';
import { Component, OnInit, computed, inject, signal } from '@angular/core';
import { firstValueFrom } from 'rxjs';

import { ConfigService } from '../../core/config/config.service';
import { LayoutService } from '../../core/layout/layout.service';
import { enMillones } from './muro/muro-subgrupos.component';

interface Cobertura {
  metas: number; proyectos: number; vigencias: number[];
  vigencia_desde: number | null; vigencia_hasta: number | null;
}
interface CifraOficial {
  apropiacion: number | null; comprometido: number | null; girado: number | null;
  proyectado: number | null; cobertura: Cobertura; fuente: string;
}
interface CifraBogData {
  comprometido: number | null; girado: number | null;
  anterior_al_pdl: number | null; filas: number; fuente: string;
}
interface FilaProyecto {
  proyecto_codigo: string; proyecto_id: number | null; proyecto: string | null;
  oficial: CifraOficial; bogdata: CifraBogData | null; diferencia: number | null;
}
interface CorteMatriz {
  corte_oficial: string | null; cargado_at: string | null;
  archivo: string | null; fuente: string;
}
interface Contraste {
  vigencia: number | null;
  items: FilaProyecto[];
  totales: {
    oficial: CifraOficial;
    bogdata: CifraBogData & {
      atribuido_a_proyecto: number | null; sin_proyecto: number | null;
      cobertura_pct: number | null; girado_atribuido_a_proyecto: number | null;
    };
    diferencia: number | null;
  };
  cortes: { matriz: CorteMatriz | null; bogdata: string | null; secop: string | null };
  nota_alcance: string;
}

/**
 * FUENTES — la Matriz frente a BogData, proyecto por proyecto.
 *
 * POR QUÉ ES UNA PANTALLA Y NO UNA PESTAÑA DEL TABLERO. El tablero es página
 * única a propósito: tenía cinco pestañas y se quitaron porque escondían el
 * contenido tras dos clics. Reponer una para esto sería deshacer esa decisión.
 *
 * QUÉ MUESTRA, Y QUÉ NO PUEDE MOSTRAR. La cifra oficial es la Matriz y va
 * primero; BogData va al lado, con su propia fecha de corte. La diferencia se
 * calcula pero NO se interpreta: no está conciliada, y decidir de qué lado está
 * la explicación sin haberlo medido es exactamente lo que este módulo evita.
 *
 * La comparación existe por proyecto y por totales, y **no puede existir por
 * meta**: BogData atribuye la plata al proyecto y ahí se detiene. Pedirla más
 * abajo no es difícil, es imposible con las fuentes que hay.
 *
 * Y LAS FILAS SUMAN MENOS QUE EL TOTAL, a propósito: BogData no atribuye a
 * ningún proyecto las obligaciones por pagar de vigencias anteriores. Al corte
 * del 7 de septiembre eso son $92.160 M en 1.056 filas. Si el total se sumara
 * de las filas visibles, la diferencia contra la Matriz saldría más del triple
 * de la real, y ese exceso no sería un desacuerdo: sería plata que BogData no
 * alcanza a atribuir.
 */
@Component({
  standalone: true,
  selector: 'app-fuentes',
  imports: [CommonModule],
  template: `
    <div class="page">
      <header class="page__header">
        <h1><i class="fa fa-scale-balanced" aria-hidden="true"></i> Fuentes</h1>
        <p class="page__subtitle">
          De dónde sale cada cifra del Plan. La Matriz manda y va primero;
          BogData va al lado como contraste, con su propia fecha de corte.
        </p>
      </header>

      <div class="vigencia" role="group" aria-labelledby="vig-rot">
        <span class="rotulo" id="vig-rot">Vigencia</span>
        <button type="button" class="vchip" [class.vchip--on]="!vigencia()"
                [attr.aria-pressed]="!vigencia()" (click)="setVigencia(null)">Todas</button>
        @for (v of VIGENCIAS; track v) {
          <button type="button" class="vchip" [class.vchip--on]="vigencia() === v"
                  [attr.aria-pressed]="vigencia() === v" (click)="setVigencia(v)">{{ v }}</button>
        }
      </div>

      @if (cargando()) {
        <p class="muted">Cargando…</p>
      } @else if (!datos()) {
        <div class="ui-empty-state">
          <i class="fa fa-info-circle" aria-hidden="true"></i>
          <p>No se pudo leer el contraste de fuentes.</p>
        </div>
      } @else {
        <!-- ── De cuándo es cada fuente ─────────────────────────────── -->
        <section class="cortes" aria-label="Fecha de corte de cada fuente">
          <div class="corte">
            <span class="corte__f">Matriz PDL · ALK</span>
            <span class="corte__d">{{ corteMatriz() }}</span>
          </div>
          <div class="corte">
            <span class="corte__f">BogData · CRP</span>
            <span class="corte__d">{{ fecha(datos()!.cortes.bogdata) }}</span>
          </div>
          <div class="corte">
            <span class="corte__f">SECOP II</span>
            <span class="corte__d">{{ fecha(datos()!.cortes.secop) }}</span>
          </div>
        </section>

        <!-- ── Los totales, cara a cara ─────────────────────────────── -->
        <section class="caras" aria-label="Totales por fuente">
          <article class="cara cara--oficial">
            <h2 class="cara__t">Matriz PDL <small>la fuente oficial</small></h2>
            <div class="cara__cifras">
              <div><span class="c__l">Apropiado</span><span class="c__v">{{ mm(t().oficial.apropiacion) }}</span></div>
              <div><span class="c__l">Comprometido</span><span class="c__v">{{ mm(t().oficial.comprometido) }}</span></div>
              <div><span class="c__l">Girado</span><span class="c__v">{{ mm(t().oficial.girado) }}</span></div>
            </div>
            <p class="cara__cob">{{ coberturaTexto() }}</p>
          </article>

          <article class="cara cara--contraste">
            <h2 class="cara__t">BogData · CRP <small>referencia, no cálculo</small></h2>
            <div class="cara__cifras">
              <div><span class="c__l">Comprometido</span><span class="c__v">{{ mm(t().bogdata.comprometido) }}</span></div>
              <div><span class="c__l">Girado</span><span class="c__v">{{ mm(t().bogdata.girado) }}</span></div>
              <div><span class="c__l">Anterior al Plan</span><span class="c__v">{{ mm(t().bogdata.anterior_al_pdl) }}</span></div>
            </div>
            <p class="cara__cob">
              Atribuido a un proyecto: {{ mm(t().bogdata.atribuido_a_proyecto) }}
              @if (t().bogdata.cobertura_pct != null) { ({{ t().bogdata.cobertura_pct }} %) }
              · sin proyecto {{ mm(t().bogdata.sin_proyecto) }}
            </p>
          </article>
        </section>

        @if (t().diferencia != null) {
          <p class="dif">
            Las dos fuentes difieren en <strong>{{ mm(t().diferencia) }}</strong> de comprometido.
            No está conciliada: se muestra, no se interpreta.
          </p>
        }

        <p class="alcance"><i class="fa fa-circle-info" aria-hidden="true"></i> {{ datos()!.nota_alcance }}</p>

        <!-- ── Proyecto por proyecto ────────────────────────────────── -->
        <div class="tabla-wrap">
          <table class="tabla">
            <caption class="ui-sr-only">Comparación por proyecto entre la Matriz y BogData</caption>
            <thead>
              <tr>
                <th scope="col">Proyecto</th>
                <th scope="col" class="num">Apropiado<br><small>Matriz</small></th>
                <th scope="col" class="num">Comprometido<br><small>Matriz</small></th>
                <th scope="col" class="num">Girado<br><small>Matriz</small></th>
                <th scope="col" class="num sep">Comprometido<br><small>BogData</small></th>
                <th scope="col" class="num">Girado<br><small>BogData</small></th>
                <th scope="col" class="num">Diferencia</th>
              </tr>
            </thead>
            <tbody>
              @for (f of datos()!.items; track f.proyecto_codigo) {
                <tr>
                  <th scope="row" class="proy">
                    <span class="proy__c">{{ f.proyecto_codigo }}</span>
                    <span class="proy__n">{{ f.proyecto || 'Sin nombre' }}</span>
                  </th>
                  <td class="num">{{ mm(f.oficial.apropiacion) }}</td>
                  <td class="num">{{ mm(f.oficial.comprometido) }}</td>
                  <td class="num">{{ mm(f.oficial.girado) }}</td>
                  <td class="num sep">{{ mm(f.bogdata?.comprometido ?? null) }}</td>
                  <td class="num">{{ mm(f.bogdata?.girado ?? null) }}</td>
                  <td class="num" [class.dif--alta]="esGrande(f.diferencia)">{{ mm(f.diferencia) }}</td>
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

    .vigencia { display: flex; align-items: center; gap: $space-2; margin: $space-3 0; flex-wrap: wrap; }
    .rotulo { font-size: $font-size-sm; color: $color-text-muted; }
    .vchip { border: 1px solid rgba(0,0,0,.15); background: #fff; border-radius: 999px;
             padding: 2px 12px; font-size: $font-size-sm; cursor: pointer; }
    .vchip--on { background: $color-primary; color: #fff; border-color: $color-primary; }

    .cortes { display: flex; gap: $space-4; flex-wrap: wrap; margin-bottom: $space-3;
              padding: $space-2 0; border-bottom: 1px solid rgba(0,0,0,.08); }
    .corte { display: flex; flex-direction: column; }
    .corte__f { font-size: $font-size-sm; font-weight: 600; }
    .corte__d { font-size: $font-size-sm; color: $color-text-muted; }

    .caras { display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
             gap: $space-3; margin-bottom: $space-3; }
    .cara { border: 1px solid rgba(0,0,0,.1); border-radius: 8px; padding: $space-3; }
    .cara--oficial { border-left: 4px solid $color-primary; }
    .cara--contraste { border-left: 4px solid rgba(0,0,0,.2); background: rgba(0,0,0,.015); }
    .cara__t { margin: 0 0 $space-2; font-size: $font-size-base;
               small { font-weight: 400; color: $color-text-muted; margin-left: $space-2; } }
    .cara__cifras { display: flex; gap: $space-4; flex-wrap: wrap; }
    .c__l { display: block; font-size: $font-size-sm; color: $color-text-muted; }
    .c__v { display: block; font-weight: 700; font-variant-numeric: tabular-nums; }
    .cara__cob { margin: $space-2 0 0; font-size: $font-size-sm; color: $color-text-muted; }

    .dif { margin: 0 0 $space-2; font-size: $font-size-sm; }
    .alcance { margin: 0 0 $space-3; font-size: $font-size-sm; color: $color-text-muted;
               i { margin-right: $space-1; } }

    .tabla-wrap { overflow-x: auto; }
    .tabla { width: 100%; border-collapse: collapse; font-size: $font-size-sm; }
    .tabla th, .tabla td { padding: $space-2 $space-3; border-bottom: 1px solid rgba(0,0,0,.08);
                           text-align: left; vertical-align: top; }
    .tabla thead th { font-size: $font-size-sm; small { font-weight: 400; color: $color-text-muted; } }
    .tabla th.num, .tabla td.num { text-align: right; font-variant-numeric: tabular-nums; }
    .tabla .sep { border-left: 2px solid rgba(0,0,0,.08); }
    .proy { font-weight: 400; }
    .proy__c { display: block; font-weight: 700; }
    .proy__n { display: block; color: $color-text-muted; }
    .dif--alta { font-weight: 700; }
    .muted { color: $color-text-muted; }
  `],
})
export class FuentesComponent implements OnInit {
  private http = inject(HttpClient);
  private cfg = inject(ConfigService);
  private layout = inject(LayoutService);

  /** Las cuatro del Plan. Un año sin dato se puede elegir igual y las cifras
   *  dicen «sin dato», que es distinto de cero. */
  readonly VIGENCIAS = [2025, 2026, 2027, 2028];

  datos = signal<Contraste | null>(null);
  cargando = signal<boolean>(true);
  vigencia = signal<number | null>(null);

  t = computed(() => this.datos()!.totales);

  async ngOnInit(): Promise<void> {
    this.layout.setBreadcrumb([
      { label: 'Plan de Desarrollo', url: '/plan' },
      { label: 'Fuentes' },
    ]);
    await this.cargar();
  }

  setVigencia(v: number | null): void {
    this.vigencia.set(v);
    void this.cargar();
  }

  private async cargar(): Promise<void> {
    this.cargando.set(true);
    const v = this.vigencia();
    const url = this.cfg.url(`/presupuesto/api/plata/contraste/${v ? `?vigencia=${v}` : ''}`);
    try {
      this.datos.set(await firstValueFrom(this.http.get<Contraste>(url)));
    } catch {
      this.datos.set(null);
    } finally {
      this.cargando.set(false);
    }
  }

  /** Pesos a millones. `null` es «sin dato», NUNCA «$0»: es la regla de la
   *  casa, y en una pantalla que compara fuentes es lo que distingue «esta
   *  fuente no lo cubre» de «esta fuente dice cero». */
  mm(v: number | null | undefined): string {
    return v === null || v === undefined ? 'Sin dato' : enMillones(v);
  }

  fecha(iso: string | null): string {
    if (!iso) return 'sin corte declarado';
    return new Date(iso).toLocaleDateString('es-CO', {
      year: 'numeric', month: 'long', day: 'numeric',
    });
  }

  /** El corte de la Matriz publica DOS fechas y no una: cuándo es el dato y
   *  desde cuándo lo tenemos. Se muestra la declarada si existe. */
  corteMatriz(): string {
    const c = this.datos()?.cortes.matriz;
    if (!c) return 'sin corte declarado';
    if (c.corte_oficial) return this.fecha(c.corte_oficial);
    return c.cargado_at ? `${this.fecha(c.cargado_at)} (cargada)` : 'sin corte declarado';
  }

  coberturaTexto(): string {
    const c = this.t().oficial.cobertura;
    if (!c?.metas) return 'sin cobertura declarada';
    const rango = c.vigencia_desde === c.vigencia_hasta
      ? `${c.vigencia_desde}` : `${c.vigencia_desde}-${c.vigencia_hasta}`;
    return `${c.metas} metas · ${c.proyectos} proyectos${c.vigencia_desde ? ` · ${rango}` : ''}`;
  }

  /** Resalta las diferencias grandes. No las califica: solo las hace visibles,
   *  porque no están conciliadas y no sabemos de qué lado está la explicación. */
  esGrande(d: number | null): boolean {
    return d !== null && Math.abs(d) >= 1e9;
  }
}
