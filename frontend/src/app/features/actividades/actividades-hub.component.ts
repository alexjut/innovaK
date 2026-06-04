import { CommonModule } from '@angular/common';
import {
  ChangeDetectionStrategy, Component, OnInit, inject, signal,
} from '@angular/core';
import { RouterLink } from '@angular/router';
import { ActividadesService, HubTiposResponse } from '../../core/actividades/actividades.service';
import { LayoutService } from '../../core/layout/layout.service';

/**
 * Hub principal de Actividades — Angular nativo.
 *
 * Reemplaza el iframe al hub Django. Consume
 * `GET /api/actividades/tipos/` que ya filtra por módulos del usuario.
 */
@Component({
  standalone: true,
  selector: 'app-actividades-hub',
  imports: [CommonModule, RouterLink],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <div class="hub">
      <header class="hub__header">
        <h1>
          <i class="fa fa-calendar-check" aria-hidden="true"></i>
          Actividades
        </h1>
        <p class="hub__subtitle">
          Eventos, capacitaciones, cursos, inscripciones, caracterizaciones
          y entregas del territorio. Selecciona un tipo de actividad para
          operar.
        </p>
      </header>

      @if (loading()) {
        <div class="hub__loading">Cargando…</div>
      } @else if (errorMsg()) {
        <div class="hub__error">⚠ {{ errorMsg() }}</div>
      } @else {
        @if (data()?.cards_admin?.length) {
          <section class="hub-section">
            <h2 class="hub-section__title">Administrativo</h2>
            <div class="hub-grid">
              @for (c of data()!.cards_admin; track c.codigo) {
                <a [routerLink]="c.ruta"
                   class="ui-card ui-card--interactive"
                   [class]="'ui-card--' + c.color">
                  <div class="hub-card__icon">
                    <i class="fa" [class]="c.icono"></i>
                  </div>
                  <div class="ui-card__body">
                    <h3 class="ui-card__title">{{ c.nombre }}</h3>
                    <p class="ui-card__subtitle">{{ c.subtitulo }}</p>
                  </div>
                </a>
              }
            </div>
          </section>
        }

        <section class="hub-section">
          <h2 class="hub-section__title">Tipos de actividad</h2>
          @if (data()?.tipos?.length) {
            <div class="hub-grid">
              @for (t of data()!.tipos; track t.codigo) {
                <a [routerLink]="['/actividades/tipo', t.codigo]"
                   class="ui-card ui-card--interactive ui-card--info">
                  <div class="hub-card__icon"
                       [style.color]="t.color_hex">
                    <i class="fa" [class]="t.icono"></i>
                  </div>
                  <div class="ui-card__body">
                    <h3 class="ui-card__title">{{ t.nombre }}</h3>
                    <p class="ui-card__subtitle">
                      {{ t.descripcion || ('Actividades de tipo ' + t.codigo) }}
                    </p>
                    <small class="hub-card__meta">
                      {{ t.num_eventos }} evento{{ t.num_eventos === 1 ? '' : 's' }}
                    </small>
                  </div>
                </a>
              }
            </div>
          } @else {
            <div class="ui-empty-state">
              <i class="fa fa-info-circle"></i>
              <p>Tu rol no tiene acceso a ningún tipo de actividad.
                 Contacta al administrador.</p>
            </div>
          }
        </section>
      }
    </div>
  `,
  styles: [`
    @use '../../../styles/tokens' as *;
    :host { display: block; }
    .hub { max-width: 1200px; margin: 0 auto; }
    .hub__header { margin-bottom: $space-6; }
    .hub__header h1 {
      margin: 0;
      color: $color-primary;
      i { margin-right: $space-2; }
    }
    .hub__subtitle {
      color: $color-text-muted;
      margin: $space-2 0 0;
      max-width: 720px;
    }
    .hub__loading, .hub__error {
      padding: $space-4;
      text-align: center;
      color: $color-text-muted;
    }
    .hub__error { color: $color-danger; }
    .hub-section { margin-top: $space-5; }
    .hub-section__title {
      font-size: $font-size-md;
      color: $color-text-muted;
      text-transform: uppercase;
      letter-spacing: 0.06em;
      margin: 0 0 $space-3;
    }
    .hub-card__meta {
      display: block;
      margin-top: $space-1;
      color: $color-text-muted;
      font-size: $font-size-xs;
    }
  `],
})
export class ActividadesHubComponent implements OnInit {
  private svc = inject(ActividadesService);
  private layout = inject(LayoutService);

  data = signal<HubTiposResponse | null>(null);
  loading = signal<boolean>(true);
  errorMsg = signal<string>('');

  /** Las cards admin (Lista/Crear/Tipos) siguen apuntando al CRUD
   * Django mientras no haya editor de evento nativo. */
  djangoBase = '';

  ngOnInit(): void {
    this.layout.setBreadcrumb([
      { label: 'Inicio', url: '/' },
      { label: 'Actividades' },
    ]);
    this.svc.tipos().subscribe({
      next: (r) => {
        this.data.set(r);
        this.loading.set(false);
        // Las cards admin apuntan al Django legacy hasta que haya editor nativo.
        // El href absoluto a /<ruta> queda mejor expresado sin prefijo —
        // mismo origen. Sustituimos: la URL Django real está en /login/...
        // pero ya el template Django acepta `/evento/...` etc.
      },
      error: () => {
        this.errorMsg.set('No se pudieron cargar los tipos de actividad.');
        this.loading.set(false);
      },
    });
  }
}
