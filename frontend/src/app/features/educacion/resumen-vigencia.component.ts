import { CommonModule } from '@angular/common';
import { Component, OnInit, inject, signal } from '@angular/core';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { LayoutService } from '../../core/layout/layout.service';
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
  imports: [CommonModule, RouterLink],
  template: `
    <div class="page">
      <header class="page__header">
        <div>
          <a routerLink="/educacion" class="ui-back-link">
            <i class="fa fa-arrow-left"></i> Colegios distritales
          </a>
          <h1>Insumos entregados · {{ vigencia }}</h1>
        </div>
      </header>

      @if (loading()) { <div class="ui-info-bar ui-info-bar--info">Cargando…</div> }
      @if (error()) { <div class="ui-info-bar ui-info-bar--danger">{{ error() }}</div> }

      @if (r(); as res) {
        <section class="kpis">
          <div class="kpi">
            <span class="kpi__val">{{ res.totales.entregas }}</span>
            <span class="kpi__lbl">Entregas</span>
          </div>
          <div class="kpi kpi--ok">
            <span class="kpi__val">{{ res.totales.valor | currency:'COP':'symbol-narrow':'1.0-0' }}</span>
            <span class="kpi__lbl">Valor total</span>
          </div>
          <div class="kpi">
            <span class="kpi__val">{{ res.totales.sedes }}</span>
            <span class="kpi__lbl">Sedes atendidas</span>
          </div>
        </section>

        <section>
          <h2>Por insumo</h2>
          <table class="ui-table">
            <thead>
              <tr><th>Insumo</th><th class="num">Cantidad</th>
                  <th class="num">Sedes</th><th class="num">Valor</th></tr>
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
        </section>

        <section>
          <h2>Por colegio</h2>
          <table class="ui-table">
            <thead>
              <tr><th>Colegio</th><th class="num">Sedes</th><th class="num">Entregas</th>
                  <th class="num">Beneficiarios</th><th class="num">Matrícula</th>
                  <th class="num">Valor</th></tr>
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
    .num { text-align: right; }
    .muted { color: var(--color-text-muted, #6b7280); }
    section { margin-bottom: 2rem; }
  `],
})
export class ResumenVigenciaComponent implements OnInit {
  private api = inject(EducacionApi);
  private route = inject(ActivatedRoute);
  private layout = inject(LayoutService);

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
