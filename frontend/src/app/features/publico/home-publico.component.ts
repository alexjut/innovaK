import { HttpClient } from '@angular/common/http';
import { Component, OnInit, inject, signal } from '@angular/core';
import { RouterLink } from '@angular/router';
import { ConfigService } from '../../core/config/config.service';

// ---------------------------------------------------------------------------
// Home PÚBLICO — lo que ve quien llega a `/app/` sin usuario.
//
// Por qué existe: la raíz estaba detrás del authGuard, así que un ente que
// recibía la URL pelada caía en un formulario de contraseña. Ahora el visitante
// anónimo entra a una bienvenida y el funcionario sigue teniendo su puerta
// ("Ingresar"), que es la misma de siempre.
//
// Sin authGuard y sin LayoutComponent a propósito: la barra lateral y el menú
// de usuario asumen sesión, y acá no hay ninguna. Todo lo que se ofrece es
// público de verdad — el mapa de transparencia y las encuestas de percepción
// que ya están abiertas. Ninguna gestión interna, ningún nombre de funcionario.
// ---------------------------------------------------------------------------

interface EncuestaAbierta {
  slug: string;
  nombre: string;
  tipo?: string | null;
  vigencia: number;
  fecha_inicio?: string | null;
  fecha_fin?: string | null;
  lugar?: string | null;
}

@Component({
  standalone: true,
  selector: 'app-home-publico',
  imports: [RouterLink],
  template: `
    <div class="home">
      <!-- ── Saludo ──────────────────────────────────────────────── -->
      <header class="hero">
        <div class="hero__inner">
          <div class="hero__kenny">
            <!-- Ruta RELATIVA a propósito: resuelve contra <base href="/app/">.
                 Con "/kenny/…" el navegador la pide en la raíz del dominio y da
                 404 — Kenny no aparece y la bienvenida queda coja. -->
            <img
              src="kenny/exp-alegre.png"
              alt="Kenny, la mascota de la Alcaldía Local de Kennedy, saludando"
              width="200"
              height="200"
            />
          </div>

          <div class="hero__texto">
            <p class="hero__hola">¡Hola! Soy <strong>Kenny</strong> 👋</p>
            <h1 class="hero__titulo">
              Bienvenido a la <span>Alcaldía Local de Kennedy</span>
            </h1>
            <p class="hero__sub">
              Acá puedes consultar lo que hacemos en el territorio y dejarnos tu
              opinión. No necesitas usuario ni contraseña.
            </p>

            <div class="hero__acciones">
              <a routerLink="/mapa" class="btn btn--principal">
                <span aria-hidden="true">🗺️</span> Ver el mapa de Kennedy
              </a>
              <a routerLink="/auth/login" class="btn btn--secundario">
                <span aria-hidden="true">🔑</span> Ingresar
              </a>
            </div>
            <p class="hero__nota">
              ¿Trabajas en la Alcaldía? Entra con tu usuario desde «Ingresar».
            </p>
          </div>
        </div>
      </header>

      <main class="contenido">
        <!-- ── El mapa, que es la puerta principal ───────────────── -->
        <section class="bloque">
          <a routerLink="/mapa" class="mapa-card">
            <div class="mapa-card__icono" aria-hidden="true">🗺️</div>
            <div class="mapa-card__texto">
              <h2>Mapa de Kennedy</h2>
              <p>
                Escuelas de cultura y deporte, parques y actividades, barrio por
                barrio y UPZ por UPZ. Es la vista de transparencia ciudadana:
                se abre sin credenciales.
              </p>
              <span class="mapa-card__cta">Abrir el mapa →</span>
            </div>
          </a>
        </section>

        <!-- ── Encuestas abiertas ────────────────────────────────── -->
        <section class="bloque">
          <h2 class="bloque__titulo">Encuestas abiertas</h2>

          @if (cargando()) {
            <p class="estado">Buscando encuestas…</p>
          } @else if (error()) {
            <p class="estado estado--error">
              No pudimos cargar las encuestas en este momento.
              <button type="button" class="relink" (click)="cargar()">Reintentar</button>
            </p>
          } @else if (encuestas().length === 0) {
            <p class="estado">
              Ahora mismo no hay encuestas abiertas. Cuando haya un festival en
              curso, aparecerá acá — o escanea el código QR del evento.
            </p>
          } @else {
            <ul class="encuestas">
              @for (e of encuestas(); track e.slug) {
                <li class="encuesta">
                  <a [routerLink]="['/p/festival-percepcion', e.slug]">
                    <span class="encuesta__tipo">{{ e.tipo || 'Festival' }}</span>
                    <span class="encuesta__nombre">{{ e.nombre }}</span>
                    @if (e.lugar) {
                      <span class="encuesta__meta">📍 {{ e.lugar }}</span>
                    }
                    <span class="encuesta__cta">Contestar la encuesta →</span>
                  </a>
                </li>
              }
            </ul>
          }
        </section>

        <!-- ── Qué es innovaK ────────────────────────────────────── -->
        <section class="bloque">
          <h2 class="bloque__titulo">¿Qué es innovaK?</h2>
          <p class="prosa">
            <strong>innovaK</strong> es el sistema con el que la Alcaldía Local
            de Kennedy gestiona lo que pasa en la localidad: los proyectos y su
            presupuesto, las actividades culturales y deportivas, y las personas
            que participan en ellas.
          </p>
          <p class="prosa">
            La mayor parte es de uso interno de los funcionarios. Lo que ves acá
            es la parte pública: el mapa del territorio y los espacios donde tu
            opinión entra directo al sistema.
          </p>
        </section>
      </main>

      <footer class="pie">
        <img src="kenny/exp-atento.png" alt="" width="40" height="40" aria-hidden="true" />
        <span>Alcaldía Local de Kennedy · Bogotá D.C.</span>
      </footer>
    </div>
  `,
  styles: [
    `
      $rojo: #d6001c;
      $rojo-osc: #b50015;
      $amarillo: #ffc72c;
      $grad: linear-gradient(135deg, #{$rojo-osc} 0%, #{$rojo} 60%, #ff1f38 100%);
      $tinta: #1f2937;
      $gris: #6b7280;

      :host {
        display: block;
        min-height: 100vh;
        background: #f8fafc;
        color: $tinta;
        font-family: system-ui, -apple-system, 'Segoe UI', Roboto, sans-serif;
      }

      /* ── Saludo ─────────────────────────────────────────────── */
      .hero {
        background: $grad;
        color: #fff;
        padding: 2.5rem 1.25rem 3.25rem;
        position: relative;
        overflow: hidden;

        /* Franja amarilla institucional al pie del bloque rojo. */
        &::after {
          content: '';
          position: absolute;
          left: 0;
          right: 0;
          bottom: 0;
          height: 6px;
          background: $amarillo;
        }
      }

      .hero__inner {
        max-width: 1000px;
        margin: 0 auto;
        display: flex;
        align-items: center;
        gap: 2rem;
        flex-wrap: wrap;
        justify-content: center;
      }

      .hero__kenny {
        flex: 0 0 auto;
        img {
          display: block;
          width: 200px;
          height: auto;
          filter: drop-shadow(0 12px 24px rgba(0, 0, 0, 0.25));
          animation: saludo 3.2s ease-in-out infinite;
          transform-origin: 60% 90%;
        }
      }

      /* Un balanceo corto y suave: da vida sin volverse una distracción. */
      @keyframes saludo {
        0%,
        70%,
        100% {
          transform: rotate(0deg);
        }
        78% {
          transform: rotate(-5deg);
        }
        86% {
          transform: rotate(5deg);
        }
        94% {
          transform: rotate(-2deg);
        }
      }

      /* Respeta a quien pidió no ver movimiento (mareo, vestibular). */
      @media (prefers-reduced-motion: reduce) {
        .hero__kenny img {
          animation: none;
        }
      }

      .hero__texto {
        flex: 1 1 380px;
        min-width: 280px;
      }

      .hero__hola {
        margin: 0 0 0.35rem;
        font-size: 1.05rem;
        opacity: 0.95;
      }

      .hero__titulo {
        margin: 0 0 0.75rem;
        font-size: clamp(1.6rem, 4vw, 2.4rem);
        line-height: 1.15;
        font-weight: 800;

        span {
          display: block;
          color: $amarillo;
        }
      }

      .hero__sub {
        margin: 0 0 1.5rem;
        font-size: 1.05rem;
        line-height: 1.5;
        max-width: 46ch;
        opacity: 0.95;
      }

      .hero__acciones {
        display: flex;
        gap: 0.75rem;
        flex-wrap: wrap;
      }

      .hero__nota {
        margin: 0.9rem 0 0;
        font-size: 0.85rem;
        opacity: 0.8;
      }

      .btn {
        display: inline-flex;
        align-items: center;
        gap: 0.5rem;
        padding: 0.8rem 1.4rem;
        border-radius: 999px;
        font-weight: 700;
        font-size: 1rem;
        text-decoration: none;
        transition: transform 0.15s ease, box-shadow 0.15s ease;

        &:hover {
          transform: translateY(-2px);
        }
        &:focus-visible {
          outline: 3px solid #fff;
          outline-offset: 3px;
        }
      }

      .btn--principal {
        background: $amarillo;
        color: #3a2a00;
        box-shadow: 0 8px 20px rgba(0, 0, 0, 0.22);
      }

      .btn--secundario {
        background: rgba(255, 255, 255, 0.14);
        color: #fff;
        border: 2px solid rgba(255, 255, 255, 0.55);
      }

      /* ── Contenido ──────────────────────────────────────────── */
      .contenido {
        max-width: 1000px;
        margin: 0 auto;
        padding: 2.25rem 1.25rem 1rem;
      }

      .bloque {
        margin-bottom: 2.5rem;
      }

      .bloque__titulo {
        margin: 0 0 1rem;
        font-size: 1.3rem;
        font-weight: 800;
        color: $tinta;

        /* Guiño de marca sin cargar la página de color. */
        &::before {
          content: '';
          display: inline-block;
          width: 5px;
          height: 1.05em;
          background: $rojo;
          border-radius: 3px;
          margin-right: 0.6rem;
          vertical-align: -0.15em;
        }
      }

      .mapa-card {
        display: flex;
        align-items: center;
        gap: 1.25rem;
        padding: 1.5rem;
        background: #fff;
        border: 1px solid #e5e7eb;
        border-left: 6px solid $rojo;
        border-radius: 16px;
        text-decoration: none;
        color: inherit;
        box-shadow: 0 2px 10px rgba(0, 0, 0, 0.05);
        transition: transform 0.15s ease, box-shadow 0.15s ease;

        &:hover {
          transform: translateY(-3px);
          box-shadow: 0 12px 28px rgba(0, 0, 0, 0.1);
        }
        &:focus-visible {
          outline: 3px solid $rojo;
          outline-offset: 3px;
        }

        h2 {
          margin: 0 0 0.4rem;
          font-size: 1.25rem;
          font-weight: 800;
        }
        p {
          margin: 0 0 0.6rem;
          color: $gris;
          line-height: 1.5;
        }
      }

      .mapa-card__icono {
        font-size: 2.75rem;
        line-height: 1;
      }

      .mapa-card__cta {
        font-weight: 700;
        color: $rojo;
      }

      .encuestas {
        list-style: none;
        margin: 0;
        padding: 0;
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
        gap: 1rem;
      }

      .encuesta a {
        display: flex;
        flex-direction: column;
        gap: 0.35rem;
        height: 100%;
        padding: 1.15rem;
        background: #fff;
        border: 1px solid #e5e7eb;
        border-radius: 14px;
        text-decoration: none;
        color: inherit;
        transition: transform 0.15s ease, box-shadow 0.15s ease;

        &:hover {
          transform: translateY(-3px);
          box-shadow: 0 10px 24px rgba(0, 0, 0, 0.09);
        }
        &:focus-visible {
          outline: 3px solid $rojo;
          outline-offset: 3px;
        }
      }

      .encuesta__tipo {
        align-self: flex-start;
        font-size: 0.72rem;
        font-weight: 800;
        letter-spacing: 0.04em;
        text-transform: uppercase;
        color: #92400e;
        background: rgba($amarillo, 0.28);
        padding: 0.2rem 0.6rem;
        border-radius: 999px;
      }

      .encuesta__nombre {
        font-weight: 700;
        font-size: 1.05rem;
        line-height: 1.3;
      }

      .encuesta__meta {
        font-size: 0.85rem;
        color: $gris;
      }

      .encuesta__cta {
        margin-top: auto;
        padding-top: 0.5rem;
        font-weight: 700;
        color: $rojo;
        font-size: 0.9rem;
      }

      .estado {
        margin: 0;
        padding: 1.1rem 1.25rem;
        background: #fff;
        border: 1px dashed #d1d5db;
        border-radius: 12px;
        color: $gris;
        line-height: 1.5;
      }

      .estado--error {
        border-color: rgba($rojo, 0.4);
        color: $rojo-osc;
      }

      .relink {
        margin-left: 0.5rem;
        border: 0;
        background: none;
        padding: 0;
        font: inherit;
        font-weight: 700;
        color: $rojo;
        text-decoration: underline;
        cursor: pointer;
      }

      .prosa {
        margin: 0 0 0.85rem;
        line-height: 1.65;
        color: #374151;
        max-width: 68ch;
      }

      /* ── Pie ────────────────────────────────────────────────── */
      .pie {
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 0.6rem;
        padding: 1.5rem 1.25rem 2.25rem;
        color: $gris;
        font-size: 0.9rem;
        border-top: 1px solid #e5e7eb;
        margin-top: 1rem;

        img {
          width: 40px;
          height: auto;
        }
      }

      @media (max-width: 640px) {
        .hero {
          padding: 2rem 1rem 2.75rem;
          text-align: center;
        }
        .hero__kenny img {
          width: 150px;
        }
        .hero__acciones {
          justify-content: center;
        }
        .hero__sub {
          margin-inline: auto;
        }
        .mapa-card {
          flex-direction: column;
          text-align: center;
        }
      }
    `,
  ],
})
export class HomePublicoComponent implements OnInit {
  private readonly http = inject(HttpClient);
  private readonly cfg = inject(ConfigService);

  readonly encuestas = signal<EncuestaAbierta[]>([]);
  readonly cargando = signal(true);
  readonly error = signal(false);

  ngOnInit(): void {
    this.cargar();
  }

  /** Encuestas de percepción abiertas. Endpoint público (AllowAny). */
  cargar(): void {
    this.cargando.set(true);
    this.error.set(false);
    this.http
      .get<{ encuestas: EncuestaAbierta[] }>(
        this.cfg.url('/festivales/api/percepcion/abiertas/'),
      )
      .subscribe({
        next: (r) => {
          this.encuestas.set(r.encuestas ?? []);
          this.cargando.set(false);
        },
        // Que no haya encuestas no puede romper la bienvenida: el mapa y la
        // presentación siguen sirviendo, y el bloque muestra su propio aviso.
        error: () => {
          this.error.set(true);
          this.cargando.set(false);
        },
      });
  }
}
