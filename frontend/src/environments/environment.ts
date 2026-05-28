/**
 * Environment de desarrollo local.
 *
 * Apunta al backend Django sirviendo en :8034 (innova_nginx delante
 * de innova_k Gunicorn :8032).
 *
 * Para reutilizar este frontend en otra alcaldía: cambia las constantes
 * `appName`, `alcaldiaName`, `apiBaseUrl`. Cero código tocado.
 */
export const environment = {
  production: false,
  appName: 'innovaK',
  alcaldiaName: 'Alcaldía Local de Kennedy',
  apiBaseUrl: 'http://localhost:8034',
  apiSchemaUrl: 'http://localhost:8034/api/schema/',
  jwtAccessKey: 'innovak_access_token',
  jwtRefreshKey: 'innovak_refresh_token',
  /** Endpoint para validar conexión con el backend en boot. */
  pingEndpoint: '/api/schema/',
};
