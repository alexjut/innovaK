import { Component, EventEmitter, Input, Output } from '@angular/core';

import {
  FilaActividad,
  MESES_CRONOGRAMA,
  SEMANAS_CRONOGRAMA,
} from './banco-form.model';

/**
 * §8.3 · Cronograma en matriz cerrada Mes 1-4 × Semana 1-4, por actividad.
 *
 * Cada celda marcada es una fila de `inscripcion_banco_cronograma`
 * (`actividad_id`, `mes`, `semana`), así que en la UI la clave de la celda es
 * `"mes-semana"` y la traducción a filas ocurre una sola vez, al construir el
 * payload.
 *
 * En móvil no cabe una tabla de 17 columnas: se pinta una tabla por actividad
 * con 4 filas (los meses) y 4 columnas (las semanas), que a 320 px entra sin
 * scroll horizontal. Los botones son de 44 px para que se puedan tocar con el
 * dedo, no con el borde de la uña.
 */
@Component({
  standalone: true,
  selector: 'app-cronograma-matriz',
  template: `
    @if (actividades.length === 0) {
      <p class="cm__vacio">
        Primero registra las actividades en el punto anterior; el cronograma se
        arma sobre ellas.
      </p>
    }

    @for (act of actividades; track $index; let i = $index) {
      <div class="cm__act">
        <h4 class="cm__titulo">
          Actividad {{ i + 1 }}@if (act.nombre) { · {{ act.nombre }} }
        </h4>

        <table class="cm__tabla">
          <caption class="cm__caption">
            Marca las semanas en que se ejecuta esta actividad.
          </caption>
          <thead>
            <tr>
              <th scope="col" class="cm__esq"><span class="cm__sr">Mes</span></th>
              @for (s of semanas; track s) {
                <th scope="col" class="cm__th">S{{ s }}</th>
              }
            </tr>
          </thead>
          <tbody>
            @for (m of meses; track m) {
              <tr>
                <th scope="row" class="cm__th cm__th--mes">Mes {{ m }}</th>
                @for (s of semanas; track s) {
                  <td class="cm__td">
                    <button type="button"
                            class="cm__celda"
                            [class.cm__celda--on]="act.celdas.has(clave(m, s))"
                            [attr.aria-pressed]="act.celdas.has(clave(m, s))"
                            [attr.aria-label]="'Mes ' + m + ', semana ' + s"
                            (click)="alternar(act, m, s)">
                      @if (act.celdas.has(clave(m, s))) { ✓ }
                    </button>
                  </td>
                }
              </tr>
            }
          </tbody>
        </table>

        <p class="cm__resumen">
          {{ act.celdas.size }} semana(s) marcada(s).
        </p>
      </div>
    }
  `,
  styles: [`
    @use '../../../../styles/tokens' as *;

    .cm__vacio {
      margin: 0;
      padding: $space-3;
      border-radius: $radius-md;
      background: $color-warning-bg;
      font-size: $font-size-sm;
    }

    .cm__act {
      border: 1px solid $color-border;
      border-radius: $radius-lg;
      padding: $space-3;
      margin-bottom: $space-3;
      background: $color-bg;
    }

    .cm__titulo {
      margin: 0 0 $space-2;
      font-size: $font-size-sm;
      font-weight: $font-weight-semibold;
      color: $color-primary;
    }

    .cm__tabla { width: 100%; border-collapse: collapse; }
    .cm__caption {
      caption-side: top;
      text-align: left;
      font-size: $font-size-xs;
      color: $color-text-muted;
      padding-bottom: $space-2;
    }

    .cm__th {
      font-size: $font-size-xs;
      font-weight: $font-weight-semibold;
      color: $color-text-muted;
      padding: $space-1;
      text-align: center;
      white-space: nowrap;
    }
    .cm__th--mes { text-align: left; padding-right: $space-2; }
    .cm__esq { width: 4.5rem; }
    .cm__td { padding: 2px; }

    .cm__celda {
      width: 100%;
      min-width: 40px;
      height: 44px;
      display: grid;
      place-items: center;
      border: 1px solid $color-border-strong;
      border-radius: $radius-sm;
      background: $color-bg;
      color: $color-text-inverse;
      font-weight: $font-weight-bold;
      cursor: pointer;

      &--on { background: $color-primary; border-color: $color-primary; }
      &:focus-visible { outline: $focus-ring-width solid $focus-ring-color; outline-offset: 2px; }
    }

    .cm__resumen { margin: $space-2 0 0; font-size: $font-size-xs; color: $color-text-muted; }

    .cm__sr {
      position: absolute;
      width: 1px; height: 1px;
      overflow: hidden;
      clip: rect(0 0 0 0);
      white-space: nowrap;
    }
  `],
})
export class CronogramaMatrizComponent {
  @Input({ required: true }) actividades: FilaActividad[] = [];
  @Output() cambio = new EventEmitter<void>();

  protected readonly meses = MESES_CRONOGRAMA;
  protected readonly semanas = SEMANAS_CRONOGRAMA;

  protected clave(mes: number, semana: number): string {
    return `${mes}-${semana}`;
  }

  protected alternar(act: FilaActividad, mes: number, semana: number): void {
    const k = this.clave(mes, semana);
    if (act.celdas.has(k)) act.celdas.delete(k);
    else act.celdas.add(k);
    this.cambio.emit();
  }
}
