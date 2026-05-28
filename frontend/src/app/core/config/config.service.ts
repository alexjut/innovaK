import { Injectable } from '@angular/core';
import { environment } from '../../../environments/environment';

/**
 * Servicio singleton que expone la configuración global del frontend.
 *
 * Toda referencia a environment.ts debe pasar por aquí — los componentes
 * NO importan environment directamente. Así si el día de mañana cambia
 * cómo se carga la configuración (p.ej. desde un endpoint /config/),
 * solo este servicio cambia.
 */
@Injectable({ providedIn: 'root' })
export class ConfigService {
  readonly production = environment.production;
  readonly appName = environment.appName;
  readonly alcaldiaName = environment.alcaldiaName;
  readonly apiBaseUrl = environment.apiBaseUrl;
  readonly apiSchemaUrl = environment.apiSchemaUrl;
  readonly jwtAccessKey = environment.jwtAccessKey;
  readonly jwtRefreshKey = environment.jwtRefreshKey;
  readonly pingEndpoint = environment.pingEndpoint;

  /** Construye URL absoluta concatenando el path al apiBaseUrl. */
  url(path: string): string {
    const base = this.apiBaseUrl.replace(/\/$/, '');
    const clean = path.startsWith('/') ? path : `/${path}`;
    return `${base}${clean}`;
  }
}
