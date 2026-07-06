import { EstadoKenny } from '../onboarding/mascot-presenter/mascot-presenter.component';

/** Expresiones del chat (mapeadas a los estados de la mascota). */
export type Expr = 'alegre' | 'atento' | 'orgulloso';

export const EXPR_A_ESTADO: Record<Expr, EstadoKenny> = {
  alegre: 'saludo',
  atento: 'senalando',
  orgulloso: 'celebrando',
};

export interface ChatMessage {
  role: 'bot' | 'user';
  text: string;
  expr?: Expr;
}

export interface Chip {
  label: string;
  action: string;
  primary?: boolean;
}

export interface TramiteCard {
  titulo: string;
  descripcion: string;
  action: string;
}

export interface NewsCard {
  fecha: string;
  titulo: string;
  descripcion: string;
}

export interface Widgets {
  chips?: Chip[];
  cards?: TramiteCard[];
  news?: NewsCard[];
}

export type InputMode = 'free' | 'ia';

/** Una respuesta del bot definida como DATA (no lógica en el componente). */
export interface RespuestaBot {
  texto: string | ((ctx: FlujoCtx) => string);
  expr: Expr;
  widgets?: Widgets | ((ctx: FlujoCtx) => Widgets);
  inputMode?: InputMode;
  inputPlaceholder?: string;
  /** Navegación declarativa (el motor la ejecuta con Router). */
  navegar?: string;
  /** Lanzar un tour de TourService al entrar a la pantalla destino. */
  lanzarTour?: string;
}

/** Contexto de flujo que el motor mantiene entre pasos. */
export interface FlujoCtx {
  pqrsTipo?: string;
  citaDep?: string;
  citaDate?: string;
  citaTime?: string;
  ultimoTexto?: string;
  radicado?: string;
  codigoCita?: string;
}
