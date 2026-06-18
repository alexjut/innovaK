export type EstadoFestival = 'planeado' | 'ejecutado' | 'cerrado';

export interface Festival {
  id: number;
  nombre: string;
  tipo_festival: number | null;
  tipo_festival_nombre: string | null;
  vigencia: number;
  numero_edicion: number | null;
  estado: EstadoFestival;
  estado_display: string;
  subgrupo_id: number | null;
  fecha_inicio: string | null;
  fecha_fin: string | null;
  lugar_texto: string | null;
  descripcion: string | null;
  documentado: boolean;
  publicado: boolean;
  publicado_en: string | null;
  slug: string | null;
  n_eventos: number;
  created_at: string | null;
  updated_at: string | null;
}

export interface TipoFestival {
  codigo: number;
  nombre: string;
}

export interface FestivalCatalogos {
  tipos_festival: TipoFestival[];
  vigencias: number[];
  estados: { value: EstadoFestival; label: string }[];
}

export type FestivalInput = Partial<
  Pick<
    Festival,
    | 'nombre'
    | 'tipo_festival'
    | 'vigencia'
    | 'numero_edicion'
    | 'estado'
    | 'fecha_inicio'
    | 'fecha_fin'
    | 'lugar_texto'
    | 'descripcion'
    | 'subgrupo_id'
  >
>;
