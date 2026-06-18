/**
 * Tipos del módulo Cursos del Docente. Backend ya tiene endpoints
 * DRF completos en apps/login/api/views.py (Etapa D PR-A/B/C/D del
 * módulo Curso Docente):
 *
 *   GET /api/eventos/<id>/sesiones/
 *   POST /api/eventos/<id>/sesiones/
 *   GET /api/sesiones/<id>/asistencia/
 *   POST /api/sesiones/<id>/asistencia/
 *   GET /api/eventos/<id>/notas/
 *   POST /api/eventos/<id>/notas/
 *   GET /api/eventos/<id>/reporte/
 *
 * Pero aún NO hay endpoint REST para "Mis cursos" del docente. Hoy
 * eso solo está como HTML Django en /cursos/. Este feature provee
 * acceso al curso individual y sus sesiones/asistencia, dejando
 * "mis cursos" como link al Django legacy hasta que se cree el
 * endpoint correspondiente.
 */

export interface Sesion {
  id: number;
  evento_id: number;
  fecha: string;
  hora_inicio: string | null;
  hora_fin: string | null;
  nombre: string | null;
  descripcion: string | null;
  lugar: string | null;
}

export interface SesionesResponse {
  evento_id: number;
  count: number;
  results: Sesion[];
}

export interface AsistenciaItem {
  participante_id: number;
  nombre: string;
  asistencia_id: number | null;
  presente: boolean | null;
  observacion: string | null;
}

export interface AsistenciaResponse {
  clase_id: number;
  evento_id: number;
  fecha: string;
  nombre: string | null;
  total_inscritos: number;
  lista: AsistenciaItem[];
}

export interface AsistenciaMarcas {
  fecha?: string;
  marcas: Array<{
    participante_id: number;
    presente: boolean;
    observacion?: string;
  }>;
}

export interface AsistenciaResult {
  presentes: number;
  ausentes: number;
  total: number;
}

export interface ReporteItem {
  participante_id: number;
  persona_nombre: string;
  documento: string;
  asistencias: number;
  inasistencias: number;
  total_marcas: number;
  pct_asistencia: number | null;
  notas: string[];
  promedio: string | null;
  aprobado: boolean | null;
}

export interface ReporteResponse {
  evento_id: number;
  evento_nombre: string | null;
  count: number;
  results: ReporteItem[];
}

export interface CursoLite {
  id: number;
  nombre: string | null;
  tipo_codigo: string | null;
  tipo_nombre: string | null;
  subgrupo: string | null;
  fecha_inicio: string | null;
  fecha_fin: string | null;
  funcionario_nombre: string;
  inscritos: number;
  en_espera: number;
  cupo_maximo: number | null;
  sesiones: number;
  pasadas: number;
  activo: boolean;
}

export interface MisCursosResponse {
  count: number;
  results: CursoLite[];
}

export interface CursoDetalle {
  id: number;
  nombre: string | null;
  descripcion: string;
  tipo_codigo: string | null;
  tipo_nombre: string | null;
  subgrupo: string | null;
  fecha_inicio: string | null;
  fecha_fin: string | null;
  funcionario_nombre: string;
  activo: boolean;
  url_inscripcion?: string | null;
  resumen: {
    inscritos_count: number;
    en_espera_count: number;
    cupo_maximo: number | null;
    disponibles: number | null;
    sesiones_count: number;
    sesiones_pasadas: number;
    [k: string]: any;
  };
}

export interface NotaItem {
  id: number;
  evento_id: number;
  participante_id: number;
  nota: number | string;
  etiqueta: string | null;
  fecha: string | null;
}

export interface NotasResponse {
  evento_id: number;
  count: number;
  results: NotaItem[];
  promedios: Record<string, string>;
}

export interface NotaBulkItem {
  participante_id: number;
  nota: number | string;
  etiqueta?: string;
  fecha?: string;
  evaluacion_id?: number;
}

export interface NotasBulkResult {
  creadas: number;
  actualizadas: number;
  errores: Array<{ participante_id: number; error: string }>;
}

export interface SesionCrearItem {
  fecha: string;
  hora_inicio?: string;
  hora_fin?: string;
  lugar?: string;
  nombre?: string;
  descripcion?: string;
}

export interface SesionesCrearResult {
  creadas: number;
  sesion_ids: number[];
}
