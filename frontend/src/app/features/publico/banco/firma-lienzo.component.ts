import {
  AfterViewInit,
  Component,
  ElementRef,
  EventEmitter,
  OnDestroy,
  Output,
  ViewChild,
  signal,
} from '@angular/core';

/**
 * §9 · Firma manuscrita: lienzo Canvas HTML5 **o** PDF firmado físicamente.
 *
 * El documento exige una de las dos, no las dos, y sin firma no se libera la
 * radicación. En el piloto anterior 0 de 4 inscripciones quedaron con firma
 * porque el campo era una foto opcional: acá la firma es el evento que
 * desbloquea el botón de enviar, y el estado ("firmado" / "sin firmar") se ve.
 *
 * Decisiones que importan:
 *   · Se dibuja con Pointer Events, que cubren dedo, lápiz y mouse con un solo
 *     camino de código. `touch-action: none` sobre el lienzo evita que el gesto
 *     de firmar haga scroll de la página, que es el bug clásico en móvil.
 *   · El backing store se dimensiona con `devicePixelRatio`: sin eso la firma
 *     sale pixelada en celular, y una firma borrosa es una firma impugnable.
 *   · Al soltar el trazo se emite un `File` PNG. No se guarda el dataURL en el
 *     modelo: el archivo va como multipart bajo la clave `firma`, igual que el
 *     PDF, así el servidor no distingue el camino.
 *   · El lienzo se rellena de blanco antes de exportar. Un PNG con fondo
 *     transparente se ve vacío al imprimirlo sobre papel blanco.
 */
@Component({
  standalone: true,
  selector: 'app-firma-lienzo',
  template: `
    <div class="fl">
      <div class="fl__tabs" role="tablist" aria-label="Cómo quieres firmar">
        <button type="button" class="fl__tab" role="tab"
                [class.fl__tab--on]="modo() === 'lienzo'"
                [attr.aria-selected]="modo() === 'lienzo'"
                (click)="cambiarModo('lienzo')">
          ✍️ Firmar en pantalla
        </button>
        <button type="button" class="fl__tab" role="tab"
                [class.fl__tab--on]="modo() === 'archivo'"
                [attr.aria-selected]="modo() === 'archivo'"
                (click)="cambiarModo('archivo')">
          📄 Subir PDF firmado
        </button>
      </div>

      @if (modo() === 'lienzo') {
        <div class="fl__marco">
          <canvas #lienzo class="fl__canvas"
                  (pointerdown)="iniciar($event)"
                  (pointermove)="mover($event)"
                  (pointerup)="terminar()"
                  (pointerleave)="terminar()"
                  (pointercancel)="terminar()"
                  aria-label="Área de firma: dibuja tu firma con el dedo o el mouse"
                  role="img"></canvas>
          @if (!hayTrazo()) {
            <span class="fl__placeholder" aria-hidden="true">Firma aquí</span>
          }
        </div>
        <div class="fl__acciones">
          <button type="button" class="fl__btn" (click)="limpiar()">
            ↺ Borrar y firmar de nuevo
          </button>
          @if (hayTrazo()) {
            <span class="fl__ok">✓ Firma capturada</span>
          }
        </div>
      } @else {
        <label class="fl__drop" for="firma-archivo">
          <span class="fl__drop-icon" aria-hidden="true">📄</span>
          <span class="fl__drop-txt">
            @if (nombreArchivo()) {
              {{ nombreArchivo() }}
            } @else {
              Seleccionar el PDF o la foto del documento firmado
            }
          </span>
          <span class="fl__drop-sub">PDF, PNG o JPG, hasta 2 MB</span>
        </label>
        <input id="firma-archivo" type="file" class="fl__input"
               accept="application/pdf,image/png,image/jpeg"
               (change)="elegirArchivo($event)"
               aria-label="Documento firmado">
        @if (nombreArchivo()) {
          <div class="fl__acciones">
            <button type="button" class="fl__btn" (click)="limpiar()">✕ Quitar</button>
            <span class="fl__ok">✓ Documento adjunto</span>
          </div>
        }
      }

      @if (error()) {
        <p class="fl__error" role="alert">{{ error() }}</p>
      }
    </div>
  `,
  styles: [`
    @use '../../../../styles/tokens' as *;

    .fl { display: flex; flex-direction: column; gap: $space-3; }

    .fl__tabs { display: flex; gap: $space-2; }
    .fl__tab {
      flex: 1 1 0;
      min-height: 44px;
      padding: $space-2;
      border: 1px solid $color-border-strong;
      border-radius: $radius-md;
      background: $color-bg;
      color: $color-text;
      font: inherit;
      font-size: $font-size-sm;
      cursor: pointer;

      &--on {
        background: $color-primary;
        border-color: $color-primary;
        color: $color-text-inverse;
        font-weight: $font-weight-semibold;
      }
      &:focus-visible { outline: $focus-ring-width solid $focus-ring-color; outline-offset: 2px; }
    }

    .fl__marco {
      position: relative;
      border: 2px dashed $color-border-strong;
      border-radius: $radius-lg;
      background: #fff;
      overflow: hidden;
    }
    .fl__canvas {
      display: block;
      width: 100%;
      height: 180px;
      touch-action: none;
      cursor: crosshair;
    }
    .fl__placeholder {
      position: absolute;
      inset: 0;
      display: grid;
      place-items: center;
      color: $color-text-muted;
      font-size: $font-size-sm;
      pointer-events: none;
    }

    .fl__acciones { display: flex; align-items: center; gap: $space-3; flex-wrap: wrap; }
    .fl__btn {
      min-height: 44px;
      padding: $space-2 $space-4;
      border: 1px solid $color-primary;
      border-radius: $radius-md;
      background: $color-bg;
      color: $color-primary;
      font: inherit;
      cursor: pointer;
    }
    .fl__ok { color: $color-success; font-weight: $font-weight-semibold; font-size: $font-size-sm; }

    .fl__drop {
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: $space-1;
      padding: $space-6 $space-4;
      border: 2px dashed $color-border-strong;
      border-radius: $radius-lg;
      background: $color-bg;
      text-align: center;
      cursor: pointer;
    }
    .fl__drop-icon { font-size: 2rem; }
    .fl__drop-txt { font-weight: $font-weight-semibold; color: $color-text; }
    .fl__drop-sub { font-size: $font-size-xs; color: $color-text-muted; }
    .fl__input {
      position: absolute;
      width: 1px; height: 1px;
      opacity: 0;
      overflow: hidden;
    }

    .fl__error { margin: 0; color: $color-danger; font-size: $font-size-sm; }
  `],
})
export class FirmaLienzoComponent implements AfterViewInit, OnDestroy {
  /** `File` PNG del lienzo, o el PDF/imagen subido. `null` = sin firma. */
  @Output() firmaCambio = new EventEmitter<File | null>();

  @ViewChild('lienzo') private lienzoRef?: ElementRef<HTMLCanvasElement>;

  protected modo = signal<'lienzo' | 'archivo'>('lienzo');
  protected hayTrazo = signal(false);
  protected nombreArchivo = signal('');
  protected error = signal('');

  private ctx: CanvasRenderingContext2D | null = null;
  private dibujando = false;
  private observer?: ResizeObserver;

  ngAfterViewInit(): void {
    this.prepararLienzo();
    const canvas = this.lienzoRef?.nativeElement;
    if (canvas && typeof ResizeObserver !== 'undefined') {
      // Rotar el celular cambia el ancho: el lienzo se re-dimensiona. Se pierde
      // el trazo, y se avisa borrando el estado en lugar de dejar una firma
      // deformada que el usuario cree correcta.
      this.observer = new ResizeObserver(() => this.prepararLienzo());
      this.observer.observe(canvas);
    }
  }

  ngOnDestroy(): void {
    this.observer?.disconnect();
  }

  protected cambiarModo(modo: 'lienzo' | 'archivo'): void {
    if (this.modo() === modo) return;
    this.modo.set(modo);
    this.limpiar();
    if (modo === 'lienzo') {
      // El canvas se vuelve a crear al cambiar de pestaña.
      setTimeout(() => this.prepararLienzo());
    }
  }

  // ── Lienzo ────────────────────────────────────────────────────────
  private prepararLienzo(): void {
    const canvas = this.lienzoRef?.nativeElement;
    if (!canvas) return;
    const ratio = window.devicePixelRatio || 1;
    const ancho = canvas.clientWidth || 320;
    const alto = canvas.clientHeight || 180;
    if (canvas.width === Math.round(ancho * ratio) &&
        canvas.height === Math.round(alto * ratio)) {
      return; // mismo tamaño: no se pierde lo dibujado
    }
    canvas.width = Math.round(ancho * ratio);
    canvas.height = Math.round(alto * ratio);

    const ctx = canvas.getContext('2d');
    if (!ctx) return;
    ctx.scale(ratio, ratio);
    ctx.fillStyle = '#ffffff';
    ctx.fillRect(0, 0, ancho, alto);
    ctx.lineWidth = 2.2;
    ctx.lineCap = 'round';
    ctx.lineJoin = 'round';
    ctx.strokeStyle = '#111827';
    this.ctx = ctx;
    if (this.hayTrazo()) {
      this.hayTrazo.set(false);
      this.firmaCambio.emit(null);
    }
  }

  private punto(ev: PointerEvent): { x: number; y: number } {
    const canvas = this.lienzoRef!.nativeElement;
    const caja = canvas.getBoundingClientRect();
    return { x: ev.clientX - caja.left, y: ev.clientY - caja.top };
  }

  protected iniciar(ev: PointerEvent): void {
    if (!this.ctx) this.prepararLienzo();
    if (!this.ctx) return;
    ev.preventDefault();
    this.dibujando = true;
    const p = this.punto(ev);
    this.ctx.beginPath();
    this.ctx.moveTo(p.x, p.y);
    // Un toque simple debe dejar marca: sin esto, firmar un punto no pinta nada.
    this.ctx.lineTo(p.x + 0.1, p.y + 0.1);
    this.ctx.stroke();
    this.hayTrazo.set(true);
    this.error.set('');
  }

  protected mover(ev: PointerEvent): void {
    if (!this.dibujando || !this.ctx) return;
    ev.preventDefault();
    const p = this.punto(ev);
    this.ctx.lineTo(p.x, p.y);
    this.ctx.stroke();
  }

  protected terminar(): void {
    if (!this.dibujando) return;
    this.dibujando = false;
    this.exportar();
  }

  private exportar(): void {
    const canvas = this.lienzoRef?.nativeElement;
    if (!canvas) return;
    canvas.toBlob((blob) => {
      if (!blob) {
        this.error.set('No se pudo capturar la firma. Intenta de nuevo.');
        this.firmaCambio.emit(null);
        return;
      }
      this.firmaCambio.emit(
        new File([blob], 'firma.png', { type: 'image/png' }),
      );
    }, 'image/png');
  }

  protected limpiar(): void {
    this.hayTrazo.set(false);
    this.nombreArchivo.set('');
    this.error.set('');
    const canvas = this.lienzoRef?.nativeElement;
    if (canvas && this.ctx) {
      this.ctx.fillStyle = '#ffffff';
      this.ctx.fillRect(0, 0, canvas.clientWidth, canvas.clientHeight);
    }
    this.firmaCambio.emit(null);
  }

  // ── PDF / imagen firmada ──────────────────────────────────────────
  protected elegirArchivo(ev: Event): void {
    const input = ev.target as HTMLInputElement;
    const file = input.files?.[0];
    if (!file) return;
    // Mismo tope que el servidor (DOCUMENTOS_MAX_UPLOAD_BYTES = 2 MB).
    if (file.size > 2 * 1024 * 1024) {
      this.error.set('El archivo pesa más de 2 MB. Sube una versión más liviana.');
      input.value = '';
      return;
    }
    this.error.set('');
    this.nombreArchivo.set(`${file.name} (${Math.round(file.size / 1024)} KB)`);
    this.firmaCambio.emit(file);
  }
}
