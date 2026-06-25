import { HttpClient, HttpParams } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';
import { ConfigService } from '../../core/config/config.service';

export interface RolItem {
  id: number;
  name: string;
  num_users: number;
  num_modulos: number;
  es_protegido: boolean;
  activo: boolean;
}
export interface RolDetalle {
  id: number;
  name: string;
  es_protegido: boolean;
  activo: boolean;
  modulos: { codigo: string; nombre: string; asignado: boolean }[];
  usuarios: { id: number; username: string; nombre: string }[];
}

export interface OrgItem {
  id: number;
  nombre?: string;
  [key: string]: any;
}
export interface OrgListaResponse {
  entidad: string;
  count: number;
  page: number;
  page_size: number;
  results: OrgItem[];
}

export interface PersonaLite {
  id: number;
  nombre: string;
  documento: string | null;
}
export interface PersonasResponse {
  count: number;
  page: number;
  page_size: number;
  results: PersonaLite[];
}

export interface UsuarioLite {
  id: number;
  username: string;
  nombre: string;
}
export interface UsuariosResponse {
  count: number;
  page: number;
  page_size: number;
  results: UsuarioLite[];
}

@Injectable({ providedIn: 'root' })
export class AdminApi {
  private http = inject(HttpClient);
  private cfg = inject(ConfigService);

  listarRoles(): Observable<{ count: number; results: RolItem[] }> {
    return this.http.get<{ count: number; results: RolItem[] }>(
      this.cfg.url('/api/admin/roles/'),
    );
  }
  rolDetalle(id: number): Observable<RolDetalle> {
    return this.http.get<RolDetalle>(this.cfg.url(`/api/admin/roles/${id}/`));
  }
  orgLista(entidad: string, q = '', page = 1): Observable<OrgListaResponse> {
    let p = new HttpParams().set('page', String(page));
    if (q) p = p.set('q', q);
    return this.http.get<OrgListaResponse>(
      this.cfg.url(`/api/admin/org/${entidad}/`), { params: p },
    );
  }
  buscarPersonas(q = '', page = 1): Observable<PersonasResponse> {
    let p = new HttpParams().set('page', String(page));
    if (q) p = p.set('q', q);
    return this.http.get<PersonasResponse>(
      this.cfg.url('/api/admin/personas/'), { params: p },
    );
  }

  crearRol(name: string): Observable<{ id: number; name: string; detail: string }> {
    return this.http.post<{ id: number; name: string; detail: string }>(
      this.cfg.url('/api/admin/roles/crear/'), { name },
    );
  }

  guardarModulos(rolId: number, codigos: string[]): Observable<{ detail: string; count: number }> {
    return this.http.post<{ detail: string; count: number }>(
      this.cfg.url(`/api/admin/roles/${rolId}/modulos/`), { codigos },
    );
  }

  toggleActivoRol(rolId: number): Observable<{ id: number; activo: boolean }> {
    return this.http.post<{ id: number; activo: boolean }>(
      this.cfg.url(`/api/admin/roles/${rolId}/toggle/`), {},
    );
  }

  buscarUsuarios(q = '', excludeRol?: number, page = 1): Observable<UsuariosResponse> {
    let p = new HttpParams().set('page', String(page));
    if (q) p = p.set('q', q);
    if (excludeRol) p = p.set('exclude_rol', String(excludeRol));
    return this.http.get<UsuariosResponse>(
      this.cfg.url('/api/admin/usuarios/'), { params: p },
    );
  }

  agregarUsuarioRol(rolId: number, usuarioId: number): Observable<{ detail: string; usuario: UsuarioLite }> {
    return this.http.post<{ detail: string; usuario: UsuarioLite }>(
      this.cfg.url(`/api/admin/roles/${rolId}/usuarios/`), { usuario_id: usuarioId },
    );
  }

  quitarUsuarioRol(rolId: number, userId: number): Observable<{ detail: string }> {
    return this.http.delete<{ detail: string }>(
      this.cfg.url(`/api/admin/roles/${rolId}/usuarios/${userId}/`),
    );
  }

  crearOrg(entidad: string, payload: any): Observable<{ id: number; detail: string }> {
    return this.http.post<{ id: number; detail: string }>(
      this.cfg.url(`/api/admin/org/${entidad}/`), payload,
    );
  }

  editarOrg(entidad: string, id: number, payload: any): Observable<{ id: number; detail: string }> {
    return this.http.patch<{ id: number; detail: string }>(
      this.cfg.url(`/api/admin/org/${entidad}/${id}/`), payload,
    );
  }

  crearPersona(payload: any): Observable<{ id: number; detail: string; ya_existia: boolean }> {
    return this.http.post<any>(this.cfg.url('/api/personas/crear/'), payload);
  }
  tiposDocumento(): Observable<{ tipos_documento: { codigo: number; nombre: string }[] }> {
    return this.http.get<any>(this.cfg.url('/api/personas/crear/'));
  }

  // ── PR-5a · Usuarios y accesos (subgrupo + auditoría) ───────────────
  usuariosAcceso(): Observable<UsuarioAcceso[]> {
    return this.http.get<UsuarioAcceso[]>(this.cfg.url('/api/admin/usuarios-acceso/'));
  }
  subgruposCatalogo(): Observable<SubgrupoCat[]> {
    return this.http.get<SubgrupoCat[]>(this.cfg.url('/api/admin/subgrupos/'));
  }
  asignarSubgrupo(userId: number, subgrupoId: number | null): Observable<{ id: number; subgrupo_id: number | null; subgrupo_nombre: string | null }> {
    return this.http.patch<any>(this.cfg.url(`/api/admin/usuarios/${userId}/subgrupo/`), { subgrupo_id: subgrupoId });
  }
  auditoriaRoles(): Observable<AuditoriaRow[]> {
    return this.http.get<AuditoriaRow[]>(this.cfg.url('/api/admin/auditoria-roles/'));
  }
}

export interface UsuarioAcceso {
  id: number;
  username: string;
  nombre: string;
  is_superuser: boolean;
  roles: string[];
  subgrupo_id: number | null;
  subgrupo_nombre: string | null;
}
export interface SubgrupoCat {
  id: number;
  nombre: string;
  dependencia: string | null;
}
export interface AuditoriaRow {
  id: number;
  ts: string | null;
  accion: string;
  actor: string;
  usuario: string | null;
  rol: string | null;
  detalle: string | null;
}
