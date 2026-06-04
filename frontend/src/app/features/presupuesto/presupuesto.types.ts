/**
 * Tipos del módulo Presupuesto. 4 entidades:
 *   - proyectos      (Proyecto del PDL)
 *   - indicadores    (KPI de meta-proyecto)
 *   - cdps           (Certificado de Disponibilidad Presupuestal)
 *   - contratos      (Contrato vinculado a CDP)
 */

export type PresupEntidad = 'proyectos' | 'indicadores' | 'cdps' | 'contratos';

export interface PresupItem {
  id: number;
  [extra: string]: unknown;
}

export interface PaginatedResponse<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}

export const ENTIDADES: {
  codigo: PresupEntidad;
  label: string;
  icon: string;
  color: string;
  columnas: { key: string; label: string; type?: 'text' | 'badge' | 'money' | 'percent' }[];
}[] = [
  {
    codigo: 'proyectos',
    label: 'Proyectos',
    icon: 'fa-folder-open',
    color: 'primary',
    columnas: [
      { key: 'codigo', label: 'Código', type: 'text' },
      { key: 'nombre', label: 'Nombre' },
      { key: 'subgrupo_nombre', label: 'Subgrupo' },
    ],
  },
  {
    codigo: 'indicadores',
    label: 'Indicadores (KPIs)',
    icon: 'fa-bullseye',
    color: 'accent',
    columnas: [
      { key: 'codigo', label: 'Código' },
      { key: 'nombre', label: 'Nombre' },
      { key: 'unidad_medida', label: 'Unidad' },
      { key: 'meta_magnitud', label: 'Meta', type: 'text' },
    ],
  },
  {
    codigo: 'cdps',
    label: 'CDPs',
    icon: 'fa-file-invoice-dollar',
    color: 'info',
    columnas: [
      { key: 'numero', label: 'Número' },
      { key: 'proyecto_nombre', label: 'Proyecto' },
      { key: 'valor', label: 'Valor', type: 'money' },
      { key: 'fecha', label: 'Fecha' },
    ],
  },
  {
    codigo: 'contratos',
    label: 'Contratos',
    icon: 'fa-file-signature',
    color: 'success',
    columnas: [
      { key: 'numero', label: 'Número' },
      { key: 'beneficiario_nombre', label: 'Beneficiario' },
      { key: 'valor', label: 'Valor', type: 'money' },
      { key: 'fecha_inicio', label: 'Inicio' },
    ],
  },
];
