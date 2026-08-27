import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';
import { ConfigService } from '../../core/config/config.service';
import {
  BusquedaSecop, ContratoLigado, DocumentoFormulacion, Formulacion,
  ListaFormulaciones,
} from './formulacion.types';

/**
 * Cliente del dominio FORMULACIÓN.
 *
 * Ninguna regla se decide acá: quién puede escribir lo dice el servidor en
 * `puede_formular`, y a qué estados se puede pasar lo dice `destinos`. Si la
 * pantalla reimplementara esas reglas habría dos fuentes de verdad, y la del
 * navegador se puede editar.
 */
@Injectable({ providedIn: 'root' })
export class FormulacionApi {
  private http = inject(HttpClient);
  private cfg = inject(ConfigService);

  lista(area: string, vigencia?: number): Observable<ListaFormulaciones> {
    const q = vigencia ? `?vigencia=${vigencia}` : '';
    return this.http.get<ListaFormulaciones>(
      this.cfg.url(`/presupuesto/api/areas/${area}/formulaciones/${q}`));
  }

  crear(area: string, cuerpo: {
    actividad_plan_id: number; vigencia: number; objeto: string;
    descripcion?: string; valor_estimado?: number | null;
  }): Observable<Formulacion> {
    return this.http.post<Formulacion>(
      this.cfg.url(`/presupuesto/api/areas/${area}/formulaciones/`), cuerpo);
  }

  /** Asigna o quita el encargado. `null` lo deja sin encargado, a propósito. */
  asignarEncargado(id: number, funcionario_id: number | null):
      Observable<{ responsable: Formulacion['responsable'] }> {
    return this.http.patch<{ responsable: Formulacion['responsable'] }>(
      this.cfg.url(`/presupuesto/api/formulaciones/${id}/responsable/`),
      { funcionario_id });
  }

  detalle(id: number): Observable<Formulacion> {
    return this.http.get<Formulacion>(
      this.cfg.url(`/presupuesto/api/formulaciones/${id}/`));
  }

  /** Cambia de estado. El servidor rechaza el salto que la tabla no permite. */
  cambiarEstado(id: number, estado_codigo: number, observacion?: string):
      Observable<{ nombre: string; formulacion: Formulacion }> {
    return this.http.patch<{ nombre: string; formulacion: Formulacion }>(
      this.cfg.url(`/presupuesto/api/formulaciones/${id}/estado/`),
      { estado_codigo, observacion });
  }

  marcarRequisito(id: number, codigo: string, estado: string, observacion?: string):
      Observable<{ completitud: number | null; bloqueada: boolean }> {
    return this.http.post<{ completitud: number | null; bloqueada: boolean }>(
      this.cfg.url(`/presupuesto/api/formulaciones/${id}/requisitos/${codigo}/`),
      { estado, observacion });
  }

  documentos(id: number): Observable<{ documentos: DocumentoFormulacion[] }> {
    return this.http.get<{ documentos: DocumentoFormulacion[] }>(
      this.cfg.url(`/presupuesto/api/formulaciones/${id}/documentos/`));
  }

  /** Sube un soporte. Si va `requisitoCodigo`, además lo marca cumplido. */
  subirDocumento(id: number, archivo: File, requisitoCodigo?: string):
      Observable<{ documentos: DocumentoFormulacion[]; completitud: number | null }> {
    const fd = new FormData();
    fd.append('archivo', archivo);
    if (requisitoCodigo) fd.append('requisito_codigo', requisitoCodigo);
    return this.http.post<{ documentos: DocumentoFormulacion[]; completitud: number | null }>(
      this.cfg.url(`/presupuesto/api/formulaciones/${id}/documentos/`), fd);
  }

  borrarDocumento(id: number, docId: number):
      Observable<{ documentos: DocumentoFormulacion[]; completitud: number | null }> {
    return this.http.delete<{ documentos: DocumentoFormulacion[]; completitud: number | null }>(
      this.cfg.url(`/presupuesto/api/formulaciones/${id}/documentos/${docId}/`));
  }

  /** URL de descarga. El navegador la abre; el backend descifra y sirve. */
  urlDocumento(id: number, docId: number): string {
    return this.cfg.url(`/presupuesto/api/formulaciones/${id}/documentos/${docId}/`);
  }

  /** Contratos ligados, y —si va `q`— la búsqueda en el espejo de SECOP. */
  contratos(id: number, q?: string, vigencia?: number):
      Observable<{ contratos: ContratoLigado[]; busqueda?: BusquedaSecop }> {
    const p = new URLSearchParams();
    if (q) p.set('q', q);
    if (vigencia) p.set('vigencia', String(vigencia));
    const qs = p.toString() ? `?${p.toString()}` : '';
    return this.http.get<{ contratos: ContratoLigado[]; busqueda?: BusquedaSecop }>(
      this.cfg.url(`/presupuesto/api/formulaciones/${id}/contratos/${qs}`));
  }

  enlazar(id: number, id_contrato_secop: string):
      Observable<{ numero: string; contrato_creado: boolean; contratos: ContratoLigado[] }> {
    return this.http.post<{ numero: string; contrato_creado: boolean; contratos: ContratoLigado[] }>(
      this.cfg.url(`/presupuesto/api/formulaciones/${id}/contratos/`),
      { id_contrato_secop });
  }

  desenlazar(id: number, contrato_id: number, motivo?: string):
      Observable<{ contratos: ContratoLigado[] }> {
    return this.http.request<{ contratos: ContratoLigado[] }>(
      'delete', this.cfg.url(`/presupuesto/api/formulaciones/${id}/contratos/`),
      { body: { contrato_id, motivo } });
  }
}
