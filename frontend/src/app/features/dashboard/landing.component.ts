import { CommonModule } from '@angular/common';
import { HttpClient } from '@angular/common/http';
import { Component, computed, inject, signal } from '@angular/core';
import { ConfigService } from '../../core/config/config.service';

interface PingState {
  status: 'idle' | 'loading' | 'ok' | 'error';
  message: string;
  durationMs: number;
}

@Component({
  standalone: true,
  selector: 'app-landing',
  imports: [CommonModule],
  template: `
    <div class="container">
      <header>
        <h1>{{ cfg.appName }}</h1>
        <p class="subtitle">{{ cfg.alcaldiaName }}</p>
      </header>

      <section class="card">
        <h2>Frontend Angular — Etapa D PR-1</h2>
        <p>
          Esta es la página inicial del frontend Angular de innovaK.
          Verifica la conexión con el backend pulsando el botón.
        </p>

        <button class="btn" (click)="ping()" [disabled]="state().status === 'loading'">
          @if (state().status === 'loading') {
            Verificando…
          } @else {
            Verificar conexión con backend
          }
        </button>

        @if (state().status !== 'idle') {
          <div class="result" [class.ok]="state().status === 'ok'" [class.err]="state().status === 'error'">
            <strong>{{ state().status === 'ok' ? '✅ OK' : '⚠️ Error' }}</strong>
            <span>{{ state().message }}</span>
            @if (state().durationMs > 0) {
              <small>{{ state().durationMs }} ms</small>
            }
          </div>
        }
      </section>

      <section class="card">
        <h3>Configuración detectada</h3>
        <dl>
          <dt>API base</dt><dd><code>{{ cfg.apiBaseUrl }}</code></dd>
          <dt>Schema OpenAPI</dt><dd><code>{{ cfg.apiSchemaUrl }}</code></dd>
          <dt>Producción</dt><dd>{{ cfg.production ? 'Sí' : 'No (dev)' }}</dd>
        </dl>
      </section>

      <footer>
        <p>
          Documentación: <code>docs/FRONTEND_ANGULAR.md</code> ·
          API Swagger: <a [href]="cfg.apiBaseUrl + '/api/docs/'" target="_blank">/api/docs/</a>
        </p>
      </footer>
    </div>
  `,
  styles: [`
    :host { display: block; padding: 2rem; max-width: 720px; margin: 0 auto;
            font-family: system-ui, -apple-system, sans-serif; color: #0f172a; }
    header h1 { margin: 0; font-size: 2rem; color: #0D9488; }
    .subtitle { margin: 0.25rem 0 2rem; color: #64748b; }
    .card { border: 1px solid #e2e8f0; border-radius: 8px; padding: 1.5rem;
            margin-bottom: 1rem; background: white; }
    .card h2, .card h3 { margin-top: 0; }
    .btn { background: #0D9488; color: white; border: 0; padding: 0.6rem 1.2rem;
           border-radius: 6px; cursor: pointer; font-size: 1rem; }
    .btn:disabled { opacity: 0.6; cursor: wait; }
    .btn:hover:not(:disabled) { background: #0B7A6E; }
    .result { margin-top: 1rem; padding: 0.75rem; border-radius: 6px;
              display: flex; gap: 0.75rem; align-items: center; flex-wrap: wrap; }
    .result.ok { background: #ecfdf5; color: #047857; }
    .result.err { background: #fef2f2; color: #b91c1c; }
    .result small { color: inherit; opacity: 0.75; }
    dl { display: grid; grid-template-columns: max-content 1fr; gap: 0.5rem 1rem; margin: 0; }
    dt { font-weight: 600; color: #64748b; }
    dd { margin: 0; }
    code { background: #f1f5f9; padding: 0.15rem 0.4rem; border-radius: 4px;
           font-size: 0.875rem; }
    footer { text-align: center; color: #64748b; font-size: 0.875rem; margin-top: 2rem; }
    a { color: #0D9488; }
  `],
})
export class LandingComponent {
  cfg = inject(ConfigService);
  private http = inject(HttpClient);

  state = signal<PingState>({ status: 'idle', message: '', durationMs: 0 });

  ping(): void {
    this.state.set({ status: 'loading', message: '', durationMs: 0 });
    const start = performance.now();

    this.http.get(this.cfg.url(this.cfg.pingEndpoint), { responseType: 'text' }).subscribe({
      next: () => {
        const ms = Math.round(performance.now() - start);
        this.state.set({
          status: 'ok',
          message: 'Backend respondió correctamente desde ' + this.cfg.apiBaseUrl,
          durationMs: ms,
        });
      },
      error: (e) => {
        const ms = Math.round(performance.now() - start);
        this.state.set({
          status: 'error',
          message: `No se pudo conectar al backend (${e?.status ?? 'sin status'}): ${e?.message ?? 'desconocido'}`,
          durationMs: ms,
        });
      },
    });
  }
}
