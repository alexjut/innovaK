import { CommonModule } from '@angular/common';
import { Component, OnInit, computed, inject, signal } from '@angular/core';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { LayoutService } from '../../core/layout/layout.service';
import { CaracterizacionApi } from './caracterizacion.api';
import { CaractDetail, CaractSector, SECTORES } from './caracterizacion.types';

/**
 * Detalle de una caracterización. Renderiza todos los campos del
 * detail serializer del sector como pares clave-valor. Detecta
 * automáticamente strings/booleans/objetos.
 */
@Component({
  standalone: true,
  selector: 'app-caracterizacion-detail',
  imports: [CommonModule, RouterLink],
  template: `
    <div class="page">
      @if (loading()) {
        <div class="ui-info-bar ui-info-bar--info">Cargando…</div>
      }
      @if (!loading() && errorMsg()) {
        <div class="ui-info-bar ui-info-bar--danger">
          <strong>Error:</strong> {{ errorMsg() }}
        </div>
        <a [routerLink]="['/caracterizacion', sector()]" class="ui-btn ui-btn--ghost">
          ↩ Volver al listado
        </a>
      }
      @if (!loading() && !errorMsg() && data(); as d) {
        <header class="page__header">
          <div>
            <h1>
              <i class="fa" [class]="meta()?.icon" aria-hidden="true"></i>
              {{ meta()?.label }} #{{ d.id }}
            </h1>
            @if (d.persona_nombre) {
              <p class="page__subtitle">{{ d.persona_nombre }}</p>
            }
          </div>
          <a [routerLink]="['/caracterizacion', sector()]" class="ui-btn ui-btn--ghost ui-btn--sm">
            <i class="fa fa-arrow-left" aria-hidden="true"></i> Listado
          </a>
        </header>

        <article class="ui-card" [class]="'ui-card--' + (meta()?.color || 'primary')">
          <header class="ui-card__header">
            <h2 class="ui-card__title"><i class="fa fa-list-alt" aria-hidden="true"></i> Datos de la caracterización</h2>
          </header>
          <dl class="kv">
            @for (entry of entries(); track entry[0]) {
              <dt>{{ formatKey(entry[0]) }}</dt>
              <dd>{{ formatValue(entry[1]) }}</dd>
            }
          </dl>
        </article>

        @if (d.hogar) {
          <article class="ui-card ui-card--accent" style="margin-top: 1rem;">
            <header class="ui-card__header">
              <h2 class="ui-card__title"><i class="fa fa-house-user" aria-hidden="true"></i> Información de hogar</h2>
            </header>
            <dl class="kv">
              @for (entry of hogarEntries(); track entry[0]) {
                <dt>{{ formatKey(entry[0]) }}</dt>
                <dd>{{ formatValue(entry[1]) }}</dd>
              }
            </dl>
          </article>
        }
      }
    </div>
  `,
  styles: [`
    @use '../../../styles/tokens' as *;

    :host { display: block; }
    .page { max-width: 1100px; margin: 0 auto; }
    .page__header {
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      gap: $space-3;
      flex-wrap: wrap;
      margin-bottom: $space-4;
    }
    .page__header h1 { margin: 0; color: $color-primary; }
    .page__header h1 i { margin-right: $space-2; }
    .page__subtitle { margin: $space-1 0 0; color: $color-text-muted; }

    .kv {
      display: grid;
      grid-template-columns: max-content 1fr;
      gap: $space-2 $space-4;
      margin: 0;
    }
    .kv dt {
      font-weight: $font-weight-semibold;
      color: $color-text-muted;
      font-size: $font-size-sm;
    }
    .kv dd { margin: 0; word-break: break-word; }
  `],
})
export class CaracterizacionDetailComponent implements OnInit {
  private api = inject(CaracterizacionApi);
  private route = inject(ActivatedRoute);
  private layout = inject(LayoutService);

  sector = signal<CaractSector>('cultura');
  loading = signal<boolean>(true);
  errorMsg = signal<string>('');
  data = signal<CaractDetail | null>(null);

  meta = computed(() => SECTORES.find((s) => s.codigo === this.sector()));

  /** Pares (key, value) excluyendo los técnicos y el hogar. */
  entries = computed<Array<[string, unknown]>>(() => {
    const d = this.data();
    if (!d) return [];
    const skip = new Set(['id', 'evento_id', 'persona_id', 'funcionario_id', 'hogar']);
    return Object.entries(d).filter(([k]) => !skip.has(k));
  });

  hogarEntries = computed<Array<[string, unknown]>>(() => {
    const hogar = this.data()?.hogar;
    if (!hogar) return [];
    return Object.entries(hogar).filter(([k]) => k !== 'id');
  });

  ngOnInit(): void {
    this.route.paramMap.subscribe((pm) => {
      const sector = (pm.get('sector') || 'cultura') as CaractSector;
      const id = Number(pm.get('id'));
      this.sector.set(sector);
      if (!id || isNaN(id)) {
        this.errorMsg.set('ID inválido.');
        this.loading.set(false);
        return;
      }
      this.layout.setBreadcrumb([
        { label: 'Inicio', url: '/' },
        { label: 'Caracterización', url: '/caracterizacion' },
        { label: this.meta()?.label || sector, url: `/caracterizacion/${sector}` },
        { label: `#${id}` },
      ]);
      this.load(sector, id);
    });
  }

  load(sector: CaractSector, id: number): void {
    this.loading.set(true);
    this.api.detail(sector, id).subscribe({
      next: (d) => {
        this.data.set(d);
        this.loading.set(false);
      },
      error: (e) => {
        this.loading.set(false);
        if (e.status === 404) this.errorMsg.set('Caracterización no encontrada.');
        else if (e.status === 403) this.errorMsg.set('No tienes permiso.');
        else this.errorMsg.set(`Error ${e.status ?? '?'}.`);
      },
    });
  }

  formatKey(k: string): string {
    return k
      .replace(/_/g, ' ')
      .replace(/\b\w/g, (c) => c.toUpperCase());
  }

  formatValue(v: unknown): string {
    if (v === null || v === undefined || v === '') return '—';
    if (typeof v === 'boolean') return v ? 'Sí' : 'No';
    if (typeof v === 'object') return JSON.stringify(v);
    return String(v);
  }
}
