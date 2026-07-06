import { Component } from '@angular/core';
import { RouterOutlet } from '@angular/router';
import { BreadcrumbComponent } from './breadcrumb/breadcrumb.component';
import { FooterComponent } from './footer/footer.component';
import { SidebarComponent } from './sidebar/sidebar.component';
import { TopbarComponent } from './topbar/topbar.component';
import { ToastHostComponent } from '../../shared/ui/toast-host.component';
import { ConfirmHostComponent } from '../../shared/ui/confirm-host.component';
import { OnboardingHostComponent } from '../../features/onboarding/onboarding-host.component';

/**
 * Layout root de la app. Compone:
 *   - Skip link (accesibilidad WCAG 2.4.1 — primero en el DOM).
 *   - Topbar fija (70px).
 *   - Sidebar overlay (slide-in).
 *   - Main content con padding-top (compensa topbar fija) y
 *     padding-bottom (compensa footer fijo).
 *   - Breadcrumb global (visible cuando alguna feature lo seteó).
 *   - Footer fijo.
 *
 * Las features renderizan dentro del <router-outlet />.
 */
@Component({
  standalone: true,
  selector: 'app-layout',
  imports: [
    RouterOutlet,
    TopbarComponent,
    SidebarComponent,
    BreadcrumbComponent,
    FooterComponent,
    ToastHostComponent,
    ConfirmHostComponent,
    OnboardingHostComponent,
  ],
  template: `
    <a class="ui-skip-link" href="#main-content">Saltar al contenido principal</a>

    <app-topbar />
    <app-sidebar />

    <main id="main-content" class="base-content" tabindex="-1">
      <app-breadcrumb />
      <router-outlet />
    </main>

    <app-footer />

    <app-toast-host />
    <app-confirm-host />
    <app-onboarding-host />
  `,
  styles: [`
    @use '../../../styles/tokens' as *;

    :host {
      display: block;
      min-height: 100vh;
    }

    .base-content {
      width: 100%;
      box-sizing: border-box;
      // 70px topbar + 14px gap visual + breathing room
      padding: calc(70px + #{$space-4}) $space-4;
      // 46px footer alto aprox + breathing
      padding-bottom: calc(46px + #{$space-6});
      min-height: 100vh;
      outline: 0;
    }
  `],
})
export class LayoutComponent {}
