import { EstadoKenny } from './mascot-presenter/mascot-presenter.component';

export type PosicionTour = 'top' | 'bottom' | 'left' | 'right' | 'over';

/** Un paso del tour, definido como DATA (no hardcodeado en componentes). */
export interface PasoTour {
  selector: string;
  texto: string;
  estadoMascota: EstadoKenny;
  posicion: PosicionTour;
}

export interface Tour {
  id: string;
  saludo?: string;
  pasos: PasoTour[];
}
