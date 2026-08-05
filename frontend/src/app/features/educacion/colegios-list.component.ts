import { CommonModule } from '@angular/common';
import { Component, OnInit, computed, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { LayoutService } from '../../core/layout/layout.service';
import { EducacionApi } from './educacion.api';
import { ColegioSede } from './educacion.types';

/**
 * Listado de las sedes de colegios distritales de Kennedy.
 *
 * La unidad de la tabla es la SEDE y no el colegio a propósito: los insumos se
 * entregan en una sede concreta, y un colegio de cuatro sedes con una sola
 * fila obliga a adivinar a cuál llegó la dotación.
 */
@Component({
  standalone: true,
  selector: 'app-colegios-list',
  imports: [CommonModule, FormsModule],
  template: `
    <div class="page">
      <header class="page__header">
        <div>
          <h1><i class="fa fa-graduation-cap" aria-hidden="true"></i> Colegios distritales</h1>
          <p class="page__sub">
            Sedes de Kennedy según la Secretaría de Educación del Distrito.
            @if (corte()) { <span>Corte {{ corte() }}.</span> }
            Los insumos entregados se registran en la sede, no en el colegio.
          </p>
        </div>
        <div class="page__actions">
          <button class="ui-btn ui-btn--ghost" (click)="verResumen()">
            <i class="fa fa-chart-column"></i> Resumen {{ vigencia }}
          </button>
        </div>
      </header>

      @if (!disponible() && !loading()) {
        <!-- Se distingue "no hay datos cargados" de "falló": el área no puede
             hacer nada con "error", pero sí con "falta correr el sync". -->
        <div class="ui-info-bar ui-info-bar--warn">
          Todavía no hay colegios cargados. Se cargan desde la fuente oficial con
          <code>manage.py sync_colegios</code>.
        </div>
      }

      <section class="kpis">
        <div class="kpi">
          <span class="kpi__val">{{ totalColegios() }}</span>
          <span class="kpi__lbl">Colegios</span>
        </div>
        <div class="kpi">
          <span class="kpi__val">{{ sedes().length }}</span>
          <span class="kpi__lbl">Sedes ubicadas</span>
        </div>
        <div class="kpi kpi--ok">
          <span class="kpi__val">{{ matriculaTotal() | number:'1.0-0' }}</span>
          <span class="kpi__lbl">
            Alumnos
            @if (matriculaCorte()) { <small>· corte {{ matriculaCorte() }}</small> }
          </span>
        </div>
        @if (sinUbicacion().length) {
          <div class="kpi kpi--warn">
            <span class="kpi__val">{{ sinUbicacion().length }}</span>
            <span class="kpi__lbl">Sedes sin coordenada</span>
          </div>
        }
      </section>

      <section class="filtros">
        <label class="ui-field">
          <span>Buscar</span>
          <input class="ui-input" type="search" [(ngModel)]="q"
                 (input)="aplicar()" placeholder="Colegio, sede o dirección…">
        </label>
        <label class="ui-field">
          <span>Clase</span>
          <select class="ui-input" [(ngModel)]="clase" (ngModelChange)="cargar()">
            <option [ngValue]="null">Todas</option>
            <option [ngValue]="1">Distrital</option>
            <option [ngValue]="2">Distrital - Adm. contratada</option>
          </select>
        </label>
        <label class="ui-check">
          <input type="checkbox" [(ngModel)]="soloPrincipales" (ngModelChange)="cargar()">
          Solo sedes principales
        </label>
      </section>

      @if (loading()) { <div class="ui-info-bar ui-info-bar--info">Cargando…</div> }
      @if (error()) { <div class="ui-info-bar ui-info-bar--danger">{{ error() }}</div> }

      <table class="ui-table">
        <thead>
          <tr>
            <th>Colegio</th>
            <th>Sede</th>
            <th class="num">Alumnos</th>
            <th>Dirección</th>
            <th>UPZ</th>
            <th class="num">Entregas</th>
          </tr>
        </thead>
        <tbody>
          @for (s of visibles(); track s.id) {
            <tr role="button" tabindex="0" (click)="abrir(s)" (keyup.enter)="abrir(s)">
              <td>
                {{ s.colegio }}
                @if (s.clase === 2) {
                  <span class="badge badge--info" title="Distrital - Administración contratada">AC</span>
                }
              </td>
              <td>
                @if (s.es_principal) { <span class="badge badge--ok">Principal</span> }
                @else { <span class="badge">Sede {{ s.orden_sede }}</span> }
                {{ s.sede }}
              </td>
              <td class="num">
                @if (s.matricula_total != null) { {{ s.matricula_total | number:'1.0-0' }} }
                @else { <span class="muted">sin dato</span> }
              </td>
              <td>{{ s.direccion || '—' }}</td>
              <td>{{ s.upz_codigo || '—' }}</td>
              <td class="num">
                @if (s.entregas_n) { {{ s.entregas_n }} } @else { <span class="muted">—</span> }
              </td>
            </tr>
          } @empty {
            <tr><td colspan="6" class="muted">Ninguna sede coincide con el filtro.</td></tr>
          }
        </tbody>
      </table>

      @if (sinUbicacion().length) {
        <!-- No se ocultan: una sede que no aparece se lee como "no existe" en
             vez de "no sabemos dónde queda", y son las que hay que arreglar. -->
        <details class="ui-details">
          <summary>{{ sinUbicacion().length }} sedes sin coordenada (no salen en el mapa)</summary>
          <ul>
            @for (s of sinUbicacion(); track s.id) {
              <li>{{ s.colegio }} — {{ s.sede }} · {{ s.direccion || 'sin dirección' }}</li>
            }
          </ul>
        </details>
      }
    </div>
  `,
  styles: [`
    .filtros { display: flex; flex-wrap: wrap; gap: 1rem; align-items: end; margin: 1rem 0; }
    .num { text-align: right; }
    .muted { color: var(--color-text-muted, #6b7280); }
    tbody tr { cursor: pointer; }
    .ui-details { margin-top: 1.5rem; }
    .ui-details ul { margin: .5rem 0 0 1rem; }
  `],
})
export class ColegiosListComponent implements OnInit {
  private api = inject(EducacionApi);
  private layout = inject(LayoutService);
  private router = inject(Router);

  sedes = signal<ColegioSede[]>([]);
  sinUbicacion = signal<ColegioSede[]>([]);
  totalColegios = signal<number>(0);
  matriculaTotal = signal<number>(0);
  disponible = signal<boolean>(true);
  loading = signal<boolean>(true);
  error = signal<string>('');

  q = '';
  clase: number | null = null;
  soloPrincipales = false;
  vigencia = new Date().getFullYear();

  /** El filtro de texto se aplica en el cliente: son 79 filas, no vale un viaje. */
  visibles = computed<ColegioSede[]>(() => {
    const t = this.q.trim().toLowerCase();
    if (!t) return this.sedes();
    return this.sedes().filter((s) =>
      [s.colegio, s.sede, s.direccion].filter(Boolean).join(' ').toLowerCase().includes(t));
  });

  corte = computed<string | null>(() => this.sedes()[0]?.fecha_corte ?? null);
  matriculaCorte = computed<string | null>(
    () => this.sedes().find((s) => s.matricula_corte)?.matricula_corte ?? null);

  ngOnInit(): void {
    this.layout.setBreadcrumb([
      { label: 'Inicio', url: '/' },
      { label: 'Educación' },
    ]);
    this.cargar();
  }

  cargar(): void {
    this.loading.set(true);
    this.error.set('');
    this.api.colegios({
      clase: this.clase ? [this.clase] : undefined,
      solo_principales: this.soloPrincipales,
    }).subscribe({
      next: (r) => {
        this.sedes.set((r.features || []).map((f) => f.properties));
        this.sinUbicacion.set(r.sin_ubicacion || []);
        this.totalColegios.set(r.colegios || 0);
        this.matriculaTotal.set(r.matricula_total || 0);
        this.disponible.set(r.disponible !== false);
        this.loading.set(false);
      },
      error: () => {
        this.error.set('No se pudieron cargar los colegios.');
        this.loading.set(false);
      },
    });
  }

  aplicar(): void { /* el filtro de texto es un computed; esto solo dispara CD */ }

  abrir(s: ColegioSede): void {
    this.router.navigate(['/educacion', s.id]);
  }

  verResumen(): void {
    this.router.navigate(['/educacion/resumen', this.vigencia]);
  }
}
