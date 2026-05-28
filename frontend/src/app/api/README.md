# API Client — innovaK Angular

Este directorio aloja los clientes HTTP tipados que consumen la API DRF
del backend Django (Etapa B/C del Plan Frontend).

## Estrategia híbrida

### Modo 1: Auto-generado (recomendado — requiere Java o Docker)

Cuando el host tiene Java 11+ o Docker, regenera todo desde el schema
OpenAPI publicado por el backend con:

```bash
npm run api:gen
```

(internamente ejecuta `openapi-generator-cli` con preset
`typescript-angular`.)

El comando lee `INNOVAK_API_SCHEMA_URL` (default
`http://localhost:8034/api/schema/`) y sobreescribe los archivos
generados.

**Convención:** los archivos generados NO se editan a mano. Si falta
un campo o un endpoint, se agrega en el backend → se regenera aquí.

### Modo 2: Manual (sin Java/Docker, default actual)

Mientras el host no tenga Java, cada PR de feature trae su propio
service mínimo tipado a mano dentro de `core/auth/` (auth ya existe)
o `features/<feature>/api/`.

Convención del service manual:

```typescript
// features/banco-iniciativas/api/inscripciones.api.ts
@Injectable({ providedIn: 'root' })
export class InscripcionesApi {
  private http = inject(HttpClient);
  private cfg = inject(ConfigService);

  list(filters: ListFilters): Observable<PaginatedResponse<Inscripcion>> {
    const params = new HttpParams({ fromObject: filters });
    return this.http.get<PaginatedResponse<Inscripcion>>(
      this.cfg.url('/banco-iniciativas/api/inscripciones/'),
      { params },
    );
  }
}
```

## Cuando habilitar Modo 1

Cuando se instale Java/Docker en CI o en la máquina de desarrollo, se
ejecuta una vez `npm run api:gen` y se commitean los archivos
auto-generados. A partir de ahí, cada cambio del schema requiere
re-correr el comando (lo hace el dev que toca el backend en su PR).

## Estado actual (PR-4 Etapa D)

- `core/auth/auth.service.ts` ya tiene los tipos `LoginRequest`,
  `LoginResponse` manualmente. NO regenerar mientras eso esté en
  uso (re-generaría duplicado).
- Próximos PRs (5..14) traen su feature service manual hasta que se
  active el codegen.
