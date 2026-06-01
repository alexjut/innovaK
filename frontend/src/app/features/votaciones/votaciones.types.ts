/**
 * Tipos del módulo Votaciones (organizador).
 *
 * Backend: apps/votaciones/api/views.py (Etapa C #2).
 *
 * Nota: el flujo de scan QR + voto sigue 100% en Django HTML (regla B
 * del plan: formularios públicos no se migran). Este feature en
 * Angular es solo para el ORGANIZADOR (votaciones_admin).
 */

export interface EventoVotacion {
  id: number;
  name: string;
  starts_at: string | null;
  ends_at: string | null;
  is_open: boolean;
  status: string;
  status_message: string;
}

export interface EventosResponse {
  count: number;
  results: EventoVotacion[];
}

export interface Candidato {
  id: number;
  name: string;
  genre: string;
  group: 'IDENTIDADES' | 'DERECHOS' | string;
  curul: string;
  code: string;
  photo_url: string;
  bio: string;
  is_active: boolean;
  event_id: number;
}

export interface CandidatosResponse {
  event: EventoVotacion;
  identidades: Candidato[];
  derechos: Candidato[];
  count_identidades: number;
  count_derechos: number;
}

export interface RankingItem {
  candidate_id: number | null;
  candidate_name: string;
  photo_url: string;
  curul: string;
  votes: number;
  percentage: number;
}

export interface Resultados {
  event: { id: number; name: string } | null;
  total_votes: number;
  unique_voters: number;
  ranking_identidades: RankingItem[];
  ranking_derechos: RankingItem[];
  total_identidades_votes: number;
  total_derechos_votes: number;
}
