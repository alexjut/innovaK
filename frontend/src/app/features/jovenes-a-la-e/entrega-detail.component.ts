import { CommonModule } from '@angular/common';
import { Component, OnInit, inject, signal } from '@angular/core';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { LayoutService } from '../../core/layout/layout.service';
import { JovenesApi } from './jovenes.api';
import { EntregaDetail, EntregaEstado } from './jovenes.types';

/**
 * Vista 360° de una entrega Jóvenes a la E. Permite validar/rechazar.
 *
 * El backend usa `accion: 'validar'|'rechazar'` (no `estado` como
 * el Banco). El rechazo requiere observaciones no vacías.
 */
@Component({
  standalone: true,
  selector: 'app-jovenes-entrega-detail',
  imports: [CommonModule, RouterLink],
  template: `
    <div class="page">
      @if (loading()) {
        <div class="ui-info-bar ui-info-bar--info">Cargando entrega…</div>
      }
      @if (!loading() && errorMsg()) {
        <div class="ui-info-bar ui-info-bar--danger">
          <strong>Error:</strong> {{ errorMsg() }}
        </div>
        <a routerLink="/jovenes" class="ui-btn ui-btn--ghost">↩ Volver al listado</a>
      }
      @if (!loading() && !errorMsg() && data(); as d) {
        <header class="page__header">
          <div>
            <h1><i class="fa fa-graduation-cap" aria-hidden="true"></i> Entrega #{{ d.id }}</h1>
            <p class="page__subtitle">
              <span class="ui-badge" [class]="badgeClass(d.estado)">
                {{ estadoLabel(d.estado) }}
              </span>
              · Creada {{ d.created_at | date:'mediumDate' }}
              @if (d.convenio_codigo) {
                · Convenio <strong>{{ d.convenio_codigo }}</strong>
              }
            </p>
          </div>
          <div class="actions">
            <a routerLink="/jovenes" class="ui-btn ui-btn--ghost ui-btn--sm">
              <i class="fa fa-arrow-left" aria-hidden="true"></i> Listado
            </a>
            @if (d.estado === 'enviada') {
              <button class="ui-btn ui-btn--primary" (click)="validar()"
                      [disabled]="actionLoading()">
                <i class="fa fa-check" aria-hidden="true"></i> Validar
              </button>
              <button class="ui-btn ui-btn--danger" (click)="rechazar()"
                      [disabled]="actionLoading()">
                <i class="fa fa-times" aria-hidden="true"></i> Rechazar
              </button>
            }
          </div>
        </header>

        @if (actionResult()) {
          <div class="ui-info-bar ui-info-bar--success">{{ actionResult() }}</div>
        }

        <div class="grid">
          <!-- Beneficiario -->
          <article class="ui-card">
            <header class="ui-card__header">
              <h2 class="ui-card__title"><i class="fa fa-user" aria-hidden="true"></i> Beneficiario</h2>
            </header>
            <dl class="kv">
              <dt>Documento</dt><dd><code>{{ d.tipo_doc_codigo }} {{ d.numero_documento }}</code></dd>
              <dt>Nombre</dt><dd>{{ d.nombre_completo }}</dd>
              <dt>Teléfono</dt><dd>{{ d.telefono || '—' }}</dd>
              <dt>Correo</dt><dd>{{ d.correo || '—' }}</dd>
              <dt>Dirección</dt><dd>{{ d.direccion || '—' }}</dd>
              @if (d.barrio_nombre) {
                <dt>Barrio</dt><dd>{{ d.barrio_nombre }} <small class="muted">({{ d.barrio_codigo }})</small></dd>
              }
              @if (d.upl_nombre) {
                <dt>UPL</dt><dd>{{ d.upl_nombre }} <small class="muted">({{ d.upl_codigo }})</small></dd>
              }
            </dl>
          </article>

          <!-- Académico -->
          <article class="ui-card">
            <header class="ui-card__header">
              <h2 class="ui-card__title"><i class="fa fa-book-open" aria-hidden="true"></i> Información académica</h2>
            </header>
            <dl class="kv">
              <dt>Nivel</dt><dd>{{ d.nivel_formacion_label || '—' }}</dd>
              <dt>Institución</dt><dd>{{ d.institucion || '—' }}</dd>
              <dt>Programa</dt><dd>{{ d.programa_academico || '—' }}</dd>
              <dt>Periodo</dt><dd>{{ d.periodo_academico || '—' }}</dd>
            </dl>
          </article>

          <!-- Cumplimiento -->
          <article class="ui-card ui-card--accent" style="grid-column: 1 / -1;">
            <header class="ui-card__header">
              <h2 class="ui-card__title"><i class="fa fa-bullseye" aria-hidden="true"></i> Cumplimiento de metas</h2>
              <p class="ui-card__subtitle">
                Convenio 773-2025: acceso (meta 23771) y permanencia (meta 23772).
              </p>
            </header>
            <div class="cumplimiento">
              <div class="cumpl-item" [class.cumpl-item--ok]="d.cumplimiento_acceso">
                @if (d.cumplimiento_acceso) {
                  <i class="fa fa-check-circle" aria-hidden="true"></i>
                } @else {
                  <i class="fa fa-times-circle" aria-hidden="true"></i>
                }
                <strong>Acceso (23771)</strong>
                <small>{{ d.cumplimiento_acceso ? 'Cumple' : 'No cumple' }}</small>
              </div>
              <div class="cumpl-item" [class.cumpl-item--ok]="d.cumplimiento_permanencia">
                @if (d.cumplimiento_permanencia) {
                  <i class="fa fa-check-circle" aria-hidden="true"></i>
                } @else {
                  <i class="fa fa-times-circle" aria-hidden="true"></i>
                }
                <strong>Permanencia (23772)</strong>
                <small>{{ d.cumplimiento_permanencia ? 'Cumple' : 'No cumple' }}</small>
              </div>
            </div>
            @if (d.metas_cumplidas?.length) {
              <p class="muted">
                <small>Metas reportadas: {{ d.metas_cumplidas.join(', ') }}</small>
              </p>
            }
          </article>

          <!-- Elementos entregados -->
          @if (d.elementos?.length) {
            <article class="ui-card" style="grid-column: 1 / -1;">
              <header class="ui-card__header">
                <h2 class="ui-card__title"><i class="fa fa-box-open" aria-hidden="true"></i> Elementos entregados</h2>
                <p class="ui-card__subtitle">{{ d.elementos.length }} elemento{{ d.elementos.length === 1 ? '' : 's' }}.</p>
              </header>
              <div class="ui-table-responsive">
                <table class="ui-table">
                  <thead>
                    <tr>
                      <th>Código</th>
                      <th>Elemento</th>
                      <th class="ui-table__cell--center">Cantidad</th>
                    </tr>
                  </thead>
                  <tbody>
                    @for (el of d.elementos; track el.codigo) {
                      <tr>
                        <td><code class="small">{{ el.codigo || '—' }}</code></td>
                        <td>{{ el.nombre || '—' }}</td>
                        <td class="ui-table__cell--center"><strong>{{ el.cantidad }}</strong></td>
                      </tr>
                    }
                  </tbody>
                </table>
              </div>
            </article>
          }

          <!-- Firma -->
          @if (d.tiene_firma) {
            <article class="ui-card" style="grid-column: 1 / -1;">
              <header class="ui-card__header">
                <h2 class="ui-card__title"><i class="fa fa-signature" aria-hidden="true"></i> Firma del beneficiario</h2>
                <p class="ui-card__subtitle">
                  Almacenada cifrada en MongoDB.
                  @if (d.firma_fecha) {
                    Fecha: {{ d.firma_fecha | date:'medium' }}
                  }
                </p>
              </header>
              <p class="muted">
                <small><i class="fa fa-check-circle text-success" aria-hidden="true"></i>
                Firma registrada correctamente.</small>
              </p>
            </article>
          }

          @if (d.observaciones) {
            <article class="ui-card" style="grid-column: 1 / -1;">
              <header class="ui-card__header">
                <h2 class="ui-card__title"><i class="fa fa-comment-dots" aria-hidden="true"></i> Observaciones</h2>
              </header>
              <p>{{ d.observaciones }}</p>
            </article>
          }
        </div>
      }
    </div>
  `,
  styles: [`
    @use '../../../styles/tokens' as *;

    :host { display: block; }
    .page { max-width: 1200px; margin: 0 auto; }
    .page__header {
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      gap: $space-3;
      flex-wrap: wrap;
      margin-bottom: $space-4;
    }
    .page__header h1 { margin: 0; color: $color-primary; i { margin-right: $space-2; } }
    .page__subtitle { margin: $space-1 0 0; color: $color-text-muted; }
    .actions { display: flex; gap: $space-2; flex-wrap: wrap; }

    .grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(360px, 1fr));
      gap: $space-4;
    }

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

    .cumplimiento {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
      gap: $space-3;
    }
    .cumpl-item {
      display: flex;
      flex-direction: column;
      align-items: flex-start;
      gap: $space-1;
      padding: $space-3;
      border: 1px solid $color-border;
      border-radius: $radius-md;
      background: $color-bg-subtle;
      color: $color-text-muted;

      i {
        font-size: 1.5rem;
        color: $color-danger;
      }
      &--ok {
        border-color: $color-success;
        background: $color-success-bg;
        color: $color-text;
        i { color: $color-success; }
      }
    }

    .muted { color: $color-text-muted; }
    .small { font-size: $font-size-xs; }
    .text-success { color: $color-success; }
  `],
})
export class EntregaDetailComponent implements OnInit {
  private api = inject(JovenesApi);
  private route = inject(ActivatedRoute);
  private layout = inject(LayoutService);

  loading = signal<boolean>(true);
  errorMsg = signal<string>('');
  data = signal<EntregaDetail | null>(null);
  actionLoading = signal<boolean>(false);
  actionResult = signal<string>('');

  ngOnInit(): void {
    const id = Number(this.route.snapshot.paramMap.get('id'));
    if (!id || isNaN(id)) {
      this.errorMsg.set('ID inválido.');
      this.loading.set(false);
      return;
    }
    this.layout.setBreadcrumb([
      { label: 'Inicio', url: '/' },
      { label: 'Jóvenes a la E', url: '/jovenes' },
      { label: `#${id}` },
    ]);
    this.load(id);
  }

  load(id: number): void {
    this.loading.set(true);
    this.api.detail(id).subscribe({
      next: (d) => {
        this.data.set(d);
        this.loading.set(false);
      },
      error: (e) => {
        this.loading.set(false);
        if (e.status === 404) {
          this.errorMsg.set('Entrega no encontrada.');
        } else if (e.status === 403) {
          this.errorMsg.set('No tienes permiso para ver esta entrega.');
        } else {
          this.errorMsg.set(`Error ${e.status ?? '?'}: ${e.message ?? 'desconocido'}`);
        }
      },
    });
  }

  validar(): void {
    const d = this.data();
    if (!d) return;
    if (!confirm(`¿Confirmas que la entrega #${d.id} cumple con los requisitos?`)) return;
    this.executeAction(d.id, 'validar', 'Entrega validada correctamente.');
  }

  rechazar(): void {
    const d = this.data();
    if (!d) return;
    const obs = prompt('Motivo del rechazo (obligatorio):');
    if (!obs || !obs.trim()) {
      alert('El motivo de rechazo es obligatorio.');
      return;
    }
    this.executeAction(d.id, 'rechazar', 'Entrega rechazada.', obs.trim());
  }

  private executeAction(
    id: number,
    accion: 'validar' | 'rechazar',
    successMsg: string,
    observaciones?: string,
  ): void {
    this.actionLoading.set(true);
    this.actionResult.set('');
    this.api.updateEstado(id, { accion, observaciones }).subscribe({
      next: (d) => {
        this.data.set(d);
        this.actionLoading.set(false);
        this.actionResult.set(successMsg);
      },
      error: (e) => {
        this.actionLoading.set(false);
        const msg = e.error?.observaciones?.[0] ?? e.message ?? 'desconocido';
        this.errorMsg.set(`Error ${e.status ?? '?'} al actualizar: ${msg}`);
      },
    });
  }

  estadoLabel(e: EntregaEstado): string {
    return e === 'enviada' ? 'Enviada' : e === 'validada' ? 'Validada' : 'Rechazada';
  }

  badgeClass(e: EntregaEstado): string {
    return e === 'validada'
      ? 'ui-badge--success'
      : e === 'rechazada'
        ? 'ui-badge--danger'
        : 'ui-badge--warning';
  }
}
