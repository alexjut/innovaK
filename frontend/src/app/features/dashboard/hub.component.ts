import { CommonModule } from '@angular/common';
import { HttpClient } from '@angular/common/http';
import { Component, OnInit, computed, inject, signal } from '@angular/core';
import { RouterLink } from '@angular/router';
import { LucideAngularModule } from 'lucide-angular';
import { AuthService } from '../../core/auth/auth.service';
import { ConfigService } from '../../core/config/config.service';
import { LayoutService } from '../../core/layout/layout.service';
import { TourService } from '../onboarding/tour.service';

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
    // La puerta a las 15 áreas: cada subgrupo tiene su lugar y se entra por
    // acá. Va de primera porque para el operativo es el punto de partida —
    // "Actividades" es el flujo, "Mi área" es dónde vive lo suyo.
    title: 'Mi área',
    subtitle: 'Tu subgrupo: el plan, la plata, lo ejecutado y lo que falta enganchar.',
    icon: 'fa-sitemap',
    color: 'primary',
    route: '/subgrupo',
    modules: ['eventos'],
  },
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
    title: 'Educación',
    subtitle: 'Colegios distritales de Kennedy: sedes, matrícula e insumos entregados',
    icon: 'fa-graduation-cap',
    color: 'primary',
    route: '/educacion',
    modules: ['educacion'],
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
  imports: [CommonModule, RouterLink, LucideAngularModule],
  template: `
    <div class="hub">
      <header class="welcome" data-tour="welcome-banner">
        <div class="welcome__text">
          <h1>¡Bienvenido a innovaK!</h1>
          <p class="welcome__sub">Hola, {{ auth.displayName() }} · {{ cfg.alcaldiaName }}</p>
          <span class="welcome__hint">Soy Kenny 🐦, tu asistente. Elige un módulo o pregúntame abajo a la derecha.</span>
          @if (auth.user()?.is_superuser) {
            <span class="ui-badge ui-badge--light">Superusuario</span>
          } @else if (visibleCards().length === 0) {
            <div class="ui-info-bar ui-info-bar--warning">
              <strong>Atención:</strong> Tu rol no tiene módulos asignados.
              Contacta al administrador del sistema.
            </div>
          }
        </div>
        <img class="welcome__kenny" src="kenny/cuerpo.png" alt="Kenny, mascota de la Alcaldía Local de Kennedy" draggable="false" />
      </header>

      @if (visibleCards().length > 0) {
        <div class="hub-grid" data-tour="hub-cards">
          @for (card of visibleCards(); track card.route) {
            <a
              [routerLink]="card.route"
              class="hub-card"
              [class]="'hub-card--' + card.color"
            >
              <div class="hub-card__icon">
                <lucide-icon [name]="lucideDe(card)" [size]="26" aria-hidden="true"></lucide-icon>
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

    .welcome {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: $space-4;
      background: linear-gradient(120deg, #e41e26, #c8161d);
      border-radius: 20px;
      padding: 22px 28px;
      margin-bottom: $space-8;
      box-shadow: 0 14px 34px rgba(228, 30, 38, 0.28);
      overflow: hidden;
    }
    .welcome__text { color: #fff; min-width: 0; }
    .welcome__text h1 {
      margin: 0;
      font-size: $font-size-3xl;
      font-weight: $font-weight-bold;
      color: #fff;
    }
    .welcome__sub { margin: 8px 0 2px; color: #ffe3e4; font-size: $font-size-md; }
    .welcome__hint { display: block; margin-top: 4px; color: #ffd9da; font-size: $font-size-sm; }
    .welcome__kenny {
      height: 138px;
      width: auto;
      flex: none;
      user-select: none;
      filter: drop-shadow(0 8px 14px rgba(0, 0, 0, 0.25));
    }
    .ui-badge--light {
      display: inline-block;
      margin-top: 8px;
      background: rgba(255, 255, 255, 0.18);
      color: #fff;
      border-radius: 999px;
      padding: 3px 12px;
      font-size: 12px;
      font-weight: 700;
    }
    @media (max-width: 620px) {
      .welcome { padding: 18px 20px; }
      .welcome__kenny { height: 92px; }
      .welcome__text h1 { font-size: $font-size-2xl; }
    }
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
  private http = inject(HttpClient);
  private tour = inject(TourService);

  // Cards traídas del backend (tabla hub_card, manejadas por datos). null
  // hasta que responda; si falla, se usa el fallback hardcodeado.
  private cards = signal<HubCard[] | null>(null);

  readonly visibleCards = computed<HubCard[]>(() => {
    const fromApi = this.cards();
    if (fromApi !== null) return fromApi;  // backend ya filtró por módulos
    // Fallback (sin red): filtra las cards por defecto con los módulos locales.
    if (this.auth.user()?.is_superuser) return CARDS;
    const mods = this.auth.modules();
    return CARDS.filter((c) => c.modules.some((m) => mods.has(m)));
  });

  // Icono lucide por ruta (estable frente a cambios de título del backend).
  private readonly LUCIDE: Record<string, string> = {
    '/subgrupo': 'layout-grid',
    '/actividades': 'calendar-check',
    '/presupuesto': 'wallet',
    '/festivales': 'party-popper',
    '/educacion': 'graduation-cap',
    '/mapa': 'map-pin',
    '/votaciones': 'vote',
    '/ia': 'sparkles',
    '/admin': 'shield',
  };

  lucideDe(card: HubCard): string {
    return this.LUCIDE[card.route] ?? 'layout-dashboard';
  }

  ngOnInit(): void {
    this.layout.setBreadcrumb([{ label: 'Inicio' }]);
    this.http
      .get<{ cards: ApiCard[] }>(this.cfg.url('/dashboard/api/hub/cards/'))
      .subscribe({
        next: (r) => this.cards.set((r.cards || []).map(toHubCard)),
        error: () => this.cards.set(null),  // mantiene el fallback
      });

    // Onboarding Kenny: arranca el tour del hub la primera vez. Espera al
    // render de las cards (el tour apunta a [data-tour="hub-cards"]).
    setTimeout(() => this.tour.iniciarSiProcede('hub-principal'), 700);
  }
}

interface ApiCard {
  codigo: string; titulo: string; subtitulo: string;
  icono: string; color: string; ruta: string; modulos: string[];
}

function toHubCard(c: ApiCard): HubCard {
  return {
    title: c.titulo, subtitle: c.subtitulo, icon: c.icono,
    color: (c.color as HubCard['color']) || 'primary',
    route: c.ruta, modules: c.modulos || [],
  };
}
