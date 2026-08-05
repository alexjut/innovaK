import { CommonModule } from '@angular/common';
import { Component, computed, inject } from '@angular/core';
import { RouterLink, RouterLinkActive } from '@angular/router';
import { AuthService } from '../../auth/auth.service';
import { KennyChatService } from '../../../features/asistente/kenny-chat.service';
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
  /** Acción especial en vez de navegar (p. ej. 'kenny' abre el asistente). */
  action?: 'kenny';
  /** Módulo N15 requerido. null = siempre visible (auth o no). */
  module?: string | null;
  /**
   * Si true, además del módulo exige rol administrador (superuser o grupo
   * "Admin"). Se usa para reservar la vista "Actividades" completa a admin:
   * el operativo entra por "Mi subgrupo" (RBAC B6). Reusa la fuente RBAC ya
   * existente (`auth.user()` de /api/me/), no inventa permisos nuevos.
   */
  adminOnly?: boolean;
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
      { label: 'Pregúntale a Kenny', icon: '', route: '', action: 'kenny', module: null },
      { label: 'UI Showcase', icon: 'fa-palette', route: '/showcase', module: null },
    ],
  },
  {
    title: 'Módulos',
    items: [
      // RBAC B6: el operativo entra a su área por "Mi subgrupo" (panel
      // evento-céntrico con su tronco "General"). La vista "Actividades"
      // completa (todos los tipos × todos los subgrupos) queda para admin.
      { label: 'Mi área', icon: 'fa-sitemap', route: '/subgrupo', module: 'eventos' },
      // Reorg 2026-06-01: Actividades es el hub central. Banco / Jóvenes /
      // Caracterización / Cursos NO son items top-level — viven dentro de
      // /actividades/tipo/<código>/sub/<subgrupo>. Aparecen automáticamente
      // según el tipo_evento del evento que se esté gestionando.
      { label: 'Actividades', icon: 'fa-calendar-check', route: '/actividades', module: 'eventos', adminOnly: true },
      // Festivales, Educación e Infraestructura NO van acá (2026-08-05).
      // Son módulos de un área concreta y se llega a ellos por "Mi área",
      // que es la puerta a las 15. Tenerlos también en el menú lateral
      // mandaba el mensaje contrario al del home y obligaba a decidir, área
      // por área, cuál merece atajo — que es justo lo que no queremos.
      // Sus rutas siguen funcionando; lo que cambia es por dónde se entra.
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
  private chat = inject(KennyChatService);

  /** Rol administrador: superuser o miembro del grupo "Admin". Reusa la
   *  fuente RBAC ya existente (perfil de /api/me/); no inventa permisos. */
  readonly esAdmin = computed<boolean>(() => {
    const u = this.auth.user();
    return !!u && (u.is_superuser || (u.groups ?? []).includes('Admin'));
  });

  /**
   * Grupos filtrados: cada item pasa si module=null o si el user lo tiene.
   * Los items `adminOnly` además exigen rol administrador.
   * Si no hay user (no logueado), solo se ven items con module=null.
   * Los grupos vacíos no se muestran.
   */
  readonly groups = computed<SidebarGroup[]>(() => {
    const admin = this.esAdmin();
    const out: SidebarGroup[] = [];
    for (const g of MENU) {
      const items = g.items.filter((it) => {
        const moduleOk =
          it.module === null || it.module === undefined
            ? true
            : this.auth.hasModule(it.module);
        return moduleOk && (!it.adminOnly || admin);
      });
      if (items.length > 0) out.push({ title: g.title, items });
    }
    return out;
  });

  closeAndNavigate(): void {
    this.layout.closeSidebar();
  }

  abrirKenny(): void {
    this.layout.closeSidebar();
    this.chat.abrir();
  }
}
