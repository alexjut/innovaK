import { HttpClient } from '@angular/common/http';
import { Component, OnInit, inject, signal } from '@angular/core';
import { ActivatedRoute } from '@angular/router';
import { ConfigService } from '../../core/config/config.service';

// ---------------------------------------------------------------------------
// Contrato GET /api/eventos/<id>/info-terreno/
// ---------------------------------------------------------------------------

interface InfoTerrenoContexto {
  evento: {
    id: number;
    nombre: string;
    fecha_inicio?: string;
    fecha_fin?: string;
    abierto: boolean;
  };
  planeacion: {
    hallazgos?: string | null;
    recorrido?: string | null;
    observaciones?: string | null;
  };
  confirmado: boolean;
  fotos_registradas: number;
}

interface FotoPendiente {
  file: File;
  preview: string;
}

type GpsStatus = 'idle' | 'cargando' | 'ok' | 'error';

@Component({
  standalone: true,
  selector: 'app-info-terreno-publico',
  template: `
    <!-- ══ CARGANDO ══ -->
    @if (cargando()) {
      <div class="loading-wrap" role="status" aria-live="polite">
        <div class="loading-spinner" aria-hidden="true"></div>
        <p>Cargando…</p>
      </div>
    }

    <!-- ══ CERRADO ══ -->
    @if (!cargando() && cerrado()) {
      <div class="estado-wrap">
        <div class="estado-card estado-card--cerrado">
          <div class="estado-icono" aria-hidden="true"><i class="fa fa-lock"></i></div>
          <h1 class="estado-titulo">Visita cerrada</h1>
          <p class="estado-msg">{{ cerradoMsg() }}</p>
          <p class="estado-sub">Esta visita en terreno ya no está activa.</p>
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
          <button class="btn-brand btn-lg" (click)="cargar()">
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
          <h1 class="exito-titulo">¡Llegada confirmada!</h1>
          <p class="exito-desc">
            Se registró tu llegada a terreno con {{ fotosEnviadas() }} foto(s) de evidencia
            y la ubicación GPS.
          </p>
          <div class="exito-coords">
            <i class="fa fa-map-marker" aria-hidden="true"></i>
            {{ latitud() }}, {{ longitud() }}
          </div>
          <div class="estado-brand">
            <span class="estado-brand__escudo" aria-hidden="true">🏛</span>
            <span>Alcaldía Local de Kennedy · Visita en terreno</span>
          </div>
        </div>
      </div>
    }

    <!-- ══ FORMULARIO ══ -->
    @if (!cargando() && !cerrado() && !errorCarga() && !exito() && ctx()) {
      <header class="form-header" role="banner">
        <div class="form-banner">
          <div class="form-banner__left">
            <div class="form-banner__escudo" aria-hidden="true">🏛</div>
            <div>
              <p class="form-banner__institucion">Alcaldía Local de Kennedy</p>
              <h1 class="form-banner__titulo">Confirmar llegada a terreno</h1>
              <p class="form-banner__sub">Evidencia de visita en campo</p>
            </div>
          </div>
          <div class="form-banner__badge" aria-hidden="true"><i class="fa fa-map-pin"></i></div>
        </div>
        <div class="form-header__evento">
          <i class="fa fa-clipboard" aria-hidden="true"></i>
          <span>{{ ctx()!.evento.nombre }}</span>
        </div>
      </header>

      <main class="form-main" role="main">

        @if (ctx()!.confirmado) {
          <div class="aviso aviso--info" role="status">
            <i class="fa fa-info-circle" aria-hidden="true"></i>
            <span>
              Esta visita ya tiene una llegada confirmada
              ({{ ctx()!.fotos_registradas }} foto(s)). Si confirmas de nuevo, se
              actualizará la ubicación y se agregarán las fotos nuevas.
            </span>
          </div>
        }

        @if (planeacionVisible()) {
          <section class="card-plan">
            <h2 class="card-plan__titulo"><i class="fa fa-compass" aria-hidden="true"></i> Planeación de la visita</h2>
            @if (ctx()!.planeacion.recorrido) {
              <div class="card-plan__item"><strong>Recorrido:</strong> {{ ctx()!.planeacion.recorrido }}</div>
            }
            @if (ctx()!.planeacion.hallazgos) {
              <div class="card-plan__item"><strong>Hallazgos esperados:</strong> {{ ctx()!.planeacion.hallazgos }}</div>
            }
            @if (ctx()!.planeacion.observaciones) {
              <div class="card-plan__item"><strong>Observaciones:</strong> {{ ctx()!.planeacion.observaciones }}</div>
            }
          </section>
        }

        @if (errorEnvio()) {
          <div class="aviso aviso--error" role="alert">
            <i class="fa fa-exclamation-circle" aria-hidden="true"></i>
            <span>{{ errorEnvio() }}</span>
          </div>
        }

        <!-- PASO 1: GPS -->
        <section class="paso" [class.paso--ok]="gpsStatus() === 'ok'">
          <div class="paso__num" aria-hidden="true">
            @if (gpsStatus() === 'ok') { <i class="fa fa-check"></i> } @else { 1 }
          </div>
          <div class="paso__cuerpo">
            <h2 class="paso__titulo">Tu ubicación</h2>
            <p class="paso__hint">Necesitamos confirmar que estás en el lugar de la visita.</p>

            @if (gpsStatus() === 'ok') {
              <div class="gps-ok">
                <i class="fa fa-map-marker" aria-hidden="true"></i>
                <div>
                  <span class="gps-ok__label">Ubicación capturada</span>
                  <span class="gps-ok__coords">{{ latitud() }}, {{ longitud() }}</span>
                </div>
                <button type="button" class="btn-outline-sm" (click)="capturarGps()">
                  <i class="fa fa-refresh" aria-hidden="true"></i> Recapturar
                </button>
              </div>
            } @else {
              <button type="button" class="btn-gps"
                      (click)="capturarGps()" [disabled]="gpsStatus() === 'cargando'">
                @if (gpsStatus() === 'cargando') {
                  <span class="spinner-inline spinner-inline--dark" aria-hidden="true"></span>
                  Obteniendo ubicación…
                } @else {
                  <i class="fa fa-location-arrow" aria-hidden="true"></i>
                  Activar mi ubicación GPS
                }
              </button>
              @if (gpsStatus() === 'error') {
                <p class="field__error" role="alert">
                  <i class="fa fa-warning" aria-hidden="true"></i> {{ gpsError() }}
                </p>
              }
            }
          </div>
        </section>

        <!-- PASO 2: FOTOS -->
        <section class="paso" [class.paso--ok]="fotos().length > 0">
          <div class="paso__num" aria-hidden="true">
            @if (fotos().length > 0) { <i class="fa fa-check"></i> } @else { 2 }
          </div>
          <div class="paso__cuerpo">
            <h2 class="paso__titulo">Fotos de evidencia</h2>
            <p class="paso__hint">Toma al menos una foto del lugar como evidencia de la visita.</p>

            @if (fotos().length > 0) {
              <div class="fotos-grid">
                @for (f of fotos(); track f.preview) {
                  <div class="foto-thumb">
                    <img [src]="f.preview" alt="Evidencia de visita">
                    <button type="button" class="foto-thumb__del" (click)="quitarFoto(f)"
                            aria-label="Quitar foto">
                      <i class="fa fa-times" aria-hidden="true"></i>
                    </button>
                  </div>
                }
              </div>
            }

            <label for="foto_input" class="btn-foto">
              <i class="fa fa-camera" aria-hidden="true"></i>
              {{ fotos().length > 0 ? 'Agregar otra foto' : '📸 Tomar foto' }}
            </label>
            <input id="foto_input" type="file" accept="image/*" capture="environment"
                   multiple class="input-oculto" (change)="onFotosChange($event)"
                   aria-label="Tomar foto de evidencia">

            @if (fotoError()) {
              <p class="field__error" role="alert">
                <i class="fa fa-warning" aria-hidden="true"></i> {{ fotoError() }}
              </p>
            }
          </div>
        </section>

        <div class="form-submit-wrap">
          <button type="button" class="btn-brand btn-submit" (click)="enviar()" [disabled]="enviando()">
            @if (enviando()) {
              <span class="spinner-inline" aria-hidden="true"></span> Confirmando…
            } @else {
              <i class="fa fa-check-circle" aria-hidden="true"></i> Confirmar llegada
            }
          </button>
          <p class="form-submit__hint">
            <i class="fa fa-shield" aria-hidden="true"></i>
            Se registrará tu ubicación y la hora de llegada.
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

    :host { display: block; background: $color-bg-subtle; min-height: 100vh; font-family: $font-family-base; }

    .loading-wrap { display: flex; flex-direction: column; align-items: center; justify-content: center; min-height: 100vh; gap: $space-4; color: $color-text-muted; }
    .loading-spinner { width: 44px; height: 44px; border: 4px solid $color-border; border-top-color: $brand-rojo; border-radius: 50%; animation: spin 0.8s linear infinite; @media (prefers-reduced-motion: reduce) { animation: none; } }

    .estado-wrap { display: flex; align-items: center; justify-content: center; min-height: 100vh; padding: $space-6; }
    .estado-card {
      background: $color-bg; border-radius: $radius-2xl; padding: $space-10 $space-8; text-align: center;
      max-width: 480px; width: 100%; box-shadow: $shadow-lg;
      &--cerrado { border-top: 6px solid $brand-rojo; }
      &--exito   { border-top: 6px solid $color-success; }
    }
    .estado-icono { font-size: 3.5rem; margin-bottom: $space-4; color: $brand-rojo; }
    .estado-titulo { font-size: $font-size-2xl; font-weight: $font-weight-bold; color: $color-text; margin: 0 0 $space-3; }
    .estado-msg { font-size: $font-size-md; color: $color-text; font-weight: $font-weight-semibold; margin-bottom: $space-3; }
    .estado-sub { color: $color-text-muted; font-size: $font-size-sm; line-height: $line-height-relaxed; margin-bottom: $space-6; }
    .estado-brand { display: inline-flex; align-items: center; gap: $space-2; font-size: $font-size-xs; color: $color-text-muted; font-weight: $font-weight-semibold; letter-spacing: 0.03em; &__escudo { font-size: 1.1rem; } }

    .exito-check { width: 80px; height: 80px; margin: 0 auto $space-5; svg { width: 100%; height: 100%; } }
    .exito-titulo { font-size: $font-size-2xl; font-weight: $font-weight-bold; color: $color-success; margin: 0 0 $space-3; }
    .exito-desc { color: $color-text; font-size: $font-size-md; margin-bottom: $space-4; line-height: $line-height-relaxed; }
    .exito-coords {
      display: inline-flex; align-items: center; gap: $space-2; background: $brand-gradient-sub;
      border: 1px solid rgba($brand-rojo, 0.2); border-radius: $radius-lg; padding: $space-2 $space-4;
      margin-bottom: $space-5; font-size: $font-size-sm; color: $brand-rojo; font-weight: $font-weight-semibold;
    }

    .form-header { background: $color-bg; box-shadow: $shadow-sm; position: sticky; top: 0; z-index: $z-sticky; }
    .form-banner { display: flex; align-items: center; justify-content: space-between; background: $brand-gradient; color: $color-text-inverse; padding: $space-5; gap: $space-3; }
    .form-banner__left { display: flex; align-items: center; gap: $space-3; }
    .form-banner__escudo { font-size: 2.2rem; flex-shrink: 0; }
    .form-banner__institucion { font-size: $font-size-xs; opacity: 0.85; letter-spacing: 0.04em; text-transform: uppercase; margin: 0 0 $space-1; }
    .form-banner__titulo { font-size: $font-size-lg; font-weight: $font-weight-bold; margin: 0; line-height: $line-height-tight; @media (min-width: #{$bp-md}) { font-size: $font-size-xl; } }
    .form-banner__sub { font-size: $font-size-xs; opacity: 0.85; margin: $space-1 0 0; }
    .form-banner__badge { font-size: 2.5rem; opacity: 0.25; flex-shrink: 0; @media (max-width: 400px) { display: none; } }
    .form-header__evento { display: flex; align-items: center; gap: $space-2; padding: $space-2 $space-5; font-size: $font-size-xs; color: $color-text-muted; background: $color-bg; border-bottom: 1px solid $color-border; }

    .form-main { max-width: 100%; margin: 0 auto; padding: $space-4; @media (min-width: #{$bp-md}) { max-width: 640px; padding: $space-6 $space-4; } }

    .aviso {
      display: flex; align-items: flex-start; gap: $space-3; border-radius: $radius-lg;
      padding: $space-3 $space-4; margin-bottom: $space-4; font-size: $font-size-sm; line-height: $line-height-relaxed;
      i { flex-shrink: 0; margin-top: 2px; }
      &--info { background: rgba($color-info, 0.08); border: 1px solid rgba($color-info, 0.25); color: $color-info; }
      &--error { background: $color-danger-bg; border-left: 4px solid $color-danger; color: $color-danger; }
    }

    .card-plan {
      background: $color-bg; border: 1.5px solid $color-border; border-radius: $radius-xl;
      padding: $space-4 $space-5; margin-bottom: $space-4; box-shadow: $shadow-sm;
    }
    .card-plan__titulo { display: flex; align-items: center; gap: $space-2; font-size: $font-size-sm; font-weight: $font-weight-bold; color: $brand-rojo; text-transform: uppercase; letter-spacing: 0.05em; margin: 0 0 $space-3; }
    .card-plan__item { font-size: $font-size-sm; color: $color-text; margin-bottom: $space-2; line-height: $line-height-relaxed; strong { color: $color-text; } }

    .paso {
      display: flex; gap: $space-4; background: $color-bg; border: 1.5px solid $color-border;
      border-radius: $radius-xl; padding: $space-5; margin-bottom: $space-3; box-shadow: $shadow-sm;
      transition: border-color $transition-base;
      &--ok { border-color: rgba($color-success, 0.5); }
    }
    .paso__num {
      display: flex; align-items: center; justify-content: center; width: 36px; height: 36px; min-width: 36px;
      border-radius: 50%; background: $brand-gradient-sub; color: $brand-rojo; font-weight: $font-weight-bold; font-size: $font-size-base;
      .paso--ok & { background: $color-success; color: $color-text-inverse; }
    }
    .paso__cuerpo { flex: 1; min-width: 0; }
    .paso__titulo { font-size: $font-size-base; font-weight: $font-weight-semibold; color: $color-text; margin: 0 0 $space-1; }
    .paso__hint { font-size: $font-size-sm; color: $color-text-muted; margin: 0 0 $space-4; line-height: $line-height-relaxed; }

    .btn-gps {
      display: inline-flex; align-items: center; justify-content: center; gap: $space-2; width: 100%;
      min-height: $touch-target-min; padding: $space-3 $space-5; background: $brand-gradient-sub;
      color: $brand-rojo; border: 1.5px solid rgba($brand-rojo, 0.4); border-radius: $radius-lg;
      font-size: $font-size-base; font-family: $font-family-base; font-weight: $font-weight-semibold; cursor: pointer;
      transition: background $transition-base;
      &:hover:not(:disabled) { background: rgba($brand-rojo, 0.1); }
      &:disabled { opacity: 0.6; cursor: not-allowed; }
      &:focus-visible { outline: $focus-ring; outline-offset: $focus-ring-offset; }
    }
    .gps-ok {
      display: flex; align-items: center; gap: $space-3; background: rgba($color-success, 0.08);
      border: 1px solid rgba($color-success, 0.25); border-radius: $radius-lg; padding: $space-3 $space-4;
      i { color: $color-success; font-size: 1.3rem; }
      div { flex: 1; min-width: 0; display: flex; flex-direction: column; }
    }
    .gps-ok__label { font-size: $font-size-xs; color: $color-text-muted; text-transform: uppercase; letter-spacing: 0.04em; }
    .gps-ok__coords { font-size: $font-size-sm; font-weight: $font-weight-semibold; color: $color-text; word-break: break-all; }

    .fotos-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(96px, 1fr)); gap: $space-3; margin-bottom: $space-4; }
    .foto-thumb {
      position: relative; aspect-ratio: 1; border-radius: $radius-lg; overflow: hidden;
      border: 1.5px solid $color-border; background: $color-bg-subtle;
      img { width: 100%; height: 100%; object-fit: cover; }
    }
    .foto-thumb__del {
      position: absolute; top: 4px; right: 4px; width: 26px; height: 26px; border-radius: 50%;
      background: rgba(0, 0, 0, 0.6); color: #fff; border: none; cursor: pointer; display: flex; align-items: center; justify-content: center;
      font-size: $font-size-xs;
      &:hover { background: $color-danger; }
    }
    .btn-foto {
      display: inline-flex; align-items: center; justify-content: center; gap: $space-2; width: 100%;
      min-height: $touch-target-min; padding: $space-3 $space-5; background: $color-bg-muted;
      color: $color-text; border: 1.5px dashed $color-border-strong; border-radius: $radius-lg;
      font-size: $font-size-base; font-weight: $font-weight-semibold; cursor: pointer; transition: background $transition-base;
      &:hover { background: $color-border; }
    }
    .input-oculto { position: absolute; left: -9999px; width: 1px; height: 1px; opacity: 0; }

    .field__error { color: $color-danger; font-size: $font-size-xs; margin: $space-2 0 0; font-weight: $font-weight-medium; display: flex; align-items: center; gap: $space-1; }

    .form-submit-wrap { text-align: center; padding: $space-6 0 $space-10; }
    .btn-brand {
      display: inline-flex; align-items: center; justify-content: center; gap: $space-2; min-height: $touch-target-min;
      padding: $space-3 $space-6; background: $brand-gradient; color: $color-text-inverse; border: none; border-radius: $radius-lg;
      font-size: $font-size-base; font-family: $font-family-base; font-weight: $font-weight-semibold; cursor: pointer;
      transition: filter $transition-base, box-shadow $transition-base; box-shadow: 0 4px 14px rgba($brand-rojo, 0.35);
      &:hover { filter: brightness(0.92); box-shadow: 0 6px 20px rgba($brand-rojo, 0.45); }
      &:focus-visible { outline: $focus-ring; outline-offset: $focus-ring-offset; }
      &[disabled] { opacity: 0.65; cursor: not-allowed; box-shadow: none; }
      &-lg { font-size: $font-size-md; padding: $space-4 $space-8; }
    }
    .btn-submit { width: 100%; max-width: 400px; font-size: $font-size-md; padding: $space-4 $space-8; border-radius: $radius-xl; }
    .btn-outline-sm {
      display: inline-flex; align-items: center; gap: $space-1; min-height: 32px; padding: $space-1 $space-3;
      font-size: $font-size-sm; font-weight: $font-weight-semibold; background: $color-bg; color: $brand-rojo;
      border: 1.5px solid $brand-rojo; border-radius: $radius-lg; cursor: pointer; transition: background $transition-base; flex-shrink: 0;
      &:hover { background: rgba($brand-rojo, 0.06); }
    }
    .form-submit__hint { font-size: $font-size-xs; color: $color-text-muted; margin: $space-3 0 0; display: flex; align-items: center; justify-content: center; gap: $space-2; }

    .spinner-inline {
      display: inline-block; width: 16px; height: 16px; border: 2px solid rgba(255, 255, 255, 0.4);
      border-top-color: $color-text-inverse; border-radius: 50%; animation: spin 0.7s linear infinite;
      @media (prefers-reduced-motion: reduce) { animation: none; }
      &--dark { border-color: rgba($brand-rojo, 0.3); border-top-color: $brand-rojo; }
    }
    @keyframes spin { to { transform: rotate(360deg); } }
  `],
})
export class InfoTerrenoPublicoComponent implements OnInit {
  private route = inject(ActivatedRoute);
  private http  = inject(HttpClient);
  private cfg   = inject(ConfigService);

  cargando   = signal(true);
  errorCarga = signal('');
  cerrado    = signal(false);
  cerradoMsg = signal('');
  exito      = signal(false);
  enviando   = signal(false);

  ctx = signal<InfoTerrenoContexto | null>(null);

  // GPS
  gpsStatus = signal<GpsStatus>('idle');
  gpsError  = signal('');
  latitud   = signal<string>('');
  longitud  = signal<string>('');

  // Fotos
  fotos        = signal<FotoPendiente[]>([]);
  fotoError    = signal('');
  fotosEnviadas = signal(0);

  errorEnvio = signal('');

  ngOnInit(): void {
    this.cargar();
  }

  private eventoId(): number {
    return Number(this.route.snapshot.paramMap.get('eventoId') ?? '0');
  }

  planeacionVisible(): boolean {
    const p = this.ctx()?.planeacion;
    return !!(p && (p.recorrido || p.hallazgos || p.observaciones));
  }

  cargar(): void {
    this.cargando.set(true);
    this.errorCarga.set('');
    this.cerrado.set(false);

    const url = this.cfg.url(`/api/eventos/${this.eventoId()}/info-terreno/`);
    this.http.get<InfoTerrenoContexto>(url).subscribe({
      next: (data) => {
        if (!data.evento.abierto) {
          this.cerrado.set(true);
          this.cerradoMsg.set('Esta visita en terreno ya no está activa.');
          this.cargando.set(false);
          return;
        }
        this.ctx.set(data);
        this.cargando.set(false);
      },
      error: (err) => {
        this.cargando.set(false);
        this.errorCarga.set(
          err.error?.detail || 'No se pudo cargar la visita. Revisa tu conexión.',
        );
      },
    });
  }

  // ── GPS ────────────────────────────────────────────────────────────
  capturarGps(): void {
    if (!('geolocation' in navigator)) {
      this.gpsStatus.set('error');
      this.gpsError.set('Tu dispositivo no permite obtener la ubicación.');
      return;
    }
    this.gpsStatus.set('cargando');
    this.gpsError.set('');
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        this.latitud.set(pos.coords.latitude.toFixed(6));
        this.longitud.set(pos.coords.longitude.toFixed(6));
        this.gpsStatus.set('ok');
      },
      (err) => {
        this.gpsStatus.set('error');
        this.gpsError.set(
          err.code === err.PERMISSION_DENIED
            ? 'Permiso de ubicación denegado. Actívalo en el navegador y reintenta.'
            : 'No se pudo obtener la ubicación. Verifica el GPS y reintenta.',
        );
      },
      { enableHighAccuracy: true, timeout: 15000, maximumAge: 0 },
    );
  }

  // ── Fotos ──────────────────────────────────────────────────────────
  onFotosChange(event: Event): void {
    const input = event.target as HTMLInputElement;
    const files = Array.from(input.files ?? []);
    if (!files.length) return;

    this.fotoError.set('');
    for (const file of files) {
      if (file.size > 5 * 1024 * 1024) {
        this.fotoError.set(`"${file.name}" pesa más de 5 MB. Toma otra con menor calidad.`);
        continue;
      }
      const reader = new FileReader();
      reader.onload = (e) => {
        const preview = e.target?.result as string;
        this.fotos.set([...this.fotos(), { file, preview }]);
      };
      reader.readAsDataURL(file);
    }
    input.value = '';
  }

  quitarFoto(foto: FotoPendiente): void {
    this.fotos.set(this.fotos().filter((f) => f !== foto));
  }

  // ── Envío ──────────────────────────────────────────────────────────
  enviar(): void {
    this.errorEnvio.set('');
    if (this.gpsStatus() !== 'ok') {
      this.errorEnvio.set('Primero activa tu ubicación GPS (paso 1).');
      this.gpsStatus.set(this.gpsStatus() === 'idle' ? 'error' : this.gpsStatus());
      if (this.gpsStatus() === 'error' && !this.gpsError()) {
        this.gpsError.set('La ubicación GPS es obligatoria.');
      }
      window.scrollTo({ top: 0, behavior: 'smooth' });
      return;
    }
    if (this.fotos().length === 0) {
      this.errorEnvio.set('Adjunta al menos una foto de evidencia (paso 2).');
      this.fotoError.set('Toma al menos una foto.');
      window.scrollTo({ top: 0, behavior: 'smooth' });
      return;
    }

    this.enviando.set(true);
    const fd = new globalThis.FormData();
    fd.append('latitude', this.latitud());
    fd.append('longitude', this.longitud());
    for (const f of this.fotos()) {
      fd.append('fotos', f.file, f.file.name);
    }

    const url = this.cfg.url(`/api/eventos/${this.eventoId()}/info-terreno/confirmar/`);
    this.http.post<{ detail: string; fotos: number }>(url, fd).subscribe({
      next: (resp) => {
        this.enviando.set(false);
        this.fotosEnviadas.set(resp.fotos);
        this.exito.set(true);
        window.scrollTo({ top: 0, behavior: 'smooth' });
      },
      error: (err) => {
        this.enviando.set(false);
        if (err.status === 410) {
          this.cerrado.set(true);
          this.cerradoMsg.set(err.error?.detail || 'La visita cerró mientras confirmabas.');
          return;
        }
        this.errorEnvio.set(err.error?.detail || 'Error al confirmar. Intenta nuevamente.');
        window.scrollTo({ top: 0, behavior: 'smooth' });
      },
    });
  }
}
