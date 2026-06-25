import { CommonModule } from '@angular/common';
import { Component, OnInit, inject, signal } from '@angular/core';
import { Router } from '@angular/router';
import { LayoutService } from '../../core/layout/layout.service';
import { SubgrupoApi } from './subgrupo.api';
import { SubgrupoLite } from './subgrupo.types';

/**
 * Entrada del panel operativo por subgrupo (RBAC B4).
 *
 * Lista los subgrupos visibles del usuario (`/subgrupos/mios/`). Si solo
 * tiene uno, entra directo a su detalle (es su landing operativo). Si tiene
 * varios, muestra un picker de tarjetas. Superuser ve todos.
 */
@Component({
  standalone: true,
  selector: 'app-subgrupo-panel',
  imports: [CommonModule],
  template: `
    <div class="page">
      <header class="page__header">
        <div>
          <h1><i class="fa fa-sitemap" aria-hidden="true"></i> Mi subgrupo</h1>
          <p class="page__sub">
            Panel operativo de tu área. Aquí ves tus proyectos, actividades,
            eventos y contratos — todo lo que cuelga de tu subgrupo.
          </p>
        </div>
      </header>

      @if (loading()) { <div class="ui-info-bar ui-info-bar--info">Cargando…</div> }
      @if (error()) { <div class="ui-info-bar ui-info-bar--danger">{{ error() }}</div> }

      @if (!loading() && subgrupos().length > 1) {
        <section class="grid">
          @for (s of subgrupos(); track s.id) {
            <button class="card" (click)="abrir(s)"
                    [attr.aria-label]="'Abrir panel de ' + (s.nombre || 'subgrupo')">
              <span class="card__icon"><i class="fa fa-layer-group"></i></span>
              <span class="card__body">
                <strong class="card__title">{{ s.nombre || 'Subgrupo ' + s.id }}</strong>
                @if (s.dependencia) { <span class="card__dep">{{ s.dependencia }}</span> }
                <span class="card__n">
                  {{ s.n_eventos }} evento{{ s.n_eventos === 1 ? '' : 's' }}
                </span>
              </span>
              <i class="fa fa-chevron-right card__go"></i>
            </button>
          }
        </section>
      }

      @if (!loading() && subgrupos().length === 0 && !error()) {
        <div class="ui-empty-state">
          <i class="fa fa-sitemap"></i>
          <p>No tienes ningún subgrupo asignado. Pide a un administrador que te
            vincule a un subgrupo para ver tu panel operativo.</p>
        </div>
      }
    </div>
  `,
  styles: [`
    @use '../../../styles/tokens' as *;
    :host { display: block; }
    .page { max-width: 1100px; margin: 0 auto; padding-bottom: $space-6; }
    .page__header h1 { margin: 0; color: $color-primary; }
    .page__header h1 i { margin-right: $space-2; }
    .page__sub { color: $color-text-muted; margin: $space-1 0 $space-4; max-width: 720px; }

    .grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: $space-3; }
    .card {
      display: flex; align-items: center; gap: $space-3; text-align: left;
      background: #fff; border: 1px solid $color-border; border-radius: $radius-lg;
      padding: $space-3; cursor: pointer; transition: box-shadow .15s, transform .15s, border-color .15s;
      border-left: 4px solid $color-primary;
    }
    .card:hover { box-shadow: 0 6px 20px rgba(0,0,0,.08); transform: translateY(-2px); border-color: $color-primary; }
    .card:focus-visible { outline: 2px solid $color-primary; outline-offset: 2px; }
    .card__icon {
      width: 44px; height: 44px; border-radius: $radius-md; flex: 0 0 auto;
      display: grid; place-items: center; background: #EEF2FF; color: #4338CA; font-size: 1.2rem;
    }
    .card__body { display: flex; flex-direction: column; gap: 2px; flex: 1; min-width: 0; }
    .card__title { color: $color-primary; }
    .card__dep { color: $color-text-muted; font-size: $font-size-sm; }
    .card__n { color: $color-text-muted; font-size: .78rem; }
    .card__go { color: $color-text-muted; }
  `],
})
export class SubgrupoPanelComponent implements OnInit {
  private api = inject(SubgrupoApi);
  private layout = inject(LayoutService);
  private router = inject(Router);

  loading = signal(false);
  error = signal('');
  subgrupos = signal<SubgrupoLite[]>([]);

  ngOnInit(): void {
    this.layout.setBreadcrumb([
      { label: 'Inicio', url: '/' },
      { label: 'Mi subgrupo' },
    ]);
    this.cargar();
  }

  abrir(s: SubgrupoLite): void {
    this.router.navigate(['/subgrupo', s.id]);
  }

  private cargar(): void {
    this.loading.set(true);
    this.error.set('');
    this.api.mios().subscribe({
      next: (r) => {
        const lista = r.results ?? [];
        this.subgrupos.set(lista);
        this.loading.set(false);
        // Un solo subgrupo → entra directo (es su landing operativo).
        if (lista.length === 1) {
          this.router.navigate(['/subgrupo', lista[0].id], { replaceUrl: true });
        }
      },
      error: (e) => { this.loading.set(false); this.error.set(this.msg(e)); },
    });
  }

  private msg(e: { error?: { detail?: string }; status?: number; message?: string }): string {
    if (e?.error?.detail) return e.error.detail;
    if (e?.status === 401 || e?.status === 403) return 'No tienes permiso para ver subgrupos.';
    return e?.message || 'Error inesperado al cargar tus subgrupos.';
  }
}
