import { CommonModule } from '@angular/common';
import { Component, OnInit, computed, inject } from '@angular/core';
import { RouterLink } from '@angular/router';
import { AuthService } from '../../core/auth/auth.service';
import { ConfigService } from '../../core/config/config.service';
import { LayoutService } from '../../core/layout/layout.service';

/**
 * Hub principal (replica `dashboard_home` de Django).
 *
 * Muestra cards de los 9 módulos productivos. Cada card es visible
 * solo si el usuario tiene al menos uno de los módulos requeridos.
 *
 * El backend ya hizo el filtrado: `auth.modules()` viene de `/api/me/`
 * que reusa el mismo servicio `permisos.get_modulos_usuario()` que
 * gatea el dashboard HTML legacy. Cero divergencia.
 */

interface HubCard {
  title: string;
  subtitle: string;
  icon: string;
  color: 'primary' | 'success' | 'info' | 'warning' | 'accent' | 'danger';
  route: string;
  /** Card visible si el user tiene CUALQUIERA de estos módulos. */
  modules: string[];
}

const CARDS: HubCard[] = [
  {
    title: 'Presupuesto',
    subtitle: 'Proyectos, programas, KPIs y avances',
    icon: 'fa-chart-line',
    color: 'primary',
    route: '/presupuesto',
    modules: ['presupuesto_proyectos', 'presupuesto_cdp', 'presupuesto_metas'],
  },
  {
    title: 'Actividades',
    subtitle: 'Eventos, capacitaciones y entregas',
    icon: 'fa-calendar-check',
    color: 'success',
    route: '/eventos',
    modules: ['eventos', 'tipos_evento', 'banco_iniciativas', 'cursos', 'eventos_asistencia'],
  },
  {
    title: 'Banco de Iniciativas',
    subtitle: 'Validar/rechazar inscripciones',
    icon: 'fa-trophy',
    color: 'accent',
    route: '/banco',
    modules: ['banco_iniciativas'],
  },
  {
    title: 'Jóvenes a la E',
    subtitle: 'Entrega de becas y dotación',
    icon: 'fa-graduation-cap',
    color: 'info',
    route: '/jovenes',
    modules: ['jovenes_a_la_e'],
  },
  {
    title: 'Caracterización',
    subtitle: '6 wizards: cultura, deporte, mujer…',
    icon: 'fa-clipboard-list',
    color: 'warning',
    route: '/caracterizacion',
    modules: ['caracterizacion'],
  },
  {
    title: 'Cursos del docente',
    subtitle: 'Sesiones, asistencia, notas, reporte',
    icon: 'fa-chalkboard-teacher',
    color: 'accent',
    route: '/cursos',
    modules: ['cursos', 'eventos_asistencia'],
  },
  {
    title: 'Mapa Kennedy',
    subtitle: 'Eventos en territorio',
    icon: 'fa-map-marked-alt',
    color: 'info',
    route: '/mapa',
    modules: ['mapa_kennedy'],
  },
  {
    title: 'Votaciones',
    subtitle: 'Gestión de eventos de votación',
    icon: 'fa-vote-yea',
    color: 'danger',
    route: '/votaciones',
    modules: ['votaciones_admin', 'votaciones_votantes'],
  },
  {
    title: 'Consulta IA',
    subtitle: 'Pregunta en lenguaje natural',
    icon: 'fa-brain',
    color: 'warning',
    route: '/ia',
    modules: ['dashboard_ia'],
  },
  {
    title: 'Administración',
    subtitle: 'Roles, personas, organización',
    icon: 'fa-cogs',
    color: 'accent',
    route: '/admin',
    modules: ['roles', 'org_admin', 'tipos_evento', 'personas_registro'],
  },
];

@Component({
  standalone: true,
  selector: 'app-hub',
  imports: [CommonModule, RouterLink],
  template: `
    <div class="hub">
      <header class="hub__header">
        <h1>Hola, {{ auth.displayName() }}</h1>
        <p class="hub__subtitle">{{ cfg.alcaldiaName }} · {{ cfg.appName }}</p>
        @if (auth.user()?.is_superuser) {
          <span class="ui-badge ui-badge--primary">Superusuario</span>
        } @else if (visibleCards().length === 0) {
          <div class="ui-info-bar ui-info-bar--warning">
            <strong>Atención:</strong> Tu rol no tiene módulos asignados.
            Contacta al administrador del sistema.
          </div>
        }
      </header>

      @if (visibleCards().length > 0) {
        <div class="hub-grid">
          @for (card of visibleCards(); track card.route) {
            <a
              [routerLink]="card.route"
              class="hub-card"
              [class]="'hub-card--' + card.color"
            >
              <div class="hub-card__icon">
                <i class="fa" [class]="card.icon" aria-hidden="true"></i>
              </div>
              <h3 class="hub-card__title">{{ card.title }}</h3>
              <p class="hub-card__subtitle">{{ card.subtitle }}</p>
            </a>
          }
        </div>
      }

      <footer class="hub__footer">
        <small>
          {{ auth.modules().size }} módulo{{ auth.modules().size === 1 ? '' : 's' }} asignado{{ auth.modules().size === 1 ? '' : 's' }}
          @if (auth.user()?.groups?.length) {
            · Rol: {{ auth.user()!.groups.join(', ') }}
          }
        </small>
      </footer>
    </div>
  `,
  styles: [`
    @use '../../../styles/tokens' as *;

    :host { display: block; }
    .hub { max-width: 1100px; margin: 0 auto; }
    .hub__header { margin-bottom: $space-6; }
    .hub__header h1 {
      margin: 0;
      color: $color-primary;
      font-size: $font-size-3xl;
    }
    .hub__subtitle { margin: $space-1 0 $space-3; color: $color-text-muted; }
    .hub__footer {
      margin-top: $space-6;
      padding-top: $space-3;
      border-top: 1px solid $color-border;
      color: $color-text-muted;
      text-align: center;
    }
  `],
})
export class HubComponent implements OnInit {
  cfg = inject(ConfigService);
  auth = inject(AuthService);
  private layout = inject(LayoutService);

  readonly visibleCards = computed<HubCard[]>(() => {
    if (this.auth.user()?.is_superuser) return CARDS;
    const mods = this.auth.modules();
    return CARDS.filter((c) => c.modules.some((m) => mods.has(m)));
  });

  ngOnInit(): void {
    this.layout.setBreadcrumb([{ label: 'Inicio' }]);
  }
}
