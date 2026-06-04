import { CommonModule } from '@angular/common';
import { Component, OnInit, inject, signal } from '@angular/core';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { LayoutService } from '../../core/layout/layout.service';
import { BancoApi } from './banco.api';
import { InscripcionDetail, InscripcionEstado } from './banco.types';

/**
 * Vista 360° de una inscripción del Banco de Iniciativas.
 * Replica y supera el HTML legacy `inscripcion_detalle.html` con
 * 8 secciones temáticas, header con gradiente institucional,
 * chips de colores, imagen de firma real, auditoría y accesos rápidos.
 */
@Component({
  standalone: true,
  selector: 'app-banco-inscripcion-detail',
  imports: [CommonModule, RouterLink],
  template: `
    <div class="page">

      @if (loading()) {
        <div class="ui-info-bar ui-info-bar--info">
          <i class="fa fa-spinner fa-spin" aria-hidden="true"></i>
          Cargando inscripción…
        </div>
      }

      @if (!loading() && errorMsg()) {
        <div class="ui-info-bar ui-info-bar--danger">
          <i class="fa fa-triangle-exclamation" aria-hidden="true"></i>
          <strong>Error:</strong> {{ errorMsg() }}
        </div>
        <a routerLink="/banco" class="ui-btn ui-btn--ghost">
          <i class="fa fa-arrow-left" aria-hidden="true"></i> Volver al listado
        </a>
      }

      @if (!loading() && !errorMsg() && data(); as d) {

        <!-- ══ HERO HEADER ══════════════════════════════════════════════ -->
        <header class="hero">
          <div class="hero__bg" aria-hidden="true"></div>
          <div class="hero__content">
            <div class="hero__left">
              <div class="hero__icon-wrap">
                <i class="fa fa-clipboard-list" aria-hidden="true"></i>
              </div>
              <div>
                <h1 class="hero__title">{{ d.organizacion?.nombre || 'Inscripción #' + d.id }}</h1>
                <p class="hero__meta">
                  Banco de Iniciativas · BI-{{ d.id }}
                  @if (d.evento?.nombre) {
                    · <em>{{ d.evento!.nombre }}</em>
                  }
                </p>
              </div>
            </div>
            <div class="hero__right">
              <span class="ui-badge hero__badge" [class]="'ui-badge--' + badgeVariant(d.estado)">
                <i class="fa" [class]="estadoIconClass(d.estado)" aria-hidden="true"></i>
                {{ estadoLabel(d.estado) }}
              </span>
            </div>
          </div>

          <!-- Barra de acciones -->
          <div class="hero__actions">
            <a routerLink="/banco" class="ui-btn ui-btn--ghost ui-btn--sm">
              <i class="fa fa-arrow-left" aria-hidden="true"></i> Listado
            </a>
            @if (d.evento?.id) {
              <a [href]="'/app/p/banco/' + d.evento!.id"
                 target="_blank" rel="noopener"
                 class="ui-btn ui-btn--outline ui-btn--sm">
                <i class="fa fa-file-lines" aria-hidden="true"></i> Formulario público
              </a>
              <a [href]="'/evento/' + d.evento!.id + '/qr/'"
                 target="_blank" rel="noopener"
                 class="ui-btn ui-btn--outline ui-btn--sm">
                <i class="fa fa-qrcode" aria-hidden="true"></i> Ver QR
              </a>
            }
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
          <div class="ui-info-bar ui-info-bar--success" role="status">
            <i class="fa fa-circle-check" aria-hidden="true"></i>
            {{ actionResult() }}
          </div>
        }

        <!-- ══ GRID PRINCIPAL ═══════════════════════════════════════════ -->
        <div class="detail-grid">

          <!-- 1. Organización -->
          <article class="ui-card detail-card" aria-labelledby="sec-org">
            <header class="ui-card__header">
              <span class="card-icon card-icon--primary">
                <i class="fa fa-building" aria-hidden="true"></i>
              </span>
              <h2 class="ui-card__title" id="sec-org">Organización</h2>
            </header>
            <dl class="kv">
              <dt>Nombre</dt>
              <dd><strong>{{ d.organizacion?.nombre || '—' }}</strong></dd>
              <dt>NIT</dt>
              <dd>
                @if (d.organizacion?.nit) {
                  <code class="mono">{{ d.organizacion!.nit }}</code>
                } @else {
                  —
                }
              </dd>
              <dt>Proyecto</dt>
              <dd>
                @if (d.proyecto_codigo) {
                  <code class="mono">{{ d.proyecto_codigo }}</code>
                } @else {
                  —
                }
              </dd>
              <dt>Disciplina</dt>
              <dd>{{ d.disciplina_principal || '—' }}</dd>
              <dt>Evento</dt>
              <dd>{{ d.evento?.nombre || '—' }}</dd>
            </dl>
          </article>

          <!-- 2. Representante legal -->
          <article class="ui-card detail-card" aria-labelledby="sec-rep">
            <header class="ui-card__header">
              <span class="card-icon card-icon--info">
                <i class="fa fa-user-tie" aria-hidden="true"></i>
              </span>
              <h2 class="ui-card__title" id="sec-rep">Representante legal</h2>
            </header>
            <dl class="kv">
              <dt>Nombre</dt>
              <dd><strong>{{ d.rep_nombre || '—' }}</strong></dd>
              <dt>Documento</dt>
              <dd>
                @if (d.rep_tipo_doc || d.rep_numero_doc) {
                  <span class="doc-pill">
                    @if (d.rep_tipo_doc) { {{ d.rep_tipo_doc }} }
                    <code class="mono">{{ d.rep_numero_doc }}</code>
                  </span>
                } @else {
                  —
                }
              </dd>
              <dt>Experiencia</dt>
              <dd>{{ d.anios_experiencia || '—' }}</dd>
              <dt>Nivel educativo</dt>
              <dd>{{ d.nivel_educativo || '—' }}</dd>
              <dt>Títulos</dt>
              <dd>{{ d.titulos_obtenidos || '—' }}</dd>
            </dl>
          </article>

          <!-- 3. Ubicación -->
          <article class="ui-card detail-card" aria-labelledby="sec-ubic">
            <header class="ui-card__header">
              <span class="card-icon card-icon--success">
                <i class="fa fa-location-dot" aria-hidden="true"></i>
              </span>
              <h2 class="ui-card__title" id="sec-ubic">Ubicación</h2>
            </header>
            <dl class="kv">
              <dt>Dirección</dt>
              <dd>{{ d.direccion || '—' }}</dd>
              <dt>Barrio</dt>
              <dd>{{ d.barrio || '—' }}</dd>
              <dt>UPL</dt>
              <dd>{{ d.upl || '—' }}</dd>
            </dl>
            @if (d.direccion) {
              <a [href]="'https://www.google.com/maps/search/' + encodeURI(d.direccion + ', Kennedy, Bogotá')"
                 target="_blank" rel="noopener"
                 class="ui-btn ui-btn--ghost ui-btn--sm map-link">
                <i class="fa fa-map" aria-hidden="true"></i> Ver en mapa
              </a>
            }
          </article>

          <!-- 4. Población -->
          <article class="ui-card detail-card" aria-labelledby="sec-pob">
            <header class="ui-card__header">
              <span class="card-icon card-icon--warning">
                <i class="fa fa-people-group" aria-hidden="true"></i>
              </span>
              <h2 class="ui-card__title" id="sec-pob">Población</h2>
            </header>
            <dl class="kv">
              <dt>Rango población</dt>
              <dd>{{ d.rango_poblacion || '—' }}</dd>
              <dt>Estrato</dt>
              <dd>
                @if (d.estrato !== null && d.estrato !== undefined) {
                  <span class="estrato-badge">{{ d.estrato }}</span>
                } @else {
                  —
                }
              </dd>
              <dt>Característica</dt>
              <dd>{{ d.caracteristica_pob || '—' }}</dd>
            </dl>
            @if (d.rango_etarios?.length) {
              <div class="chips-section">
                <span class="chips-label">
                  <i class="fa fa-users" aria-hidden="true"></i> Rangos etarios
                </span>
                <div class="chips">
                  @for (r of d.rango_etarios; track r) {
                    <span class="ui-badge ui-badge--info chip-pill">{{ r }}</span>
                  }
                </div>
              </div>
            }
            @if (d.enfoques?.length) {
              <div class="chips-section">
                <span class="chips-label">
                  <i class="fa fa-heart" aria-hidden="true"></i> Enfoques diferenciales
                </span>
                <div class="chips">
                  @for (e of d.enfoques; track e) {
                    <span class="ui-badge ui-badge--success chip-pill">{{ e }}</span>
                  }
                </div>
              </div>
            }
          </article>

          <!-- 5. Caracterización del proyecto (full-width) -->
          <article class="ui-card detail-card detail-card--wide" aria-labelledby="sec-car">
            <header class="ui-card__header">
              <span class="card-icon card-icon--accent">
                <i class="fa fa-chart-bar" aria-hidden="true"></i>
              </span>
              <h2 class="ui-card__title" id="sec-car">Caracterización del proyecto</h2>
            </header>
            <div class="chips-grid">
              @if (d.escenarios?.length) {
                <div class="chips-block">
                  <span class="chips-label">
                    <i class="fa fa-flag" aria-hidden="true"></i> Escenarios solicitados
                  </span>
                  <div class="chips">
                    @for (s of d.escenarios; track s) {
                      <span class="ui-badge ui-badge--neutral chip-pill">{{ s }}</span>
                    }
                  </div>
                </div>
              }
              @if (d.escenarios_actuales?.length) {
                <div class="chips-block">
                  <span class="chips-label">
                    <i class="fa fa-location-pin" aria-hidden="true"></i> Escenarios actuales
                  </span>
                  <div class="chips">
                    @for (s of d.escenarios_actuales; track s) {
                      <span class="ui-badge chip-pill chip-pill--teal">{{ s }}</span>
                    }
                  </div>
                </div>
              }
              @if (d.implementos?.length) {
                <div class="chips-block">
                  <span class="chips-label">
                    <i class="fa fa-futbol" aria-hidden="true"></i> Implementos deportivos
                  </span>
                  <div class="chips">
                    @for (i of d.implementos; track i) {
                      <span class="ui-badge chip-pill chip-pill--purple">{{ i }}</span>
                    }
                  </div>
                </div>
              }
            </div>
          </article>

          <!-- 6. Beneficios ALK -->
          <article class="ui-card detail-card" aria-labelledby="sec-alk">
            <header class="ui-card__header">
              <span class="card-icon card-icon--secondary">
                <i class="fa fa-star" aria-hidden="true"></i>
              </span>
              <h2 class="ui-card__title" id="sec-alk">Beneficios ALK</h2>
            </header>
            <div class="alk-beneficiada">
              @if (d.beneficiada_alk === true) {
                <span class="alk-si">
                  <i class="fa fa-check-circle" aria-hidden="true"></i> Ya beneficiada por ALK
                </span>
              } @else if (d.beneficiada_alk === false) {
                <span class="alk-no">
                  <i class="fa fa-times-circle" aria-hidden="true"></i> No ha recibido beneficios ALK
                </span>
              } @else {
                <span class="alk-nd">—</span>
              }
            </div>
            @if (d.uso_beneficio) {
              <dl class="kv kv--compact">
                <dt>Uso del beneficio</dt>
                <dd>{{ d.uso_beneficio }}</dd>
              </dl>
            }
            @if (d.beneficios_alk?.length) {
              <div class="chips-section">
                <span class="chips-label">Tipos de beneficio recibido</span>
                <div class="chips">
                  @for (b of d.beneficios_alk; track b) {
                    <span class="ui-badge ui-badge--warning chip-pill">{{ b }}</span>
                  }
                </div>
              </div>
            }
          </article>

          <!-- 7. Impacto en políticas -->
          <article class="ui-card detail-card" aria-labelledby="sec-imp">
            <header class="ui-card__header">
              <span class="card-icon card-icon--danger">
                <i class="fa fa-landmark" aria-hidden="true"></i>
              </span>
              <h2 class="ui-card__title" id="sec-imp">Impacto en políticas</h2>
            </header>
            <dl class="kv">
              <dt>Nivel de impacto</dt>
              <dd>
                @if (d.impacto_politicas) {
                  <span class="ui-badge ui-badge--info chip-pill">{{ d.impacto_politicas }}</span>
                } @else {
                  —
                }
              </dd>
              <dt>Justificación</dt>
              <dd class="text-wrap">{{ d.impacto_justificacion || '—' }}</dd>
            </dl>
          </article>

          <!-- 8. Soporte legal (full-width) -->
          <article class="ui-card detail-card detail-card--wide" aria-labelledby="sec-legal">
            <header class="ui-card__header">
              <span class="card-icon card-icon--neutral">
                <i class="fa fa-file-contract" aria-hidden="true"></i>
              </span>
              <h2 class="ui-card__title" id="sec-legal">Soporte legal y firma</h2>
            </header>
            <div class="legal-grid">
              <div class="legal-block">
                <dl class="kv">
                  <dt>N° soporte legal</dt>
                  <dd>
                    @if (d.numero_soporte_legal) {
                      <code class="mono">{{ d.numero_soporte_legal }}</code>
                    } @else {
                      —
                    }
                  </dd>
                  <dt>Documento</dt>
                  <dd>
                    @if (d.soporte_legal_url) {
                      <a [href]="d.soporte_legal_url" target="_blank" rel="noopener"
                         class="ui-btn ui-btn--outline ui-btn--sm">
                        <i class="fa fa-file-pdf" aria-hidden="true"></i> Ver documento
                      </a>
                    } @else if (d.tiene_soporte_legal) {
                      <span class="ui-badge ui-badge--neutral">
                        <i class="fa fa-lock" aria-hidden="true"></i> Cifrado en MongoDB
                      </span>
                    } @else {
                      <span class="ui-badge ui-badge--danger">Sin soporte legal</span>
                    }
                  </dd>
                </dl>
              </div>

              <div class="legal-block">
                <p class="chips-label">
                  <i class="fa fa-signature" aria-hidden="true"></i> Firma del representante
                </p>
                @if (d.tiene_firma) {
                  <div class="firma-wrap">
                    <img [src]="'/banco-iniciativas/inscripciones/' + d.id + '/firma/'"
                         alt="Firma del representante legal"
                         class="firma-img"
                         loading="lazy"
                         (error)="onFirmaError($event)" />
                    <span class="ui-badge ui-badge--success firma-badge">
                      <i class="fa fa-check" aria-hidden="true"></i> Registrada
                    </span>
                  </div>
                } @else {
                  <span class="ui-badge ui-badge--danger">
                    <i class="fa fa-times" aria-hidden="true"></i> Sin firma
                  </span>
                }
              </div>
            </div>
          </article>

          <!-- 9. Auditoría (sidebar) -->
          <article class="ui-card detail-card detail-card--audit" aria-labelledby="sec-audit">
            <header class="ui-card__header">
              <span class="card-icon card-icon--neutral">
                <i class="fa fa-clock-rotate-left" aria-hidden="true"></i>
              </span>
              <h2 class="ui-card__title" id="sec-audit">Auditoría</h2>
            </header>
            <dl class="kv kv--compact">
              <dt>Estado actual</dt>
              <dd>
                <span class="ui-badge" [class]="'ui-badge--' + badgeVariant(d.estado)">
                  {{ estadoLabel(d.estado) }}
                </span>
              </dd>
              <dt>Creada</dt>
              <dd>{{ d.created_at | date:'dd/MM/yyyy HH:mm' }}</dd>
              <dt>Actualizada</dt>
              <dd>{{ d.updated_at | date:'dd/MM/yyyy HH:mm' }}</dd>
            </dl>
          </article>

        </div>
      }
    </div>
  `,
  styles: [`
    @use '../../../styles/tokens' as *;

    :host { display: block; }

    .page {
      max-width: 1200px;
      margin: 0 auto;
      padding: 0 $space-4 $space-8;
      animation: fade-in $transition-slow both;
    }

    @keyframes fade-in {
      from { opacity: 0; transform: translateY(8px); }
      to   { opacity: 1; transform: translateY(0); }
    }

    @media (prefers-reduced-motion: reduce) {
      .page { animation: none; }
    }

    /* ── Hero header ─────────────────────────────────────────────────── */
    .hero {
      position: relative;
      border-radius: $radius-xl;
      overflow: hidden;
      margin-bottom: $space-6;
      box-shadow: $shadow-lg;
    }

    .hero__bg {
      position: absolute;
      inset: 0;
      background: linear-gradient(135deg, $color-primary-dark 0%, $color-primary 55%, $color-primary-light 100%);
      z-index: 0;

      &::after {
        content: '';
        position: absolute;
        inset: 0;
        background: url("data:image/svg+xml,%3Csvg width='60' height='60' xmlns='http://www.w3.org/2000/svg'%3E%3Ccircle cx='30' cy='30' r='1.5' fill='rgba(255,255,255,0.08)'/%3E%3C/svg%3E") repeat;
      }
    }

    .hero__content {
      position: relative;
      z-index: 1;
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: $space-4;
      flex-wrap: wrap;
      padding: $space-6 $space-6 $space-4;
    }

    .hero__left {
      display: flex;
      align-items: center;
      gap: $space-4;
    }

    .hero__icon-wrap {
      width: 56px;
      height: 56px;
      border-radius: $radius-xl;
      background: rgba(255, 255, 255, 0.15);
      backdrop-filter: blur(4px);
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 1.5rem;
      color: $color-text-inverse;
      flex-shrink: 0;
    }

    .hero__title {
      margin: 0;
      font-size: $font-size-xl;
      font-weight: $font-weight-bold;
      color: $color-text-inverse;
      line-height: $line-height-tight;
    }

    .hero__meta {
      margin: $space-1 0 0;
      color: rgba(255, 255, 255, 0.8);
      font-size: $font-size-sm;
    }

    .hero__right {
      flex-shrink: 0;
    }

    .hero__badge {
      font-size: $font-size-base;
      padding: $space-2 $space-4;
      border: 2px solid rgba(255, 255, 255, 0.3);
    }

    .hero__actions {
      position: relative;
      z-index: 1;
      display: flex;
      gap: $space-2;
      flex-wrap: wrap;
      padding: $space-3 $space-6;
      background: rgba(0, 0, 0, 0.15);
      border-top: 1px solid rgba(255, 255, 255, 0.1);
    }

    /* ── Grid de detalle ─────────────────────────────────────────────── */
    .detail-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(340px, 1fr));
      gap: $space-4;
      align-items: start;
    }

    .detail-card {
      transition: box-shadow $transition-base;

      &:hover {
        box-shadow: $shadow-md;
      }

      &--wide {
        grid-column: 1 / -1;
      }

      &--audit {
        grid-column: -2 / -1;
        @media (max-width: $bp-md) {
          grid-column: 1 / -1;
        }
      }
    }

    /* ── Card icon ───────────────────────────────────────────────────── */
    .card-icon {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      width: 32px;
      height: 32px;
      border-radius: $radius-md;
      font-size: 0.875rem;
      flex-shrink: 0;

      &--primary  { background: $color-primary-bg;  color: $color-primary; }
      &--info     { background: $color-info-bg;     color: $color-info; }
      &--success  { background: $color-success-bg;  color: $color-success; }
      &--warning  { background: $color-warning-bg;  color: $color-warning; }
      &--danger   { background: $color-danger-bg;   color: $color-danger; }
      &--neutral  { background: $color-bg-muted;    color: $color-text-muted; }
      &--accent   { background: #E0F2FE;            color: #0369A1; }
      &--secondary { background: $color-secondary-bg; color: $color-secondary-dark; }
    }

    .ui-card__header {
      display: flex;
      align-items: center;
      gap: $space-2;
    }

    /* ── Key-value ───────────────────────────────────────────────────── */
    .kv {
      display: grid;
      grid-template-columns: max-content 1fr;
      gap: $space-2 $space-4;
      margin: 0;
      padding-top: $space-3;
    }

    .kv--compact {
      gap: $space-1 $space-3;
    }

    .kv dt {
      font-weight: $font-weight-semibold;
      color: $color-text-muted;
      font-size: $font-size-sm;
      white-space: nowrap;
    }

    .kv dd {
      margin: 0;
      word-break: break-word;
      font-size: $font-size-sm;
    }

    .text-wrap { white-space: pre-wrap; }

    /* ── Chips ───────────────────────────────────────────────────────── */
    .chips-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
      gap: $space-4;
      padding-top: $space-3;
    }

    .chips-section {
      margin-top: $space-3;
      padding-top: $space-3;
      border-top: 1px solid $color-border;
    }

    .chips-block {
      display: flex;
      flex-direction: column;
      gap: $space-2;
    }

    .chips-label {
      display: flex;
      align-items: center;
      gap: $space-1;
      font-size: $font-size-xs;
      font-weight: $font-weight-semibold;
      color: $color-text-muted;
      text-transform: uppercase;
      letter-spacing: 0.06em;
      margin: 0 0 $space-1;
    }

    .chips {
      display: flex;
      flex-wrap: wrap;
      gap: $space-1;
    }

    .chip-pill {
      border-radius: $radius-pill;
      font-size: $font-size-xs;
    }

    .chip-pill--teal {
      background: #CCFBF1;
      color: #0F766E;
      border: 1px solid #99F6E4;
    }

    .chip-pill--purple {
      background: #EDE9FE;
      color: #6D28D9;
      border: 1px solid #DDD6FE;
    }

    /* ── Documento pill ──────────────────────────────────────────────── */
    .doc-pill {
      display: inline-flex;
      align-items: center;
      gap: $space-1;
      background: $color-bg-subtle;
      border: 1px solid $color-border;
      border-radius: $radius-sm;
      padding: 2px $space-2;
      font-size: $font-size-xs;
    }

    .mono {
      font-family: $font-family-mono;
      font-size: 0.8em;
    }

    /* ── Estrato badge ───────────────────────────────────────────────── */
    .estrato-badge {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      width: 28px;
      height: 28px;
      border-radius: $radius-pill;
      background: $color-secondary-bg;
      color: $color-secondary-dark;
      font-weight: $font-weight-bold;
      font-size: $font-size-sm;
      border: 1px solid $color-secondary-light;
    }

    /* ── Mapa link ───────────────────────────────────────────────────── */
    .map-link {
      margin-top: $space-3;
      width: 100%;
      justify-content: center;
    }

    /* ── ALK beneficiada ─────────────────────────────────────────────── */
    .alk-beneficiada {
      padding: $space-3 0;
    }

    .alk-si, .alk-no, .alk-nd {
      display: inline-flex;
      align-items: center;
      gap: $space-2;
      font-weight: $font-weight-semibold;
      font-size: $font-size-sm;
    }

    .alk-si {
      color: $color-success;
      i { color: $color-success; }
    }

    .alk-no {
      color: $color-text-muted;
      i { color: $color-text-muted; }
    }

    .alk-nd { color: $color-text-muted; }

    /* ── Legal + firma ───────────────────────────────────────────────── */
    .legal-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
      gap: $space-6;
      padding-top: $space-3;
    }

    .legal-block {
      display: flex;
      flex-direction: column;
      gap: $space-3;
    }

    .firma-wrap {
      position: relative;
      display: inline-block;
    }

    .firma-img {
      display: block;
      max-width: 280px;
      max-height: 140px;
      border: 2px solid $color-border;
      border-radius: $radius-md;
      background: $color-bg-subtle;
      object-fit: contain;
      padding: $space-2;
    }

    .firma-badge {
      position: absolute;
      bottom: $space-1;
      right: $space-1;
      font-size: $font-size-xs;
      border-radius: $radius-pill;
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
      { label: `BI-${id}` },
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
    this.executeAction(d.id, 'validar', 'Inscripción validada correctamente.');
  }

  rechazar(): void {
    const d = this.data();
    if (!d) return;
    if (!confirm(`¿Rechazar la inscripción #${d.id}?`)) return;
    this.executeAction(d.id, 'rechazar', 'Inscripción rechazada.');
  }

  private executeAction(
    id: number,
    accion: 'validar' | 'rechazar',
    successMsg: string,
  ): void {
    this.actionLoading.set(true);
    this.actionResult.set('');
    this.api.updateEstado(id, { accion }).subscribe({
      next: () => {
        this.actionLoading.set(false);
        this.actionResult.set(successMsg);
        this.load(id);
      },
      error: (e) => {
        this.actionLoading.set(false);
        this.errorMsg.set(`Error ${e.status ?? '?'} al actualizar: ${e.message ?? 'desconocido'}`);
      },
    });
  }

  estadoLabel(e: InscripcionEstado): string {
    const map: Record<InscripcionEstado, string> = {
      borrador: 'Borrador', enviada: 'Enviada',
      validada: 'Validada', rechazada: 'Rechazada',
    };
    return map[e] ?? e;
  }

  badgeVariant(e: InscripcionEstado): string {
    return e === 'validada' ? 'success'
      : e === 'rechazada'  ? 'danger'
      : e === 'borrador'   ? 'neutral'
      : 'warning';
  }

  /** @deprecated usa badgeVariant — se mantiene para retrocompatibilidad del template */
  badgeClass(e: InscripcionEstado): string {
    return `ui-badge--${this.badgeVariant(e)}`;
  }

  estadoIconClass(e: InscripcionEstado): string {
    return e === 'validada'  ? 'fa-circle-check'
      : e === 'rechazada'    ? 'fa-circle-xmark'
      : e === 'enviada'      ? 'fa-paper-plane'
      : 'fa-pen-to-square';
  }

  encodeURI(s: string): string {
    return encodeURIComponent(s);
  }

  onFirmaError(event: Event): void {
    const img = event.target as HTMLImageElement;
    img.style.display = 'none';
    const wrap = img.closest('.firma-wrap');
    if (wrap) {
      const fallback = document.createElement('span');
      fallback.className = 'ui-badge ui-badge--neutral';
      fallback.textContent = 'Cifrada en MongoDB';
      wrap.appendChild(fallback);
    }
  }
}
