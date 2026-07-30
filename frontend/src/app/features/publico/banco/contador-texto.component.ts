import { Component, Input, computed, signal } from '@angular/core';

import { contarPalabras } from './banco-form.model';

/**
 * Contador visible de extensión mínima (§7.1, §7.2, §7.10, §8.1).
 *
 * El documento exige mínimos (200 caracteres en la problemática y la
 * justificación, 100 palabras en el sustento ambiental) y un límite superior en
 * la metodología. Un mínimo que el usuario no puede ver es un mínimo que
 * descubre cuando el formulario ya le rechazó el envío, después de 50 minutos.
 * Por eso el conteo va debajo del textarea, en vivo, y cambia de color cuando
 * ya cumple.
 */
@Component({
  standalone: true,
  selector: 'app-contador-texto',
  template: `
    <p class="ct" [class.ct--ok]="cumple()" [class.ct--exceso]="excede()"
       aria-live="polite">
      @if (minPalabras > 0) {
        <span>{{ palabras() }} de {{ minPalabras }} palabras mínimas</span>
      } @else if (minCaracteres > 0) {
        <span>{{ caracteres() }} de {{ minCaracteres }} caracteres mínimos</span>
      } @else {
        <span>{{ caracteres() }} caracteres</span>
      }
      @if (maxCaracteres > 0) {
        <span class="ct__max">· máximo {{ maxCaracteres }}</span>
      }
      @if (cumple()) { <span class="ct__ok" aria-hidden="true">✓</span> }
    </p>
  `,
  styles: [`
    @use '../../../../styles/tokens' as *;

    .ct {
      display: flex;
      flex-wrap: wrap;
      gap: $space-2;
      margin: $space-1 0 0;
      font-size: $font-size-xs;
      color: $color-text-muted;
    }
    .ct--ok { color: $color-success; font-weight: $font-weight-semibold; }
    .ct--exceso { color: $color-danger; font-weight: $font-weight-semibold; }
    .ct__max { color: $color-text-muted; font-weight: $font-weight-regular; }
    .ct__ok { font-weight: $font-weight-bold; }
  `],
})
export class ContadorTextoComponent {
  /** Se pasa el texto crudo; el componente no muta nada. */
  @Input() set texto(valor: string) {
    this.valor.set(valor ?? '');
  }
  @Input() minCaracteres = 0;
  @Input() minPalabras = 0;
  @Input() maxCaracteres = 0;

  protected valor = signal('');

  protected caracteres = computed(() => this.valor().trim().length);
  protected palabras = computed(() => contarPalabras(this.valor()));

  protected cumple = computed(() => {
    if (this.minPalabras > 0) return this.palabras() >= this.minPalabras;
    if (this.minCaracteres > 0) return this.caracteres() >= this.minCaracteres;
    return false;
  });

  protected excede = computed(
    () => this.maxCaracteres > 0 && this.valor().length > this.maxCaracteres,
  );
}
