import { Component, EventEmitter, Input, Output } from '@angular/core';

import {
  FamiliaEnfoque,
  SeleccionEnfoque,
  esNinguno,
} from './banco-form.model';

/**
 * §5.2 y §7.8 · Enfoques poblacionales: checkboxes en cascada con submenú.
 *
 * ── El orden ES el dato ────────────────────────────────────────────────
 * En §7.8 el puntaje no depende de qué enfoque se marcó sino de CUÁNDO se
 * marcó (1º, 2º, 3º…). Por eso la selección se guarda como arreglo ordenado y
 * no como Set: la posición viaja explícita al servidor como `orden`. Si el
 * usuario desmarca el 2º, el 3º pasa a ser 2º — y el badge que ve en pantalla
 * cambia con él, para que la consecuencia de reordenar sea visible antes de
 * radicar y no una sorpresa después.
 *
 * No se muestra cuántos puntos vale cada posición: el modelo es ciego por
 * diseño. Se muestra la posición, que es lo que el ciudadano decide.
 *
 * ── Tope de §5.2 ───────────────────────────────────────────────────────
 * "Mujer y Género" + hasta 3 adicionales. El componente impide la cuarta
 * adicional en la interacción (no después, en el envío): un tope que solo
 * existe en el servidor es un formulario que se llena mal y se rechaza entero.
 *
 * ── "Ninguno" es excluyente ────────────────────────────────────────────
 * Marcarlo limpia todo lo demás; marcar cualquier otro lo apaga. "Ninguno y
 * también discapacidad" no es una respuesta.
 */
@Component({
  standalone: true,
  selector: 'app-enfoques-cascada',
  template: `
    <div class="ec">
      @for (fam of familias; track fam.codigo) {
        <div class="ec__fam" [class.ec__fam--activa]="posicion(fam.codigo) > 0">
          <button type="button"
                  class="ec__check"
                  role="checkbox"
                  [attr.aria-checked]="posicion(fam.codigo) > 0"
                  (click)="alternar(fam)">
            <span class="ec__box" aria-hidden="true">
              @if (posicion(fam.codigo) > 0) { ✓ }
            </span>
            <span class="ec__nombre">{{ fam.nombre }}</span>
            @if (mostrarOrden && posicion(fam.codigo) > 0) {
              <span class="ec__orden" [attr.aria-label]="'Enfoque número ' + posicion(fam.codigo)">
                {{ posicion(fam.codigo) }}º
              </span>
            }
          </button>

          <!-- Submenú en cascada: solo existe si la familia está activa. -->
          @if (posicion(fam.codigo) > 0 && fam.opciones.length > 0) {
            <div class="ec__submenu">
              <p class="ec__submenu-hint">Precisa dentro de este enfoque:</p>
              <div class="ec__chips">
                @for (op of fam.opciones; track op.codigo) {
                  <button type="button"
                          class="ec__chip"
                          [class.ec__chip--activo]="tieneOpcion(fam.codigo, op.codigo)"
                          [attr.aria-pressed]="tieneOpcion(fam.codigo, op.codigo)"
                          (click)="alternarOpcion(fam.codigo, op.codigo)">
                    {{ op.nombre }}
                  </button>
                }
              </div>
            </div>
          }
        </div>
      }

      @if (avisoTope()) {
        <p class="ec__aviso" role="status">{{ avisoTope() }}</p>
      }

      @if (maxAdicionales !== null) {
        <p class="ec__cupo">
          Adicionales marcados: <strong>{{ adicionales() }}</strong> de {{ maxAdicionales }}.
        </p>
      }
    </div>
  `,
  styles: [`
    @use '../../../../styles/tokens' as *;

    .ec { display: flex; flex-direction: column; gap: $space-2; }

    .ec__fam {
      border: 1px solid $color-border;
      border-radius: $radius-lg;
      background: $color-bg;
      overflow: hidden;
    }
    .ec__fam--activa {
      border-color: $color-primary;
      box-shadow: 0 0 0 1px $color-primary inset;
    }

    .ec__check {
      display: flex;
      align-items: center;
      gap: $space-3;
      width: 100%;
      min-height: $touch-target-min;
      padding: $space-3;
      background: none;
      border: 0;
      text-align: left;
      cursor: pointer;
      font: inherit;
      color: $color-text;

      &:focus-visible { outline: $focus-ring-width solid $focus-ring-color; outline-offset: -2px; }
    }

    .ec__box {
      flex: 0 0 auto;
      width: 24px;
      height: 24px;
      display: grid;
      place-items: center;
      border: 2px solid $color-border-strong;
      border-radius: $radius-sm;
      font-weight: $font-weight-bold;
      color: $color-text-inverse;
      background: $color-bg;
    }
    .ec__fam--activa .ec__box {
      background: $color-primary;
      border-color: $color-primary;
    }

    .ec__nombre { flex: 1 1 auto; font-weight: $font-weight-medium; line-height: $line-height-snug; }

    .ec__orden {
      flex: 0 0 auto;
      min-width: 2.25rem;
      text-align: center;
      padding: 2px $space-2;
      border-radius: $radius-pill;
      background: $color-secondary;
      color: $color-text-inverse;
      font-size: $font-size-xs;
      font-weight: $font-weight-bold;
    }

    .ec__submenu {
      padding: 0 $space-3 $space-3;
      border-top: 1px dashed $color-border;
      background: $color-bg-subtle;
    }
    .ec__submenu-hint {
      margin: $space-2 0;
      font-size: $font-size-xs;
      color: $color-text-muted;
    }
    .ec__chips { display: flex; flex-wrap: wrap; gap: $space-2; }

    .ec__chip {
      min-height: 40px;
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

    .ec__aviso {
      margin: 0;
      padding: $space-2 $space-3;
      border-radius: $radius-md;
      background: $color-warning-bg;
      color: $color-text;
      font-size: $font-size-sm;
    }

    .ec__cupo { margin: 0; font-size: $font-size-xs; color: $color-text-muted; }
  `],
})
export class EnfoquesCascadaComponent {
  /** Catálogo de la sección (`enfoques_familias_52` o `enfoques_familias_78`). */
  @Input({ required: true }) familias: FamiliaEnfoque[] = [];

  /**
   * Selección viva, EN ORDEN DE ACTIVACIÓN. Se muta en sitio (el componente
   * padre es dueño del arreglo) y se avisa por `cambio` para que el padre
   * dispare el guardado progresivo.
   */
  @Input({ required: true }) seleccion: SeleccionEnfoque[] = [];

  /** `null` = sin tope (§7.8). `3` = §5.2, contando aparte la familia base. */
  @Input() maxAdicionales: number | null = null;

  /** Familia que no consume cupo de "adicionales" (§5.2 · Mujer y Género). */
  @Input() familiaBase: string | null = null;

  /** §7.8 muestra la posición; §5.2 no la usa para puntuar y no la muestra. */
  @Input() mostrarOrden = false;

  @Output() cambio = new EventEmitter<void>();

  protected aviso = '';

  /** Posición 1-based dentro de la selección, o 0 si no está marcada. */
  posicion(codigo: string): number {
    return this.seleccion.findIndex((s) => s.familia === codigo) + 1;
  }

  tieneOpcion(familia: string, opcion: string): boolean {
    return !!this.seleccion.find((s) => s.familia === familia)?.opciones.has(opcion);
  }

  protected adicionales(): number {
    return this.seleccion.filter(
      (s) => s.familia !== this.familiaBase && !this.esCodigoNinguno(s.familia),
    ).length;
  }

  protected avisoTope(): string {
    return this.aviso;
  }

  protected alternar(fam: FamiliaEnfoque): void {
    this.aviso = '';
    const idx = this.seleccion.findIndex((s) => s.familia === fam.codigo);

    if (idx >= 0) {
      // Desmarcar arrastra sus subopciones: no quedan huérfanas marcadas.
      this.seleccion.splice(idx, 1);
      this.cambio.emit();
      return;
    }

    if (esNinguno(fam)) {
      this.seleccion.splice(0, this.seleccion.length);
      this.seleccion.push({ familia: fam.codigo, opciones: new Set<string>() });
      this.cambio.emit();
      return;
    }

    // Cualquier enfoque real apaga "Ninguno".
    const iNinguno = this.seleccion.findIndex((s) => this.esCodigoNinguno(s.familia));
    if (iNinguno >= 0) this.seleccion.splice(iNinguno, 1);

    const cuentaComoAdicional =
      this.maxAdicionales !== null && fam.codigo !== this.familiaBase;
    if (cuentaComoAdicional && this.adicionales() >= this.maxAdicionales!) {
      this.aviso =
        `Ya marcaste ${this.maxAdicionales} enfoques adicionales, que es el ` +
        'máximo permitido. Desmarca uno si quieres cambiarlo.';
      return;
    }

    this.seleccion.push({ familia: fam.codigo, opciones: new Set<string>() });
    this.cambio.emit();
  }

  protected alternarOpcion(familia: string, opcion: string): void {
    const sel = this.seleccion.find((s) => s.familia === familia);
    if (!sel) return;
    if (sel.opciones.has(opcion)) sel.opciones.delete(opcion);
    else sel.opciones.add(opcion);
    this.cambio.emit();
  }

  private esCodigoNinguno(codigo: string): boolean {
    const fam = this.familias.find((f) => f.codigo === codigo);
    return !!fam && esNinguno(fam);
  }
}
