import { inject } from '@angular/core';
import { CanMatchFn } from '@angular/router';
import { AuthService } from './auth.service';

/**
 * `canMatch` que solo deja pasar al visitante SIN sesión.
 *
 * Es `canMatch` y no `canActivate` a propósito: cuando devuelve `false` el
 * router NO bloquea, simplemente **descarta esa ruta y sigue probando** las
 * siguientes. Eso es lo que permite que una misma URL (`/app/`) sirva dos
 * cosas distintas sin un redirect ni un `if` dentro de un componente:
 *
 *     sin token  →  home público (bienvenida con Kenny)
 *     con token  →  el hub de siempre
 *
 * Y el resto no cambia: las rutas profundas (`/app/presupuesto`, …) no casan
 * con la ruta raíz, así que siguen cayendo en el bloque protegido y su
 * `authGuard` las manda al login con `?next=`, igual que antes.
 */
export const soloAnonimoMatch: CanMatchFn = () =>
  !inject(AuthService).isAuthenticated();
