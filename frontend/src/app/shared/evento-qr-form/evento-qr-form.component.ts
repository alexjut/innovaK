import { Component, Input } from '@angular/core';
import { RouterLink } from '@angular/router';

/**
 * Botones compartidos "Formulario" + "QR" por evento — FUENTE ÚNICA del markup.
 *
 * Se usa en `actividades-eventos` y en `subgrupo-detalle`. La regresión que
 * este componente resuelve ocurrió porque el markup vivía en UN solo
 * componente (actividades-eventos) y el panel de Área (subgrupo-detalle, B4)
 * nunca lo replicó; al rutear a los operativos allí (B6), los botones
 * "desaparecieron". Centralizar el markup evita que vuelva a pasar.
 *
 * El COMPONENTE solo pinta; el GATE (si el evento tiene formulario público)
 * lo decide cada padre con su `@if` (el backend del panel ya entrega
 * `url_publica` = null cuando el tipo no tiene formulario).
 */
@Component({
  standalone: true,
  selector: 'app-evento-qr-form',
  imports: [RouterLink],
  template: `
    <a [href]="urlPublica" target="_blank" rel="noopener"
       class="ui-btn ui-btn--sm ui-btn--outline"
       title="Abrir el formulario público (el que se llena por QR)">
      <i class="fa fa-file-lines"></i> {{ etiquetaForm }}
    </a>
    <a [routerLink]="['/eventos', eventoId, 'qr']"
       class="ui-btn ui-btn--sm ui-btn--ghost"
       title="Ver/descargar el QR para compartir">
      <i class="fa fa-qrcode"></i> QR
    </a>
  `,
})
export class EventoQrFormComponent {
  @Input({ required: true }) eventoId!: number;
  @Input({ required: true }) urlPublica!: string;
  /** "Inscripción" para cursos; "Formulario" para el resto. */
  @Input() etiquetaForm = 'Formulario';
}
