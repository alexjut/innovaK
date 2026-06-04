import { CommonModule } from '@angular/common';
import { Component, computed, inject } from '@angular/core';
import { RouterLink, RouterLinkActive } from '@angular/router';
import { AuthService } from '../../auth/auth.service';
import { LayoutService } from '../layout.service';

/**
 * Menú lateral institucional. Replica `.base-sidebar` del Django legacy.
 *
 * Items filtrados por módulos N15 del usuario via `auth.hasModule()`.
 * Superuser ve todo. Invitado solo ve "Iniciar sesión" (los items
 * gated quedan ocultos).
 */

interface SidebarItem {
  label: string;
  icon: string;
  route: string;
  /** Módulo N15 requerido. null = siempre visible (auth o no). */
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
      { label: 'Inicio', icon: 'fa-home', route: '/', module: null },
      { label: 'UI Showcase', icon: 'fa-palette', route: '/showcase', module: null },
    ],
  },
  {
    title: 'Módulos',
    items: [
      // Reorg 2026-06-01: Actividades es el hub central. Banco / Jóvenes /
      // Caracterización / Cursos NO son items top-level — viven dentro de
      // /actividades/tipo/<código>/sub/<subgrupo>. Aparecen automáticamente
      // según el tipo_evento del evento que se esté gestionando.
      { label: 'Actividades', icon: 'fa-calendar-check', route: '/actividades', module: 'eventos' },
      { label: 'Presupuesto', icon: 'fa-coins', route: '/presupuesto', module: 'presupuesto_proyectos' },
      { label: 'Mapa Kennedy', icon: 'fa-map-marked-alt', route: '/mapa', module: 'mapa_kennedy' },
      { label: 'Votaciones', icon: 'fa-vote-yea', route: '/votaciones', module: 'votaciones_admin' },
      { label: 'Consulta IA', icon: 'fa-brain', route: '/ia', module: 'dashboard_ia' },
    ],
  },
  {
    title: 'Administración',
    items: [
      { label: 'Roles', icon: 'fa-user-shield', route: '/admin/roles', module: 'roles' },
      { label: 'Organización', icon: 'fa-building', route: '/admin/org', module: 'org_admin' },
      { label: 'Personas', icon: 'fa-user-plus', route: '/admin/personas', module: 'personas_registro' },
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

  /**
   * Grupos filtrados: cada item pasa si module=null o si el user lo tiene.
   * Si no hay user (no logueado), solo se ven items con module=null.
   * Los grupos vacíos no se muestran.
   */
  readonly groups = computed<SidebarGroup[]>(() => {
    const out: SidebarGroup[] = [];
    for (const g of MENU) {
      const items = g.items.filter((it) =>
        it.module === null || it.module === undefined
          ? true
          : this.auth.hasModule(it.module),
      );
      if (items.length > 0) out.push({ title: g.title, items });
    }
    return out;
  });

  closeAndNavigate(): void {
    this.layout.closeSidebar();
  }
}
