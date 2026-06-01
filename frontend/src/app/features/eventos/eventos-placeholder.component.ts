import { CommonModule } from '@angular/common';
import { Component, OnInit, inject } from '@angular/core';
import { ConfigService } from '../../core/config/config.service';
import { LayoutService } from '../../core/layout/layout.service';

/**
 * Placeholder del módulo Eventos.
 *
 * El backend aún tiene el CRUD de Evento principalmente en HTML
 * Django legacy (no hay DRF completo de listado/edición de eventos).
 *
 * Mientras se construye el endpoint DRF, este placeholder ofrece
 * link directo al hub de Actividades del Django legacy (mismo
 * funcionario, mismo gating de módulos) para no perder usabilidad.
 *
 * Cuando exista `/api/v2/eventos/` con CRUD completo, este componente
 * se reemplaza por la lista paginada estilo Banco/Jóvenes.
 */
@Component({
  standalone: true,
  selector: 'app-eventos-placeholder',
  imports: [CommonModule],
  template: `
    <div class="page">
      <header class="page__header">
        <h1>Actividades / Eventos</h1>
        <p class="page__subtitle">Listar, crear y editar eventos en territorio.</p>
      </header>

      <article class="ui-card ui-card--info">
        <header class="ui-card__header">
          <h2 class="ui-card__title">Próximamente en Angular</h2>
          <p class="ui-card__subtitle">
            El CRUD completo de eventos llegará en el próximo iteración.
          </p>
        </header>
        <div class="ui-card__body">
          <p>
            Mientras tanto, sigue usando el hub de Actividades en la versión
            actual del sistema:
          </p>
          <p>
            <a [href]="hubUrl" target="_blank" rel="noopener" class="ui-btn ui-btn--primary">
              <i class="fa fa-external-link-alt" aria-hidden="true"></i>
              Abrir Hub de Actividades (versión actual)
            </a>
          </p>
          <p>
            Endpoints DRF disponibles ahora:
          </p>
          <ul>
            <li><code>POST /api/eventos/&lt;id&gt;/inscripciones/</code> — inscripción pública por QR</li>
            <li><code>GET /api/eventos/&lt;id&gt;/sesiones/</code> — sesiones del curso</li>
            <li><code>POST /api/sesiones/&lt;id&gt;/asistencia/</code> — tomar lista</li>
            <li><code>GET /api/eventos/&lt;id&gt;/reporte/</code> — reporte consolidado</li>
          </ul>
          <p>
            El feature <strong>Cursos del docente</strong> (siguiente en el
            sidebar) ya consume estos endpoints.
          </p>
        </div>
      </article>
    </div>
  `,
  styles: [`
    @use '../../../styles/tokens' as *;
    :host { display: block; }
    .page { max-width: 900px; margin: 0 auto; }
    .page__header h1 { margin: 0; color: $color-primary; }
    .page__subtitle { color: $color-text-muted; margin: $space-1 0 $space-4; }
    ul { padding-left: $space-6; }
    li { margin: $space-1 0; }
  `],
})
export class EventosPlaceholderComponent implements OnInit {
  private cfg = inject(ConfigService);
  private layout = inject(LayoutService);

  get hubUrl(): string {
    return this.cfg.url('/dashboard/hub/actividades/');
  }

  ngOnInit(): void {
    this.layout.setBreadcrumb([
      { label: 'Inicio', url: '/' },
      { label: 'Actividades' },
    ]);
  }
}
