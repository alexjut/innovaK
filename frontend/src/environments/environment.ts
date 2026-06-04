/**
 * Environment de desarrollo / servido desde Django.
 *
 * `apiBaseUrl` queda vacío para que TODAS las peticiones HTTP usen
 * URLs relativas al mismo origen donde está servido el index.html.
 * Esto evita CORS por completo cuando Angular se sirve desde Django
 * (PR-5: `/app/*` servido por `apps.login.views.spa`).
 *
 * Si en algún momento necesitas hacer dev separado con `ng serve`
 * apuntando a un backend remoto, cambia esta constante a la URL
 * absoluta de ese backend.
 */
export const environment = {
  production: false,
  appName: 'innovaK',
  alcaldiaName: 'Alcaldía Local de Kennedy',
  apiBaseUrl: '',
  apiSchemaUrl: '/api/schema/',
  jwtAccessKey: 'innovak_access_token',
  jwtRefreshKey: 'innovak_refresh_token',
  /** Endpoint para validar conexión con el backend en boot. */
  pingEndpoint: '/api/schema/',
};
