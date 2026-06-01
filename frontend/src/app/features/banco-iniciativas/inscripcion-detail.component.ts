import { CommonModule } from '@angular/common';
import { Component, OnInit, inject, signal } from '@angular/core';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { LayoutService } from '../../core/layout/layout.service';
import { BancoApi } from './banco.api';
import { InscripcionDetail, InscripcionEstado } from './banco.types';

/**
 * Vista 360° de una inscripción del Banco. Permite validar/rechazar.
 *
 * Réplica del HTML Django `inscripcion_detalle.html`. Muestra todas
 * las secciones (persona, organización, caracterización, firma) en
 * un layout de 2 columnas en desktop.
 */
@Component({
  standalone: true,
  selector: 'app-banco-inscripcion-detail',
  imports: [CommonModule, RouterLink],
  template: `
    <div class="page">
      @if (loading()) {
        <div class="ui-info-bar ui-info-bar--info">Cargando inscripción…</div>
      } @else if (errorMsg()) {
        <div class="ui-info-bar ui-info-bar--danger">
          <strong>Error:</strong> {{ errorMsg() }}
        </div>
        <a routerLink="/banco" class="ui-btn ui-btn--ghost">↩ Volver al listado</a>
      }
      @if (!loading() && !errorMsg() && data(); as d) {
        <header class="page__header">
          <div>
            <h1>Inscripción #{{ d.id }}</h1>
            <p class="page__subtitle">
              <span class="ui-badge" [class]="badgeClass(d.estado)">
                {{ estadoLabel(d.estado) }}
              </span>
              · Creada {{ d.created_at | date:'mediumDate' }}
            </p>
          </div>
          <div class="actions">
            <a routerLink="/banco" class="ui-btn ui-btn--ghost ui-btn--sm">
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
          <!-- Persona representante -->
          <article class="ui-card">
            <header class="ui-card__header">
              <h2 class="ui-card__title">Representante</h2>
            </header>
            <dl class="kv">
              <dt>Documento</dt><dd><code>{{ d.numero_documento }}</code></dd>
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

          <!-- Organización -->
          <article class="ui-card">
            <header class="ui-card__header">
              <h2 class="ui-card__title">Organización / Colectivo</h2>
            </header>
            <dl class="kv">
              <dt>Nombre</dt><dd>{{ d.organizacion_nombre || '—' }}</dd>
              <dt>Tipo</dt><dd>{{ d.tipo_organizacion_codigo || '—' }}</dd>
              <dt>Personas</dt><dd>{{ d.total_personas ?? '—' }}</dd>
              <dt>Evento</dt><dd>{{ d.evento_nombre || '—' }}</dd>
              @if (d.redes_sociales && socialKeys(d.redes_sociales).length) {
                <dt>Redes</dt>
                <dd>
                  <ul class="redes">
                    @for (k of socialKeys(d.redes_sociales); track k) {
                      <li>
                        <strong>{{ k }}:</strong>
                        <a [href]="d.redes_sociales![k]" target="_blank" rel="noopener">
                          {{ d.redes_sociales![k] }}
                        </a>
                      </li>
                    }
                  </ul>
                </dd>
              }
            </dl>
          </article>

          <!-- Caracterización -->
          <article class="ui-card ui-card--accent" style="grid-column: 1 / -1;">
            <header class="ui-card__header">
              <h2 class="ui-card__title">Caracterización del proyecto</h2>
            </header>
            <div class="chips-group">
              @if (d.enfoques?.length) {
                <div class="chips-block">
                  <h4>Enfoques diferenciales</h4>
                  <div class="chips">
                    @for (e of d.enfoques; track e) {
                      <span class="ui-badge ui-badge--info">{{ e }}</span>
                    }
                  </div>
                </div>
              }
              @if (d.escenarios?.length) {
                <div class="chips-block">
                  <h4>Escenarios</h4>
                  <div class="chips">
                    @for (s of d.escenarios; track s) {
                      <span class="ui-badge ui-badge--neutral">{{ s }}</span>
                    }
                  </div>
                </div>
              }
              @if (d.implementos?.length) {
                <div class="chips-block">
                  <h4>Implementos</h4>
                  <div class="chips">
                    @for (i of d.implementos; track i) {
                      <span class="ui-badge ui-badge--neutral">{{ i }}</span>
                    }
                  </div>
                </div>
              }
              @if (d.beneficios_alk?.length) {
                <div class="chips-block">
                  <h4>Beneficios ALK</h4>
                  <div class="chips">
                    @for (b of d.beneficios_alk; track b) {
                      <span class="ui-badge ui-badge--success">{{ b }}</span>
                    }
                  </div>
                </div>
              }
            </div>
            @if (d.observaciones) {
              <hr>
              <h4>Observaciones</h4>
              <p>{{ d.observaciones }}</p>
            }
          </article>

          <!-- Firma -->
          @if (hasFirma()) {
            <article class="ui-card" style="grid-column: 1 / -1;">
              <header class="ui-card__header">
                <h2 class="ui-card__title">Firma del representante</h2>
                <p class="ui-card__subtitle">Imagen cifrada almacenada en MongoDB.</p>
              </header>
              @if (firmaUrl(); as url) {
                <img [src]="url" alt="Firma del representante" class="firma">
              } @else {
                <p class="muted">Firma registrada (id: <code>{{ firmaMongoId() }}</code>) pero no descargable desde el cliente.</p>
              }
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
    .page__header h1 { margin: 0; color: $color-primary; }
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

    .redes { list-style: none; padding: 0; margin: 0; }
    .redes li { margin-bottom: $space-1; font-size: $font-size-sm; }

    .chips-group {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
      gap: $space-3;
    }
    .chips-block h4 {
      margin: 0 0 $space-2;
      color: $color-text-muted;
      font-size: $font-size-sm;
      font-weight: $font-weight-semibold;
      text-transform: uppercase;
      letter-spacing: 0.05em;
    }
    .chips { display: flex; flex-wrap: wrap; gap: $space-1; }

    .firma {
      max-width: 100%;
      max-height: 300px;
      border: 1px solid $color-border;
      border-radius: $radius-md;
      padding: $space-3;
      background: $color-bg-subtle;
    }

    .muted { color: $color-text-muted; }

    hr {
      border: 0;
      border-top: 1px solid $color-border;
      margin: $space-3 0;
    }
  `],
})
export class InscripcionDetailComponent implements OnInit {
  private api = inject(BancoApi);
  private route = inject(ActivatedRoute);
  private router = inject(Router);
  private layout = inject(LayoutService);

  loading = signal<boolean>(true);
  errorMsg = signal<string>('');
  data = signal<InscripcionDetail | null>(null);
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
      { label: 'Banco de Iniciativas', url: '/banco' },
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
          this.errorMsg.set('Inscripción no encontrada.');
        } else if (e.status === 403) {
          this.errorMsg.set('No tienes permiso para ver esta inscripción.');
        } else {
          this.errorMsg.set(`Error ${e.status ?? '?'}: ${e.message ?? 'desconocido'}`);
        }
      },
    });
  }

  validar(): void {
    const d = this.data();
    if (!d) return;
    if (!confirm(`¿Confirmas que la inscripción #${d.id} cumple con los requisitos?`)) return;
    this.executeAction(d.id, 'validada', 'Inscripción validada correctamente.');
  }

  rechazar(): void {
    const d = this.data();
    if (!d) return;
    const obs = prompt('Motivo del rechazo (opcional):') ?? '';
    if (obs === null) return;
    this.executeAction(d.id, 'rechazada', 'Inscripción rechazada.', obs);
  }

  private executeAction(
    id: number,
    estado: 'validada' | 'rechazada',
    successMsg: string,
    observacion?: string,
  ): void {
    this.actionLoading.set(true);
    this.actionResult.set('');
    this.api.updateEstado(id, { estado, observacion }).subscribe({
      next: (d) => {
        this.data.set(d);
        this.actionLoading.set(false);
        this.actionResult.set(successMsg);
      },
      error: (e) => {
        this.actionLoading.set(false);
        this.errorMsg.set(`Error ${e.status ?? '?'} al actualizar: ${e.message ?? 'desconocido'}`);
      },
    });
  }

  estadoLabel(e: InscripcionEstado): string {
    return e === 'enviada' ? 'Enviada' : e === 'validada' ? 'Validada' : 'Rechazada';
  }

  badgeClass(e: InscripcionEstado): string {
    return e === 'validada'
      ? 'ui-badge--success'
      : e === 'rechazada'
        ? 'ui-badge--danger'
        : 'ui-badge--warning';
  }

  socialKeys(redes: Record<string, string> | null): string[] {
    return redes ? Object.keys(redes) : [];
  }

  hasFirma(): boolean {
    const d = this.data();
    return !!(d && (d.firma_url || d.firma_mongo_id));
  }

  firmaUrl(): string | null {
    return this.data()?.firma_url ?? null;
  }

  firmaMongoId(): string | null {
    return this.data()?.firma_mongo_id ?? null;
  }
}
