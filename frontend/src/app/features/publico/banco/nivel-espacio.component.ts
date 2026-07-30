import { Component, EventEmitter, Input, Output } from '@angular/core';
import { FormsModule } from '@angular/forms';

import {
  CatalogoItem,
  EscenarioItem,
  NIVELES_ESPACIO,
  codigoStr,
} from './banco-form.model';

/**
 * §4.2 y §7.9.1 · Clasificación de entornos: 4 niveles y botones dinámicos.
 *
 * Mecánica del documento: el usuario da clic en el NIVEL y solo entonces el
 * frontend despliega los botones de selección múltiple de ese nivel más una
 * caja "Otro". Los botones no son una lista aparte: son los `escenario` cuyo
 * `categoria_pot` apunta a esa `red`, así que agregar un botón es un INSERT en
 * el catálogo y no un cambio de código.
 *
 * Cambiar de nivel limpia los botones del nivel anterior a propósito: una
 * selección de "Coliseo cubierto" dentro del nivel "espacios barriales" es un
 * dato contradictorio que después nadie puede interpretar.
 *
 * El bloque de localización obligatorio (Parque/Espacio · Dirección · Estrato ·
 * Actividad) NO vive acá: sus campos son distintos en §4.2 (`arraigo_*`) y en
 * §7.9 (`ejecucion_*`), y la dirección se elige con el picker de Catastro. Lo
 * pinta la sección, justo debajo, cuando ya hay nivel elegido.
 */
@Component({
  standalone: true,
  selector: 'app-nivel-espacio',
  imports: [FormsModule],
  template: `
    <div class="ne">
      @for (nivel of niveles; track nivel.red) {
        <div class="ne__nivel" [class.ne__nivel--activo]="redSeleccionada === nivel.red">
          <button type="button"
                  class="ne__cab"
                  role="radio"
                  [attr.aria-checked]="redSeleccionada === nivel.red"
                  (click)="elegirNivel(nivel.red)">
            <span class="ne__radio" aria-hidden="true"></span>
            <span class="ne__txt">
              <span class="ne__etiqueta">{{ nivel.etiqueta }}</span>
              <span class="ne__desc">{{ nivel.descripcion }}</span>
            </span>
          </button>

          @if (redSeleccionada === nivel.red) {
            <div class="ne__cuerpo">
              @if (botonesDe(nivel.red).length > 0) {
                <p class="ne__hint">Marca los espacios de este nivel que usas o necesitas:</p>
                <div class="ne__botones">
                  @for (esc of botonesDe(nivel.red); track esc.codigo) {
                    <button type="button"
                            class="ne__boton"
                            [class.ne__boton--activo]="seleccion.has(cod(esc.codigo))"
                            [attr.aria-pressed]="seleccion.has(cod(esc.codigo))"
                            (click)="alternarBoton(cod(esc.codigo))">
                      {{ esc.nombre }}
                    </button>
                  }
                </div>
              } @else {
                <p class="ne__hint">
                  Este nivel no tiene espacios parametrizados; descríbelo en «Otro».
                </p>
              }

              <label class="ne__otro-lbl" [attr.for]="idOtro">
                Otro (opcional) — si el espacio no está en la lista, escríbelo
              </label>
              <input [id]="idOtro" type="text" class="ne__otro"
                     [ngModel]="otro" (ngModelChange)="otroChange.emit($event)"
                     maxlength="150"
                     placeholder="Ej. Cancha del conjunto residencial">
            </div>
          }
        </div>
      }
    </div>
  `,
  styles: [`
    @use '../../../../styles/tokens' as *;

    .ne { display: flex; flex-direction: column; gap: $space-3; }

    .ne__nivel {
      border: 1px solid $color-border;
      border-radius: $radius-lg;
      background: $color-bg;
      overflow: hidden;
    }
    .ne__nivel--activo { border-color: $color-primary; box-shadow: $shadow-sm; }

    .ne__cab {
      display: flex;
      gap: $space-3;
      align-items: flex-start;
      width: 100%;
      padding: $space-3;
      min-height: $touch-target-min;
      background: none;
      border: 0;
      text-align: left;
      font: inherit;
      color: $color-text;
      cursor: pointer;

      &:focus-visible { outline: $focus-ring-width solid $focus-ring-color; outline-offset: -2px; }
    }

    .ne__radio {
      flex: 0 0 auto;
      width: 22px;
      height: 22px;
      margin-top: 2px;
      border: 2px solid $color-border-strong;
      border-radius: 50%;
      background: $color-bg;
    }
    .ne__nivel--activo .ne__radio {
      border-color: $color-primary;
      background: radial-gradient(circle, #{$color-primary} 0 45%, #{$color-bg} 50%);
    }

    .ne__txt { display: flex; flex-direction: column; gap: 2px; }
    .ne__etiqueta { font-weight: $font-weight-semibold; line-height: $line-height-snug; }
    .ne__desc { font-size: $font-size-sm; color: $color-text-muted; line-height: $line-height-snug; }

    .ne__cuerpo {
      padding: $space-3;
      border-top: 1px dashed $color-border;
      background: $color-bg-subtle;
    }
    .ne__hint { margin: 0 0 $space-2; font-size: $font-size-xs; color: $color-text-muted; }

    .ne__botones { display: flex; flex-wrap: wrap; gap: $space-2; }

    .ne__boton {
      min-height: 44px;
      padding: $space-2 $space-3;
      border: 1px solid $color-border-strong;
      border-radius: $radius-pill;
      background: $color-bg;
      color: $color-text;
      font-size: $font-size-sm;
      cursor: pointer;

      &--activo {
        background: $color-primary;
        border-color: $color-primary;
        color: $color-text-inverse;
        font-weight: $font-weight-semibold;
      }
      &:focus-visible { outline: $focus-ring-width solid $focus-ring-color; outline-offset: 2px; }
    }

    .ne__otro-lbl {
      display: block;
      margin: $space-3 0 $space-1;
      font-size: $font-size-xs;
      color: $color-text-muted;
    }
    .ne__otro {
      width: 100%;
      min-height: 44px;
      padding: $space-2 $space-3;
      border: 1px solid $color-border;
      border-radius: $radius-md;
      font: inherit;
      background: $color-bg;
      color: $color-text;
    }
  `],
})
export class NivelEspacioComponent {
  /** Catálogo `redes` — solo para confirmar que el nivel existe en la BD. */
  @Input({ required: true }) redes: CatalogoItem[] = [];
  /** Catálogo `escenarios`, con `categoria_pot`. De acá salen los botones. */
  @Input({ required: true }) escenarios: EscenarioItem[] = [];
  /** Código de `red` elegido. */
  @Input() redSeleccionada = '';
  /** Botones marcados (Set del padre, mutado en sitio). */
  @Input({ required: true }) seleccion: Set<string> = new Set<string>();
  @Input() otro = '';
  /** Sufijo para los `id` del DOM: hay dos instancias en el mismo formulario. */
  @Input() idOtro = 'nivel-otro';

  @Output() redSeleccionadaChange = new EventEmitter<string>();
  @Output() otroChange = new EventEmitter<string>();
  @Output() cambio = new EventEmitter<void>();

  protected readonly cod = codigoStr;

  /** Solo los niveles que existen de verdad en el catálogo `red`. */
  protected get niveles() {
    const disponibles = new Set(this.redes.map((r) => codigoStr(r.codigo)));
    return NIVELES_ESPACIO.filter((n) => disponibles.has(n.red));
  }

  protected botonesDe(red: string): EscenarioItem[] {
    return this.escenarios.filter((e) => (e.categoria_pot ?? '') === red);
  }

  protected elegirNivel(red: string): void {
    if (this.redSeleccionada === red) return;
    // Cambiar de nivel invalida los botones del anterior.
    this.seleccion.clear();
    this.redSeleccionada = red;
    this.redSeleccionadaChange.emit(red);
    this.otroChange.emit('');
    this.cambio.emit();
  }

  protected alternarBoton(codigo: string): void {
    if (this.seleccion.has(codigo)) this.seleccion.delete(codigo);
    else this.seleccion.add(codigo);
    this.cambio.emit();
  }
}
