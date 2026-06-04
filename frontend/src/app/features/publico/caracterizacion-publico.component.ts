import { HttpClient } from '@angular/common/http';
import { Component, OnInit, inject, signal, computed } from '@angular/core';
import { ActivatedRoute } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { ConfigService } from '../../core/config/config.service';

// ─────────────────────────────────────────────────────────────────────────────
// Tipos del schema dinámico devuelto por GET /caracterizacion/api/publico/<id>/schema/
// ─────────────────────────────────────────────────────────────────────────────

interface SchemaOption {
  value: string;
  label: string;
}

interface SchemaField {
  name: string;
  label: string;
  type: 'text' | 'textarea' | 'email' | 'number' | 'date' | 'checkbox' | 'select' | 'multiselect' | 'file';
  required: boolean;
  help_text?: string;
  options?: SchemaOption[];
  multiple?: boolean;
  max_length?: number;
  widget_hint?: string;
}

interface CaracterizacionSchema {
  sector: string;
  sector_label: string;
  evento: { id: number; nombre: string };
  fields: SchemaField[];
}

interface ApiError {
  detail?: string;
  errors?: Record<string, string[]>;
}

// ─────────────────────────────────────────────────────────────────────────────
// Sección agrupada de campos
// ─────────────────────────────────────────────────────────────────────────────

interface Seccion {
  titulo: string;
  icono: string;
  campos: SchemaField[];
  abierta: boolean;
}

// Tamaño de grupos de campos por sección (se parte en bloques de ~5)
const SECCION_SIZE = 5;

function agruparEnSecciones(fields: SchemaField[], sector: string): Seccion[] {
  // Reglas específicas por sector para nombres de sección más descriptivos
  const titulosPorSector: Record<string, string[]> = {
    cultura:               ['Identificación', 'Datos culturales', 'Propuesta'],
    deporte:               ['Identificación', 'Práctica deportiva', 'Propuesta'],
    mujer:                 ['Identificación', 'Información del hogar', 'Caracterización'],
    salud:                 ['Identificación', 'Condición de salud', 'Firma y consentimiento'],
    poblacional:           ['Identificación', 'Datos socioeconómicos', 'Características'],
    participacion_ciudadana: ['Identificación', 'Participación', 'Propuesta'],
  };
  const iconosPorSector: Record<string, string[]> = {
    cultura:               ['fa fa-user', 'fa fa-music', 'fa fa-lightbulb'],
    deporte:               ['fa fa-user', 'fa fa-futbol-o', 'fa fa-flag'],
    mujer:                 ['fa fa-user', 'fa fa-home', 'fa fa-heart'],
    salud:                 ['fa fa-user', 'fa fa-medkit', 'fa fa-pencil-square-o'],
    poblacional:           ['fa fa-user', 'fa fa-bar-chart', 'fa fa-users'],
    participacion_ciudadana: ['fa fa-user', 'fa fa-group', 'fa fa-bullhorn'],
  };

  const titulos = titulosPorSector[sector] ?? ['Datos', 'Información adicional', 'Cierre'];
  const iconos  = iconosPorSector[sector]  ?? ['fa fa-user', 'fa fa-list', 'fa fa-check'];

  // Distribuir campos en hasta 3 secciones equitativamente
  const total = fields.length;
  const perSeccion = Math.ceil(total / 3);

  const secciones: Seccion[] = [];
  for (let i = 0; i < 3; i++) {
    const slice = fields.slice(i * perSeccion, (i + 1) * perSeccion);
    if (slice.length === 0) continue;
    secciones.push({
      titulo: titulos[i] ?? `Sección ${i + 1}`,
      icono:  iconos[i]  ?? 'fa fa-list',
      campos: slice,
      abierta: i === 0, // primera sección abierta por defecto
    });
  }
  return secciones;
}

// ─────────────────────────────────────────────────────────────────────────────
// Mapa sector → icono del banner
// ─────────────────────────────────────────────────────────────────────────────

const SECTOR_ICONOS: Record<string, string> = {
  cultura:                 'fa fa-music',
  deporte:                 'fa fa-futbol-o',
  mujer:                   'fa fa-heart',
  salud:                   'fa fa-medkit',
  poblacional:             'fa fa-users',
  participacion_ciudadana: 'fa fa-group',
};

// ─────────────────────────────────────────────────────────────────────────────
// Componente
// ─────────────────────────────────────────────────────────────────────────────

@Component({
  standalone: true,
  selector: 'app-caracterizacion-publico',
  imports: [FormsModule],
  template: `
    <!-- ══ ESTADO: CARGANDO ══ -->
    @if (cargando()) {
      <div class="loading-wrap" role="status" aria-live="polite">
        <div class="loading-spinner" aria-hidden="true"></div>
        <p>Cargando formulario…</p>
      </div>
    }

    <!-- ══ ESTADO: CERRADO (410) ══ -->
    @if (!cargando() && cerrado()) {
      <div class="estado-wrap">
        <div class="estado-card estado-card--cerrado">
          <div class="estado-icon" aria-hidden="true">
            <i class="fa fa-lock fa-3x"></i>
          </div>
          <h1 class="estado-title">Convocatoria cerrada</h1>
          <p class="estado-msg">{{ cerradoMsg() }}</p>
          <p class="estado-sub">Esta caracterización ya no acepta nuevos registros. Contacta a la Alcaldía Local de Kennedy para más información.</p>
        </div>
      </div>
    }

    <!-- ══ ESTADO: NO ENCONTRADO (404) ══ -->
    @if (!cargando() && noEncontrado()) {
      <div class="estado-wrap">
        <div class="estado-card estado-card--error">
          <div class="estado-icon" aria-hidden="true">
            <i class="fa fa-search fa-3x"></i>
          </div>
          <h1 class="estado-title">Evento no encontrado</h1>
          <p class="estado-msg">No se encontró el evento de caracterización indicado.</p>
          <p class="estado-sub">Verifica que el enlace QR sea correcto o solicita uno nuevo al organizador.</p>
        </div>
      </div>
    }

    <!-- ══ ESTADO: ERROR GENÉRICO ══ -->
    @if (!cargando() && !cerrado() && !noEncontrado() && errorCarga()) {
      <div class="estado-wrap">
        <div class="estado-card estado-card--error">
          <div class="estado-icon" aria-hidden="true">
            <i class="fa fa-exclamation-triangle fa-3x"></i>
          </div>
          <h1 class="estado-title">Error al cargar</h1>
          <p class="estado-msg">{{ errorCarga() }}</p>
          <button class="btn-brand btn-lg" (click)="cargarSchema()">
            <i class="fa fa-refresh"></i> Reintentar
          </button>
        </div>
      </div>
    }

    <!-- ══ PANTALLA DE ÉXITO ══ -->
    @if (exito()) {
      <div class="estado-wrap">
        <div class="estado-card estado-card--exito">
          <div class="estado-icon exito-check" aria-hidden="true">
            <svg viewBox="0 0 80 80" fill="none" xmlns="http://www.w3.org/2000/svg">
              <circle cx="40" cy="40" r="40" fill="#DCFCE7"/>
              <path d="M24 40l12 12 20-24" stroke="#16A34A" stroke-width="4"
                    stroke-linecap="round" stroke-linejoin="round"/>
            </svg>
          </div>
          <h1 class="estado-title estado-title--success">¡Caracterización registrada!</h1>
          <p class="estado-msg">Tu información fue guardada exitosamente en el sistema de la Alcaldía Local de Kennedy.</p>
          @if (exitoId()) {
            <div class="exito-num">
              <span class="exito-num__label">Número de registro</span>
              <span class="exito-num__val"># {{ exitoId() }}</span>
            </div>
          }
          <p class="estado-sub">Guarda este número. Podrás referenciarlo ante la Alcaldía si necesitas verificar tu participación.</p>
          <div class="exito-branding">
            <i class="fa fa-institution" aria-hidden="true"></i>
            Alcaldía Local de Kennedy · Bogotá
          </div>
        </div>
      </div>
    }

    <!-- ══ FORMULARIO DINÁMICO ══ -->
    @if (!cargando() && !cerrado() && !noEncontrado() && !errorCarga() && !exito() && schema()) {
      <!-- Header sticky con gradiente institucional -->
      <header class="wiz-header" role="banner">
        <div class="wiz-banner">
          <div class="wiz-banner__icon-wrap" aria-hidden="true">
            <i [class]="sectorIcono()" aria-hidden="true"></i>
          </div>
          <div class="wiz-banner__content">
            <div class="wiz-banner__eyebrow">Caracterización ciudadana</div>
            <h1 class="wiz-banner__title">{{ schema()!.sector_label }}</h1>
            <p class="wiz-banner__sub">{{ schema()!.evento.nombre }}</p>
          </div>
        </div>

        <!-- Progreso -->
        <div class="wiz-progress" aria-label="Progreso del formulario">
          <div class="wiz-progress__meta">
            <span class="wiz-progress__texto">
              Sección <strong>{{ seccionActualIdx() + 1 }}</strong> de <strong>{{ secciones().length }}</strong>
            </span>
            <span class="wiz-progress__label">{{ seccionActual()?.titulo ?? '' }}</span>
            <span class="wiz-progress__pct">{{ progresoPct() }}%</span>
          </div>
          <div class="wiz-progress__bar-bg"
               role="progressbar"
               [attr.aria-valuenow]="progresoPct()"
               aria-valuemin="0"
               aria-valuemax="100">
            <div class="wiz-progress__bar-fill" [style.width.%]="progresoPct()"></div>
          </div>
        </div>

        <!-- Tabs de sección (desktop) -->
        <nav class="wiz-tabs" aria-label="Secciones del formulario">
          @for (sec of secciones(); track sec.titulo; let i = $index) {
            <button type="button"
                    class="wiz-tab"
                    [class.wiz-tab--active]="seccionActualIdx() === i"
                    [class.wiz-tab--done]="seccionActualIdx() > i"
                    [disabled]="seccionActualIdx() < i"
                    (click)="irASeccion(i)"
                    [attr.aria-current]="seccionActualIdx() === i ? 'step' : null">
              <span class="wiz-tab__num">
                @if (seccionActualIdx() > i) {
                  <i class="fa fa-check" aria-hidden="true"></i>
                } @else {
                  {{ i + 1 }}
                }
              </span>
              <span class="wiz-tab__lbl">{{ sec.titulo }}</span>
            </button>
          }
        </nav>
      </header>

      <!-- Errores del servidor -->
      @if (erroresServidor().length > 0) {
        <div class="wiz-server-errors" role="alert">
          <i class="fa fa-exclamation-circle" aria-hidden="true"></i>
          <strong> Por favor corrige los siguientes errores:</strong>
          <ul>
            @for (err of erroresServidor(); track err) {
              <li>{{ err }}</li>
            }
          </ul>
        </div>
      }

      <!-- Contenido principal -->
      <main class="wiz-main">
        @if (seccionActual(); as sec) {
          <section class="wiz-seccion" [attr.aria-labelledby]="'sec-title-' + seccionActualIdx()">

            <!-- Título de sección con icono -->
            <div class="sec-header">
              <div class="sec-header__icon" aria-hidden="true">
                <i [class]="sec.icono"></i>
              </div>
              <div>
                <h2 [id]="'sec-title-' + seccionActualIdx()" class="sec-header__title">
                  {{ sec.titulo }}
                </h2>
                <p class="sec-header__hint">Completa todos los campos marcados con <span class="req-mark">*</span></p>
              </div>
            </div>

            <!-- Campos de esta sección -->
            <div class="fields-grid">
              @for (field of sec.campos; track field.name) {
                <div class="field"
                     [class.field--full]="field.type === 'textarea' || field.type === 'multiselect' || field.widget_hint === 'RadioSelect'"
                     [class.field--required]="field.required">

                  <!-- Label (excepto checkbox) -->
                  @if (field.type !== 'checkbox') {
                    <label [for]="field.name" class="field__label">
                      {{ field.label }}
                      @if (field.required) { <span class="req-mark" aria-hidden="true">*</span> }
                      @if (!field.required) { <span class="field__opt">(opcional)</span> }
                    </label>
                  }

                  <!-- Render por type -->
                  @switch (field.type) {

                    @case ('text') {
                      <input [id]="field.name"
                             type="text"
                             class="field__input"
                             [name]="field.name"
                             [(ngModel)]="valores[field.name]"
                             [required]="field.required"
                             [maxlength]="field.max_length ?? 200"
                             [placeholder]="field.help_text ?? ''">
                    }

                    @case ('email') {
                      <input [id]="field.name"
                             type="email"
                             class="field__input"
                             [name]="field.name"
                             [(ngModel)]="valores[field.name]"
                             [required]="field.required"
                             placeholder="correo@ejemplo.com">
                    }

                    @case ('number') {
                      <input [id]="field.name"
                             type="number"
                             class="field__input"
                             [name]="field.name"
                             [(ngModel)]="valores[field.name]"
                             [required]="field.required"
                             inputmode="numeric"
                             [placeholder]="field.help_text ?? '0'">
                    }

                    @case ('date') {
                      <input [id]="field.name"
                             type="date"
                             class="field__input"
                             [name]="field.name"
                             [(ngModel)]="valores[field.name]"
                             [required]="field.required">
                    }

                    @case ('textarea') {
                      <textarea [id]="field.name"
                                class="field__textarea"
                                [name]="field.name"
                                [(ngModel)]="valores[field.name]"
                                [required]="field.required"
                                rows="3"
                                [placeholder]="field.help_text ?? ''"></textarea>
                    }

                    @case ('checkbox') {
                      <label class="checkbox-label checkbox-label--lg" [for]="field.name">
                        <input [id]="field.name"
                               type="checkbox"
                               class="checkbox-input"
                               [name]="field.name"
                               [(ngModel)]="valores[field.name]">
                        <span class="checkbox-text">
                          {{ field.label }}
                          @if (field.required) { <span class="req-mark" aria-hidden="true">*</span> }
                        </span>
                      </label>
                    }

                    @case ('select') {
                      @if (field.widget_hint === 'RadioSelect') {
                        <!-- Radios tipo chips para campos Sí/No -->
                        <div class="radio-chips" role="radiogroup" [attr.aria-labelledby]="field.name + '-lbl'">
                          @for (opt of field.options ?? []; track opt.value) {
                            <label class="radio-chip"
                                   [class.radio-chip--active]="valores[field.name] === opt.value">
                              <input type="radio"
                                     [name]="field.name"
                                     [value]="opt.value"
                                     [(ngModel)]="valores[field.name]"
                                     class="radio-hidden"
                                     [required]="field.required">
                              {{ opt.label }}
                            </label>
                          }
                        </div>
                      } @else {
                        <select [id]="field.name"
                                class="field__select"
                                [name]="field.name"
                                [(ngModel)]="valores[field.name]"
                                [required]="field.required">
                          <option value="">— Seleccionar —</option>
                          @for (opt of field.options ?? []; track opt.value) {
                            <option [value]="opt.value">{{ opt.label }}</option>
                          }
                        </select>
                      }
                    }

                    @case ('multiselect') {
                      <div class="chips-grid" role="group" [attr.aria-labelledby]="field.name + '-lbl'">
                        @for (opt of (field.options ?? []); track opt.value) {
                          <button type="button"
                                  class="chip"
                                  [class.chip--active]="hasMulti(field.name, opt.value)"
                                  (click)="toggleMulti(field.name, opt.value)"
                                  [attr.aria-pressed]="hasMulti(field.name, opt.value) ? 'true' : 'false'">
                            @if (multiValores[field.name]?.has(opt.value)) {
                              <i class="fa fa-check-circle" aria-hidden="true"></i>
                            }
                            {{ opt.label }}
                          </button>
                        }
                      </div>
                      @if (field.help_text) {
                        <p class="field__hint">{{ field.help_text }}</p>
                      }
                    }

                    @case ('file') {
                      <!-- Botón cámara estilo banco-publico -->
                      @if (!firmaPreview()) {
                        <label [for]="field.name"
                               class="firma-btn"
                               [class.firma-btn--error]="firmaError()">
                          <i class="fa fa-camera firma-btn__icon" aria-hidden="true"></i>
                          <span class="firma-btn__text">Tomar foto de la firma</span>
                          <span class="firma-btn__sub">Se abrirá la cámara de tu celular</span>
                        </label>
                      } @else {
                        <div class="firma-preview">
                          <img [src]="firmaPreview()!" alt="Vista previa de la firma" class="firma-preview__img">
                          <div class="firma-preview__meta">
                            <span class="firma-preview__name">{{ firmaNombre() }}</span>
                            <button type="button" class="btn-outline-brand btn-sm"
                                    (click)="quitarFirma(field.name)">
                              <i class="fa fa-times" aria-hidden="true"></i> Quitar
                            </button>
                          </div>
                        </div>
                        <label [for]="field.name" class="firma-cambiar">
                          <i class="fa fa-camera" aria-hidden="true"></i> Cambiar foto
                        </label>
                      }
                      <input [id]="field.name"
                             type="file"
                             accept="image/*"
                             capture="environment"
                             class="firma-input-hidden"
                             (change)="onFileChange($event, field.name)"
                             [attr.aria-label]="'Seleccionar imagen para ' + field.label">
                      @if (firmaError()) {
                        <p class="field__error" role="alert">{{ firmaError() }}</p>
                      }
                      @if (field.help_text) {
                        <p class="field__hint">{{ field.help_text }}</p>
                      }
                    }

                  }

                  <!-- Help text (no para file, ya lo tiene) -->
                  @if (field.type !== 'file' && field.type !== 'checkbox' && field.type !== 'multiselect' && field.help_text) {
                    <p class="field__hint">{{ field.help_text }}</p>
                  }

                  <!-- Errores por campo -->
                  @if (fieldError(field.name)) {
                    <p class="field__error" role="alert">
                      <i class="fa fa-exclamation-circle" aria-hidden="true"></i>
                      {{ fieldError(field.name) }}
                    </p>
                  }

                  <!-- Error de required cliente -->
                  @if (erroresCliente[field.name]) {
                    <p class="field__error" role="alert">
                      <i class="fa fa-exclamation-circle" aria-hidden="true"></i>
                      {{ erroresCliente[field.name] }}
                    </p>
                  }

                </div>
              }
            </div>

          </section>
        }

        <!-- Botonera sticky -->
        <div class="wiz-actions">
          <button type="button"
                  class="btn-outline-brand btn-wiz-prev"
                  (click)="irAnterior()"
                  [disabled]="seccionActualIdx() === 0"
                  [class.btn--hidden]="seccionActualIdx() === 0">
            <i class="fa fa-chevron-left" aria-hidden="true"></i> Anterior
          </button>

          @if (seccionActualIdx() < secciones().length - 1) {
            <button type="button"
                    class="btn-brand btn-wiz-next"
                    (click)="irSiguiente()">
              Siguiente <i class="fa fa-chevron-right" aria-hidden="true"></i>
            </button>
          }

          @if (seccionActualIdx() === secciones().length - 1) {
            <button type="button"
                    class="btn-brand btn-wiz-submit"
                    (click)="enviar()"
                    [disabled]="enviando()">
              @if (enviando()) {
                <span class="spinner-inline" aria-hidden="true"></span>
                Enviando…
              } @else {
                <i class="fa fa-paper-plane" aria-hidden="true"></i>
                Enviar caracterización
              }
            </button>
          }
        </div>
      </main>
    }
  `,
  styles: [`
    @use '../../../styles/tokens' as *;

    // ── Variables locales ─────────────────────────────────────────────
    $brand-dark: #8B0010;
    $grad-primary: linear-gradient(135deg, #{$brand-dark} 0%, #D6001C 60%, #E8001F 100%);
    $grad-banner: linear-gradient(135deg, #6B0010 0%, #B50015 50%, #D6001C 100%);
    $sec-border: rgba(#D6001C, 0.15);

    // ── Host ──────────────────────────────────────────────────────────
    :host {
      display: block;
      background: $color-bg-subtle;
      min-height: 100vh;
      font-family: $font-family-base;
    }

    // ── Estados de pantalla completa ──────────────────────────────────
    .loading-wrap {
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      min-height: 100vh;
      gap: $space-4;
      color: $color-text-muted;
    }

    .loading-spinner {
      width: 44px;
      height: 44px;
      border: 4px solid $color-border;
      border-top-color: $color-primary;
      border-radius: 50%;
      animation: spin 0.8s linear infinite;

      @media (prefers-reduced-motion: reduce) { animation: none; }
    }

    .estado-wrap {
      display: flex;
      align-items: center;
      justify-content: center;
      min-height: 100vh;
      padding: $space-6;
    }

    .estado-card {
      background: $color-bg;
      border-radius: $radius-2xl;
      padding: $space-10 $space-8;
      text-align: center;
      max-width: 480px;
      width: 100%;
      box-shadow: $shadow-lg;

      &--cerrado { border-top: 5px solid $color-primary; }
      &--error   { border-top: 5px solid $color-danger; }
      &--exito   { border-top: 5px solid $color-success; }
    }

    .estado-icon {
      margin-bottom: $space-5;
      color: $color-primary;

      .estado-card--error &  { color: $color-danger; }
      .estado-card--exito &  { color: $color-success; }
    }

    .exito-check {
      width: 80px;
      height: 80px;
      margin: 0 auto $space-5;
      svg { width: 100%; height: 100%; }
    }

    .estado-title {
      font-size: $font-size-2xl;
      font-weight: $font-weight-bold;
      color: $color-primary;
      margin: 0 0 $space-3;

      &--success { color: $color-success; }
    }

    .estado-msg {
      font-size: $font-size-md;
      color: $color-text;
      margin-bottom: $space-3;
    }

    .estado-sub {
      color: $color-text-muted;
      font-size: $font-size-sm;
      line-height: $line-height-relaxed;
      margin: 0;
    }

    .exito-num {
      display: inline-flex;
      flex-direction: column;
      gap: $space-1;
      background: $color-bg-muted;
      border: 1px solid $color-border;
      border-radius: $radius-xl;
      padding: $space-4 $space-8;
      margin: $space-4 0 $space-4;
    }

    .exito-num__label { font-size: $font-size-xs; text-transform: uppercase; letter-spacing: 0.07em; color: $color-text-muted; font-weight: $font-weight-semibold; }
    .exito-num__val   { font-size: $font-size-2xl; font-weight: $font-weight-bold; color: $color-primary; }

    .exito-branding {
      display: flex;
      align-items: center;
      justify-content: center;
      gap: $space-2;
      margin-top: $space-6;
      font-size: $font-size-xs;
      color: $color-text-muted;
      font-weight: $font-weight-semibold;
      text-transform: uppercase;
      letter-spacing: 0.05em;

      i { color: $color-primary; }
    }

    // ── Header sticky ─────────────────────────────────────────────────
    .wiz-header {
      position: sticky;
      top: 0;
      z-index: $z-sticky;
      background: $color-bg;
      box-shadow: $shadow-md;
    }

    .wiz-banner {
      display: flex;
      align-items: center;
      gap: $space-4;
      background: $grad-banner;
      color: $color-text-inverse;
      padding: $space-4 $space-5;
    }

    .wiz-banner__icon-wrap {
      display: flex;
      align-items: center;
      justify-content: center;
      width: 48px;
      height: 48px;
      flex-shrink: 0;
      background: rgba(255,255,255,0.15);
      border-radius: $radius-xl;
      font-size: 1.4rem;
      backdrop-filter: blur(4px);
    }

    .wiz-banner__eyebrow {
      font-size: $font-size-xs;
      opacity: 0.8;
      text-transform: uppercase;
      letter-spacing: 0.08em;
      margin-bottom: $space-1;
    }

    .wiz-banner__title {
      font-size: $font-size-md;
      font-weight: $font-weight-bold;
      margin: 0;
      line-height: $line-height-tight;

      @media (min-width: #{$bp-md}) { font-size: $font-size-lg; }
    }

    .wiz-banner__sub {
      margin: $space-1 0 0;
      font-size: $font-size-xs;
      opacity: 0.85;
    }

    // Barra de progreso
    .wiz-progress {
      padding: $space-3 $space-5;
      background: $color-bg;
    }

    .wiz-progress__meta {
      display: flex;
      justify-content: space-between;
      align-items: center;
      font-size: $font-size-xs;
      color: $color-text-muted;
      margin-bottom: $space-2;

      strong { color: $color-text; }
    }

    .wiz-progress__label {
      font-weight: $font-weight-semibold;
      color: $color-primary;
      display: none;

      @media (min-width: #{$bp-sm}) { display: block; }
    }

    .wiz-progress__pct { font-weight: $font-weight-semibold; color: $color-text; }

    .wiz-progress__bar-bg {
      background: $color-border;
      height: 6px;
      border-radius: $radius-pill;
      overflow: hidden;
    }

    .wiz-progress__bar-fill {
      background: $grad-primary;
      height: 100%;
      border-radius: $radius-pill;
      transition: width $transition-slow;

      @media (prefers-reduced-motion: reduce) { transition: none; }
    }

    // Tabs de sección (desktop)
    .wiz-tabs {
      display: none;
      gap: $space-1;
      padding: $space-2 $space-5;
      flex-wrap: wrap;

      @media (min-width: #{$bp-md}) { display: flex; }
    }

    .wiz-tab {
      display: inline-flex;
      align-items: center;
      gap: $space-2;
      padding: $space-2 $space-4;
      border-radius: $radius-pill;
      font-size: $font-size-xs;
      font-weight: $font-weight-semibold;
      background: $color-bg-muted;
      color: $color-text-muted;
      border: 1px solid transparent;
      cursor: default;
      transition: background $transition-base, color $transition-base;

      &[disabled] { opacity: 0.55; }
      &:not([disabled]) { cursor: pointer; }

      &--active {
        background: rgba(#D6001C, 0.08);
        color: $color-primary;
        border-color: rgba(#D6001C, 0.25);
      }

      &--done {
        background: $color-success-bg;
        color: $color-success;
        cursor: pointer;
      }
    }

    .wiz-tab__num {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      width: 20px;
      height: 20px;
      border-radius: 50%;
      font-size: 0.65rem;
      background: rgba(0,0,0,0.08);

      .wiz-tab--active & { background: $color-primary; color: $color-text-inverse; }
      .wiz-tab--done  & { background: $color-success; color: $color-text-inverse; }
    }

    // ── Errores del servidor ──────────────────────────────────────────
    .wiz-server-errors {
      background: $color-danger-bg;
      border-left: 4px solid $color-danger;
      border-radius: $radius-md;
      padding: $space-4 $space-5;
      margin: $space-4 $space-4 0;
      color: $color-danger;
      font-size: $font-size-sm;

      ul { margin: $space-2 0 0; padding-left: $space-5; }
    }

    // ── Main ──────────────────────────────────────────────────────────
    .wiz-main {
      max-width: 100%;
      margin: 0 auto;
      padding: $space-4;

      @media (min-width: #{$bp-md}) {
        max-width: 760px;
        padding: $space-6 $space-4;
      }

      @media (min-width: #{$bp-xl}) { max-width: 900px; }
    }

    // ── Sección ───────────────────────────────────────────────────────
    .wiz-seccion {
      background: $color-bg;
      border-radius: $radius-xl;
      padding: $space-5 $space-4;
      box-shadow: $shadow-sm;
      border: 1px solid $sec-border;
      margin-bottom: 5.5rem;

      @media (min-width: #{$bp-md}) { padding: $space-8 $space-10; }

      @media (prefers-reduced-motion: no-preference) {
        animation: sec-in 0.22s ease-out both;
      }
    }

    @keyframes sec-in {
      from { opacity: 0; transform: translateY(8px); }
      to   { opacity: 1; transform: translateY(0); }
    }

    @keyframes spin {
      to { transform: rotate(360deg); }
    }

    // Encabezado de sección
    .sec-header {
      display: flex;
      align-items: flex-start;
      gap: $space-4;
      margin-bottom: $space-6;
      padding-bottom: $space-4;
      border-bottom: 2px solid $sec-border;
    }

    .sec-header__icon {
      display: flex;
      align-items: center;
      justify-content: center;
      width: 44px;
      height: 44px;
      flex-shrink: 0;
      background: $grad-primary;
      color: $color-text-inverse;
      border-radius: $radius-xl;
      font-size: 1.2rem;
      box-shadow: 0 4px 12px rgba(#D6001C, 0.3);
    }

    .sec-header__title {
      font-size: $font-size-lg;
      font-weight: $font-weight-bold;
      color: $color-primary;
      margin: 0 0 $space-1;
    }

    .sec-header__hint {
      font-size: $font-size-sm;
      color: $color-text-muted;
      margin: 0;
    }

    .req-mark {
      color: $color-primary;
      font-weight: $font-weight-bold;
      margin-left: 2px;
    }

    // Grid de campos
    .fields-grid {
      display: grid;
      grid-template-columns: 1fr;
      gap: $space-4;

      @media (min-width: #{$bp-sm}) {
        grid-template-columns: 1fr 1fr;
      }
    }

    // Campos de ancho completo
    .field--full {
      @media (min-width: #{$bp-sm}) {
        grid-column: 1 / -1;
      }
    }

    // ── Campo individual ──────────────────────────────────────────────
    .field__label {
      display: block;
      font-size: $font-size-sm;
      font-weight: $font-weight-semibold;
      color: $color-text;
      margin-bottom: $space-2;
      line-height: $line-height-tight;
    }

    .field__opt {
      font-size: $font-size-xs;
      font-weight: $font-weight-regular;
      color: $color-text-muted;
      margin-left: $space-2;
    }

    .field__input,
    .field__select,
    .field__textarea {
      display: block;
      width: 100%;
      min-height: $touch-target-min;
      padding: $space-3 $space-4;
      font-size: $font-size-base;
      font-family: $font-family-base;
      color: $color-text;
      background: $color-bg;
      border: 1.5px solid $color-border-strong;
      border-radius: $radius-lg;
      transition: border-color $transition-base, box-shadow $transition-base;
      box-sizing: border-box;

      &:focus {
        outline: none;
        border-color: $color-primary;
        box-shadow: 0 0 0 $focus-ring-width rgba(#D6001C, 0.2);
      }

      &:focus-visible {
        outline: $focus-ring;
        outline-offset: $focus-ring-offset;
      }
    }

    .field__textarea {
      min-height: 90px;
      resize: vertical;
    }

    .field__error {
      color: $color-danger;
      font-size: $font-size-xs;
      margin: $space-1 0 0;
      font-weight: $font-weight-medium;
      display: flex;
      align-items: center;
      gap: $space-1;
    }

    .field__hint {
      color: $color-text-muted;
      font-size: $font-size-xs;
      margin: $space-1 0 0;
      line-height: $line-height-relaxed;
    }

    .radio-chips {
      display: flex;
      flex-wrap: wrap;
      gap: $space-2;
    }

    .radio-chip {
      display: inline-flex;
      align-items: center;
      gap: $space-2;
      padding: $space-2 $space-5;
      min-height: $touch-target-min;
      background: $color-bg-muted;
      color: $color-text-muted;
      border: 1.5px solid $color-border;
      border-radius: $radius-pill;
      cursor: pointer;
      font-size: $font-size-sm;
      font-weight: $font-weight-semibold;
      transition: all $transition-base;
      user-select: none;

      &:hover {
        border-color: $color-primary;
        color: $color-primary;
        background: rgba(#D6001C, 0.05);
      }

      &--active {
        background: $color-primary;
        color: $color-text-inverse;
        border-color: $brand-dark;
        box-shadow: 0 2px 8px rgba(#D6001C, 0.35);

        &:hover { background: $brand-dark; }
      }
    }

    .radio-hidden { position: absolute; opacity: 0; width: 0; height: 0; pointer-events: none; }

    .chips-grid {
      display: flex;
      flex-wrap: wrap;
      gap: $space-2;
    }

    .chip {
      display: inline-flex;
      align-items: center;
      gap: $space-2;
      padding: $space-2 $space-4;
      font-size: $font-size-sm;
      font-family: $font-family-base;
      background: $color-bg-muted;
      color: $color-text-muted;
      border: 1.5px solid $color-border;
      border-radius: $radius-pill;
      cursor: pointer;
      transition: all $transition-base;
      min-height: $touch-target-min;
      user-select: none;

      &:hover {
        border-color: $color-primary;
        color: $color-primary;
        background: rgba(#D6001C, 0.05);
      }

      &:focus-visible {
        outline: $focus-ring;
        outline-offset: $focus-ring-offset;
      }

      &--active {
        background: $color-primary;
        color: $color-text-inverse;
        border-color: $brand-dark;
        box-shadow: 0 2px 8px rgba(#D6001C, 0.3);

        &:hover { background: $brand-dark; }

        i { color: $color-text-inverse; }
      }
    }

    .checkbox-label {
      display: flex;
      align-items: flex-start;
      gap: $space-3;
      cursor: pointer;

      &--lg {
        padding: $space-4;
        border: 1.5px solid $color-border;
        border-radius: $radius-lg;
        background: $color-bg-subtle;
        transition: border-color $transition-base, background $transition-base;

        &:has(.checkbox-input:checked) {
          border-color: $color-success;
          background: $color-success-bg;
        }
      }
    }

    .checkbox-input {
      width: 20px;
      height: 20px;
      min-width: 20px;
      accent-color: $color-primary;
      cursor: pointer;
      margin-top: 2px;

      &:focus-visible {
        outline: $focus-ring;
        outline-offset: $focus-ring-offset;
      }
    }

    .checkbox-text {
      font-size: $font-size-sm;
      line-height: $line-height-normal;
      color: $color-text;
    }

    .firma-input-hidden { position: absolute; left: -9999px; width: 1px; height: 1px; opacity: 0; }

    .firma-btn {
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      gap: $space-2;
      width: 100%;
      min-height: 90px;
      padding: $space-5;
      background: $grad-primary;
      color: $color-text-inverse;
      border: 2px dashed rgba(255,255,255,0.35);
      border-radius: $radius-xl;
      cursor: pointer;
      text-align: center;
      transition: filter $transition-base, transform $transition-base;

      &:hover {
        filter: brightness(0.9);
        transform: translateY(-1px);
      }

      &:focus-within {
        outline: $focus-ring;
        outline-offset: $focus-ring-offset;
      }

      &--error { border-color: rgba(#fff,0.7); outline: 2px solid $color-danger; }
    }

    .firma-btn__icon { font-size: 2rem; opacity: 0.95; }
    .firma-btn__text { font-size: $font-size-base; font-weight: $font-weight-bold; }
    .firma-btn__sub  { font-size: $font-size-xs; opacity: 0.8; }

    .firma-preview {
      border: 1.5px solid $color-border;
      border-radius: $radius-lg;
      overflow: hidden;
      background: $color-bg-subtle;
    }

    .firma-preview__img {
      display: block;
      max-width: 100%;
      max-height: 220px;
      margin: 0 auto;
      background: $color-bg;
    }

    .firma-preview__meta {
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: $space-3;
      padding: $space-2 $space-3;
      background: $color-bg-muted;
    }

    .firma-preview__name {
      font-size: $font-size-xs;
      color: $color-text-muted;
      word-break: break-all;
    }

    .firma-cambiar {
      display: inline-flex;
      align-items: center;
      gap: $space-2;
      margin-top: $space-3;
      padding: $space-2 $space-4;
      font-size: $font-size-sm;
      background: $color-bg-muted;
      border: 1.5px solid $color-border;
      border-radius: $radius-lg;
      cursor: pointer;
      transition: background $transition-base;

      &:hover { background: $color-border; }
    }

    .wiz-actions {
      position: sticky;
      bottom: 0;
      display: flex;
      gap: $space-3;
      justify-content: space-between;
      align-items: center;
      background: $color-bg;
      border-top: 1px solid $color-border;
      padding: $space-4 $space-5;
      border-radius: $radius-xl $radius-xl 0 0;
      box-shadow: 0 -4px 16px rgba(0,0,0,0.1);
    }

    .btn--hidden { visibility: hidden; }

    .btn-brand {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      gap: $space-2;
      min-height: $touch-target-min;
      padding: $space-3 $space-6;
      background: $grad-primary;
      color: $color-text-inverse;
      border: none;
      border-radius: $radius-lg;
      font-size: $font-size-base;
      font-family: $font-family-base;
      font-weight: $font-weight-semibold;
      cursor: pointer;
      transition: filter $transition-base, transform $transition-base;
      text-decoration: none;
      box-shadow: 0 2px 8px rgba(#D6001C, 0.3);

      &:hover { filter: brightness(0.9); transform: translateY(-1px); }

      &:focus-visible {
        outline: $focus-ring;
        outline-offset: $focus-ring-offset;
      }

      &[disabled] { opacity: 0.65; cursor: not-allowed; transform: none; }

      &-lg { font-size: $font-size-md; padding: $space-4 $space-8; }
    }

    .btn-wiz-prev {
      min-width: 120px;
      min-height: $touch-target-min;
    }

    .btn-wiz-next,
    .btn-wiz-submit { flex: 1; }

    .btn-outline-brand {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      gap: $space-2;
      min-height: $touch-target-min;
      padding: $space-3 $space-5;
      background: $color-bg;
      color: $color-primary;
      border: 1.5px solid $color-primary;
      border-radius: $radius-lg;
      font-size: $font-size-base;
      font-family: $font-family-base;
      font-weight: $font-weight-semibold;
      cursor: pointer;
      transition: background $transition-base;
      text-decoration: none;

      &:hover { background: rgba(#D6001C, 0.05); }

      &:focus-visible {
        outline: $focus-ring;
        outline-offset: $focus-ring-offset;
      }

      &[disabled] { opacity: 0.65; cursor: not-allowed; }
    }

    .btn-sm {
      min-height: 36px;
      padding: $space-1 $space-3;
      font-size: $font-size-sm;
    }

    .spinner-inline {
      display: inline-block;
      width: 16px;
      height: 16px;
      border: 2px solid rgba(255,255,255,0.4);
      border-top-color: $color-text-inverse;
      border-radius: 50%;
      animation: spin 0.7s linear infinite;

      @media (prefers-reduced-motion: reduce) { animation: none; }
    }
  `],
})
export class CaracterizacionPublicoComponent implements OnInit {
  private route = inject(ActivatedRoute);
  private http = inject(HttpClient);
  private cfg = inject(ConfigService);

  // ── Señales de estado ─────────────────────────────────────────────
  cargando      = signal(true);
  errorCarga    = signal('');
  cerrado       = signal(false);
  cerradoMsg    = signal('');
  noEncontrado  = signal(false);
  exito         = signal(false);
  exitoId       = signal<number | null>(null);
  enviando      = signal(false);

  schema = signal<CaracterizacionSchema | null>(null);

  // Índice de sección actual (0-based)
  private _seccionActualIdx = signal(0);
  seccionActualIdx = this.seccionActualIdx_getter();

  private seccionActualIdx_getter() {
    return this._seccionActualIdx.asReadonly();
  }

  // Errores
  private erroresCampo = signal<Record<string, string[]>>({});
  erroresServidor = signal<string[]>([]);

  // Errores de validación cliente por campo
  erroresCliente: Record<string, string> = {};

  // Firma (campo file — solo uno esperado en salud)
  firmaPreview = signal<string | null>(null);
  firmaNombre  = signal('');
  firmaError   = signal('');
  private firmaFile: File | null = null;
  private firmaCampoName = '';

  // ── Modelo dinámico de valores ────────────────────────────────────
  // Escalares: text/email/number/date/textarea/select/checkbox
  valores: Record<string, string | boolean> = {};
  // Multiselect: nombre_campo → Set<string>
  multiValores: Record<string, Set<string>> = {};

  // ── Computados ────────────────────────────────────────────────────
  secciones = computed<Seccion[]>(() => {
    const s = this.schema();
    if (!s) return [];
    return agruparEnSecciones(s.fields, s.sector);
  });

  seccionActual = computed<Seccion | null>(() => {
    const ss = this.secciones();
    return ss[this._seccionActualIdx()] ?? null;
  });

  progresoPct = computed(() => {
    const total = this.secciones().length;
    if (total === 0) return 0;
    return Math.round(((this._seccionActualIdx() + 1) / total) * 100);
  });

  sectorIcono = computed(() => {
    const s = this.schema();
    if (!s) return 'fa fa-users';
    return SECTOR_ICONOS[s.sector] ?? 'fa fa-users';
  });

  // ── Ciclo de vida ─────────────────────────────────────────────────
  ngOnInit(): void {
    this.cargarSchema();
  }

  private eventoId(): number {
    return Number(this.route.snapshot.paramMap.get('eventoId') ?? '0');
  }

  cargarSchema(): void {
    this.cargando.set(true);
    this.errorCarga.set('');
    this.cerrado.set(false);
    this.noEncontrado.set(false);

    const url = this.cfg.url(`/caracterizacion/api/publico/${this.eventoId()}/schema/`);

    this.http.get<CaracterizacionSchema>(url, { observe: 'response' }).subscribe({
      next: (resp) => {
        const data = resp.body!;
        this.schema.set(data);
        this.inicializarValores(data.fields);
        this.cargando.set(false);
      },
      error: (err) => {
        this.cargando.set(false);
        if (err.status === 410) {
          this.cerrado.set(true);
          this.cerradoMsg.set(err.error?.detail || 'Esta caracterización ya está cerrada.');
        } else if (err.status === 404) {
          this.noEncontrado.set(true);
        } else {
          this.errorCarga.set(
            err.error?.detail || 'No se pudo cargar el formulario. Revisa tu conexión.',
          );
        }
      },
    });
  }

  private inicializarValores(fields: SchemaField[]): void {
    for (const f of fields) {
      if (f.type === 'multiselect') {
        this.multiValores[f.name] = new Set();
      } else if (f.type === 'checkbox') {
        this.valores[f.name] = false;
      } else if (f.type === 'file') {
        // manejado aparte
      } else {
        this.valores[f.name] = '';
      }
    }
  }

  // ── Navegación ────────────────────────────────────────────────────
  irSiguiente(): void {
    if (!this.validarSeccionActual()) return;
    const ss = this.secciones();
    if (this._seccionActualIdx() < ss.length - 1) {
      this._seccionActualIdx.update((i) => i + 1);
      this.scrollTop();
    }
  }

  irAnterior(): void {
    if (this._seccionActualIdx() > 0) {
      this._seccionActualIdx.update((i) => i - 1);
      this.scrollTop();
    }
  }

  irASeccion(idx: number): void {
    if (idx <= this._seccionActualIdx()) {
      this._seccionActualIdx.set(idx);
      this.scrollTop();
    }
  }

  private scrollTop(): void {
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }

  // ── Validación cliente ────────────────────────────────────────────
  private validarSeccionActual(): boolean {
    const sec = this.seccionActual();
    if (!sec) return true;
    this.erroresCliente = {};
    let ok = true;

    for (const field of sec.campos) {
      if (!field.required) continue;

      if (field.type === 'multiselect') {
        if (!this.multiValores[field.name] || this.multiValores[field.name].size === 0) {
          this.erroresCliente[field.name] = `${field.label} es obligatorio — selecciona al menos una opción.`;
          ok = false;
        }
      } else if (field.type === 'checkbox') {
        if (!this.valores[field.name]) {
          this.erroresCliente[field.name] = `Debes aceptar "${field.label}".`;
          ok = false;
        }
      } else if (field.type === 'file') {
        if (!this.firmaFile) {
          this.firmaError.set('La foto de la firma es obligatoria.');
          ok = false;
        }
      } else {
        const val = this.valores[field.name];
        if (!val || String(val).trim() === '') {
          this.erroresCliente[field.name] = `${field.label} es obligatorio.`;
          ok = false;
        }
      }
    }

    return ok;
  }

  private validarTodo(): boolean {
    const ss = this.secciones();
    this.erroresCliente = {};
    let primerFallo = -1;
    let ok = true;

    for (let i = 0; i < ss.length; i++) {
      for (const field of ss[i].campos) {
        if (!field.required) continue;

        if (field.type === 'multiselect') {
          if (!this.multiValores[field.name] || this.multiValores[field.name].size === 0) {
            this.erroresCliente[field.name] = `${field.label} es obligatorio.`;
            if (primerFallo < 0) primerFallo = i;
            ok = false;
          }
        } else if (field.type === 'checkbox') {
          if (!this.valores[field.name]) {
            this.erroresCliente[field.name] = `Debes aceptar "${field.label}".`;
            if (primerFallo < 0) primerFallo = i;
            ok = false;
          }
        } else if (field.type === 'file') {
          if (!this.firmaFile) {
            this.firmaError.set('La foto de la firma es obligatoria.');
            if (primerFallo < 0) primerFallo = i;
            ok = false;
          }
        } else {
          const val = this.valores[field.name];
          if (!val || String(val).trim() === '') {
            this.erroresCliente[field.name] = `${field.label} es obligatorio.`;
            if (primerFallo < 0) primerFallo = i;
            ok = false;
          }
        }
      }
    }

    if (!ok && primerFallo >= 0) {
      this._seccionActualIdx.set(primerFallo);
      this.scrollTop();
    }

    return ok;
  }

  // ── Envío ─────────────────────────────────────────────────────────
  enviar(): void {
    if (!this.validarTodo()) return;

    this.enviando.set(true);
    this.erroresCampo.set({});
    this.erroresServidor.set([]);

    const fd = this.buildFormData();
    const url = this.cfg.url(`/caracterizacion/api/publico/${this.eventoId()}/`);

    this.http.post<{ id: number; detail: string }>(url, fd).subscribe({
      next: (resp) => {
        this.enviando.set(false);
        this.exitoId.set(resp.id);
        this.exito.set(true);
        this.scrollTop();
      },
      error: (err) => {
        this.enviando.set(false);
        const body = err.error as ApiError | null;
        if (err.status === 400 && body) {
          if (body.errors) {
            this.erroresCampo.set(body.errors);
            const msgs: string[] = [];
            for (const [campo, errs] of Object.entries(body.errors)) {
              for (const e of errs) msgs.push(`${campo}: ${e}`);
            }
            this.erroresServidor.set(msgs);
            this.irASeccionConError(Object.keys(body.errors));
          } else if (body.detail) {
            this.erroresServidor.set([body.detail]);
          }
        } else if (err.status === 410) {
          this.cerrado.set(true);
          this.cerradoMsg.set(err.error?.detail || 'La convocatoria ya cerró.');
        } else {
          this.erroresServidor.set([
            err.error?.detail || 'Error al enviar. Intenta nuevamente.',
          ]);
        }
        this.scrollTop();
      },
    });
  }

  private buildFormData(): globalThis.FormData {
    const fd = new globalThis.FormData();
    const s = this.schema();
    if (!s) return fd;

    for (const field of s.fields) {
      if (field.type === 'multiselect') {
        const set = this.multiValores[field.name];
        if (set) {
          for (const v of set) fd.append(field.name, v);
        }
      } else if (field.type === 'file') {
        if (this.firmaFile) {
          fd.append(field.name, this.firmaFile, this.firmaFile.name);
        }
      } else if (field.type === 'checkbox') {
        const val = this.valores[field.name];
        fd.append(field.name, val ? 'true' : 'false');
      } else {
        const val = this.valores[field.name];
        if (val !== undefined && val !== null && String(val).trim() !== '') {
          fd.append(field.name, String(val));
        }
      }
    }

    return fd;
  }

  private irASeccionConError(campos: string[]): void {
    const s = this.schema();
    if (!s) return;
    const ss = this.secciones();

    for (let i = 0; i < ss.length; i++) {
      const nombres = ss[i].campos.map((c) => c.name);
      if (campos.some((c) => nombres.includes(c))) {
        this._seccionActualIdx.set(i);
        return;
      }
    }
  }

  // ── Helpers ───────────────────────────────────────────────────────
  hasMulti(fieldName: string, valor: string): boolean {
    return this.multiValores[fieldName]?.has(valor) ?? false;
  }

  toggleMulti(fieldName: string, valor: string): void {
    if (!this.multiValores[fieldName]) {
      this.multiValores[fieldName] = new Set();
    }
    const set = this.multiValores[fieldName];
    if (set.has(valor)) {
      set.delete(valor);
    } else {
      set.add(valor);
    }
  }

  fieldError(campo: string): string {
    const errs = this.erroresCampo()[campo];
    return errs?.length ? errs[0] : '';
  }

  onFileChange(event: Event, fieldName: string): void {
    const input = event.target as HTMLInputElement;
    const file = input.files?.[0];
    if (!file) return;

    if (file.size > 2 * 1024 * 1024) {
      this.firmaError.set('La imagen pesa más de 2 MB. Toma otra foto con menor calidad.');
      input.value = '';
      return;
    }

    this.firmaError.set('');
    this.firmaFile = file;
    this.firmaCampoName = fieldName;
    this.firmaNombre.set(`${file.name} (${Math.round(file.size / 1024)} KB)`);

    const reader = new FileReader();
    reader.onload = (e) => {
      this.firmaPreview.set(e.target?.result as string);
    };
    reader.readAsDataURL(file);
  }

  quitarFirma(_fieldName: string): void {
    this.firmaFile = null;
    this.firmaPreview.set(null);
    this.firmaNombre.set('');
    this.firmaError.set('');
    this.firmaCampoName = '';
  }
}
