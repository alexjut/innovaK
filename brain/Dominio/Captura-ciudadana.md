# Captura ciudadana

Cómo entra al sistema lo que llena un ciudadano o un funcionario en terreno.
Cinco módulos distintos comparten el mismo patrón.

## El patrón, siempre igual

```
Evento (tipo_evento) → QR → /app/p/<flujo>/<evento_id>?t=<token>
   → endpoint DRF público → servicio → SQL + firma cifrada a Mongo
   → al validar: AvanceIndicador (+1 al KPI de la actividad del evento)
```

1. Endpoint DRF con `QrTokenPermission`.
2. Ruta Angular en `/app/p/*`, **sin** guard de autenticación.
3. `_url_publica_por_tipo()` apunta el QR ahí.
4. La vista Django vieja **redirige** — los QR impresos no se rompen.

## Quiénes lo usan

`banco_iniciativas` · caracterización (6 sectores) ·
Jóvenes a la E · entregas · festivales (percepción) · captura genérica.

## El motor genérico

`CAPTURA_SCHEMAS` (`apps/login/services/captura_schema.py`): un tipo de captura
nuevo es **una entrada en un dict**. Sin DDL y sin componente nuevo — el
frontend renderiza por `@switch(field.type)`. Los datos van a `captura_generica`
(JSONB + columnas fijas para búsqueda y dedup).

Úsalo antes de crear una tabla nueva. *Constitución VIII.*

## Lo público sigue público

El ciudadano no tiene cuenta. Los formularios de QR son `AllowAny` con token
HMAC del evento.

> **`QR_TOKEN_ENFORCE` está en modo suave**: sin token se registra un aviso pero
> **no** se bloquea, para no romper los QR ya impresos. Pasar a estricto exige
> reimprimirlos primero.

## Firma y documentos sensibles

Van cifrados a Mongo vía `apps.documentos.services.mongo_storage`, con `owner`
que identifica la fila SQL. **Nunca** en el repositorio, nunca en texto plano.

Relacionado: [[Mapa-del-sistema]] · [[Indicador]] · [[Permisos-y-roles]]
