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

/**
 * Hub principal. El flujo operativo arranca SIEMPRE en "Actividades"
 * (hub central): el usuario elige el tipo de evento + subgrupo y
 * desde ahí se abre el sub-flujo correspondiente (banco / jóvenes /
 * caracterización / cursos / asistencia genérica).
 *
 * Los módulos Banco/Jóvenes/Caracterización/Cursos NO son cards
 * top-level porque eso confunde al operador. Quedan accesibles solo
 * desde dentro de una actividad de su tipo correspondiente.
 *
 * Cards top-level reducidas: Actividades (entrada principal),
 * Presupuesto, Mapa, Votaciones, IA y Administración.
 */
const CARDS: HubCard[] = [
  {
    title: 'Actividades',
    subtitle: 'Punto de entrada al flujo operativo. Selecciona el tipo (curso, banco, becas, caracterización…) y el equipo del subgrupo.',
    icon: 'fa-calendar-check',
    color: 'primary',
    route: '/actividades',
    modules: [
      'eventos', 'tipos_evento',
      'banco_iniciativas', 'jovenes_a_la_e', 'caracterizacion',
      'cursos', 'eventos_asistencia',
    ],
  },
  {
    title: 'Presupuesto',
    subtitle: 'Proyectos, CDPs, contratos, KPIs y avances',
    icon: 'fa-chart-line',
    color: 'accent',
    route: '/presupuesto',
    modules: ['presupuesto_proyectos', 'presupuesto_cdp', 'presupuesto_metas'],
  },
  {
    title: 'Festivales',
    subtitle: 'Festivales de Cultura: registro, galería, aforo, jurados y meta (proyecto 2780)',
    icon: 'fa-music',
    color: 'primary',
    route: '/festivales',
    modules: ['festivales'],
  },
  {
    title: 'Mapa Kennedy',
    subtitle: 'Eventos, parques y escuelas en territorio',
    icon: 'fa-map-marked-alt',
    color: 'info',
    route: '/mapa',
    modules: ['mapa_kennedy'],
  },
  {
    title: 'Votaciones',
    subtitle: 'Eventos de votación, candidatos y resultados',
    icon: 'fa-vote-yea',
    color: 'danger',
    route: '/votaciones',
    modules: ['votaciones_admin', 'votaciones_votantes'],
  },
  {
    title: 'Consulta IA',
    subtitle: 'Pregunta en lenguaje natural sobre el sistema',
    icon: 'fa-brain',
    color: 'warning',
    route: '/ia',
    modules: ['dashboard_ia'],
  },
  {
    title: 'Administración',
    subtitle: 'Roles, organización, personas',
    icon: 'fa-cogs',
    color: 'success',
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
    .hub__header { margin-bottom: $space-8; }
    .hub__header h1 {
      margin: 0 0 $space-2;
      color: $color-primary;
      font-size: $font-size-3xl;
      font-weight: $font-weight-bold;

      // Línea amarilla institucional bajo el saludo
      &::after {
        content: '';
        display: block;
        margin-top: $space-2;
        width: 48px;
        height: 4px;
        border-radius: 999px;
        background: $color-secondary;
      }
    }
    .hub__subtitle { margin: $space-3 0 $space-3; color: $color-text-muted; font-size: $font-size-md; }
    .hub__footer {
      margin-top: $space-8;
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
