import { CommonModule } from '@angular/common';
import { Component, OnInit, inject } from '@angular/core';
import { LayoutService } from '../../core/layout/layout.service';

/**
 * UI Showcase — sirve como referencia visual de los componentes `.ui-*`
 * migrados desde Django en PR-2 Etapa D.
 *
 * Cada feature futuro debe usar estos componentes (cards, badges, tables,
 * filter-bars, etc.) en vez de inventar estilos propios. Este showcase
 * vive en `/showcase` durante desarrollo; en PR-15 se mueve a un módulo
 * `/dev/*` que solo se sirve fuera de producción.
 */
@Component({
  standalone: true,
  selector: 'app-showcase',
  imports: [CommonModule],
  template: `
    <div class="ui-page">
      <header class="ui-page__header">
        <h1>UI Showcase</h1>
        <p>Componentes <code>.ui-*</code> migrados desde Django para innovaK Angular.</p>
      </header>

      <!-- Breadcrumb -->
      <section class="ui-section">
        <h2 class="ui-section__title">Breadcrumb</h2>
        <nav class="ui-breadcrumb" aria-label="Breadcrumb">
          <ol>
            <li><a href="#">Inicio</a></li>
            <li><a href="#">Banco de Iniciativas</a></li>
            <li aria-current="page">Inscripción 1234</li>
          </ol>
        </nav>
      </section>

      <!-- Cards -->
      <section class="ui-section">
        <h2 class="ui-section__title">Cards</h2>
        <div class="grid">
          <article class="ui-card ui-card--primary">
            <header class="ui-card__header">
              <h3 class="ui-card__title">Presupuesto</h3>
              <p class="ui-card__subtitle">Cards primario · franja roja</p>
            </header>
            <div class="ui-card__body">Proyectos, programas, KPIs y avances.</div>
          </article>

          <article class="ui-card ui-card--success">
            <header class="ui-card__header">
              <h3 class="ui-card__title">12 metas cumplidas</h3>
              <p class="ui-card__subtitle">success</p>
            </header>
          </article>

          <article class="ui-card ui-card--warning">
            <header class="ui-card__header">
              <h3 class="ui-card__title">8 metas en riesgo</h3>
              <p class="ui-card__subtitle">warning</p>
            </header>
          </article>

          <article class="ui-card ui-card--accent ui-card--interactive">
            <header class="ui-card__header">
              <h3 class="ui-card__title">Banco de Iniciativas</h3>
              <p class="ui-card__subtitle">accent · interactive</p>
            </header>
            <div class="ui-card__body">280 colectivos meta.</div>
          </article>
        </div>
      </section>

      <!-- Buttons -->
      <section class="ui-section">
        <h2 class="ui-section__title">Botones</h2>
        <div class="row">
          <button class="ui-btn ui-btn--primary">Primary</button>
          <button class="ui-btn ui-btn--secondary">Secondary</button>
          <button class="ui-btn ui-btn--outline">Outline</button>
          <button class="ui-btn ui-btn--ghost">Ghost</button>
          <button class="ui-btn ui-btn--danger">Danger</button>
          <button class="ui-btn ui-btn--accent">Accent</button>
        </div>
        <div class="row">
          <button class="ui-btn ui-btn--primary ui-btn--sm">Small</button>
          <button class="ui-btn ui-btn--primary">Medium</button>
          <button class="ui-btn ui-btn--primary ui-btn--lg">Large</button>
          <button class="ui-btn ui-btn--primary" disabled>Disabled</button>
        </div>
      </section>

      <!-- Badges -->
      <section class="ui-section">
        <h2 class="ui-section__title">Badges</h2>
        <div class="row">
          <span class="ui-badge ui-badge--primary">Primary</span>
          <span class="ui-badge ui-badge--success">Validada</span>
          <span class="ui-badge ui-badge--warning">Pendiente</span>
          <span class="ui-badge ui-badge--danger">Rechazada</span>
          <span class="ui-badge ui-badge--info">Info</span>
          <span class="ui-badge ui-badge--neutral">Neutral</span>
        </div>
      </section>

      <!-- Filter Bar -->
      <section class="ui-section">
        <h2 class="ui-section__title">Filter Bar</h2>
        <div class="ui-filter-bar">
          <div class="ui-filter-bar__group">
            <label class="ui-filter-bar__label" for="f-estado">Estado</label>
            <select id="f-estado" class="ui-filter-bar__field">
              <option>Todos</option>
              <option>Validadas</option>
              <option>Pendientes</option>
            </select>
          </div>
          <div class="ui-filter-bar__group">
            <label class="ui-filter-bar__label" for="f-search">Buscar</label>
            <input id="f-search" type="search" class="ui-filter-bar__field"
                   placeholder="Por cédula, nombre…">
          </div>
          <div class="ui-filter-bar__actions">
            <button class="ui-btn ui-btn--primary ui-btn--sm">Aplicar</button>
            <button class="ui-btn ui-btn--ghost ui-btn--sm">Limpiar</button>
          </div>
        </div>
      </section>

      <!-- Table -->
      <section class="ui-section">
        <h2 class="ui-section__title">Tabla</h2>
        <div class="ui-table-responsive">
          <table class="ui-table">
            <thead>
              <tr>
                <th>#</th>
                <th>Documento</th>
                <th>Nombre</th>
                <th class="ui-table__cell--center">Estado</th>
                <th class="ui-table__cell--right">Avance</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td>1</td>
                <td><code>1234567890</code></td>
                <td>Juan Pérez</td>
                <td class="ui-table__cell--center"><span class="ui-badge ui-badge--success">Validada</span></td>
                <td class="ui-table__cell--right"><strong>4.50</strong></td>
              </tr>
              <tr>
                <td>2</td>
                <td><code>0987654321</code></td>
                <td>Ana Gómez</td>
                <td class="ui-table__cell--center"><span class="ui-badge ui-badge--warning">Pendiente</span></td>
                <td class="ui-table__cell--right">—</td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>

      <!-- Empty State -->
      <section class="ui-section">
        <h2 class="ui-section__title">Empty State</h2>
        <div class="ui-empty-state">
          <i class="fa fa-folder-open" aria-hidden="true"></i>
          <p>No hay actividades registradas en este filtro.</p>
          <button class="ui-btn ui-btn--primary">Crear nueva actividad</button>
        </div>
      </section>

      <!-- Info Bar -->
      <section class="ui-section">
        <h2 class="ui-section__title">Info Bar</h2>
        <div class="ui-info-bar ui-info-bar--info">
          <strong>Info:</strong> Esta actividad aporta al KPI de Kennedy Fuerza Local.
        </div>
        <div class="ui-info-bar ui-info-bar--success">
          <strong>OK:</strong> Inscripción validada correctamente.
        </div>
        <div class="ui-info-bar ui-info-bar--warning">
          <strong>Atención:</strong> Faltan campos por completar.
        </div>
      </section>

      <!-- Hub Cards -->
      <section class="ui-section">
        <h2 class="ui-section__title">Hub Cards (dashboard)</h2>
        <div class="hub-grid">
          <a class="hub-card hub-card--primary" href="#">
            <div class="hub-card__icon"><i class="fa fa-chart-line"></i></div>
            <h3 class="hub-card__title">Presupuesto</h3>
            <p class="hub-card__subtitle">Proyectos, programas, KPIs</p>
          </a>
          <a class="hub-card hub-card--success" href="#">
            <div class="hub-card__icon"><i class="fa fa-calendar-check"></i></div>
            <h3 class="hub-card__title">Actividades</h3>
            <p class="hub-card__subtitle">Eventos, capacitaciones</p>
          </a>
          <a class="hub-card hub-card--accent" href="#">
            <div class="hub-card__icon"><i class="fa fa-trophy"></i></div>
            <h3 class="hub-card__title">Banco de Iniciativas</h3>
            <p class="hub-card__subtitle">280 colectivos meta</p>
          </a>
        </div>
      </section>
    </div>
  `,
  styles: [`
    :host { display: block; padding: 2rem 1.5rem; max-width: 1200px; margin: 0 auto; }
    .ui-page__header { margin-bottom: 2rem; }
    .ui-page__header h1 { margin: 0; }
    .ui-page__header p { color: #6B7280; margin-top: 0.25rem; }
    .ui-section { margin-bottom: 2.5rem; }
    .ui-section__title { font-size: 1rem; color: #6B7280;
                         letter-spacing: 0.01em; margin-bottom: 0.75rem; }
    .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
            gap: 1rem; }
    .row { display: flex; gap: 0.75rem; flex-wrap: wrap; margin-bottom: 0.75rem;
           align-items: center; }
  `],
})
export class ShowcaseComponent implements OnInit {
  private layout = inject(LayoutService);

  ngOnInit(): void {
    this.layout.setBreadcrumb([
      { label: 'Inicio', url: '/' },
      { label: 'UI Showcase' },
    ]);
  }
}
