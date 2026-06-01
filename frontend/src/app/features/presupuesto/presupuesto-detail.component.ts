import { CommonModule } from '@angular/common';
import { Component, OnInit, computed, inject, signal } from '@angular/core';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { LayoutService } from '../../core/layout/layout.service';
import { PresupuestoApi } from './presupuesto.api';
import { ENTIDADES, PresupEntidad, PresupItem } from './presupuesto.types';

/**
 * Detalle genérico para cualquier entidad de presupuesto. Renderiza
 * todos los campos del JSON como dl/dt/dd ordenados.
 */
@Component({
  standalone: true,
  selector: 'app-presupuesto-detail',
  imports: [CommonModule, RouterLink],
  template: `
    <div class="page">
      @if (loading()) {
        <div class="ui-info-bar ui-info-bar--info">Cargando…</div>
      }
      @if (!loading() && errorMsg()) {
        <div class="ui-info-bar ui-info-bar--danger">{{ errorMsg() }}</div>
        <a [routerLink]="['/presupuesto', entidad()]" class="ui-btn ui-btn--ghost">↩ Volver</a>
      }
      @if (!loading() && !errorMsg() && data(); as d) {
        <header class="page__header">
          <div>
            <h1>
              <i class="fa" [class]="meta()?.icon" aria-hidden="true"></i>
              {{ meta()?.label }} #{{ d.id }}
            </h1>
          </div>
          <a [routerLink]="['/presupuesto', entidad()]" class="ui-btn ui-btn--ghost ui-btn--sm">
            <i class="fa fa-arrow-left" aria-hidden="true"></i> Listado
          </a>
        </header>

        <article class="ui-card" [class]="'ui-card--' + (meta()?.color || 'primary')">
          <dl class="kv">
            @for (entry of entries(); track entry[0]) {
              <dt>{{ formatKey(entry[0]) }}</dt>
              <dd>{{ formatValue(entry[1]) }}</dd>
            }
          </dl>
        </article>
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
export class PresupuestoDetailComponent implements OnInit {
  private api = inject(PresupuestoApi);
  private route = inject(ActivatedRoute);
  private layout = inject(LayoutService);

  entidad = signal<PresupEntidad>('proyectos');
  loading = signal<boolean>(true);
  errorMsg = signal<string>('');
  data = signal<PresupItem | null>(null);

  meta = computed(() => ENTIDADES.find((e) => e.codigo === this.entidad()));

  entries = computed<Array<[string, unknown]>>(() => {
    const d = this.data();
    if (!d) return [];
    return Object.entries(d).filter(([k]) => k !== 'id');
  });

  ngOnInit(): void {
    this.route.paramMap.subscribe((pm) => {
      const e = (pm.get('entidad') || 'proyectos') as PresupEntidad;
      const id = Number(pm.get('id'));
      this.entidad.set(e);
      if (!id || isNaN(id)) {
        this.errorMsg.set('ID inválido.');
        this.loading.set(false);
        return;
      }
      this.layout.setBreadcrumb([
        { label: 'Inicio', url: '/' },
        { label: 'Presupuesto', url: '/presupuesto' },
        { label: this.meta()?.label || e, url: `/presupuesto/${e}` },
        { label: `#${id}` },
      ]);
      this.load(e, id);
    });
  }

  load(entidad: PresupEntidad, id: number): void {
    this.loading.set(true);
    this.api.detail(entidad, id).subscribe({
      next: (d) => { this.data.set(d); this.loading.set(false); },
      error: (e) => {
        this.loading.set(false);
        this.errorMsg.set(
          e.status === 404 ? 'No encontrado.' :
          e.status === 403 ? 'Sin permiso.' :
          `Error ${e.status}.`
        );
      },
    });
  }

  formatKey(k: string): string {
    return k.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());
  }

  formatValue(v: unknown): string {
    if (v === null || v === undefined || v === '') return '—';
    if (typeof v === 'boolean') return v ? 'Sí' : 'No';
    if (Array.isArray(v)) return v.length ? `[${v.length} items]` : '—';
    if (typeof v === 'object') return JSON.stringify(v);
    return String(v);
  }
}
