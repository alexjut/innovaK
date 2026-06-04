import { CommonModule } from '@angular/common';
import {
  ChangeDetectionStrategy, Component, OnInit, inject, signal,
} from '@angular/core';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { ActividadesService, SubgruposResponse } from '../../core/actividades/actividades.service';
import { LayoutService } from '../../core/layout/layout.service';

/**
 * Pantalla 2 — dado un tipo, lista subgrupos con eventos vivos
 * o (si caracterización) los 6 sectores.
 */
@Component({
  standalone: true,
  selector: 'app-actividades-tipo',
  imports: [CommonModule, RouterLink],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <div class="page">
      @if (loading()) {
        <div class="page__loading">Cargando…</div>
      } @else if (errorMsg()) {
        <div class="page__error">⚠ {{ errorMsg() }}</div>
      } @else if (data()) {
        @let d = data()!;
        <header class="page__header">
          <h1>
            <i class="fa" [class]="d.tipo.icono || 'fa-folder'"
               [style.color]="d.tipo.color_hex"></i>
            {{ d.tipo.nombre }}
          </h1>
          <p class="page__subtitle">
            {{ d.tipo.descripcion || 'Selecciona un área para ver las actividades disponibles.' }}
          </p>
        </header>

        @if (d.tipo.permite_caracterizacion) {
          <h2 class="page__section">Sectores</h2>
          <div class="hub-grid">
            @for (s of d.sectores; track s.codigo) {
              <a [routerLink]="['/caracterizacion', s.codigo]"
                 class="ui-card ui-card--interactive ui-card--accent">
                <div class="hub-card__icon">
                  <i class="fa" [class]="s.icono"></i>
                </div>
                <div class="ui-card__body">
                  <h3 class="ui-card__title">{{ s.nombre }}</h3>
                  <p class="ui-card__subtitle">
                    {{ s.descripcion || ('Caracterizar persona — sector ' + s.codigo) }}
                  </p>
                </div>
              </a>
            }
          </div>
        } @else if (d.subgrupos.length) {
          <h2 class="page__section">Áreas / Subgrupos</h2>
          <div class="hub-grid">
            @for (s of d.subgrupos; track s.id) {
              <a [routerLink]="['/actividades/tipo', codigo(), 'sub', s.id]"
                 class="ui-card ui-card--interactive ui-card--info">
                <div class="hub-card__icon">
                  <i class="fa fa-layer-group"></i>
                </div>
                <div class="ui-card__body">
                  <h3 class="ui-card__title">{{ s.nombre }}</h3>
                  <p class="ui-card__subtitle">
                    {{ s.num_eventos }} actividad{{ s.num_eventos === 1 ? '' : 'es' }}
                    @if (s.dependencia_nombre) {
                      · {{ s.dependencia_nombre }}
                    }
                  </p>
                </div>
              </a>
            }
          </div>
        } @else {
          <div class="ui-empty-state">
            <i class="fa fa-folder-open"></i>
            <p>Este tipo aún no tiene áreas con actividades registradas.</p>
            <a [routerLink]="['/eventos/nueva']" [queryParams]="{ tipo: codigo() }"
               class="ui-btn ui-btn--primary">
              <i class="fa fa-plus-circle"></i>
              <span>Crear actividad de tipo «{{ d.tipo.nombre }}»</span>
            </a>
          </div>
        }
      }
    </div>
  `,
  styles: [`
    @use '../../../styles/tokens' as *;
    :host { display: block; }
    .page { max-width: 1200px; margin: 0 auto; }
    .page__header h1 {
      margin: 0;
      color: $color-primary;
      i { margin-right: $space-2; }
    }
    .page__subtitle { color: $color-text-muted; margin: $space-1 0 $space-4; }
    .page__section {
      font-size: $font-size-md;
      color: $color-text-muted;
      text-transform: uppercase;
      letter-spacing: 0.06em;
      margin: $space-4 0 $space-3;
    }
    .page__loading, .page__error {
      padding: $space-4;
      text-align: center;
      color: $color-text-muted;
    }
    .page__error { color: $color-danger; }
  `],
})
export class ActividadesTipoComponent implements OnInit {
  private svc = inject(ActividadesService);
  private route = inject(ActivatedRoute);
  private router = inject(Router);
  private layout = inject(LayoutService);

  data = signal<SubgruposResponse | null>(null);
  loading = signal<boolean>(true);
  errorMsg = signal<string>('');
  codigo = signal<string>('');

  ngOnInit(): void {
    this.route.paramMap.subscribe((p) => {
      const codigo = p.get('codigo') || '';
      this.codigo.set(codigo);
      this.cargar(codigo);
    });
  }

  private cargar(codigo: string): void {
    this.loading.set(true);
    this.errorMsg.set('');
    this.svc.subgrupos(codigo).subscribe({
      next: (r) => {
        this.data.set(r);
        this.loading.set(false);
        this.layout.setBreadcrumb([
          { label: 'Inicio', url: '/' },
          { label: 'Actividades', url: '/actividades' },
          { label: r.tipo.nombre },
        ]);
      },
      error: (err) => {
        if (err.status === 404) {
          this.errorMsg.set('Tipo de actividad no encontrado.');
        } else {
          this.errorMsg.set('No se pudo cargar la información.');
        }
        this.loading.set(false);
      },
    });
  }
}
