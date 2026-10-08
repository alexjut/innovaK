import { CommonModule } from '@angular/common';
import { Component, OnInit, computed, inject } from '@angular/core';
import { RouterLink } from '@angular/router';
import { LucideAngularModule } from 'lucide-angular';
import { AuthService } from '../../core/auth/auth.service';
import { LayoutService } from '../../core/layout/layout.service';
import { lucideDe } from './plan-iconos';
import { seccionesDe } from './plan-catalogo';

/**
 * GESTIÓN — el Plan como se opera.
 *
 * Lo que el área toca a diario: el catálogo del Plan, la plata, la ejecución
 * y las fuentes. Conserva los cuatro agrupadores que ya existían —El Plan, La
 * plata, La ejecución, Las fuentes— porque nombran preguntas que la gente ya
 * sabe hacerse, y renombrarlos al partir la pantalla habría cambiado dos cosas
 * a la vez.
 *
 * ## Filtra por módulo, y por eso puede quedar vacía
 *
 * Cada tarjeta declara el módulo que exige SU endpoint. Quien no lo tiene no
 * la ve, en vez de verla y chocarse con un 403 — que es lo que pasaba antes,
 * cuando el hub pintaba las once a todo el mundo.
 *
 * Si a alguien no le queda ninguna, esta pantalla lo dice en vez de mostrar
 * una página en blanco; y el hub directamente no le ofrece la entrada.
 */
@Component({
  standalone: true,
  selector: 'app-plan-gestion',
  imports: [CommonModule, RouterLink, LucideAngularModule],
  template: `
    <div class="page">
      <header class="page__header" data-tour="plan-gestion-titulo">
        <h1><i class="fa fa-sliders" aria-hidden="true"></i> Gestión del Plan</h1>
        <p class="page__subtitle">
          El catálogo del Plan, la plata, la ejecución y las fuentes: lo que se
          consulta a detalle y lo que se carga.
        </p>
      </header>

      @if (!secciones().length) {
        <div class="ui-empty-state">
          <i class="fa fa-lock" aria-hidden="true"></i>
          <p><strong>No tiene acceso a ninguna pantalla de gestión del Plan</strong></p>
          <p class="muted">
            Su rol no incluye los módulos de presupuesto. Pídale el acceso a
            quien administra los roles, o consulte el Plan desde
            <a routerLink="/plan/visual">la vista general</a>.
          </p>
        </div>
      }

      @for (s of secciones(); track s.titulo) {
        <section class="hub-section">
          <h2 class="hub-section__title">
            <lucide-icon [name]="icono(s.paginas[0].icono)" [size]="18"></lucide-icon>
            {{ s.titulo }}
          </h2>
          <p class="hub-section__subtitle">{{ s.subtitulo }}</p>
          <div class="hub-grid">
            @for (p of s.paginas; track p.ruta) {
              <a [routerLink]="p.ruta"
                 class="ui-card ui-card--interactive"
                 [class]="'ui-card--' + p.color">
                <div class="hub-card__icon">
                  <lucide-icon [name]="icono(p.icono)" [size]="22"></lucide-icon>
                </div>
                <div class="ui-card__body">
                  <h3 class="ui-card__title">{{ p.titulo }}</h3>
                  <p class="ui-card__subtitle">{{ p.subtitulo }}</p>
                </div>
              </a>
            }
          </div>
        </section>
      }

      <a routerLink="/plan" class="ui-back-link">← Volver al Plan de Desarrollo</a>
    </div>
  `,
  styles: [`
    @use '../../../styles/tokens' as *;
    :host { display: block; }
    .page { max-width: 1200px; margin: 0 auto; }
    .page__header h1 { margin: 0; color: $color-primary; i { margin-right: $space-2; } }
    .page__subtitle { color: $color-text-muted; margin: $space-1 0 $space-4; max-width: 72ch; }
    .muted { color: $color-text-muted; }
    .hub-section { margin-top: $space-5; }
    .hub-section__title {
      margin: 0 0 $space-1; font-size: $font-size-lg; color: $color-text;
      display: flex; align-items: center; gap: $space-2;
    }
    .hub-section__subtitle { color: $color-text-muted; margin: 0 0 $space-3; font-size: $font-size-sm; }
    .hub-grid {
      display: grid; grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
      gap: $space-3;
    }
    .ui-back-link { display: inline-block; margin-top: $space-4; color: $color-primary; }
  `],
})
export class PlanGestionComponent implements OnInit {
  private auth = inject(AuthService);
  private layout = inject(LayoutService);

  secciones = computed(() => seccionesDe(
    'gestion',
    (codigo) => this.auth.hasModule(codigo),
    !!this.auth.user()?.is_superuser,
  ));

  icono = lucideDe;

  ngOnInit(): void {
    this.layout.setBreadcrumb([
      { label: 'Inicio', url: '/' },
      { label: 'Plan de Desarrollo', url: '/plan' },
      { label: 'Gestión' },
    ]);
  }
}
