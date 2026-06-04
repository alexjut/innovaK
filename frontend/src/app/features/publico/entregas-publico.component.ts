import { HttpClient } from '@angular/common/http';
import { Component, OnInit, inject, signal } from '@angular/core';
import { ActivatedRoute } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { ConfigService } from '../../core/config/config.service';

// ---------------------------------------------------------------------------
// Tipos del catálogo devuelto por GET /entregas/api/publico/<id>/catalogos/
// ---------------------------------------------------------------------------

interface CatalogoItem {
  value: string | number;
  label: string;
}

interface InsumoItem {
  value: string;
  label: string;
  categoria: 'deportivo' | 'tecnologico' | 'logistico' | string;
}

interface EntregasCatalogos {
  evento: {
    id: number;
    nombre: string;
    fecha_fin?: string;
    abierto: boolean;
  };
  tipos_documento: CatalogoItem[];
  upls: CatalogoItem[];
  barrios: CatalogoItem[];
  insumos: InsumoItem[];
}

interface PersonaAutollenado {
  found?: boolean;
  nombre1?: string;
  nombre2?: string;
  apellido1?: string;
  apellido2?: string;
  telefono?: string;
  correo?: string;
  direccion?: string;
}

interface ApiError {
  detail?: string;
  errors?: Record<string, string[]>;
}

// ---------------------------------------------------------------------------
// Modelo de cantidad de insumo
// ---------------------------------------------------------------------------

interface InsumoConCantidad {
  codigo: string;
  nombre: string;
  categoria: string;
  cantidad: number;
}

// ---------------------------------------------------------------------------
// Secciones del formulario (acordeón en una sola página)
// ---------------------------------------------------------------------------

const SECCIONES = [
  { id: 'identificacion', titulo: 'Identificación',    icono: 'fa fa-id-card' },
  { id: 'insumos',        titulo: 'Insumos recibidos', icono: 'fa fa-cube' },
  { id: 'firma',          titulo: 'Firma',             icono: 'fa fa-pencil' },
] as const;

type SeccionId = typeof SECCIONES[number]['id'];

const ICONO_CATEGORIA: Record<string, string> = {
  deportivo:   'fa fa-futbol-o',
  tecnologico: 'fa fa-laptop',
  logistico:   'fa fa-truck',
};

// ---------------------------------------------------------------------------
// Componente
// ---------------------------------------------------------------------------

@Component({
  standalone: true,
  selector: 'app-entregas-publico',
  imports: [FormsModule],
  template: `
    <!-- ══ ESTADO: CARGANDO ══ -->
    @if (cargando()) {
      <div class="loading-wrap" role="status" aria-live="polite">
        <div class="loading-spinner" aria-hidden="true"></div>
        <p>Cargando formulario…</p>
      </div>
    }

    <!-- ══ ESTADO: ENTREGA CERRADA ══ -->
    @if (!cargando() && cerrado()) {
      <div class="estado-wrap">
        <div class="estado-card estado-card--cerrado">
          <div class="estado-icono" aria-hidden="true">
            <i class="fa fa-lock"></i>
          </div>
          <h1 class="estado-titulo">Entrega cerrada</h1>
          <p class="estado-msg">{{ cerradoMsg() }}</p>
          <p class="estado-sub">
            Esta entrega de insumos ya no está activa.<br>
            Contacta a la Alcaldía Local de Kennedy para más información.
          </p>
          <div class="estado-brand">
            <span class="estado-brand__escudo" aria-hidden="true">🏛</span>
            <span>Alcaldía Local de Kennedy</span>
          </div>
        </div>
      </div>
    }

    <!-- ══ ESTADO: ERROR DE CARGA ══ -->
    @if (!cargando() && !cerrado() && errorCarga()) {
      <div class="estado-wrap">
        <div class="estado-card">
          <div class="estado-icono" aria-hidden="true">
            <i class="fa fa-exclamation-triangle"></i>
          </div>
          <h1 class="estado-titulo">Error al cargar</h1>
          <p class="estado-msg">{{ errorCarga() }}</p>
          <button class="btn-brand btn-lg" (click)="cargarCatalogos()">
            <i class="fa fa-refresh" aria-hidden="true"></i> Reintentar
          </button>
        </div>
      </div>
    }

    <!-- ══ ESTADO: ÉXITO ══ -->
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
          <h1 class="exito-titulo">¡Entrega registrada!</h1>
          <p class="exito-desc">Los insumos recibidos fueron registrados exitosamente.</p>
          @if (exitoId()) {
            <div class="exito-num">
              <span class="exito-num__label">Número de registro</span>
              <span class="exito-num__val"># {{ exitoId() }}</span>
            </div>
          }
          <p class="exito-footer">
            Guarda este número como constancia de la entrega.
            El equipo de la Alcaldía Local de Kennedy conserva el registro.
          </p>
          <div class="estado-brand">
            <span class="estado-brand__escudo" aria-hidden="true">🏛</span>
            <span>Alcaldía Local de Kennedy · Entrega de Insumos</span>
          </div>
        </div>
      </div>
    }

    <!-- ══ FORMULARIO PRINCIPAL ══ -->
    @if (!cargando() && !cerrado() && !errorCarga() && !exito() && catalogos()) {

      <!-- Banner institucional -->
      <header class="form-header" role="banner">
        <div class="form-banner">
          <div class="form-banner__left">
            <div class="form-banner__escudo" aria-hidden="true">🏛</div>
            <div>
              <p class="form-banner__institucion">Alcaldía Local de Kennedy</p>
              <h1 class="form-banner__titulo">Entrega de Insumos</h1>
              <p class="form-banner__sub">Registro de beneficiarios</p>
            </div>
          </div>
          <div class="form-banner__badge" aria-hidden="true">
            <i class="fa fa-cube"></i>
          </div>
        </div>
        <div class="form-header__evento">
          <i class="fa fa-calendar" aria-hidden="true"></i>
          <span>{{ catalogos()!.evento.nombre }}</span>
          @if (catalogos()!.evento.fecha_fin) {
            <span class="form-header__fecha">· Cierre: {{ catalogos()!.evento.fecha_fin }}</span>
          }
        </div>
      </header>

      <!-- Errores del servidor -->
      @if (erroresServidor().length > 0) {
        <div class="server-errors" role="alert">
          <i class="fa fa-exclamation-circle" aria-hidden="true"></i>
          <div>
            <strong>Corrige los siguientes errores antes de enviar:</strong>
            <ul>
              @for (err of erroresServidor(); track err) {
                <li>{{ err }}</li>
              }
            </ul>
          </div>
        </div>
      }

      <!-- Acordeón de secciones -->
      <main class="form-main" role="main">

        <!-- ══ SECCIÓN 1: IDENTIFICACIÓN ══ -->
        <div class="seccion" [class.seccion--abierta]="seccionAbierta('identificacion')">
          <button type="button"
                  class="seccion__header"
                  (click)="toggleSeccion('identificacion')"
                  [attr.aria-expanded]="seccionAbierta('identificacion')">
            <span class="seccion__icono" aria-hidden="true"><i class="fa fa-id-card"></i></span>
            <span class="seccion__titulo">Identificación</span>
            <span class="seccion__chevron" aria-hidden="true">
              <i class="fa fa-chevron-down"></i>
            </span>
          </button>
          @if (seccionAbierta('identificacion')) {
            <div class="seccion__body">
              <p class="seccion__hint">
                Ingresa tu número de documento — si ya estás registrado en el sistema,
                tus datos se cargarán automáticamente.
              </p>

              <div class="field-row">
                <div class="field field--required">
                  <label class="field__label" for="tipo_doc">Tipo de documento</label>
                  <select id="tipo_doc" class="field__select"
                          [(ngModel)]="form.tipo_doc" required>
                    <option value="">Selecciona…</option>
                    @for (t of catalogos()!.tipos_documento; track t.value) {
                      <option [value]="t.value">{{ t.label }}</option>
                    }
                  </select>
                  @if (fieldError('tipo_doc')) {
                    <p class="field__error" role="alert">{{ fieldError('tipo_doc') }}</p>
                  }
                </div>

                <div class="field field--required">
                  <label class="field__label" for="numero_documento">Número de documento</label>
                  <div class="field__input-wrap">
                    <input id="numero_documento" type="text" class="field__input"
                           [(ngModel)]="form.numero_documento"
                           (blur)="autollenar()"
                           inputmode="numeric"
                           minlength="5" maxlength="15"
                           required
                           placeholder="12345678">
                    @if (autollenadoStatus() === 'cargando') {
                      <span class="field__spinner" aria-hidden="true"></span>
                    }
                  </div>
                  @if (autollenadoStatus() === 'ok') {
                    <p class="field__status field__status--ok" role="status" aria-live="polite">
                      <i class="fa fa-check" aria-hidden="true"></i>
                      Datos cargados desde el sistema.
                    </p>
                  }
                  @if (autollenadoStatus() === 'nuevo') {
                    <p class="field__status" role="status" aria-live="polite">
                      <i class="fa fa-info-circle" aria-hidden="true"></i>
                      Persona nueva — completa los datos.
                    </p>
                  }
                  @if (fieldError('numero_documento')) {
                    <p class="field__error" role="alert">{{ fieldError('numero_documento') }}</p>
                  }
                </div>
              </div>

              <div class="field-row">
                <div class="field field--required">
                  <label class="field__label" for="nombre1">Primer nombre</label>
                  <input id="nombre1" type="text" class="field__input"
                         [(ngModel)]="form.nombre1"
                         autocomplete="given-name"
                         required maxlength="50"
                         placeholder="Juan">
                  @if (fieldError('nombre1')) {
                    <p class="field__error" role="alert">{{ fieldError('nombre1') }}</p>
                  }
                </div>
                <div class="field">
                  <label class="field__label" for="nombre2">
                    Segundo nombre
                    <span class="field__optional">opcional</span>
                  </label>
                  <input id="nombre2" type="text" class="field__input"
                         [(ngModel)]="form.nombre2"
                         autocomplete="additional-name"
                         maxlength="50"
                         placeholder="Carlos">
                </div>
              </div>

              <div class="field-row">
                <div class="field field--required">
                  <label class="field__label" for="apellido1">Primer apellido</label>
                  <input id="apellido1" type="text" class="field__input"
                         [(ngModel)]="form.apellido1"
                         autocomplete="family-name"
                         required maxlength="50"
                         placeholder="García">
                  @if (fieldError('apellido1')) {
                    <p class="field__error" role="alert">{{ fieldError('apellido1') }}</p>
                  }
                </div>
                <div class="field">
                  <label class="field__label" for="apellido2">
                    Segundo apellido
                    <span class="field__optional">opcional</span>
                  </label>
                  <input id="apellido2" type="text" class="field__input"
                         [(ngModel)]="form.apellido2"
                         maxlength="50"
                         placeholder="López">
                </div>
              </div>

              <div class="field-row">
                <div class="field">
                  <label class="field__label" for="telefono">
                    Teléfono
                    <span class="field__optional">opcional</span>
                  </label>
                  <input id="telefono" type="tel" class="field__input"
                         [(ngModel)]="form.telefono"
                         autocomplete="tel"
                         placeholder="3001234567">
                  @if (fieldError('telefono')) {
                    <p class="field__error" role="alert">{{ fieldError('telefono') }}</p>
                  }
                </div>
                <div class="field">
                  <label class="field__label" for="correo">
                    Correo electrónico
                    <span class="field__optional">opcional</span>
                  </label>
                  <input id="correo" type="email" class="field__input"
                         [(ngModel)]="form.correo"
                         autocomplete="email"
                         placeholder="correo@ejemplo.com">
                  @if (fieldError('correo')) {
                    <p class="field__error" role="alert">{{ fieldError('correo') }}</p>
                  }
                </div>
              </div>

              <div class="field">
                <label class="field__label" for="direccion">
                  Dirección
                  <span class="field__optional">opcional</span>
                </label>
                <textarea id="direccion" class="field__textarea"
                          [(ngModel)]="form.direccion"
                          rows="2"
                          placeholder="Calle 40 # 70-15, Apto 301">
                </textarea>
              </div>

              <div class="field-row">
                <div class="field">
                  <label class="field__label" for="upl">
                    UPL
                    <span class="field__optional">opcional</span>
                  </label>
                  <select id="upl" class="field__select" [(ngModel)]="form.upl">
                    <option value="">Selecciona UPL…</option>
                    @for (u of catalogos()!.upls; track u.value) {
                      <option [value]="u.value">{{ u.label }}</option>
                    }
                  </select>
                </div>
                <div class="field">
                  <label class="field__label" for="barrio">
                    Barrio
                    <span class="field__optional">opcional</span>
                  </label>
                  <select id="barrio" class="field__select" [(ngModel)]="form.barrio">
                    <option value="">Selecciona barrio…</option>
                    @for (b of catalogos()!.barrios; track b.value) {
                      <option [value]="b.value">{{ b.label }}</option>
                    }
                  </select>
                </div>
              </div>
            </div>
          }
        </div>

        <!-- ══ SECCIÓN 2: INSUMOS RECIBIDOS ══ -->
        <div class="seccion" [class.seccion--abierta]="seccionAbierta('insumos')">
          <button type="button"
                  class="seccion__header"
                  (click)="toggleSeccion('insumos')"
                  [attr.aria-expanded]="seccionAbierta('insumos')">
            <span class="seccion__icono" aria-hidden="true"><i class="fa fa-cube"></i></span>
            <span class="seccion__titulo">Insumos recibidos</span>
            @if (totalInsumosSeleccionados() > 0) {
              <span class="seccion__badge" aria-live="polite">
                {{ totalInsumosSeleccionados() }} seleccionado{{ totalInsumosSeleccionados() !== 1 ? 's' : '' }}
              </span>
            }
            <span class="seccion__chevron" aria-hidden="true">
              <i class="fa fa-chevron-down"></i>
            </span>
          </button>
          @if (seccionAbierta('insumos')) {
            <div class="seccion__body">
              <p class="seccion__hint">
                Indica los insumos que recibiste y la cantidad de cada uno.
                <strong>Debes seleccionar al menos 1 insumo con cantidad ≥ 1.</strong>
              </p>

              <!-- Grupos de insumos por categoría -->
              @for (cat of categoriasOrdenadas(); track cat) {
                <div class="insumo-grupo">
                  <div class="insumo-grupo__header">
                    <i [class]="iconoCategoria(cat)" aria-hidden="true"></i>
                    <span>{{ etiquetaCategoria(cat) }}</span>
                  </div>
                  <div class="insumo-lista">
                    @for (insumo of insumosPorCategoria(cat); track insumo.codigo) {
                      <div class="insumo-item"
                           [class.insumo-item--activo]="insumo.cantidad > 0">
                        <div class="insumo-item__info">
                          <span class="insumo-item__nombre">{{ insumo.nombre }}</span>
                        </div>
                        <div class="insumo-item__stepper" role="group"
                             [attr.aria-label]="'Cantidad de ' + insumo.nombre">
                          <button type="button"
                                  class="stepper-btn stepper-btn--dec"
                                  (click)="decrementar(insumo)"
                                  [disabled]="insumo.cantidad === 0"
                                  [attr.aria-label]="'Disminuir cantidad de ' + insumo.nombre">
                            <i class="fa fa-minus" aria-hidden="true"></i>
                          </button>
                          <span class="stepper-valor"
                                [class.stepper-valor--activo]="insumo.cantidad > 0"
                                aria-live="polite">{{ insumo.cantidad }}</span>
                          <button type="button"
                                  class="stepper-btn stepper-btn--inc"
                                  (click)="incrementar(insumo)"
                                  [attr.aria-label]="'Aumentar cantidad de ' + insumo.nombre">
                            <i class="fa fa-plus" aria-hidden="true"></i>
                          </button>
                        </div>
                      </div>
                    }
                  </div>
                </div>
              }

              <!-- Resumen -->
              @if (totalInsumosSeleccionados() > 0) {
                <div class="insumos-resumen" role="status" aria-live="polite">
                  <i class="fa fa-check-circle" aria-hidden="true"></i>
                  <span>
                    <strong>{{ totalInsumosSeleccionados() }}</strong>
                    tipo{{ totalInsumosSeleccionados() !== 1 ? 's' : '' }} de insumo —
                    <strong>{{ totalUnidadesSeleccionadas() }}</strong>
                    unidad{{ totalUnidadesSeleccionadas() !== 1 ? 'es' : '' }} en total
                  </span>
                </div>
              }

              @if (insumoError() && seccionConError('insumos')) {
                <p class="field__error" role="alert">
                  <i class="fa fa-warning" aria-hidden="true"></i>
                  {{ insumoError() }}
                </p>
              }
              @if (fieldError('implementos')) {
                <p class="field__error" role="alert">{{ fieldError('implementos') }}</p>
              }
            </div>
          }
        </div>

        <!-- ══ SECCIÓN 3: FIRMA ══ -->
        <div class="seccion" [class.seccion--abierta]="seccionAbierta('firma')">
          <button type="button"
                  class="seccion__header"
                  (click)="toggleSeccion('firma')"
                  [attr.aria-expanded]="seccionAbierta('firma')">
            <span class="seccion__icono" aria-hidden="true"><i class="fa fa-pencil"></i></span>
            <span class="seccion__titulo">Firma</span>
            <span class="seccion__badge--req" aria-hidden="true">Requerida</span>
            <span class="seccion__chevron" aria-hidden="true">
              <i class="fa fa-chevron-down"></i>
            </span>
          </button>
          @if (seccionAbierta('firma')) {
            <div class="seccion__body">
              <p class="seccion__hint">
                Toma una foto de tu firma para confirmar la recepción de los insumos.
                La imagen se guarda cifrada y solo el organizador puede verla.
              </p>

              @if (!firmaPreview()) {
                <label for="firma_imagen"
                       class="firma-btn"
                       [class.firma-btn--error]="firmaError()">
                  <i class="fa fa-camera firma-btn__icono" aria-hidden="true"></i>
                  <span class="firma-btn__texto">📸 Tomar foto de la firma</span>
                  <span class="firma-btn__sub">Se abrirá la cámara de tu celular</span>
                </label>
              } @else {
                <div class="firma-preview">
                  <img [src]="firmaPreview()!" alt="Vista previa de la firma"
                       class="firma-preview__img">
                  <div class="firma-preview__meta">
                    <span class="firma-preview__nombre">
                      <i class="fa fa-image" aria-hidden="true"></i>
                      {{ firmaNombre() }}
                    </span>
                    <button type="button"
                            class="btn-outline-sm"
                            (click)="quitarFirma()">
                      <i class="fa fa-times" aria-hidden="true"></i> Quitar
                    </button>
                  </div>
                </div>
                <label for="firma_imagen" class="firma-cambiar">
                  <i class="fa fa-camera" aria-hidden="true"></i> Cambiar foto
                </label>
              }

              <input id="firma_imagen"
                     type="file"
                     accept="image/*"
                     capture="environment"
                     class="firma-input-oculto"
                     (change)="onFirmaChange($event)"
                     aria-label="Seleccionar imagen de firma">

              @if (firmaError()) {
                <p class="field__error" role="alert">
                  <i class="fa fa-warning" aria-hidden="true"></i>
                  {{ firmaError() }}
                </p>
              }
              @if (fieldError('firma_imagen')) {
                <p class="field__error" role="alert">{{ fieldError('firma_imagen') }}</p>
              }

              <div class="firma-aviso">
                <i class="fa fa-shield" aria-hidden="true"></i>
                Al enviar confirmas que los insumos listados fueron recibidos.
                Este registro quedará guardado con fecha y hora.
              </div>
            </div>
          }
        </div>

        <!-- Botón de envío -->
        <div class="form-submit-wrap">
          <button type="button"
                  class="btn-brand btn-submit"
                  (click)="enviar()"
                  [disabled]="enviando()">
            @if (enviando()) {
              <span class="spinner-inline" aria-hidden="true"></span>
              Enviando…
            } @else {
              <i class="fa fa-paper-plane" aria-hidden="true"></i>
              Registrar entrega
            }
          </button>
          <p class="form-submit__hint">
            <i class="fa fa-lock" aria-hidden="true"></i>
            Todos los campos requeridos deben estar completos.
          </p>
        </div>

      </main>
    }
  `,
  styles: [`
    @use '../../../styles/tokens' as *;

    // ── Variables locales ──────────────────────────────────────────────
    $brand-rojo-oscuro:  #B50015;
    $brand-rojo:         #D6001C;
    $brand-rojo-claro:   #FF1F38;
    $brand-amarillo:     #FFC72C;
    $brand-gradient:     linear-gradient(135deg, #{$brand-rojo-oscuro} 0%, #{$brand-rojo} 60%, #{$brand-rojo-claro} 100%);
    $brand-gradient-sub: linear-gradient(135deg, rgba(#B50015, 0.08) 0%, rgba(#D6001C, 0.04) 100%);

    // ── Layout base ────────────────────────────────────────────────────
    :host {
      display: block;
      background: $color-bg-subtle;
      min-height: 100vh;
      font-family: $font-family-base;
    }

    // ── Estados de carga / error / éxito ──────────────────────────────
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
      border-top-color: $brand-rojo;
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

      &--cerrado { border-top: 6px solid $brand-rojo; }
      &--exito   { border-top: 6px solid $color-success; }
    }

    .estado-icono {
      font-size: 3.5rem;
      margin-bottom: $space-4;
      color: $brand-rojo;
    }

    .estado-titulo {
      font-size: $font-size-2xl;
      font-weight: $font-weight-bold;
      color: $color-text;
      margin: 0 0 $space-3;
    }

    .estado-msg {
      font-size: $font-size-md;
      color: $color-text;
      font-weight: $font-weight-semibold;
      margin-bottom: $space-3;
    }

    .estado-sub {
      color: $color-text-muted;
      font-size: $font-size-sm;
      line-height: $line-height-relaxed;
      margin-bottom: $space-6;
    }

    .estado-brand {
      display: inline-flex;
      align-items: center;
      gap: $space-2;
      font-size: $font-size-xs;
      color: $color-text-muted;
      font-weight: $font-weight-semibold;
      letter-spacing: 0.03em;

      &__escudo { font-size: 1.1rem; }
    }

    // ── Éxito ─────────────────────────────────────────────────────────
    .exito-check {
      width: 80px;
      height: 80px;
      margin: 0 auto $space-5;

      svg { width: 100%; height: 100%; }
    }

    .exito-titulo {
      font-size: $font-size-2xl;
      font-weight: $font-weight-bold;
      color: $color-success;
      margin: 0 0 $space-3;
    }

    .exito-desc {
      color: $color-text;
      font-size: $font-size-md;
      margin-bottom: $space-5;
    }

    .exito-num {
      display: inline-flex;
      flex-direction: column;
      gap: $space-1;
      background: $brand-gradient-sub;
      border: 2px solid rgba($brand-rojo, 0.2);
      border-radius: $radius-xl;
      padding: $space-4 $space-8;
      margin-bottom: $space-5;
    }

    .exito-num__label {
      font-size: $font-size-xs;
      text-transform: uppercase;
      letter-spacing: 0.06em;
      color: $color-text-muted;
      font-weight: $font-weight-semibold;
    }

    .exito-num__val {
      font-size: $font-size-2xl;
      font-weight: $font-weight-bold;
      color: $brand-rojo;
    }

    .exito-footer {
      color: $color-text-muted;
      font-size: $font-size-sm;
      margin: 0 0 $space-6;
      line-height: $line-height-relaxed;
    }

    // ── Encabezado del formulario ─────────────────────────────────────
    .form-header {
      background: $color-bg;
      box-shadow: $shadow-sm;
      position: sticky;
      top: 0;
      z-index: $z-sticky;
    }

    .form-banner {
      display: flex;
      align-items: center;
      justify-content: space-between;
      background: $brand-gradient;
      color: $color-text-inverse;
      padding: $space-5;
      gap: $space-3;
    }

    .form-banner__left {
      display: flex;
      align-items: center;
      gap: $space-3;
    }

    .form-banner__escudo {
      font-size: 2.2rem;
      flex-shrink: 0;
    }

    .form-banner__institucion {
      font-size: $font-size-xs;
      opacity: 0.85;
      letter-spacing: 0.04em;
      text-transform: uppercase;
      margin: 0 0 $space-1;
    }

    .form-banner__titulo {
      font-size: $font-size-lg;
      font-weight: $font-weight-bold;
      margin: 0;
      line-height: $line-height-tight;

      @media (min-width: #{$bp-md}) { font-size: $font-size-xl; }
    }

    .form-banner__sub {
      font-size: $font-size-xs;
      opacity: 0.85;
      margin: $space-1 0 0;
    }

    .form-banner__badge {
      font-size: 2.5rem;
      opacity: 0.25;
      flex-shrink: 0;

      @media (max-width: 400px) { display: none; }
    }

    .form-header__evento {
      display: flex;
      align-items: center;
      gap: $space-2;
      padding: $space-2 $space-5;
      font-size: $font-size-xs;
      color: $color-text-muted;
      background: $color-bg;
      border-bottom: 1px solid $color-border;
    }

    .form-header__fecha {
      color: $brand-rojo;
      font-weight: $font-weight-semibold;
    }

    // ── Errores del servidor ──────────────────────────────────────────
    .server-errors {
      display: flex;
      align-items: flex-start;
      gap: $space-3;
      background: $color-danger-bg;
      border-left: 4px solid $color-danger;
      border-radius: $radius-md;
      padding: $space-4;
      margin: $space-4 $space-4 0;
      color: $color-danger;
      font-size: $font-size-sm;

      i { margin-top: 2px; flex-shrink: 0; }

      ul { margin: $space-2 0 0; padding-left: $space-5; }
    }

    // ── Layout principal ──────────────────────────────────────────────
    .form-main {
      max-width: 100%;
      margin: 0 auto;
      padding: $space-4;

      @media (min-width: #{$bp-md}) {
        max-width: 700px;
        padding: $space-6 $space-4;
      }
    }

    // ── Acordeón ─────────────────────────────────────────────────────
    .seccion {
      background: $color-bg;
      border-radius: $radius-xl;
      box-shadow: $shadow-sm;
      margin-bottom: $space-3;
      overflow: hidden;
      border: 1.5px solid $color-border;
      transition: border-color $transition-base, box-shadow $transition-base;

      &--abierta {
        border-color: rgba($brand-rojo, 0.3);
        box-shadow: 0 0 0 1px rgba($brand-rojo, 0.08), $shadow-md;
      }
    }

    .seccion__header {
      display: flex;
      align-items: center;
      gap: $space-3;
      width: 100%;
      padding: $space-4 $space-5;
      background: none;
      border: none;
      cursor: pointer;
      text-align: left;
      font-family: $font-family-base;
      transition: background $transition-base;

      &:hover { background: $color-bg-subtle; }

      &:focus-visible {
        outline: $focus-ring;
        outline-offset: $focus-ring-offset;
      }
    }

    .seccion__icono {
      display: flex;
      align-items: center;
      justify-content: center;
      width: 36px;
      height: 36px;
      min-width: 36px;
      background: $brand-gradient-sub;
      border-radius: $radius-md;
      color: $brand-rojo;
      font-size: $font-size-base;

      .seccion--abierta & {
        background: $brand-rojo;
        color: $color-text-inverse;
      }
    }

    .seccion__titulo {
      flex: 1;
      font-size: $font-size-base;
      font-weight: $font-weight-semibold;
      color: $color-text;
    }

    .seccion__badge {
      font-size: $font-size-xs;
      font-weight: $font-weight-semibold;
      color: $brand-rojo;
      background: rgba($brand-rojo, 0.1);
      padding: $space-1 $space-2;
      border-radius: $radius-sm;
      letter-spacing: 0.03em;
    }

    .seccion__badge--req {
      font-size: $font-size-xs;
      font-weight: $font-weight-semibold;
      color: $brand-rojo;
      background: rgba($brand-rojo, 0.08);
      padding: $space-1 $space-2;
      border-radius: $radius-sm;
      letter-spacing: 0.03em;
    }

    .seccion__chevron {
      color: $color-text-muted;
      transition: transform $transition-base;
      font-size: $font-size-sm;

      .seccion--abierta & {
        transform: rotate(180deg);
        color: $brand-rojo;
      }

      @media (prefers-reduced-motion: reduce) { transition: none; }
    }

    .seccion__body {
      padding: $space-2 $space-5 $space-6;
      border-top: 1px solid $color-border;

      @media (prefers-reduced-motion: no-preference) {
        animation: seccion-open 0.2s ease-out both;
      }
    }

    @keyframes seccion-open {
      from { opacity: 0; transform: translateY(-6px); }
      to   { opacity: 1; transform: translateY(0); }
    }

    .seccion__hint {
      font-size: $font-size-sm;
      color: $color-text-muted;
      margin: $space-4 0 $space-5;
      line-height: $line-height-relaxed;
    }

    // ── Campos de formulario ──────────────────────────────────────────
    .field {
      margin-bottom: $space-4;

      &--required .field__label::after {
        content: ' *';
        color: $brand-rojo;
        font-weight: $font-weight-bold;
      }
    }

    .field__label {
      display: block;
      font-size: $font-size-sm;
      font-weight: $font-weight-semibold;
      color: $color-text;
      margin-bottom: $space-2;
    }

    .field__optional {
      font-size: $font-size-xs;
      font-weight: $font-weight-regular;
      color: $color-text-muted;
      margin-left: $space-1;
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

      &:focus {
        outline: none;
        border-color: $brand-rojo;
        box-shadow: 0 0 0 3px rgba($brand-rojo, 0.15);
      }

      &:focus-visible {
        outline: $focus-ring;
        outline-offset: $focus-ring-offset;
      }
    }

    .field__textarea {
      min-height: 72px;
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

    .field__status {
      font-size: $font-size-xs;
      margin: $space-1 0 0;
      color: $color-info;
      display: flex;
      align-items: center;
      gap: $space-1;

      &--ok { color: $color-success; }
    }

    .field__input-wrap {
      position: relative;

      .field__input { padding-right: 2.5rem; }
    }

    .field__spinner {
      position: absolute;
      right: $space-3;
      top: 50%;
      transform: translateY(-50%);
      width: 16px;
      height: 16px;
      border: 2px solid $color-border;
      border-top-color: $brand-rojo;
      border-radius: 50%;
      animation: spin 0.8s linear infinite;

      @media (prefers-reduced-motion: reduce) { animation: none; }
    }

    .field-row {
      display: grid;
      grid-template-columns: 1fr;
      gap: $space-3;

      @media (min-width: #{$bp-sm}) { grid-template-columns: 1fr 1fr; }
    }

    // ── Insumos — grupos por categoría ────────────────────────────────
    .insumo-grupo {
      margin-bottom: $space-5;

      &:last-child { margin-bottom: 0; }
    }

    .insumo-grupo__header {
      display: flex;
      align-items: center;
      gap: $space-2;
      font-size: $font-size-sm;
      font-weight: $font-weight-bold;
      color: $brand-rojo;
      text-transform: uppercase;
      letter-spacing: 0.06em;
      padding: $space-2 0 $space-3;
      border-bottom: 2px solid rgba($brand-rojo, 0.15);
      margin-bottom: $space-3;

      i { font-size: 1rem; }
    }

    .insumo-lista {
      display: flex;
      flex-direction: column;
      gap: $space-2;
    }

    .insumo-item {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: $space-4;
      padding: $space-3 $space-4;
      background: $color-bg-subtle;
      border: 1.5px solid $color-border;
      border-radius: $radius-lg;
      transition: border-color $transition-base, background $transition-base, box-shadow $transition-base;

      &--activo {
        border-color: rgba($brand-rojo, 0.4);
        background: rgba($brand-rojo, 0.03);
        box-shadow: 0 0 0 1px rgba($brand-rojo, 0.07);
      }
    }

    .insumo-item__info {
      flex: 1;
      min-width: 0;
    }

    .insumo-item__nombre {
      display: block;
      font-size: $font-size-sm;
      font-weight: $font-weight-medium;
      color: $color-text;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }

    // ── Stepper ───────────────────────────────────────────────────────
    .insumo-item__stepper {
      display: flex;
      align-items: center;
      gap: $space-2;
      flex-shrink: 0;
    }

    .stepper-btn {
      display: flex;
      align-items: center;
      justify-content: center;
      width: 36px;
      height: 36px;
      min-width: 36px;
      border-radius: $radius-md;
      border: 1.5px solid $color-border-strong;
      background: $color-bg;
      color: $color-text-muted;
      font-size: $font-size-xs;
      cursor: pointer;
      transition: background $transition-base, border-color $transition-base, color $transition-base;

      &:focus-visible {
        outline: $focus-ring;
        outline-offset: $focus-ring-offset;
      }

      &:disabled {
        opacity: 0.35;
        cursor: not-allowed;
      }

      &--inc {
        border-color: $brand-rojo;
        color: $brand-rojo;
        background: rgba($brand-rojo, 0.06);

        &:hover:not(:disabled) {
          background: $brand-rojo;
          color: $color-text-inverse;
        }
      }

      &--dec:hover:not(:disabled) {
        border-color: $color-danger;
        color: $color-danger;
        background: $color-danger-bg;
      }
    }

    .stepper-valor {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      min-width: 32px;
      font-size: $font-size-base;
      font-weight: $font-weight-bold;
      color: $color-text-muted;
      text-align: center;
      transition: color $transition-base;

      &--activo {
        color: $brand-rojo;
        font-size: $font-size-lg;
      }
    }

    // ── Resumen de insumos ────────────────────────────────────────────
    .insumos-resumen {
      display: flex;
      align-items: center;
      gap: $space-2;
      background: rgba($color-success, 0.08);
      border: 1px solid rgba($color-success, 0.25);
      border-radius: $radius-lg;
      padding: $space-3 $space-4;
      margin-top: $space-4;
      font-size: $font-size-sm;
      color: $color-success;

      i { flex-shrink: 0; font-size: 1.1rem; }
    }

    // ── Firma ─────────────────────────────────────────────────────────
    .firma-input-oculto {
      position: absolute;
      left: -9999px;
      width: 1px;
      height: 1px;
      opacity: 0;
    }

    .firma-btn {
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      gap: $space-3;
      width: 100%;
      min-height: 100px;
      padding: $space-6;
      background: $brand-gradient;
      color: $color-text-inverse;
      border: 3px dashed rgba(255, 255, 255, 0.35);
      border-radius: $radius-xl;
      cursor: pointer;
      text-align: center;
      transition: filter $transition-base;

      &:hover { filter: brightness(0.93); }

      &:focus-within {
        outline: $focus-ring;
        outline-offset: $focus-ring-offset;
      }

      &--error {
        border-color: $color-danger;
        background: $color-danger-bg;
        color: $color-danger;
      }
    }

    .firma-btn__icono { font-size: 2.5rem; }

    .firma-btn__texto {
      font-size: $font-size-md;
      font-weight: $font-weight-bold;
    }

    .firma-btn__sub {
      font-size: $font-size-xs;
      opacity: 0.85;
    }

    .firma-preview {
      border: 1.5px solid $color-border;
      border-radius: $radius-lg;
      overflow: hidden;
      background: $color-bg-subtle;
    }

    .firma-preview__img {
      display: block;
      max-width: 100%;
      max-height: 240px;
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

    .firma-preview__nombre {
      font-size: $font-size-xs;
      color: $color-text-muted;
      word-break: break-all;
      display: flex;
      align-items: center;
      gap: $space-1;
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

    .firma-aviso {
      display: flex;
      align-items: flex-start;
      gap: $space-2;
      background: $color-bg-muted;
      border: 1px solid $color-border;
      border-radius: $radius-lg;
      padding: $space-3 $space-4;
      font-size: $font-size-xs;
      color: $color-text-muted;
      line-height: $line-height-relaxed;
      margin-top: $space-5;

      i { flex-shrink: 0; margin-top: 2px; }
    }

    // ── Botón de envío ────────────────────────────────────────────────
    .form-submit-wrap {
      text-align: center;
      padding: $space-6 0 $space-10;
    }

    .btn-brand {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      gap: $space-2;
      min-height: $touch-target-min;
      padding: $space-3 $space-6;
      background: $brand-gradient;
      color: $color-text-inverse;
      border: none;
      border-radius: $radius-lg;
      font-size: $font-size-base;
      font-family: $font-family-base;
      font-weight: $font-weight-semibold;
      cursor: pointer;
      transition: filter $transition-base, box-shadow $transition-base;
      text-decoration: none;
      box-shadow: 0 4px 14px rgba($brand-rojo, 0.35);

      &:hover {
        filter: brightness(0.92);
        box-shadow: 0 6px 20px rgba($brand-rojo, 0.45);
      }

      &:focus-visible {
        outline: $focus-ring;
        outline-offset: $focus-ring-offset;
      }

      &[disabled] {
        opacity: 0.65;
        cursor: not-allowed;
        box-shadow: none;
      }

      &-lg { font-size: $font-size-md; padding: $space-4 $space-8; }
    }

    .btn-submit {
      width: 100%;
      max-width: 400px;
      font-size: $font-size-md;
      padding: $space-4 $space-8;
      border-radius: $radius-xl;
    }

    .btn-outline-sm {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      gap: $space-1;
      min-height: 36px;
      padding: $space-1 $space-3;
      font-size: $font-size-sm;
      font-family: $font-family-base;
      font-weight: $font-weight-semibold;
      background: $color-bg;
      color: $brand-rojo;
      border: 1.5px solid $brand-rojo;
      border-radius: $radius-lg;
      cursor: pointer;
      transition: background $transition-base;

      &:hover { background: rgba($brand-rojo, 0.06); }

      &:focus-visible {
        outline: $focus-ring;
        outline-offset: $focus-ring-offset;
      }
    }

    .form-submit__hint {
      font-size: $font-size-xs;
      color: $color-text-muted;
      margin: $space-3 0 0;
      display: flex;
      align-items: center;
      justify-content: center;
      gap: $space-2;
    }

    .spinner-inline {
      display: inline-block;
      width: 16px;
      height: 16px;
      border: 2px solid rgba(255, 255, 255, 0.4);
      border-top-color: $color-text-inverse;
      border-radius: 50%;
      animation: spin 0.7s linear infinite;

      @media (prefers-reduced-motion: reduce) { animation: none; }
    }

    @keyframes spin {
      to { transform: rotate(360deg); }
    }
  `],
})
export class EntregasPublicoComponent implements OnInit {
  private route = inject(ActivatedRoute);
  private http  = inject(HttpClient);
  private cfg   = inject(ConfigService);

  // ── Señales de estado ──────────────────────────────────────────────
  cargando   = signal(true);
  errorCarga = signal('');
  cerrado    = signal(false);
  cerradoMsg = signal('');
  exito      = signal(false);
  exitoId    = signal<number | null>(null);
  enviando   = signal(false);

  catalogos = signal<EntregasCatalogos | null>(null);

  // Insumos con cantidad (lista mutable derivada del catálogo)
  insumosConCantidad = signal<InsumoConCantidad[]>([]);

  // Errores campo a campo (400 del servidor)
  private erroresCampo = signal<Record<string, string[]>>({});
  erroresServidor      = signal<string[]>([]);

  // Firma
  firmaPreview = signal<string | null>(null);
  firmaNombre  = signal('');
  firmaError   = signal('');

  // Insumo error (validación cliente)
  insumoError = signal('');

  // Autollenado
  autollenadoStatus = signal<'ok' | 'nuevo' | 'cargando' | null>(null);

  // Secciones abiertas
  private seccionesAbiertas = signal<Set<SeccionId>>(new Set(['identificacion']));

  // Secciones que tuvieron error al intentar enviar
  private seccionesConError = new Set<SeccionId>();

  // ── Modelo del formulario ─────────────────────────────────────────
  form = {
    tipo_doc:         '',
    numero_documento: '',
    nombre1:          '',
    nombre2:          '',
    apellido1:        '',
    apellido2:        '',
    telefono:         '',
    correo:           '',
    direccion:        '',
    upl:              '',
    barrio:           '',
    firma_imagen:     null as File | null,
  };

  // ── Ciclo de vida ─────────────────────────────────────────────────
  ngOnInit(): void {
    this.cargarCatalogos();
  }

  private eventoId(): number {
    return Number(this.route.snapshot.paramMap.get('eventoId') ?? '0');
  }

  // ── Carga de catálogos ────────────────────────────────────────────
  cargarCatalogos(): void {
    this.cargando.set(true);
    this.errorCarga.set('');
    this.cerrado.set(false);

    const url = this.cfg.url(
      `/entregas/api/publico/${this.eventoId()}/catalogos/`,
    );

    this.http.get<EntregasCatalogos>(url).subscribe({
      next: (data) => {
        if (!data.evento.abierto) {
          this.cerrado.set(true);
          this.cerradoMsg.set('Esta entrega ya no está activa.');
          this.cargando.set(false);
          return;
        }
        this.catalogos.set(data);
        // Inicializa lista de insumos con cantidad 0
        this.insumosConCantidad.set(
          data.insumos.map((i) => ({
            codigo:    i.value,
            nombre:    i.label,
            categoria: i.categoria,
            cantidad:  0,
          })),
        );
        this.cargando.set(false);
      },
      error: (err) => {
        this.cargando.set(false);
        if (err.status === 410) {
          this.cerrado.set(true);
          this.cerradoMsg.set(err.error?.detail || 'Esta entrega ya cerró.');
        } else {
          this.errorCarga.set(
            err.error?.detail || 'No se pudo cargar el formulario. Revisa tu conexión.',
          );
        }
      },
    });
  }

  // ── Acordeón ─────────────────────────────────────────────────────
  toggleSeccion(id: SeccionId): void {
    const abiertas = new Set(this.seccionesAbiertas());
    if (abiertas.has(id)) {
      abiertas.delete(id);
    } else {
      abiertas.add(id);
    }
    this.seccionesAbiertas.set(abiertas);
  }

  seccionAbierta(id: SeccionId): boolean {
    return this.seccionesAbiertas().has(id);
  }

  seccionConError(id: SeccionId): boolean {
    return this.seccionesConError.has(id);
  }

  // ── Helpers de insumos ────────────────────────────────────────────
  categoriasOrdenadas(): string[] {
    const orden = ['deportivo', 'tecnologico', 'logistico'];
    const cats  = [...new Set(this.insumosConCantidad().map((i) => i.categoria))];
    return [
      ...orden.filter((c) => cats.includes(c)),
      ...cats.filter((c) => !orden.includes(c)),
    ];
  }

  insumosPorCategoria(cat: string): InsumoConCantidad[] {
    return this.insumosConCantidad().filter((i) => i.categoria === cat);
  }

  iconoCategoria(cat: string): string {
    return ICONO_CATEGORIA[cat] ?? 'fa fa-cube';
  }

  etiquetaCategoria(cat: string): string {
    const etiquetas: Record<string, string> = {
      deportivo:   'Equipamiento deportivo',
      tecnologico: 'Tecnología',
      logistico:   'Logística',
    };
    return etiquetas[cat] ?? cat.charAt(0).toUpperCase() + cat.slice(1);
  }

  incrementar(insumo: InsumoConCantidad): void {
    const lista = this.insumosConCantidad().map((i) =>
      i.codigo === insumo.codigo ? { ...i, cantidad: i.cantidad + 1 } : i,
    );
    this.insumosConCantidad.set(lista);
    if (this.insumoError()) this.insumoError.set('');
  }

  decrementar(insumo: InsumoConCantidad): void {
    if (insumo.cantidad === 0) return;
    const lista = this.insumosConCantidad().map((i) =>
      i.codigo === insumo.codigo ? { ...i, cantidad: i.cantidad - 1 } : i,
    );
    this.insumosConCantidad.set(lista);
  }

  totalInsumosSeleccionados(): number {
    return this.insumosConCantidad().filter((i) => i.cantidad > 0).length;
  }

  totalUnidadesSeleccionadas(): number {
    return this.insumosConCantidad().reduce((acc, i) => acc + i.cantidad, 0);
  }

  // ── Autollenado ───────────────────────────────────────────────────
  autollenar(): void {
    const doc = this.form.numero_documento.trim();
    if (doc.length < 4) { this.autollenadoStatus.set(null); return; }

    this.autollenadoStatus.set('cargando');

    this.http
      .get<PersonaAutollenado>(
        this.cfg.url(`/caracterizacion/api/persona/?doc=${encodeURIComponent(doc)}`),
      )
      .subscribe({
        next: (data) => {
          if (!data.found) {
            this.autollenadoStatus.set('nuevo');
            return;
          }
          if (!this.form.nombre1   && data.nombre1)   this.form.nombre1   = data.nombre1;
          if (!this.form.nombre2   && data.nombre2)    this.form.nombre2   = data.nombre2;
          if (!this.form.apellido1 && data.apellido1)  this.form.apellido1 = data.apellido1;
          if (!this.form.apellido2 && data.apellido2)  this.form.apellido2 = data.apellido2;
          if (!this.form.telefono  && data.telefono)   this.form.telefono  = data.telefono;
          if (!this.form.correo    && data.correo)     this.form.correo    = data.correo;
          if (!this.form.direccion && data.direccion)  this.form.direccion = data.direccion;
          this.autollenadoStatus.set('ok');
        },
        error: () => this.autollenadoStatus.set(null),
      });
  }

  // ── Firma ─────────────────────────────────────────────────────────
  onFirmaChange(event: Event): void {
    const input = event.target as HTMLInputElement;
    const file  = input.files?.[0];
    if (!file) return;

    if (file.size > 2 * 1024 * 1024) {
      this.firmaError.set('La imagen pesa más de 2 MB. Toma otra foto con menor calidad.');
      input.value = '';
      return;
    }

    this.firmaError.set('');
    this.form.firma_imagen = file;
    this.firmaNombre.set(`${file.name} (${Math.round(file.size / 1024)} KB)`);

    const reader = new FileReader();
    reader.onload = (e) => {
      this.firmaPreview.set(e.target?.result as string);
    };
    reader.readAsDataURL(file);
  }

  quitarFirma(): void {
    this.form.firma_imagen = null;
    this.firmaPreview.set(null);
    this.firmaNombre.set('');
    this.firmaError.set('');
  }

  // ── Errores campo ─────────────────────────────────────────────────
  fieldError(campo: string): string {
    const errs = this.erroresCampo()[campo];
    return errs?.length ? errs[0] : '';
  }

  // ── Validación antes de enviar ────────────────────────────────────
  private validar(): boolean {
    this.seccionesConError.clear();
    let ok = true;

    // Identificación — campos requeridos
    if (!this.form.tipo_doc || !this.form.numero_documento.trim() ||
        !this.form.nombre1.trim() || !this.form.apellido1.trim()) {
      this.seccionesConError.add('identificacion');
      ok = false;
    }

    // Insumos — al menos 1 con cantidad >= 1
    if (this.totalInsumosSeleccionados() === 0) {
      this.seccionesConError.add('insumos');
      this.insumoError.set('Debes seleccionar al menos 1 insumo con cantidad mayor a 0.');
      ok = false;
    }

    // Firma — requerida
    if (!this.form.firma_imagen) {
      this.seccionesConError.add('firma');
      ok = false;
    }

    return ok;
  }

  // ── Envío ─────────────────────────────────────────────────────────
  enviar(): void {
    if (!this.validar()) {
      const orden: SeccionId[] = ['identificacion', 'insumos', 'firma'];
      for (const id of orden) {
        if (this.seccionesConError.has(id)) {
          const abiertas = new Set(this.seccionesAbiertas());
          abiertas.add(id);
          this.seccionesAbiertas.set(abiertas);
          break;
        }
      }
      if (this.seccionesConError.has('firma') && !this.form.firma_imagen) {
        this.firmaError.set('La foto de la firma es obligatoria.');
      }
      this.erroresServidor.set(['Completa todos los campos requeridos antes de enviar.']);
      window.scrollTo({ top: 0, behavior: 'smooth' });
      return;
    }

    this.enviando.set(true);
    this.erroresCampo.set({});
    this.erroresServidor.set([]);

    const fd  = this.buildFormData();
    const url = this.cfg.url(
      `/entregas/api/publico/${this.eventoId()}/inscribir/`,
    );

    this.http.post<{ id: number; detail: string }>(url, fd).subscribe({
      next: (resp) => {
        this.enviando.set(false);
        this.exitoId.set(resp.id);
        this.exito.set(true);
        window.scrollTo({ top: 0, behavior: 'smooth' });
      },
      error: (err) => {
        this.enviando.set(false);
        const body = err.error as ApiError | null;

        if (err.status === 410) {
          this.cerrado.set(true);
          this.cerradoMsg.set(body?.detail || 'La entrega cerró mientras completabas el formulario.');
          return;
        }

        if (err.status === 400 && body) {
          if (body.errors) {
            this.erroresCampo.set(body.errors);
            const msgs: string[] = [];
            for (const [campo, errs] of Object.entries(body.errors)) {
              for (const e of errs) msgs.push(`${campo}: ${e}`);
            }
            this.erroresServidor.set(msgs);
            this.abrirSeccionConError(Object.keys(body.errors));
          } else if (body.detail) {
            this.erroresServidor.set([body.detail]);
          }
        } else {
          this.erroresServidor.set([
            body?.detail || 'Error al enviar. Intenta nuevamente.',
          ]);
        }
        window.scrollTo({ top: 0, behavior: 'smooth' });
      },
    });
  }

  private buildFormData(): globalThis.FormData {
    const fd = new globalThis.FormData();
    const f  = this.form;

    const scalars: Array<[string, string]> = [
      ['tipo_doc',         f.tipo_doc],
      ['numero_documento', f.numero_documento],
      ['nombre1',          f.nombre1],
      ['nombre2',          f.nombre2],
      ['apellido1',        f.apellido1],
      ['apellido2',        f.apellido2],
      ['telefono',         f.telefono],
      ['correo',           f.correo],
      ['direccion',        f.direccion],
      ['upl',              f.upl],
      ['barrio',           f.barrio],
    ];

    for (const [k, v] of scalars) {
      if (v !== '') fd.append(k, v);
    }

    // Insumos con cantidad — listas PARALELAS: implementos[i] <-> cantidades[i]
    const seleccionados = this.insumosConCantidad().filter((i) => i.cantidad >= 1);
    for (const insumo of seleccionados) {
      fd.append('implementos', insumo.codigo);
      fd.append('cantidades',  String(insumo.cantidad));
    }

    // Firma
    if (f.firma_imagen) {
      fd.append('firma_imagen', f.firma_imagen, f.firma_imagen.name);
    }

    return fd;
  }

  private abrirSeccionConError(campos: string[]): void {
    const mapCampoSeccion: Record<string, SeccionId> = {
      tipo_doc:         'identificacion',
      numero_documento: 'identificacion',
      nombre1:          'identificacion',
      nombre2:          'identificacion',
      apellido1:        'identificacion',
      apellido2:        'identificacion',
      telefono:         'identificacion',
      correo:           'identificacion',
      direccion:        'identificacion',
      upl:              'identificacion',
      barrio:           'identificacion',
      implementos:      'insumos',
      cantidades:       'insumos',
      firma_imagen:     'firma',
    };

    const orden: SeccionId[] = ['identificacion', 'insumos', 'firma'];
    const conError = new Set(
      campos.map((c) => mapCampoSeccion[c]).filter(Boolean) as SeccionId[],
    );

    const primera = orden.find((s) => conError.has(s));
    if (primera) {
      const abiertas = new Set(this.seccionesAbiertas());
      abiertas.add(primera);
      this.seccionesAbiertas.set(abiertas);
    }
  }
}
