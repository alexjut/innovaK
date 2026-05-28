import { CommonModule } from '@angular/common';
import { Component, computed, inject } from '@angular/core';
import { RouterLink, RouterLinkActive } from '@angular/router';
import { AuthService } from '../../auth/auth.service';
import { LayoutService } from '../layout.service';

/**
 * Menú lateral institucional. Replica `.base-sidebar` del Django legacy
 * pero los items se filtran por módulos del usuario (cuando llegue el
 * AuthService completo en PR-4).
 *
 * Estructura:
 *   - Backdrop blur, border-left rojo 5px, border-radius grande.
 *   - Overlay slide-in: transform translateX(-120%) → translateX(0).
 *   - Cada item con icono FA + label.
 *   - Active state según ruta actual.
 *
 * Hoy (PR-3) los items son estáticos representativos. PR-5 conecta el
 * filtrado por módulo desde `auth.modules()`.
 */

interface SidebarItem {
  label: string;
  icon: string;
  route: string;
  /** Módulo requerido (cuando llegue PR-5). null = siempre visible. */
  module?: string | null;
}

interface SidebarGroup {
  title: string;
  items: SidebarItem[];
}

const MENU: SidebarGroup[] = [
  {
    title: 'Principal',
    items: [
      { label: 'Inicio', icon: 'fa-home', route: '/' },
      { label: 'UI Showcase', icon: 'fa-palette', route: '/showcase' },
    ],
  },
  {
    title: 'Módulos',
    items: [
      { label: 'Dashboard', icon: 'fa-tachometer-alt', route: '/dashboard' },
      { label: 'Presupuesto', icon: 'fa-coins', route: '/presupuesto' },
      { label: 'Actividades', icon: 'fa-calendar-check', route: '/eventos' },
      { label: 'Banco de Iniciativas', icon: 'fa-trophy', route: '/banco' },
      { label: 'Jóvenes a la E', icon: 'fa-graduation-cap', route: '/jovenes' },
      { label: 'Caracterización', icon: 'fa-clipboard-list', route: '/caracterizacion' },
      { label: 'Cursos', icon: 'fa-chalkboard-teacher', route: '/cursos' },
      { label: 'Mapa Kennedy', icon: 'fa-map-marked-alt', route: '/mapa' },
      { label: 'Votaciones', icon: 'fa-vote-yea', route: '/votaciones' },
    ],
  },
  {
    title: 'Administración',
    items: [
      { label: 'Roles', icon: 'fa-user-shield', route: '/admin/roles', module: 'roles' },
      { label: 'Organización', icon: 'fa-building', route: '/admin/org', module: 'org_admin' },
    ],
  },
];

@Component({
  standalone: true,
  selector: 'app-sidebar',
  imports: [CommonModule, RouterLink, RouterLinkActive],
  templateUrl: './sidebar.component.html',
  styleUrl: './sidebar.component.scss',
})
export class SidebarComponent {
  layout = inject(LayoutService);
  auth = inject(AuthService);

  /** Items filtrados por módulo del usuario. PR-5 implementa el filtro real. */
  readonly groups = computed<SidebarGroup[]>(() => {
    // TODO PR-5: filtrar items según auth.modules().
    return MENU;
  });

  closeAndNavigate(): void {
    this.layout.closeSidebar();
  }
}
