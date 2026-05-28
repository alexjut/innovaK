import { CommonModule } from '@angular/common';
import { Component, inject } from '@angular/core';
import { Router, RouterLink } from '@angular/router';
import { AuthService } from '../../auth/auth.service';
import { ConfigService } from '../../config/config.service';
import { LayoutService } from '../layout.service';

/**
 * Barra superior institucional fija. Replica `.base-top-nav` del Django
 * legacy:
 *   - Background rojo institucional + borde inferior amarillo 3px.
 *   - Altura 70px (clave para el padding-top del content).
 *   - Botón hamburguesa izquierda (toggle sidebar).
 *   - Logo + título centrado.
 *   - Info del usuario derecha con dropdown.
 *
 * En PR-3 el dropdown muestra solo "Cerrar sesión" si hay usuario; el
 * perfil completo llega en PR-4 con el AuthService implementado.
 */
@Component({
  standalone: true,
  selector: 'app-topbar',
  imports: [CommonModule, RouterLink],
  templateUrl: './topbar.component.html',
  styleUrl: './topbar.component.scss',
})
export class TopbarComponent {
  cfg = inject(ConfigService);
  layout = inject(LayoutService);
  auth = inject(AuthService);
  router = inject(Router);

  /** Estado del dropdown de usuario (signal local). */
  dropdownOpen = false;

  toggleDropdown(): void {
    this.dropdownOpen = !this.dropdownOpen;
  }

  logout(): void {
    this.dropdownOpen = false;
    this.auth.logout();
  }
}
