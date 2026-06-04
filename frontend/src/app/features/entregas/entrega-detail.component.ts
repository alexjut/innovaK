import { CommonModule } from '@angular/common';
import { Component, OnInit, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { LayoutService } from '../../core/layout/layout.service';
import { EntregasService } from './entregas.service';
import { ElementoEntregado, EntregaEstado, EntregaInsumoDetail } from './entregas.types';

/**
 * Vista 360° de una entrega de insumos. Permite validar/rechazar.
 *
 * El rechazo requiere observaciones (motivo obligatorio — validado en backend
 * y reforzado aquí con prompt inline). Al validar, el backend sincroniza KPIs.
 */
@Component({
  standalone: true,
  selector: 'app-entrega-detail',
  imports: [CommonModule, FormsModule, RouterLink],
  template: `
    <div class="page">

      <!-- Cargando -->
      @if (loading()) {
        <div class="ui-info-bar ui-info-bar--info">
          <i class="fa fa-spinner fa-spin" aria-hidden="true"></i>
          Cargando entrega…
        </div>
      }

      <!-- Error -->
      @if (!loading() && errorMsg()) {
        <div class="ui-info-bar ui-info-bar--danger">
          <strong>Error:</strong> {{ errorMsg() }}
        </div>
        <a routerLink="/entregas" class="ui-btn ui-btn--ghost">
          <i class="fa fa-arrow-left" aria-hidden="true"></i> Volver al listado
        </a>
      }

      <!-- Detalle -->
      @if (!loading() && !errorMsg() && data(); as d) {

        <header class="page__header">
          <div>
            <h1>
              <i class="fa fa-box-open" aria-hidden="true"></i>
              Entrega de insumos #{{ d.id }}
            </h1>
            <p class="page__subtitle">
              <span class="ui-badge" [class]="badgeClass(d.estado)">
                {{ estadoLabel(d.estado) }}
              </span>
              · Registrada {{ d.created_at | date: 'mediumDate' }}
              @if (d.evento) {
                · Evento <strong>{{ d.evento.nombre }}</strong>
              }
            </p>
          </div>

          <div class="actions">
            <a routerLink="/entregas" class="ui-btn ui-btn--ghost ui-btn--sm">
              <i class="fa fa-arrow-left" aria-hidden="true"></i> Listado
            </a>
            @if (d.estado === 'enviada') {
              <button class="ui-btn ui-btn--primary"
                      (click)="validar()"
                      [disabled]="actionLoading()">
                <i class="fa fa-check" aria-hidden="true"></i> Validar
              </button>
              <button class="ui-btn ui-btn--danger"
                      (click)="mostrarModalRechazo()"
                      [disabled]="actionLoading()">
                <i class="fa fa-times" aria-hidden="true"></i> Rechazar
              </button>
            }
          </div>
        </header>

        <!-- Feedback de acción -->
        @if (actionResult()) {
          <div class="ui-info-bar ui-info-bar--success">
            <i class="fa fa-check-circle" aria-hidden="true"></i>
            {{ actionResult() }}
          </div>
        }
        @if (actionError()) {
          <div class="ui-info-bar ui-info-bar--danger">
            <strong>Error al actualizar:</strong> {{ actionError() }}
          </div>
        }

        <!-- Modal de rechazo -->
        @if (mostrandoRechazo()) {
          <div class="modal-backdrop" (click)="cancelarRechazo()">
            <div class="modal" role="dialog" aria-modal="true"
                 aria-labelledby="modal-title"
                 (click)="$event.stopPropagation()">
              <h3 id="modal-title" class="modal__title">
                <i class="fa fa-times-circle text-danger" aria-hidden="true"></i>
                Rechazar entrega #{{ d.id }}
              </h3>
              <p class="modal__desc">
                El motivo de rechazo se guardará en la entrega y es obligatorio.
              </p>
              <label class="modal__label" for="obs-rechazo">
                Motivo de rechazo <span aria-hidden="true">*</span>
              </label>
              <textarea id="obs-rechazo"
                        class="modal__textarea"
                        rows="3"
                        placeholder="Describe el motivo de rechazo…"
                        [(ngModel)]="motivoRechazo"
                        maxlength="500"
                        autofocus></textarea>
              @if (motivoError()) {
                <p class="modal__field-error">{{ motivoError() }}</p>
              }
              <div class="modal__actions">
                <button class="ui-btn ui-btn--ghost" (click)="cancelarRechazo()">
                  Cancelar
                </button>
                <button class="ui-btn ui-btn--danger"
                        (click)="confirmarRechazo()"
                        [disabled]="actionLoading()">
                  <i class="fa fa-times" aria-hidden="true"></i> Confirmar rechazo
                </button>
              </div>
            </div>
          </div>
        }

        <!-- Grid de cards -->
        <div class="grid">

          <!-- Beneficiario -->
          <article class="ui-card">
            <header class="ui-card__header">
              <h2 class="ui-card__title">
                <i class="fa fa-user" aria-hidden="true"></i> Beneficiario
              </h2>
            </header>
            <dl class="kv">
              <dt>Documento</dt>
              <dd>
                <code>{{ d.tipo_doc_codigo ?? '' }} {{ d.numero_documento }}</code>
              </dd>
              <dt>Nombre</dt>
              <dd>{{ d.nombre_completo || '—' }}</dd>
              <dt>Teléfono</dt>
              <dd>{{ d.telefono || '—' }}</dd>
              <dt>Correo</dt>
              <dd>{{ d.correo || '—' }}</dd>
              <dt>Dirección</dt>
              <dd>{{ d.direccion || '—' }}</dd>
              @if (d.barrio_nombre || d.barrio_codigo) {
                <dt>Barrio</dt>
                <dd>
                  {{ d.barrio_nombre || '—' }}
                  @if (d.barrio_codigo) {
                    <small class="muted">({{ d.barrio_codigo }})</small>
                  }
                </dd>
              }
              @if (d.upl_nombre || d.upl_codigo) {
                <dt>UPL</dt>
                <dd>
                  {{ d.upl_nombre || '—' }}
                  @if (d.upl_codigo) {
                    <small class="muted">({{ d.upl_codigo }})</small>
                  }
                </dd>
              }
            </dl>
          </article>

          <!-- Evento y KPIs -->
          <article class="ui-card ui-card--primary">
            <header class="ui-card__header">
              <h2 class="ui-card__title">
                <i class="fa fa-calendar-check" aria-hidden="true"></i> Evento de captura
              </h2>
            </header>
            @if (d.evento) {
              <dl class="kv">
                <dt>Nombre</dt>
                <dd>{{ d.evento.nombre }}</dd>
                <dt>ID evento</dt>
                <dd><code>#{{ d.evento.id }}</code></dd>
              </dl>
            } @else {
              <p class="muted">Sin evento asociado.</p>
            }
            <div class="kpi-hint">
              <i class="fa fa-chart-line" aria-hidden="true"></i>
              Al validar, se actualizan los indicadores vinculados a este evento.
            </div>
          </article>

          <!-- Tabla de insumos — ocupa ancho completo -->
          <article class="ui-card span-full">
            <header class="ui-card__header">
              <h2 class="ui-card__title">
                <i class="fa fa-boxes-stacked" aria-hidden="true"></i>
                Insumos entregados
              </h2>
              <p class="ui-card__subtitle">
                @if (d.elementos.length > 0) {
                  {{ d.elementos.length }} tipo{{ d.elementos.length === 1 ? '' : 's' }} de insumo ·
                  {{ totalUnidades(d.elementos) }} unidad{{ totalUnidades(d.elementos) === 1 ? '' : 'es' }} en total.
                } @else {
                  Sin insumos registrados.
                }
              </p>
            </header>
            @if (d.elementos.length > 0) {
              <div class="ui-table-responsive">
                <table class="ui-table">
                  <thead>
                    <tr>
                      <th>Código</th>
                      <th>Insumo</th>
                      <th>Categoría</th>
                      <th class="ui-table__cell--center">Cantidad</th>
                    </tr>
                  </thead>
                  <tbody>
                    @for (el of d.elementos; track el.codigo) {
                      <tr>
                        <td><code class="small">{{ el.codigo || '—' }}</code></td>
                        <td>{{ el.nombre || '—' }}</td>
                        <td>
                          @if (el.categoria) {
                            <span class="categoria-badge">{{ el.categoria }}</span>
                          } @else {
                            <span class="muted">—</span>
                          }
                        </td>
                        <td class="ui-table__cell--center">
                          <strong class="cantidad">{{ el.cantidad }}</strong>
                        </td>
                      </tr>
                    }
                  </tbody>
                  <tfoot>
                    <tr>
                      <td colspan="3" class="ui-table__cell--right">
                        <strong>Total unidades</strong>
                      </td>
                      <td class="ui-table__cell--center">
                        <strong class="cantidad cantidad--total">
                          {{ totalUnidades(d.elementos) }}
                        </strong>
                      </td>
                    </tr>
                  </tfoot>
                </table>
              </div>
            } @else {
              <div class="ui-empty-state ui-empty-state--compact">
                <i class="fa fa-box-open" aria-hidden="true"></i>
                <p>No se registraron insumos en esta entrega.</p>
              </div>
            }
          </article>

          <!-- Firma -->
          @if (d.tiene_firma) {
            <article class="ui-card span-full">
              <header class="ui-card__header">
                <h2 class="ui-card__title">
                  <i class="fa fa-signature" aria-hidden="true"></i> Firma del beneficiario
                </h2>
                <p class="ui-card__subtitle">
                  Almacenada cifrada en MongoDB.
                  @if (d.firma_fecha) {
                    Fecha: {{ d.firma_fecha | date: 'medium' }}
                  }
                </p>
              </header>
              <p class="firma-ok">
                <i class="fa fa-check-circle text-success" aria-hidden="true"></i>
                Firma registrada correctamente.
              </p>
            </article>
          }

          <!-- Observaciones -->
          @if (d.observaciones) {
            <article class="ui-card span-full">
              <header class="ui-card__header">
                <h2 class="ui-card__title">
                  <i class="fa fa-comment-dots" aria-hidden="true"></i> Observaciones
                </h2>
              </header>
              <p class="observaciones">{{ d.observaciones }}</p>
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
    .page__header h1 {
      margin: 0;
      color: $color-primary;
      i { margin-right: $space-2; }
    }
    .page__subtitle {
      margin: $space-1 0 0;
      color: $color-text-muted;
    }
    .actions {
      display: flex;
      gap: $space-2;
      flex-wrap: wrap;
      align-items: flex-start;
    }

    /* Grid de cards */
    .grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(360px, 1fr));
      gap: $space-4;
    }
    .span-full { grid-column: 1 / -1; }

    /* KV descriptor list */
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

    /* Hint KPI en card evento */
    .kpi-hint {
      margin-top: $space-3;
      padding: $space-2 $space-3;
      border-radius: $radius-md;
      background: rgba(0,0,0,.04);
      color: $color-text-muted;
      font-size: $font-size-sm;
      display: flex;
      align-items: center;
      gap: $space-2;
    }

    /* Tabla insumos */
    .cantidad {
      font-size: $font-size-md;
      font-weight: $font-weight-bold;
    }
    .cantidad--total {
      font-size: $font-size-lg;
      color: $color-primary;
    }
    .categoria-badge {
      display: inline-block;
      padding: 1px $space-2;
      border-radius: $radius-sm;
      background: $color-bg-subtle;
      border: 1px solid $color-border;
      font-size: $font-size-xs;
      color: $color-text-muted;
      text-transform: capitalize;
    }

    /* Firma */
    .firma-ok {
      display: flex;
      align-items: center;
      gap: $space-2;
      color: $color-text-muted;
      font-size: $font-size-sm;
    }

    /* Observaciones */
    .observaciones {
      white-space: pre-wrap;
      color: $color-text;
      font-size: $font-size-sm;
    }

    /* Modal de rechazo */
    .modal-backdrop {
      position: fixed;
      inset: 0;
      background: rgba(0,0,0,.45);
      display: flex;
      align-items: center;
      justify-content: center;
      z-index: 1000;
      padding: $space-4;
    }
    .modal {
      background: #fff;
      border-radius: $radius-lg;
      padding: $space-6;
      max-width: 480px;
      width: 100%;
      box-shadow: 0 20px 60px rgba(0,0,0,.2);
    }
    .modal__title {
      margin: 0 0 $space-2;
      font-size: $font-size-lg;
      display: flex;
      align-items: center;
      gap: $space-2;
    }
    .modal__desc {
      color: $color-text-muted;
      font-size: $font-size-sm;
      margin: 0 0 $space-4;
    }
    .modal__label {
      display: block;
      font-weight: $font-weight-semibold;
      font-size: $font-size-sm;
      margin-bottom: $space-1;
    }
    .modal__textarea {
      width: 100%;
      border: 1.5px solid $color-border;
      border-radius: $radius-md;
      padding: $space-2 $space-3;
      font-family: inherit;
      font-size: $font-size-sm;
      resize: vertical;
      box-sizing: border-box;
      transition: border-color 0.15s;

      &:focus {
        outline: none;
        border-color: $color-primary;
        box-shadow: 0 0 0 $focus-ring-width $focus-ring-color;
      }
    }
    .modal__field-error {
      color: $color-danger;
      font-size: $font-size-xs;
      margin: $space-1 0 0;
    }
    .modal__actions {
      display: flex;
      justify-content: flex-end;
      gap: $space-2;
      margin-top: $space-4;
    }

    .muted { color: $color-text-muted; }
    .small { font-size: $font-size-xs; }
    .text-success { color: $color-success; }
    .text-danger  { color: $color-danger; }
  `],
})
export class EntregaDetailComponent implements OnInit {
  private svc = inject(EntregasService);
  private route = inject(ActivatedRoute);
  private layout = inject(LayoutService);

  loading = signal<boolean>(true);
  errorMsg = signal<string>('');
  data = signal<EntregaInsumoDetail | null>(null);
  actionLoading = signal<boolean>(false);
  actionResult = signal<string>('');
  actionError = signal<string>('');

  mostrandoRechazo = signal<boolean>(false);
  motivoRechazo = '';
  motivoError = signal<string>('');

  ngOnInit(): void {
    const id = Number(this.route.snapshot.paramMap.get('id'));
    if (!id || isNaN(id)) {
      this.errorMsg.set('ID de entrega inválido.');
      this.loading.set(false);
      return;
    }
    this.layout.setBreadcrumb([
      { label: 'Inicio', url: '/' },
      { label: 'Entrega de insumos', url: '/entregas' },
      { label: `#${id}` },
    ]);
    this.load(id);
  }

  load(id: number): void {
    this.loading.set(true);
    this.svc.detail(id).subscribe({
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
    if (!confirm(`¿Confirmas que la entrega #${d.id} cumple los requisitos y los insumos fueron entregados correctamente?`)) {
      return;
    }
    this.actionResult.set('');
    this.actionError.set('');
    this.executeAction(d.id, 'validar', 'Entrega validada. Los indicadores han sido actualizados.');
  }

  mostrarModalRechazo(): void {
    this.motivoRechazo = '';
    this.motivoError.set('');
    this.mostrandoRechazo.set(true);
  }

  cancelarRechazo(): void {
    this.mostrandoRechazo.set(false);
  }

  confirmarRechazo(): void {
    const motivo = this.motivoRechazo.trim();
    if (!motivo) {
      this.motivoError.set('El motivo de rechazo es obligatorio.');
      return;
    }
    const d = this.data();
    if (!d) return;
    this.mostrandoRechazo.set(false);
    this.actionResult.set('');
    this.actionError.set('');
    this.executeAction(d.id, 'rechazar', 'Entrega rechazada.', motivo);
  }

  private executeAction(
    id: number,
    accion: 'validar' | 'rechazar',
    successMsg: string,
    observaciones?: string,
  ): void {
    this.actionLoading.set(true);
    this.svc.updateEstado(id, { accion, observaciones }).subscribe({
      next: (d) => {
        this.data.set(d);
        this.actionLoading.set(false);
        this.actionResult.set(successMsg);
      },
      error: (e) => {
        this.actionLoading.set(false);
        const msg =
          e.error?.observaciones?.[0] ??
          e.error?.detail ??
          e.message ??
          'desconocido';
        this.actionError.set(`Error ${e.status ?? '?'}: ${msg}`);
      },
    });
  }

  totalUnidades(elementos: ElementoEntregado[]): number {
    return elementos.reduce((acc, el) => acc + el.cantidad, 0);
  }

  estadoLabel(e: EntregaEstado): string {
    const map: Record<EntregaEstado, string> = {
      enviada: 'Enviada',
      validada: 'Validada',
      rechazada: 'Rechazada',
    };
    return map[e] ?? e;
  }

  badgeClass(e: EntregaEstado): string {
    return e === 'validada'
      ? 'ui-badge--success'
      : e === 'rechazada'
        ? 'ui-badge--danger'
        : 'ui-badge--warning';
  }
}
