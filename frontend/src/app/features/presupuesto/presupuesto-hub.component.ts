import { CommonModule } from '@angular/common';
import { Component, computed, inject } from '@angular/core';
import { RouterLink } from '@angular/router';
import { LucideAngularModule } from 'lucide-angular';
import { AuthService } from '../../core/auth/auth.service';
import { lucideDe } from './plan-iconos';
import { paginasDe } from './plan-catalogo';

/**
 * El hub del Plan de Desarrollo: DOS entradas.
 *
 * ## De once tarjetas a dos
 *
 * Esta pantalla llegó a tener cuatro secciones y quince tarjetas, y la
 * densidad estaba anotada como deuda desde hacía meses. El problema no era el
 * número: era que todas pesaban lo mismo. El alcalde que entra a mirar cómo va
 * el Plan y la persona que carga la Matriz veían exactamente la misma lista.
 *
 * Ahora la primera pregunta es **qué viene a hacer**:
 *
 *   · VISUAL   ver el Plan — el árbol completo y los tableros.
 *   · GESTIÓN  operarlo — el catálogo, la plata, la ejecución, las fuentes.
 *
 * ## Los accesos directos
 *
 * Partir en dos le cuesta un clic a quien usa Gestión a diario, y eso no es
 * orden: es lentitud con cara de orden. Los chips de abajo lo devuelven.
 *
 * Van como **bloque aislado y fácil de quitar** (la constante
 * `MOSTRAR_ACCESOS_DIRECTOS` y su `@if`): si con el tiempo se ve que nadie los
 * usa, se retiran sin tocar nada más.
 *
 * ## Filtra por módulo
 *
 * Hasta hoy no lo hacía: pintaba las once tarjetas a todo el mundo y quien no
 * tenía el módulo se encontraba el 403 al entrar. Con dos entradas eso deja de
 * ser un detalle — ofrecer «Gestión» a alguien que no puede abrir ninguna de
 * sus pantallas es mandarlo a chocarse. Si una entrada le queda vacía, no se
 * le muestra.
 */

/** Poner en `false` retira la fila de chips sin tocar nada más. */
const MOSTRAR_ACCESOS_DIRECTOS = true;

@Component({
  standalone: true,
  selector: 'app-presupuesto-hub',
  imports: [CommonModule, RouterLink, LucideAngularModule],
  template: `
    <div class="page">
      <header class="page__header" data-tour="presupuesto-titulo">
        <h1><i class="fa fa-diagram-project" aria-hidden="true"></i> Plan de Desarrollo</h1>
        <p class="page__subtitle">
          Plan de Desarrollo Local 2025-2028. ¿Viene a verlo o a trabajarlo?
        </p>
      </header>

      <div class="entradas" data-tour="presupuesto-cards">
        @if (visual().length) {
          <a routerLink="/plan/visual" class="entrada entrada--visual">
            <div class="entrada__icono">
              <lucide-icon name="gauge" [size]="34"></lucide-icon>
            </div>
            <div class="entrada__texto">
              <h2 class="entrada__titulo">Visual</h2>
              <p class="entrada__sub">
                El Plan a la vista: el árbol completo de objetivo a meta, y los
                tableros con las cifras ya agregadas.
              </p>
              <span class="entrada__pista">
                El árbol · {{ visual().length }}
                {{ visual().length === 1 ? 'tablero' : 'tableros' }}
              </span>
            </div>
          </a>
        }

        @if (gestion().length) {
          <a routerLink="/plan/gestion" class="entrada entrada--gestion">
            <div class="entrada__icono">
              <lucide-icon name="settings" [size]="34"></lucide-icon>
            </div>
            <div class="entrada__texto">
              <h2 class="entrada__titulo">Gestión</h2>
              <p class="entrada__sub">
                Lo operativo: el catálogo del Plan, los contratos y CDPs, las
                actividades y avances, y de dónde sale cada cifra.
              </p>
              <span class="entrada__pista">
                {{ gestion().length }}
                {{ gestion().length === 1 ? 'pantalla' : 'pantallas' }}
              </span>
            </div>
          </a>
        }
      </div>

      @if (!visual().length && !gestion().length) {
        <div class="ui-empty-state">
          <i class="fa fa-lock" aria-hidden="true"></i>
          <p><strong>No tiene acceso al Plan de Desarrollo</strong></p>
          <p class="muted">
            Su rol no incluye los módulos de presupuesto. Pídale el acceso a
            quien administra los roles.
          </p>
        </div>
      }

      <!-- ── ACCESOS DIRECTOS ────────────────────────────────────────────
           Bloque aislado: se quita poniendo MOSTRAR_ACCESOS_DIRECTOS en
           false, sin tocar el resto. Existe para que partir en dos no le
           cueste un clic de más a quien usa Gestión todos los días.
      -->
      @if (mostrarAccesos && gestion().length) {
        <section class="atajos">
          <h2 class="atajos__titulo">Accesos directos</h2>
          <div class="atajos__fila">
            @for (p of gestion(); track p.ruta) {
              <a [routerLink]="p.ruta" class="chip" [attr.title]="p.subtitulo">
                <lucide-icon [name]="icono(p.icono)" [size]="14"></lucide-icon>
                {{ p.titulo }}
              </a>
            }
          </div>
        </section>
      }
    </div>
  `,
  styles: [`
    @use '../../../styles/tokens' as *;
    :host { display: block; }
    .page { max-width: 1200px; margin: 0 auto; }
    .page__header h1 { margin: 0; color: $color-primary; i { margin-right: $space-2; } }
    .page__subtitle { color: $color-text-muted; margin: $space-1 0 $space-4; }
    .muted { color: $color-text-muted; }

    // Las dos entradas: grandes a propósito. Son la primera decisión que toma
    // quien abre el Plan, y tienen que leerse antes que nada.
    .entradas {
      display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
      gap: $space-3;
    }
    .entrada {
      display: flex; gap: $space-3; align-items: flex-start;
      padding: $space-4; border-radius: $radius-md;
      border: 1px solid $color-border; background: $color-bg;
      text-decoration: none; color: inherit;
      transition: transform .15s ease, box-shadow .15s ease, border-color .15s ease;
      &:hover, &:focus-visible {
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(0,0,0,.08);
        border-color: $color-primary;
      }
    }
    .entrada__icono {
      flex: 0 0 auto; width: 58px; height: 58px; border-radius: $radius-md;
      display: grid; place-items: center;
    }
    .entrada--visual .entrada__icono { background: $color-primary-bg; color: $color-primary; }
    .entrada--gestion .entrada__icono { background: $color-info-bg; color: $color-info-hondo; }
    .entrada__titulo { margin: 0 0 $space-1; font-size: 1.3rem; color: $color-text; }
    .entrada__sub { margin: 0 0 $space-2; color: $color-text-muted; font-size: $font-size-sm; }
    .entrada__pista { font-size: $font-size-xs; color: $color-neutral-600; }

    .atajos { margin-top: $space-5; }
    .atajos__titulo {
      margin: 0 0 $space-2; font-size: $font-size-sm; font-weight: 600;
      color: $color-text-muted; text-transform: uppercase; letter-spacing: .03em;
    }
    .atajos__fila { display: flex; flex-wrap: wrap; gap: $space-2; }
    .chip {
      display: inline-flex; align-items: center; gap: 6px;
      padding: 5px 12px; border-radius: 999px;
      border: 1px solid $color-border; background: $color-bg-subtle;
      font-size: $font-size-sm; color: $color-text; text-decoration: none;
      &:hover, &:focus-visible { border-color: $color-primary; color: $color-primary; }
    }

    @media (max-width: 560px) {
      .entrada { padding: $space-3; }
      .entrada__icono { width: 44px; height: 44px; }
    }
  `],
})
export class PresupuestoHubComponent {
  private auth = inject(AuthService);

  mostrarAccesos = MOSTRAR_ACCESOS_DIRECTOS;
  icono = lucideDe;

  private puede = (codigo: string) => this.auth.hasModule(codigo);
  private get alcance() { return !!this.auth.user()?.is_superuser; }

  visual = computed(() => paginasDe('visual', this.puede, this.alcance));
  gestion = computed(() => paginasDe('gestion', this.puede, this.alcance));
}
