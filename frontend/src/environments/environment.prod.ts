/**
 * Environment de producción.
 *
 * Los placeholders `__ENV_*__` se sustituyen en runtime por el entrypoint
 * Docker (PR-15) o en build time por un script de CI. Esto permite que
 * el MISMO build de Angular sirva a múltiples alcaldías solo cambiando
 * variables de entorno al desplegar.
 *
 * Para Kennedy (default actual):
 *   APP_NAME=innovaK
 *   ALCALDIA_NAME="Alcaldía Local de Kennedy"
 *   API_BASE_URL=https://intranet.alcaldia-kennedy.gov.co
 *
 * Para otra alcaldía:
 *   APP_NAME=innovaB
 *   ALCALDIA_NAME="Alcaldía Local de Bosa"
 *   API_BASE_URL=https://intranet.alcaldia-bosa.gov.co
 */
export const environment = {
  production: true,
  appName: '__ENV_APP_NAME__',
  alcaldiaName: '__ENV_ALCALDIA_NAME__',
  apiBaseUrl: '__ENV_API_BASE_URL__',
  apiSchemaUrl: '__ENV_API_BASE_URL__/api/schema/',
  jwtAccessKey: 'innovak_access_token',
  jwtRefreshKey: 'innovak_refresh_token',
  pingEndpoint: '/api/schema/',
};
