import { CommonModule } from '@angular/common';
import { Component, OnInit, inject, signal } from '@angular/core';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { LayoutService } from '../../core/layout/layout.service';
import { FestivalesApi } from './festivales.api';
import { FestivalDetalle } from './festivales.types';

/**
 * Vista de detalle de un festival (FEST-F-09): datos generales + lista de
 * actos (eventos) asociados. Se llega desde la tarjeta del listado.
 */
@Component({
  standalone: true,
  selector: 'app-festival-detalle',
  imports: [CommonModule, RouterLink],
  template: `
    <div class="page">
      @if (loading()) { <div class="ui-info-bar ui-info-bar--info">Cargando festival…</div> }
      @if (!loading() && error()) {
        <div class="ui-info-bar ui-info-bar--danger"><strong>Error:</strong> {{ error() }}</div>
        <a routerLink="/festivales" class="ui-btn ui-btn--ghost"><i class="fa fa-arrow-left"></i> Volver</a>
      }

      @if (!loading() && !error() && festival(); as f) {
        <header class="page__header">
          <div>
            <h1><i class="fa fa-music" aria-hidden="true"></i> {{ f.nombre }}</h1>
            <p class="page__sub">
              <span class="badge badge--{{ f.estado }}">{{ f.estado_display }}</span>
              @if (f.tipo_festival_nombre) { <span class="chip">{{ f.tipo_festival_nombre }}</span> }
              @if (f.numero_edicion) { <span class="chip">{{ f.numero_edicion }}ª edición</span> }
              <span class="chip">Vigencia {{ f.vigencia }}</span>
            </p>
          </div>
          <div class="actions">
            <a routerLink="/festivales" class="ui-btn ui-btn--ghost ui-btn--sm">
              <i class="fa fa-arrow-left"></i> Listado
            </a>
            <a [routerLink]="['/presupuesto/proyectos', 2780]" class="ui-btn ui-btn--ghost ui-btn--sm">
              <i class="fa fa-coins"></i> Ver en presupuesto
            </a>
          </div>
        </header>

        <section class="cards">
          <div class="info">
            <h2>Datos generales</h2>
            <dl>
              <dt>Fechas</dt>
              <dd>
                {{ f.fecha_inicio || 'Sin fecha de inicio' }}
                @if (f.fecha_fin) { — {{ f.fecha_fin }} }
              </dd>
              <dt>Lugar</dt>
              <dd>{{ f.lugar_texto || '—' }}</dd>
              <dt>Actos</dt>
              <dd>{{ f.n_eventos }} evento(s) asociado(s)</dd>
              <dt>Estado documental</dt>
              <dd>
                <span [class.ok]="f.documentado">{{ f.documentado ? 'Documentado' : 'Sin documentar' }}</span>
                ·
                <span [class.ok]="f.publicado">{{ f.publicado ? 'Publicado' : 'No publicado' }}</span>
              </dd>
            </dl>
            @if (f.descripcion) {
              <h3>Descripción</h3>
              <p class="desc">{{ f.descripcion }}</p>
            }
          </div>

          <div class="actos">
            <h2>Actos del festival</h2>
            @if (f.eventos.length === 0) {
              <div class="ui-empty-state ui-empty-state--sm">
                <i class="fa fa-calendar-xmark"></i>
                <p>Este festival aún no tiene actos (eventos) asociados.</p>
              </div>
            } @else {
              <ul class="acto-list">
                @for (e of f.eventos; track e.id) {
                  <li class="acto">
                    <a [routerLink]="['/eventos', e.id, 'editar']" class="acto__name">{{ e.nombre || 'Evento #' + e.id }}</a>
                    <div class="acto__meta">
                      @if (e.tipo_evento_nombre) { <span class="chip">{{ e.tipo_evento_nombre }}</span> }
                      @if (e.subgrupo_nombre) { <span>{{ e.subgrupo_nombre }}</span> }
                      <span><i class="fa fa-calendar"></i> {{ e.fecha_inicio || 'sin fecha' }}</span>
                    </div>
                  </li>
                }
              </ul>
            }
          </div>
        </section>
      }
    </div>
  `,
  styles: [`
    @use '../../../styles/tokens' as *;
    :host { display: block; }
    .page { max-width: 1100px; margin: 0 auto; padding-bottom: $space-6; }
    .page__header { display: flex; justify-content: space-between; align-items: flex-start; gap: $space-3; flex-wrap: wrap; }
    .page__header h1 { margin: 0; color: $color-primary; }
    .page__header h1 i { margin-right: $space-2; }
    .page__sub { display: flex; gap: $space-2; flex-wrap: wrap; align-items: center; margin: $space-2 0 $space-3; }
    .actions { display: flex; gap: $space-2; align-items: center; flex-wrap: wrap; }
    .cards { display: grid; grid-template-columns: 1fr 1.4fr; gap: $space-3; }
    @media (max-width: 800px) { .cards { grid-template-columns: 1fr; } }
    .info, .actos { background: #fff; border: 1px solid $color-border; border-radius: $radius-lg; padding: $space-4; }
    .info h2, .actos h2 { margin: 0 0 $space-3; color: $color-primary; font-size: 1.1rem; }
    .info h3 { margin: $space-3 0 $space-1; font-size: .9rem; color: $color-text; }
    dl { display: grid; grid-template-columns: auto 1fr; gap: $space-1 $space-3; margin: 0; }
    dt { color: $color-text-muted; font-size: $font-size-sm; font-weight: 600; }
    dd { margin: 0; font-size: $font-size-sm; color: $color-text; }
    .ok { color: #16A34A; font-weight: 600; }
    .desc { color: $color-text-muted; font-size: $font-size-sm; white-space: pre-wrap; }
    .acto-list { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: $space-2; }
    .acto { border: 1px solid $color-border; border-radius: $radius-md; padding: $space-2 $space-3; }
    .acto__name { font-weight: 600; color: $color-primary; text-decoration: none; }
    .acto__name:hover { text-decoration: underline; }
    .acto__meta { display: flex; gap: $space-2; flex-wrap: wrap; font-size: $font-size-sm; color: $color-text-muted; margin-top: 4px; align-items: center; }
    .chip { background: #F3F4F6; color: #374151; border-radius: 99px; padding: 2px 10px; font-size: .72rem; }
    .badge { border-radius: 99px; padding: 3px 12px; font-size: .72rem; font-weight: 600; }
    .badge--planeado { background: #FEF3C7; color: #92400E; }
    .badge--ejecutado { background: #DCFCE7; color: #166534; }
    .badge--cerrado { background: #E5E7EB; color: #374151; }
  `],
})
export class FestivalDetalleComponent implements OnInit {
  private api = inject(FestivalesApi);
  private route = inject(ActivatedRoute);
  private layout = inject(LayoutService);

  loading = signal(true);
  error = signal('');
  festival = signal<FestivalDetalle | null>(null);

  ngOnInit(): void {
    this.layout.setBreadcrumb([
      { label: 'Inicio', url: '/' },
      { label: 'Festivales', url: '/festivales' },
      { label: 'Detalle' },
    ]);
    const id = Number(this.route.snapshot.paramMap.get('id'));
    if (!id) { this.error.set('Festival no válido.'); this.loading.set(false); return; }
    this.api.detalle(id).subscribe({
      next: (f) => {
        this.festival.set(f);
        this.loading.set(false);
        this.layout.setBreadcrumb([
          { label: 'Inicio', url: '/' },
          { label: 'Festivales', url: '/festivales' },
          { label: f.nombre },
        ]);
      },
      error: (e) => { this.loading.set(false); this.error.set(this.msg(e)); },
    });
  }

  private msg(e: { error?: { detail?: string }; status?: number; message?: string }): string {
    if (e?.error?.detail) return e.error.detail;
    if (e?.status === 404) return 'Festival no encontrado.';
    if (e?.status === 401 || e?.status === 403) return 'No tienes permiso para ver festivales.';
    return e?.message || 'Error inesperado.';
  }
}
