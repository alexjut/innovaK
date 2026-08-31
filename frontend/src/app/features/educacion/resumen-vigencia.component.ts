import { CommonModule, CurrencyPipe } from '@angular/common';
import { Component, OnInit, inject, signal } from '@angular/core';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { LayoutService } from '../../core/layout/layout.service';
import { PageHeaderComponent } from '../../shared/ui/page-header.component';
import { StatGridComponent, StatItem } from '../../shared/ui/stat-grid.component';
import { EducacionApi } from './educacion.api';
import { ResumenVigencia } from './educacion.types';

/**
 * Qué se entregó en una vigencia, por insumo y por colegio.
 *
 * Es la pregunta que motivó el módulo — "en 2025, ¿qué le entregamos a
 * quién?" — y la razón de que el insumo salga de un catálogo: sumar por
 * texto libre no funciona en cuanto dos actas escriben distinto.
 */
@Component({
  standalone: true,
  selector: 'app-resumen-vigencia',
  imports: [CommonModule, RouterLink, PageHeaderComponent, StatGridComponent],
  providers: [CurrencyPipe],
  template: `
    <div class="page">
      <!-- Sin back-link: el breadcrumb global (Inicio › Educación › Resumen {vigencia})
           ya resuelve esa navegación — no se duplica. -->
      <app-page-header title="Resumen de entregas" [description]="'Vigencia ' + vigencia" />

      @if (loading()) {
        <div class="ui-info-bar ui-info-bar--info" role="status">Cargando…</div>
      }
      @if (error()) {
        <div class="ui-info-bar ui-info-bar--danger" role="alert">{{ error() }}</div>
      }

      @if (r(); as res) {
        <app-stat-grid [stats]="kpiStats(res)" />

        <section>
          <h2>Por insumo</h2>
          <div class="ui-table-responsive">
          <table class="ui-table">
            <thead>
              <tr><th scope="col">Insumo</th><th scope="col" class="num">Cantidad</th>
                  <th scope="col" class="num">Sedes</th><th scope="col" class="num">Valor</th></tr>
            </thead>
            <tbody>
              @for (i of res.por_insumo; track i.insumo) {
                <tr>
                  <td>{{ i.insumo }}</td>
                  <td class="num">{{ i.cantidad | number:'1.0-2' }}</td>
                  <td class="num">{{ i.sedes }}</td>
                  <td class="num">{{ i.valor | currency:'COP':'symbol-narrow':'1.0-0' }}</td>
                </tr>
              } @empty {
                <tr><td colspan="4" class="muted">Nada registrado en {{ vigencia }}.</td></tr>
              }
            </tbody>
          </table>
          </div>
        </section>

        <section>
          <h2>Por colegio</h2>
          <div class="ui-table-responsive">
          <table class="ui-table">
            <thead>
              <tr><th scope="col">Colegio</th><th scope="col" class="num">Sedes</th>
                  <th scope="col" class="num">Entregas</th>
                  <th scope="col" class="num">Beneficiarios</th>
                  <th scope="col" class="num">Matrícula</th>
                  <th scope="col" class="num">Valor</th></tr>
            </thead>
            <tbody>
              @for (c of res.por_colegio; track c.dane_establecimiento) {
                <tr>
                  <td>{{ c.colegio }}</td>
                  <td class="num">{{ c.sedes }}</td>
                  <td class="num">{{ c.entregas }}</td>
                  <td class="num">{{ c.beneficiarios | number:'1.0-0' }}</td>
                  <td class="num">{{ c.matricula | number:'1.0-0' }}</td>
                  <td class="num">{{ c.valor | currency:'COP':'symbol-narrow':'1.0-0' }}</td>
                </tr>
              } @empty {
                <tr><td colspan="6" class="muted">Nada registrado en {{ vigencia }}.</td></tr>
              }
            </tbody>
          </table>
          </div>
          <p class="muted">
            «Beneficiarios» son los que reporta cada entrega, no la matrícula:
            dotar un aula no beneficia a todo el colegio. Las dos columnas están
            para poder compararlas, no para sumarlas.
          </p>
        </section>
      }
    </div>
  `,
  styles: [`
    @use '../../../styles/tokens' as *;
    .num { text-align: right; }
    .muted { color: $color-text-muted; }
    section { margin-bottom: 2rem; }
  `],
})
export class ResumenVigenciaComponent implements OnInit {
  private api = inject(EducacionApi);
  private route = inject(ActivatedRoute);
  private layout = inject(LayoutService);
  private currencyPipe = inject(CurrencyPipe);

  kpiStats(res: ResumenVigencia): StatItem[] {
    return [
      { value: res.totales.entregas, label: 'Entregas' },
      {
        value: this.currencyPipe.transform(res.totales.valor, 'COP', 'symbol-narrow', '1.0-0') ?? '—',
        label: 'Valor total',
        variant: 'ok',
      },
      { value: res.totales.sedes, label: 'Sedes atendidas' },
    ];
  }

  r = signal<ResumenVigencia | null>(null);
  loading = signal<boolean>(true);
  error = signal<string>('');
  vigencia = new Date().getFullYear();

  ngOnInit(): void {
    this.vigencia = Number(this.route.snapshot.paramMap.get('vigencia')) || this.vigencia;
    this.layout.setBreadcrumb([
      { label: 'Inicio', url: '/' },
      { label: 'Educación', url: '/educacion' },
      { label: `Resumen ${this.vigencia}` },
    ]);
    this.api.resumen(this.vigencia).subscribe({
      next: (r) => { this.r.set(r); this.loading.set(false); },
      error: () => {
        this.error.set('No se pudo cargar el resumen.');
        this.loading.set(false);
      },
    });
  }
}
