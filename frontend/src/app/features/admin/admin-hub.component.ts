import { CommonModule } from '@angular/common';
import { Component, OnInit, inject } from '@angular/core';
import { RouterLink } from '@angular/router';
import { LayoutService } from '../../core/layout/layout.service';

/**
 * Hub de Administración. 3 sub-áreas: Roles, Organización, Personas.
 *
 * El backend aún tiene CRUDs HTML legacy en `/org/*`. Mientras se
 * construyen los endpoints DRF correspondientes, cada sub-área es
 * placeholder con link al legacy. La URL Angular `/admin/*` ya está
 * preparada para que cuando lleguen los endpoints, se reemplacen
 * solo los componentes.
 */
@Component({
  standalone: true,
  selector: 'app-admin-hub',
  imports: [CommonModule, RouterLink],
  template: `
    <div class="page">
      <header class="page__header">
        <h1>Administración</h1>
        <p class="page__subtitle">Gestión de roles, organización y personas del sistema.</p>
      </header>

      <div class="hub-grid">
        <a routerLink="/admin/roles" class="hub-card hub-card--accent">
          <div class="hub-card__icon"><i class="fa fa-user-shield" aria-hidden="true"></i></div>
          <h3 class="hub-card__title">Roles y permisos</h3>
          <p class="hub-card__subtitle">Definir qué módulos ve cada rol N15.</p>
        </a>

        <a routerLink="/admin/org" class="hub-card hub-card--primary">
          <div class="hub-card__icon"><i class="fa fa-building" aria-hidden="true"></i></div>
          <h3 class="hub-card__title">Organización</h3>
          <p class="hub-card__subtitle">Dependencias, subgrupos, funcionarios, organizaciones, proveedores, beneficiarios.</p>
        </a>

        <a routerLink="/admin/personas" class="hub-card hub-card--info">
          <div class="hub-card__icon"><i class="fa fa-user-plus" aria-hidden="true"></i></div>
          <h3 class="hub-card__title">Personas</h3>
          <p class="hub-card__subtitle">Crear personas (sirve para participante, beneficiario, contratista, funcionario).</p>
        </a>
      </div>
    </div>
  `,
  styles: [`
    @use '../../../styles/tokens' as *;
    :host { display: block; }
    .page { max-width: 1100px; margin: 0 auto; }
    .page__header h1 { margin: 0; color: $color-primary; }
    .page__subtitle { color: $color-text-muted; margin: $space-1 0 $space-6; }
  `],
})
export class AdminHubComponent implements OnInit {
  private layout = inject(LayoutService);

  ngOnInit(): void {
    this.layout.setBreadcrumb([
      { label: 'Inicio', url: '/' },
      { label: 'Administración' },
    ]);
  }
}
