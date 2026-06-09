import { HttpClient } from '@angular/common/http';
import { Component, OnInit, inject, signal } from '@angular/core';
import { ActivatedRoute } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { ConfigService } from '../../core/config/config.service';

// ---------------------------------------------------------------------------
// Tipos del catálogo GET /api/eventos/<id>/inscripcion/catalogos/
// ---------------------------------------------------------------------------

interface CatalogoItem {
  value: string | number;
  label: string;
}

interface InscripcionCatalogos {
  evento: {
    id: number;
    nombre: string;
    fecha_fin?: string;
    abierto: boolean;
  };
  sexos: CatalogoItem[];
  generos: CatalogoItem[];
  orientaciones: CatalogoItem[];
  grupos_etnicos: CatalogoItem[];
  upz: CatalogoItem[];
  barrios: CatalogoItem[];
}

interface PersonaAutollenado {
  found?: boolean;
  nombre1?: string;
  nombre2?: string;
  apellido1?: string;
  apellido2?: string;
  telefono?: string;
  correo?: string;
}

interface ApiError {
  detail?: string;
  // El serializer DRF devuelve errores por campo como {campo: [msgs]}.
  [campo: string]: unknown;
}

const SECCIONES = [
  { id: 'identificacion', titulo: 'Identificación',  icono: 'fa fa-id-card' },
  { id: 'demografia',     titulo: 'Datos personales', icono: 'fa fa-user' },
  { id: 'contacto',       titulo: 'Contacto y lugar', icono: 'fa fa-map-marker' },
] as const;

type SeccionId = typeof SECCIONES[number]['id'];

@Component({
  standalone: true,
  selector: 'app-inscripcion-publico',
  imports: [FormsModule],
  template: `
    <!-- ══ CARGANDO ══ -->
    @if (cargando()) {
      <div class="loading-wrap" role="status" aria-live="polite">
        <div class="loading-spinner" aria-hidden="true"></div>
        <p>Cargando formulario…</p>
      </div>
    }

    <!-- ══ CERRADO ══ -->
    @if (!cargando() && cerrado()) {
      <div class="estado-wrap">
        <div class="estado-card estado-card--cerrado">
          <div class="estado-icono" aria-hidden="true"><i class="fa fa-lock"></i></div>
          <h1 class="estado-titulo">Inscripción cerrada</h1>
          <p class="estado-msg">{{ cerradoMsg() }}</p>
          <p class="estado-sub">
            Esta actividad ya no admite inscripciones.<br>
            Contacta a la Alcaldía Local de Kennedy para más información.
          </p>
          <div class="estado-brand">
            <span class="estado-brand__escudo" aria-hidden="true">🏛</span>
            <span>Alcaldía Local de Kennedy</span>
          </div>
        </div>
      </div>
    }

    <!-- ══ ERROR DE CARGA ══ -->
    @if (!cargando() && !cerrado() && errorCarga()) {
      <div class="estado-wrap">
        <div class="estado-card">
          <div class="estado-icono" aria-hidden="true"><i class="fa fa-exclamation-triangle"></i></div>
          <h1 class="estado-titulo">Error al cargar</h1>
          <p class="estado-msg">{{ errorCarga() }}</p>
          <button class="btn-brand btn-lg" (click)="cargarCatalogos()">
            <i class="fa fa-refresh" aria-hidden="true"></i> Reintentar
          </button>
        </div>
      </div>
    }

    <!-- ══ ÉXITO ══ -->
    @if (!cargando() && exito()) {
      <div class="estado-wrap">
        <div class="estado-card estado-card--exito">
          <div class="exito-check" aria-hidden="true">
            <svg viewBox="0 0 80 80" fill="none" xmlns="http://www.w3.org/2000/svg">
              <circle cx="40" cy="40" r="40" fill="#DCFCE7"/>
              <path d="M24 40l12 12 20-24" stroke="#16A34A" stroke-width="4"
                    stroke-linecap="round" stroke-linejoin="round"/>
            </svg>
          </div>
          <h1 class="exito-titulo">¡Inscripción registrada!</h1>
          <p class="exito-desc">Tu inscripción a la actividad fue registrada exitosamente.</p>
          @if (exitoId()) {
            <div class="exito-num">
              <span class="exito-num__label">Número de registro</span>
              <span class="exito-num__val"># {{ exitoId() }}</span>
            </div>
          }
          <p class="exito-footer">
            Guarda este número como constancia. El equipo de la Alcaldía Local
            de Kennedy conserva el registro.
          </p>
          <div class="estado-brand">
            <span class="estado-brand__escudo" aria-hidden="true">🏛</span>
            <span>Alcaldía Local de Kennedy · Inscripción</span>
          </div>
        </div>
      </div>
    }

    <!-- ══ FORMULARIO ══ -->
    @if (!cargando() && !cerrado() && !errorCarga() && !exito() && catalogos()) {
      <header class="form-header" role="banner">
        <div class="form-banner">
          <div class="form-banner__left">
            <div class="form-banner__escudo" aria-hidden="true">🏛</div>
            <div>
              <p class="form-banner__institucion">Alcaldía Local de Kennedy</p>
              <h1 class="form-banner__titulo">Inscripción a la actividad</h1>
              <p class="form-banner__sub">Registro de participante</p>
            </div>
          </div>
          <div class="form-banner__badge" aria-hidden="true"><i class="fa fa-user-plus"></i></div>
        </div>
        <div class="form-header__evento">
          <i class="fa fa-calendar" aria-hidden="true"></i>
          <span>{{ catalogos()!.evento.nombre }}</span>
          @if (catalogos()!.evento.fecha_fin) {
            <span class="form-header__fecha">· Cierre: {{ catalogos()!.evento.fecha_fin }}</span>
          }
        </div>
      </header>

      @if (erroresServidor().length > 0) {
        <div class="server-errors" role="alert">
          <i class="fa fa-exclamation-circle" aria-hidden="true"></i>
          <div>
            <strong>Corrige los siguientes errores antes de enviar:</strong>
            <ul>
              @for (err of erroresServidor(); track err) { <li>{{ err }}</li> }
            </ul>
          </div>
        </div>
      }

      <main class="form-main" role="main">

        <!-- IDENTIFICACIÓN -->
        <div class="seccion" [class.seccion--abierta]="seccionAbierta('identificacion')">
          <button type="button" class="seccion__header"
                  (click)="toggleSeccion('identificacion')"
                  [attr.aria-expanded]="seccionAbierta('identificacion')">
            <span class="seccion__icono" aria-hidden="true"><i class="fa fa-id-card"></i></span>
            <span class="seccion__titulo">Identificación</span>
            <span class="seccion__chevron" aria-hidden="true"><i class="fa fa-chevron-down"></i></span>
          </button>
          @if (seccionAbierta('identificacion')) {
            <div class="seccion__body">
              <p class="seccion__hint">
                Ingresa tu número de documento — si ya estás registrado, tus
                datos se cargarán automáticamente.
              </p>

              <div class="field">
                <label class="field__label" for="documento">
                  Número de documento <span class="field__optional">opcional</span>
                </label>
                <div class="field__input-wrap">
                  <input id="documento" type="text" class="field__input"
                         [(ngModel)]="form.documento" (blur)="autollenar()"
                         inputmode="numeric" maxlength="15" placeholder="12345678">
                  @if (autollenadoStatus() === 'cargando') {
                    <span class="field__spinner" aria-hidden="true"></span>
                  }
                </div>
                @if (autollenadoStatus() === 'ok') {
                  <p class="field__status field__status--ok" role="status" aria-live="polite">
                    <i class="fa fa-check" aria-hidden="true"></i> Datos cargados desde el sistema.
                  </p>
                }
                @if (autollenadoStatus() === 'nuevo') {
                  <p class="field__status" role="status" aria-live="polite">
                    <i class="fa fa-info-circle" aria-hidden="true"></i> Persona nueva — completa los datos.
                  </p>
                }
                @if (fieldError('documento')) {
                  <p class="field__error" role="alert">{{ fieldError('documento') }}</p>
                }
              </div>

              <div class="field-row">
                <div class="field field--required">
                  <label class="field__label" for="nombre1">Primer nombre</label>
                  <input id="nombre1" type="text" class="field__input" [(ngModel)]="form.nombre1"
                         autocomplete="given-name" required maxlength="120" placeholder="Juan">
                  @if (fieldError('nombre1')) { <p class="field__error" role="alert">{{ fieldError('nombre1') }}</p> }
                </div>
                <div class="field">
                  <label class="field__label" for="nombre2">Segundo nombre <span class="field__optional">opcional</span></label>
                  <input id="nombre2" type="text" class="field__input" [(ngModel)]="form.nombre2"
                         autocomplete="additional-name" maxlength="120" placeholder="Carlos">
                </div>
              </div>

              <div class="field-row">
                <div class="field field--required">
                  <label class="field__label" for="apellido1">Primer apellido</label>
                  <input id="apellido1" type="text" class="field__input" [(ngModel)]="form.apellido1"
                         autocomplete="family-name" required maxlength="120" placeholder="García">
                  @if (fieldError('apellido1')) { <p class="field__error" role="alert">{{ fieldError('apellido1') }}</p> }
                </div>
                <div class="field">
                  <label class="field__label" for="apellido2">Segundo apellido <span class="field__optional">opcional</span></label>
                  <input id="apellido2" type="text" class="field__input" [(ngModel)]="form.apellido2"
                         maxlength="120" placeholder="López">
                </div>
              </div>
            </div>
          }
        </div>

        <!-- DEMOGRAFÍA -->
        <div class="seccion" [class.seccion--abierta]="seccionAbierta('demografia')">
          <button type="button" class="seccion__header"
                  (click)="toggleSeccion('demografia')"
                  [attr.aria-expanded]="seccionAbierta('demografia')">
            <span class="seccion__icono" aria-hidden="true"><i class="fa fa-user"></i></span>
            <span class="seccion__titulo">Datos personales</span>
            <span class="seccion__badge">opcional</span>
            <span class="seccion__chevron" aria-hidden="true"><i class="fa fa-chevron-down"></i></span>
          </button>
          @if (seccionAbierta('demografia')) {
            <div class="seccion__body">
              <div class="field-row">
                <div class="field">
                  <label class="field__label" for="fecha_nacimiento">Fecha de nacimiento</label>
                  <input id="fecha_nacimiento" type="date" class="field__input" [(ngModel)]="form.fecha_nacimiento">
                </div>
                <div class="field">
                  <label class="field__label" for="sexo">Sexo</label>
                  <select id="sexo" class="field__select" [(ngModel)]="form.sexo_biologico">
                    <option value="">Selecciona…</option>
                    @for (s of catalogos()!.sexos; track s.value) { <option [value]="s.value">{{ s.label }}</option> }
                  </select>
                </div>
              </div>
              <div class="field-row">
                <div class="field">
                  <label class="field__label" for="genero">Identidad de género</label>
                  <select id="genero" class="field__select" [(ngModel)]="form.identidad_genero">
                    <option value="">Selecciona…</option>
                    @for (g of catalogos()!.generos; track g.value) { <option [value]="g.value">{{ g.label }}</option> }
                  </select>
                </div>
                <div class="field">
                  <label class="field__label" for="orientacion">Orientación sexual</label>
                  <select id="orientacion" class="field__select" [(ngModel)]="form.orientacion_sexual">
                    <option value="">Selecciona…</option>
                    @for (o of catalogos()!.orientaciones; track o.value) { <option [value]="o.value">{{ o.label }}</option> }
                  </select>
                </div>
              </div>
              <div class="field-row">
                <div class="field">
                  <label class="field__label" for="etnia">Grupo étnico</label>
                  <select id="etnia" class="field__select" [(ngModel)]="form.grupo_etnico">
                    <option value="">Selecciona…</option>
                    @for (e of catalogos()!.grupos_etnicos; track e.value) { <option [value]="e.value">{{ e.label }}</option> }
                  </select>
                </div>
                <div class="field field--check">
                  <label class="check">
                    <input type="checkbox" [(ngModel)]="form.discapacidad">
                    <span>¿Presenta alguna discapacidad?</span>
                  </label>
                </div>
              </div>
            </div>
          }
        </div>

        <!-- CONTACTO -->
        <div class="seccion" [class.seccion--abierta]="seccionAbierta('contacto')">
          <button type="button" class="seccion__header"
                  (click)="toggleSeccion('contacto')"
                  [attr.aria-expanded]="seccionAbierta('contacto')">
            <span class="seccion__icono" aria-hidden="true"><i class="fa fa-map-marker"></i></span>
            <span class="seccion__titulo">Contacto y lugar</span>
            <span class="seccion__badge">opcional</span>
            <span class="seccion__chevron" aria-hidden="true"><i class="fa fa-chevron-down"></i></span>
          </button>
          @if (seccionAbierta('contacto')) {
            <div class="seccion__body">
              <div class="field-row">
                <div class="field">
                  <label class="field__label" for="telefono">Teléfono</label>
                  <input id="telefono" type="tel" class="field__input" [(ngModel)]="form.telefono"
                         autocomplete="tel" placeholder="3001234567">
                  @if (fieldError('telefono')) { <p class="field__error" role="alert">{{ fieldError('telefono') }}</p> }
                </div>
                <div class="field">
                  <label class="field__label" for="correo">Correo electrónico</label>
                  <input id="correo" type="email" class="field__input" [(ngModel)]="form.correo"
                         autocomplete="email" placeholder="correo@ejemplo.com">
                  @if (fieldError('correo')) { <p class="field__error" role="alert">{{ fieldError('correo') }}</p> }
                </div>
              </div>
              <div class="field-row">
                <div class="field">
                  <label class="field__label" for="upz">UPZ</label>
                  <select id="upz" class="field__select" [(ngModel)]="form.upz">
                    <option value="">Selecciona UPZ…</option>
                    @for (u of catalogos()!.upz; track u.value) { <option [value]="u.value">{{ u.label }}</option> }
                  </select>
                </div>
                <div class="field">
                  <label class="field__label" for="barrio">Barrio</label>
                  <select id="barrio" class="field__select" [(ngModel)]="form.barrio">
                    <option value="">Selecciona barrio…</option>
                    @for (b of catalogos()!.barrios; track b.value) { <option [value]="b.value">{{ b.label }}</option> }
                  </select>
                </div>
              </div>
            </div>
          }
        </div>

        <div class="form-submit-wrap">
          <button type="button" class="btn-brand btn-submit" (click)="enviar()" [disabled]="enviando()">
            @if (enviando()) {
              <span class="spinner-inline" aria-hidden="true"></span> Enviando…
            } @else {
              <i class="fa fa-paper-plane" aria-hidden="true"></i> Registrar inscripción
            }
          </button>
          <p class="form-submit__hint">
            <i class="fa fa-lock" aria-hidden="true"></i>
            Solo nombre y apellido son obligatorios.
          </p>
        </div>
      </main>
    }
  `,
  styles: [`
    @use '../../../styles/tokens' as *;

    $brand-rojo-oscuro:  #B50015;
    $brand-rojo:         #D6001C;
    $brand-rojo-claro:   #FF1F38;
    $brand-gradient:     linear-gradient(135deg, #{$brand-rojo-oscuro} 0%, #{$brand-rojo} 60%, #{$brand-rojo-claro} 100%);
    $brand-gradient-sub: linear-gradient(135deg, rgba(#B50015, 0.08) 0%, rgba(#D6001C, 0.04) 100%);

    :host {
      display: block;
      background: $color-bg-subtle;
      min-height: 100vh;
      font-family: $font-family-base;
    }

    .loading-wrap {
      display: flex; flex-direction: column; align-items: center; justify-content: center;
      min-height: 100vh; gap: $space-4; color: $color-text-muted;
    }
    .loading-spinner {
      width: 44px; height: 44px; border: 4px solid $color-border;
      border-top-color: $brand-rojo; border-radius: 50%; animation: spin 0.8s linear infinite;
      @media (prefers-reduced-motion: reduce) { animation: none; }
    }

    .estado-wrap { display: flex; align-items: center; justify-content: center; min-height: 100vh; padding: $space-6; }
    .estado-card {
      background: $color-bg; border-radius: $radius-2xl; padding: $space-10 $space-8;
      text-align: center; max-width: 480px; width: 100%; box-shadow: $shadow-lg;
      &--cerrado { border-top: 6px solid $brand-rojo; }
      &--exito   { border-top: 6px solid $color-success; }
    }
    .estado-icono { font-size: 3.5rem; margin-bottom: $space-4; color: $brand-rojo; }
    .estado-titulo { font-size: $font-size-2xl; font-weight: $font-weight-bold; color: $color-text; margin: 0 0 $space-3; }
    .estado-msg { font-size: $font-size-md; color: $color-text; font-weight: $font-weight-semibold; margin-bottom: $space-3; }
    .estado-sub { color: $color-text-muted; font-size: $font-size-sm; line-height: $line-height-relaxed; margin-bottom: $space-6; }
    .estado-brand {
      display: inline-flex; align-items: center; gap: $space-2; font-size: $font-size-xs;
      color: $color-text-muted; font-weight: $font-weight-semibold; letter-spacing: 0.03em;
      &__escudo { font-size: 1.1rem; }
    }

    .exito-check { width: 80px; height: 80px; margin: 0 auto $space-5; svg { width: 100%; height: 100%; } }
    .exito-titulo { font-size: $font-size-2xl; font-weight: $font-weight-bold; color: $color-success; margin: 0 0 $space-3; }
    .exito-desc { color: $color-text; font-size: $font-size-md; margin-bottom: $space-5; }
    .exito-num {
      display: inline-flex; flex-direction: column; gap: $space-1; background: $brand-gradient-sub;
      border: 2px solid rgba($brand-rojo, 0.2); border-radius: $radius-xl; padding: $space-4 $space-8; margin-bottom: $space-5;
    }
    .exito-num__label { font-size: $font-size-xs; text-transform: uppercase; letter-spacing: 0.06em; color: $color-text-muted; font-weight: $font-weight-semibold; }
    .exito-num__val { font-size: $font-size-2xl; font-weight: $font-weight-bold; color: $brand-rojo; }
    .exito-footer { color: $color-text-muted; font-size: $font-size-sm; margin: 0 0 $space-6; line-height: $line-height-relaxed; }

    .form-header { background: $color-bg; box-shadow: $shadow-sm; position: sticky; top: 0; z-index: $z-sticky; }
    .form-banner {
      display: flex; align-items: center; justify-content: space-between; background: $brand-gradient;
      color: $color-text-inverse; padding: $space-5; gap: $space-3;
    }
    .form-banner__left { display: flex; align-items: center; gap: $space-3; }
    .form-banner__escudo { font-size: 2.2rem; flex-shrink: 0; }
    .form-banner__institucion { font-size: $font-size-xs; opacity: 0.85; letter-spacing: 0.04em; text-transform: uppercase; margin: 0 0 $space-1; }
    .form-banner__titulo { font-size: $font-size-lg; font-weight: $font-weight-bold; margin: 0; line-height: $line-height-tight; @media (min-width: #{$bp-md}) { font-size: $font-size-xl; } }
    .form-banner__sub { font-size: $font-size-xs; opacity: 0.85; margin: $space-1 0 0; }
    .form-banner__badge { font-size: 2.5rem; opacity: 0.25; flex-shrink: 0; @media (max-width: 400px) { display: none; } }
    .form-header__evento {
      display: flex; align-items: center; gap: $space-2; padding: $space-2 $space-5;
      font-size: $font-size-xs; color: $color-text-muted; background: $color-bg; border-bottom: 1px solid $color-border;
    }
    .form-header__fecha { color: $brand-rojo; font-weight: $font-weight-semibold; }

    .server-errors {
      display: flex; align-items: flex-start; gap: $space-3; background: $color-danger-bg;
      border-left: 4px solid $color-danger; border-radius: $radius-md; padding: $space-4;
      margin: $space-4 $space-4 0; color: $color-danger; font-size: $font-size-sm;
      i { margin-top: 2px; flex-shrink: 0; }
      ul { margin: $space-2 0 0; padding-left: $space-5; }
    }

    .form-main { max-width: 100%; margin: 0 auto; padding: $space-4; @media (min-width: #{$bp-md}) { max-width: 700px; padding: $space-6 $space-4; } }

    .seccion {
      background: $color-bg; border-radius: $radius-xl; box-shadow: $shadow-sm; margin-bottom: $space-3;
      overflow: hidden; border: 1.5px solid $color-border; transition: border-color $transition-base, box-shadow $transition-base;
      &--abierta { border-color: rgba($brand-rojo, 0.3); box-shadow: 0 0 0 1px rgba($brand-rojo, 0.08), $shadow-md; }
    }
    .seccion__header {
      display: flex; align-items: center; gap: $space-3; width: 100%; padding: $space-4 $space-5;
      background: none; border: none; cursor: pointer; text-align: left; font-family: $font-family-base;
      transition: background $transition-base;
      &:hover { background: $color-bg-subtle; }
      &:focus-visible { outline: $focus-ring; outline-offset: $focus-ring-offset; }
    }
    .seccion__icono {
      display: flex; align-items: center; justify-content: center; width: 36px; height: 36px; min-width: 36px;
      background: $brand-gradient-sub; border-radius: $radius-md; color: $brand-rojo; font-size: $font-size-base;
      .seccion--abierta & { background: $brand-rojo; color: $color-text-inverse; }
    }
    .seccion__titulo { flex: 1; font-size: $font-size-base; font-weight: $font-weight-semibold; color: $color-text; }
    .seccion__badge {
      font-size: $font-size-xs; font-weight: $font-weight-semibold; color: $brand-rojo;
      background: rgba($brand-rojo, 0.1); padding: $space-1 $space-2; border-radius: $radius-sm; letter-spacing: 0.03em;
    }
    .seccion__chevron {
      color: $color-text-muted; transition: transform $transition-base; font-size: $font-size-sm;
      .seccion--abierta & { transform: rotate(180deg); color: $brand-rojo; }
      @media (prefers-reduced-motion: reduce) { transition: none; }
    }
    .seccion__body {
      padding: $space-2 $space-5 $space-6; border-top: 1px solid $color-border;
      @media (prefers-reduced-motion: no-preference) { animation: seccion-open 0.2s ease-out both; }
    }
    @keyframes seccion-open { from { opacity: 0; transform: translateY(-6px); } to { opacity: 1; transform: translateY(0); } }
    .seccion__hint { font-size: $font-size-sm; color: $color-text-muted; margin: $space-4 0 $space-5; line-height: $line-height-relaxed; }

    .field { margin-bottom: $space-4; &--required .field__label::after { content: ' *'; color: $brand-rojo; font-weight: $font-weight-bold; } }
    .field__label { display: block; font-size: $font-size-sm; font-weight: $font-weight-semibold; color: $color-text; margin-bottom: $space-2; }
    .field__optional { font-size: $font-size-xs; font-weight: $font-weight-regular; color: $color-text-muted; margin-left: $space-1; }
    .field__input, .field__select {
      display: block; width: 100%; min-height: $touch-target-min; padding: $space-3 $space-4;
      font-size: $font-size-base; font-family: $font-family-base; color: $color-text; background: $color-bg;
      border: 1.5px solid $color-border-strong; border-radius: $radius-lg; transition: border-color $transition-base, box-shadow $transition-base;
      &:focus { outline: none; border-color: $brand-rojo; box-shadow: 0 0 0 3px rgba($brand-rojo, 0.15); }
      &:focus-visible { outline: $focus-ring; outline-offset: $focus-ring-offset; }
    }
    .field__error { color: $color-danger; font-size: $font-size-xs; margin: $space-1 0 0; font-weight: $font-weight-medium; display: flex; align-items: center; gap: $space-1; }
    .field__status { font-size: $font-size-xs; margin: $space-1 0 0; color: $color-info; display: flex; align-items: center; gap: $space-1; &--ok { color: $color-success; } }
    .field__input-wrap { position: relative; .field__input { padding-right: 2.5rem; } }
    .field__spinner {
      position: absolute; right: $space-3; top: 50%; transform: translateY(-50%); width: 16px; height: 16px;
      border: 2px solid $color-border; border-top-color: $brand-rojo; border-radius: 50%; animation: spin 0.8s linear infinite;
      @media (prefers-reduced-motion: reduce) { animation: none; }
    }
    .field-row { display: grid; grid-template-columns: 1fr; gap: $space-3; @media (min-width: #{$bp-sm}) { grid-template-columns: 1fr 1fr; } }
    .field--check { display: flex; align-items: flex-end; }
    .check { display: flex; align-items: center; gap: $space-2; font-size: $font-size-sm; color: $color-text; cursor: pointer; padding-bottom: $space-3;
      input { width: 20px; height: 20px; accent-color: $brand-rojo; } }

    .form-submit-wrap { text-align: center; padding: $space-6 0 $space-10; }
    .btn-brand {
      display: inline-flex; align-items: center; justify-content: center; gap: $space-2; min-height: $touch-target-min;
      padding: $space-3 $space-6; background: $brand-gradient; color: $color-text-inverse; border: none; border-radius: $radius-lg;
      font-size: $font-size-base; font-family: $font-family-base; font-weight: $font-weight-semibold; cursor: pointer;
      transition: filter $transition-base, box-shadow $transition-base; text-decoration: none; box-shadow: 0 4px 14px rgba($brand-rojo, 0.35);
      &:hover { filter: brightness(0.92); box-shadow: 0 6px 20px rgba($brand-rojo, 0.45); }
      &:focus-visible { outline: $focus-ring; outline-offset: $focus-ring-offset; }
      &[disabled] { opacity: 0.65; cursor: not-allowed; box-shadow: none; }
      &-lg { font-size: $font-size-md; padding: $space-4 $space-8; }
    }
    .btn-submit { width: 100%; max-width: 400px; font-size: $font-size-md; padding: $space-4 $space-8; border-radius: $radius-xl; }
    .form-submit__hint { font-size: $font-size-xs; color: $color-text-muted; margin: $space-3 0 0; display: flex; align-items: center; justify-content: center; gap: $space-2; }
    .spinner-inline {
      display: inline-block; width: 16px; height: 16px; border: 2px solid rgba(255, 255, 255, 0.4);
      border-top-color: $color-text-inverse; border-radius: 50%; animation: spin 0.7s linear infinite;
      @media (prefers-reduced-motion: reduce) { animation: none; }
    }
    @keyframes spin { to { transform: rotate(360deg); } }
  `],
})
export class InscripcionPublicoComponent implements OnInit {
  private route = inject(ActivatedRoute);
  private http  = inject(HttpClient);
  private cfg   = inject(ConfigService);

  cargando   = signal(true);
  errorCarga = signal('');
  cerrado    = signal(false);
  cerradoMsg = signal('');
  exito      = signal(false);
  exitoId    = signal<number | null>(null);
  enviando   = signal(false);

  catalogos = signal<InscripcionCatalogos | null>(null);

  private erroresCampo = signal<Record<string, string[]>>({});
  erroresServidor      = signal<string[]>([]);

  autollenadoStatus = signal<'ok' | 'nuevo' | 'cargando' | null>(null);

  private seccionesAbiertas = signal<Set<SeccionId>>(new Set(['identificacion']));

  form = {
    documento:          '',
    nombre1:            '',
    nombre2:            '',
    apellido1:          '',
    apellido2:          '',
    fecha_nacimiento:   '',
    sexo_biologico:     '',
    identidad_genero:   '',
    orientacion_sexual: '',
    grupo_etnico:       '',
    discapacidad:       false,
    telefono:           '',
    correo:             '',
    upz:                '',
    barrio:             '',
  };

  ngOnInit(): void {
    this.cargarCatalogos();
  }

  private eventoId(): number {
    return Number(this.route.snapshot.paramMap.get('eventoId') ?? '0');
  }

  cargarCatalogos(): void {
    this.cargando.set(true);
    this.errorCarga.set('');
    this.cerrado.set(false);

    const url = this.cfg.url(`/api/eventos/${this.eventoId()}/inscripcion/catalogos/`);

    this.http.get<InscripcionCatalogos>(url).subscribe({
      next: (data) => {
        if (!data.evento.abierto) {
          this.cerrado.set(true);
          this.cerradoMsg.set('Esta actividad ya no admite inscripciones.');
          this.cargando.set(false);
          return;
        }
        this.catalogos.set(data);
        this.cargando.set(false);
      },
      error: (err) => {
        this.cargando.set(false);
        this.errorCarga.set(
          err.error?.detail || 'No se pudo cargar el formulario. Revisa tu conexión.',
        );
      },
    });
  }

  toggleSeccion(id: SeccionId): void {
    const abiertas = new Set(this.seccionesAbiertas());
    abiertas.has(id) ? abiertas.delete(id) : abiertas.add(id);
    this.seccionesAbiertas.set(abiertas);
  }

  seccionAbierta(id: SeccionId): boolean {
    return this.seccionesAbiertas().has(id);
  }

  autollenar(): void {
    const doc = this.form.documento.trim();
    if (doc.length < 4) { this.autollenadoStatus.set(null); return; }

    this.autollenadoStatus.set('cargando');
    this.http
      .get<PersonaAutollenado>(this.cfg.url(`/caracterizacion/api/persona/?doc=${encodeURIComponent(doc)}`))
      .subscribe({
        next: (data) => {
          if (!data.found) { this.autollenadoStatus.set('nuevo'); return; }
          if (!this.form.nombre1   && data.nombre1)   this.form.nombre1   = data.nombre1;
          if (!this.form.nombre2   && data.nombre2)   this.form.nombre2   = data.nombre2;
          if (!this.form.apellido1 && data.apellido1) this.form.apellido1 = data.apellido1;
          if (!this.form.apellido2 && data.apellido2) this.form.apellido2 = data.apellido2;
          if (!this.form.telefono  && data.telefono)  this.form.telefono  = data.telefono;
          if (!this.form.correo    && data.correo)    this.form.correo    = data.correo;
          this.autollenadoStatus.set('ok');
        },
        error: () => this.autollenadoStatus.set(null),
      });
  }

  fieldError(campo: string): string {
    const errs = this.erroresCampo()[campo];
    return errs?.length ? errs[0] : '';
  }

  private validar(): boolean {
    if (!this.form.nombre1.trim() || !this.form.apellido1.trim()) {
      const abiertas = new Set(this.seccionesAbiertas());
      abiertas.add('identificacion');
      this.seccionesAbiertas.set(abiertas);
      this.erroresServidor.set(['El primer nombre y el primer apellido son obligatorios.']);
      window.scrollTo({ top: 0, behavior: 'smooth' });
      return false;
    }
    return true;
  }

  enviar(): void {
    if (!this.validar()) return;

    this.enviando.set(true);
    this.erroresCampo.set({});
    this.erroresServidor.set([]);

    const url = this.cfg.url(`/api/eventos/${this.eventoId()}/inscripciones/`);
    this.http.post<{ persona_id: number; participante_evento_id: number }>(url, this.payload()).subscribe({
      next: (resp) => {
        this.enviando.set(false);
        this.exitoId.set(resp.participante_evento_id);
        this.exito.set(true);
        window.scrollTo({ top: 0, behavior: 'smooth' });
      },
      error: (err) => {
        this.enviando.set(false);
        const body = err.error as ApiError | null;
        if (err.status === 400 && body) {
          const errores: Record<string, string[]> = {};
          const msgs: string[] = [];
          for (const [campo, val] of Object.entries(body)) {
            if (campo === 'detail') continue;
            if (Array.isArray(val)) {
              errores[campo] = val as string[];
              for (const e of val) msgs.push(`${campo}: ${e}`);
            }
          }
          this.erroresCampo.set(errores);
          this.erroresServidor.set(msgs.length ? msgs : [body.detail || 'Revisa los campos.']);
        } else {
          this.erroresServidor.set([body?.detail || 'Error al enviar. Intenta nuevamente.']);
        }
        window.scrollTo({ top: 0, behavior: 'smooth' });
      },
    });
  }

  private payload(): Record<string, unknown> {
    const f = this.form;
    const out: Record<string, unknown> = {
      nombre1: f.nombre1.trim(),
      apellido1: f.apellido1.trim(),
      discapacidad: f.discapacidad,
    };
    const opt: Array<[string, string]> = [
      ['nombre2', f.nombre2], ['apellido2', f.apellido2],
      ['fecha_nacimiento', f.fecha_nacimiento], ['sexo_biologico', f.sexo_biologico],
      ['identidad_genero', f.identidad_genero], ['orientacion_sexual', f.orientacion_sexual],
      ['grupo_etnico', f.grupo_etnico], ['documento', f.documento.trim()],
      ['telefono', f.telefono.trim()], ['correo', f.correo.trim()],
      ['upz', f.upz], ['barrio', f.barrio],
    ];
    for (const [k, v] of opt) {
      if (v) out[k] = v;
    }
    return out;
  }
}
