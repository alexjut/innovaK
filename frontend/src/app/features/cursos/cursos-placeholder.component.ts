import { CommonModule } from '@angular/common';
import { Component, OnInit, inject } from '@angular/core';
import { ConfigService } from '../../core/config/config.service';
import { LayoutService } from '../../core/layout/layout.service';

/**
 * Placeholder del módulo Cursos. El listado de "Mis cursos" del
 * docente aún solo está en HTML Django (apps/login/views/curso_docente).
 *
 * Los endpoints DRF de sesiones/asistencia/notas/reporte SÍ existen
 * desde la Etapa D Curso Docente PR-B..PR-D. Cuando se agregue el
 * endpoint `GET /api/cursos/mios/` se reemplazará este placeholder
 * por la lista interactiva.
 */
@Component({
  standalone: true,
  selector: 'app-cursos-placeholder',
  imports: [CommonModule],
  template: `
    <div class="page">
      <header class="page__header">
        <h1>Cursos del docente</h1>
        <p class="page__subtitle">Sesiones, asistencia, notas y reporte por curso.</p>
      </header>

      <article class="ui-card ui-card--accent">
        <header class="ui-card__header">
          <h2 class="ui-card__title">Mis cursos</h2>
        </header>
        <div class="ui-card__body">
          <p>
            El listado de cursos asignados al docente aún se sirve desde
            la versión actual del sistema. Sigue este enlace:
          </p>
          <p>
            <a [href]="misCursosUrl" target="_blank" rel="noopener"
               class="ui-btn ui-btn--accent">
              <i class="fa fa-chalkboard-teacher" aria-hidden="true"></i>
              Abrir Mis Cursos (versión actual)
            </a>
          </p>

          <hr>

          <h3>Ya disponibles en Angular vía API:</h3>
          <ul>
            <li>
              <strong>Sesiones del curso</strong> —
              <code>GET /api/eventos/&lt;id&gt;/sesiones/</code>
            </li>
            <li>
              <strong>Tomar lista de una sesión</strong> —
              <code>POST /api/sesiones/&lt;id&gt;/asistencia/</code>
            </li>
            <li>
              <strong>Registrar notas</strong> —
              <code>POST /api/eventos/&lt;id&gt;/notas/</code>
            </li>
            <li>
              <strong>Reporte consolidado</strong> —
              <code>GET /api/eventos/&lt;id&gt;/reporte/</code>
            </li>
          </ul>

          <p>
            <small class="muted">
              El cliente HTTP de estos endpoints está en
              <code>features/cursos/cursos.api.ts</code> listo para usar
              cuando se agreguen las vistas Angular respectivas.
            </small>
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
    h3 { margin: $space-4 0 $space-2; font-size: $font-size-md; }
    ul { padding-left: $space-6; }
    li { margin: $space-1 0; }
    hr { border: 0; border-top: 1px solid $color-border; margin: $space-4 0; }
    .muted { color: $color-text-muted; }
  `],
})
export class CursosPlaceholderComponent implements OnInit {
  private cfg = inject(ConfigService);
  private layout = inject(LayoutService);

  get misCursosUrl(): string {
    return this.cfg.url('/cursos/');
  }

  ngOnInit(): void {
    this.layout.setBreadcrumb([
      { label: 'Inicio', url: '/' },
      { label: 'Cursos del docente' },
    ]);
  }
}
