import { CommonModule } from '@angular/common';
import { Component, OnInit, computed, inject } from '@angular/core';
import { RouterLink } from '@angular/router';
import { LucideAngularModule } from 'lucide-angular';
import { AuthService } from '../../core/auth/auth.service';
import { LayoutService } from '../../core/layout/layout.service';
import { PlanArbolComponent } from './plan-arbol/plan-arbol.component';
import { lucideDe } from './plan-iconos';
import { seccionesDe } from './plan-catalogo';

/**
 * VISUAL — el Plan como se mira.
 *
 * Es la entrada de quien quiere VER lo que se construyó, no operarlo: el
 * alcalde, un concejal, alguien del Despacho. El árbol va arriba y de
 * protagonista, porque es lo que ninguna otra pantalla daba — la jerarquía
 * completa, de objetivo a meta, con lo que lleva cada rama.
 *
 * ## Solo lectura, y es una decisión de pantalla
 *
 * No hay un botón de crear, editar ni cargar. Eso **no es un permiso**: el
 * backend sigue siendo el que decide qué puede escribir cada quien, y el
 * alcalde es superusuario. Es una convención de esta pantalla, y conviene que
 * se entienda así: nadie debe apoyarse en Visual para impedir una escritura.
 *
 * ## Pensada para crecer
 *
 * Las cosas nuevas que se van pidiendo aterrizan acá. Por eso las tarjetas
 * salen de `plan-catalogo`, como datos: agregar una es una línea en esa lista,
 * no un rediseño de esta pantalla.
 */
@Component({
  standalone: true,
  selector: 'app-plan-visual',
  imports: [CommonModule, RouterLink, LucideAngularModule, PlanArbolComponent],
  template: `
    <div class="page">
      <header class="page__header" data-tour="plan-visual-titulo">
        <h1><i class="fa fa-eye" aria-hidden="true"></i> El Plan, a la vista</h1>
        <p class="page__subtitle">
          Todo lo que llevamos construido del Plan de Desarrollo Local
          2025-2028, para consultarlo. Las cifras son las de la Matriz de
          Seguimiento PDL.
        </p>
      </header>

      <!-- El árbol PRIMERO: es lo que esta entrada vino a dar. -->
      <div data-tour="plan-visual-arbol">
        <app-plan-arbol />
      </div>

      @for (s of secciones(); track s.titulo) {
        <section class="hub-section">
          <h2 class="hub-section__title">
            <lucide-icon [name]="icono('fa-chart-pie')" [size]="18"></lucide-icon>
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
export class PlanVisualComponent implements OnInit {
  private auth = inject(AuthService);
  private layout = inject(LayoutService);

  secciones = computed(() => seccionesDe(
    'visual',
    (codigo) => this.auth.hasModule(codigo),
    !!this.auth.user()?.is_superuser,
  ));

  icono = lucideDe;

  ngOnInit(): void {
    this.layout.setBreadcrumb([
      { label: 'Inicio', url: '/' },
      { label: 'Plan de Desarrollo', url: '/plan' },
      { label: 'Visual' },
    ]);
  }
}
