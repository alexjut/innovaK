import { HttpClient } from '@angular/common/http';
import { CommonModule } from '@angular/common';
import { Component, OnInit, inject, signal } from '@angular/core';
import { ActivatedRoute } from '@angular/router';
import { ConfigService } from '../../core/config/config.service';

interface ActoPub { id: number; nombre: string; fecha_inicio: string | null; aforo: number; }
interface DiaPub { fecha: string; nombre: string | null; escenario: string | null; actos: ActoPub[]; }
interface FotoPub { id: number; url: string; descripcion: string | null; }
interface FichaPublica {
  nombre: string; tipo: string | null; estado_display: string;
  numero_edicion: number | null; vigencia: number; descripcion: string | null;
  fecha_inicio: string | null; fecha_fin: string | null; lugar: string | null;
  dias: DiaPub[]; fotos: FotoPub[]; aforo_total: number;
}

/**
 * Ficha PÚBLICA de un festival (PR-F). Read-only, por slug, sin login.
 * Muestra agenda + galería + aforo de un festival publicado. Las imágenes
 * se sirven públicas (solo de festivales publicados).
 */
@Component({
  standalone: true,
  selector: 'app-festival-publico',
  imports: [CommonModule],
  template: `
    <div class="page">
      @if (loading()) { <p class="info">Cargando…</p> }
      @if (error()) { <div class="bar">{{ error() }}</div> }

      @if (f(); as fest) {
        <header class="hero">
          @if (fest.tipo) { <span class="kicker">{{ fest.tipo }}</span> }
          <h1>{{ fest.nombre }}</h1>
          <p class="sub">
            @if (fest.numero_edicion) { <span>{{ fest.numero_edicion }}ª edición · </span> }
            <span>{{ fest.vigencia }}</span>
            @if (fest.fecha_inicio) { <span> · {{ fest.fecha_inicio }}@if (fest.fecha_fin) { — {{ fest.fecha_fin }} }</span> }
          </p>
          @if (fest.lugar) { <p class="lugar"><i class="fa fa-location-dot"></i> {{ fest.lugar }}</p> }
          @if (fest.aforo_total > 0) {
            <p class="aforo"><i class="fa fa-users"></i> {{ fest.aforo_total }} asistentes</p>
          }
        </header>

        @if (fest.descripcion) { <p class="desc">{{ fest.descripcion }}</p> }

        @if (fest.fotos.length > 0) {
          <section>
            <h2>Galería</h2>
            <div class="galeria">
              @for (foto of fest.fotos; track foto.id) {
                <figure>
                  <img [src]="url(foto.url)" [alt]="foto.descripcion || fest.nombre" loading="lazy">
                  @if (foto.descripcion) { <figcaption>{{ foto.descripcion }}</figcaption> }
                </figure>
              }
            </div>
          </section>
        }

        @if (fest.dias.length > 0) {
          <section>
            <h2>Programación</h2>
            <div class="agenda">
              @for (d of fest.dias; track d.fecha) {
                <article class="dia">
                  <div class="dia__cab">
                    <span class="dia__fecha">{{ d.fecha }}</span>
                    @if (d.nombre) { <span class="dia__nombre">{{ d.nombre }}</span> }
                  </div>
                  @if (d.escenario) { <p class="dia__esc"><i class="fa fa-location-dot"></i> {{ d.escenario }}</p> }
                  @if (d.actos.length > 0) {
                    <ul>
                      @for (a of d.actos; track a.id) {
                        <li>
                          <span class="acto">{{ a.nombre || 'Acto' }}</span>
                          @if (a.aforo > 0) { <span class="acto__aforo">{{ a.aforo }} asistentes</span> }
                        </li>
                      }
                    </ul>
                  } @else { <p class="vacio">Programación por confirmar.</p> }
                </article>
              }
            </div>
          </section>
        }

        <footer class="pie">Alcaldía Local de Kennedy · Cultura</footer>
      }
    </div>
  `,
  styles: [`
    :host { display: block; background: #0F172A; min-height: 100vh; }
    .page { max-width: 760px; margin: 0 auto; padding: 24px 16px 48px; color: #E2E8F0; }
    .info, .bar { color: #E2E8F0; text-align: center; padding: 16px; }
    .bar { background: #7F1D1D; border-radius: 8px; }
    .hero { text-align: center; padding: 24px 0; }
    .kicker { color: #2DD4BF; font-weight: 700; letter-spacing: .05em; text-transform: uppercase; font-size: .8rem; }
    .hero h1 { font-size: 2.2rem; margin: 8px 0; color: #fff; }
    .sub { color: #94A3B8; }
    .lugar, .aforo { color: #CBD5E1; font-size: .9rem; margin: 4px 0; }
    .aforo { color: #2DD4BF; }
    .desc { color: #CBD5E1; line-height: 1.6; white-space: pre-wrap; margin: 16px 0; }
    section { margin-top: 32px; }
    h2 { color: #fff; border-bottom: 2px solid #2DD4BF; padding-bottom: 6px; display: inline-block; }
    .galeria { display: grid; grid-template-columns: repeat(auto-fill, minmax(150px, 1fr)); gap: 12px; margin-top: 16px; }
    .galeria figure { margin: 0; border-radius: 12px; overflow: hidden; background: #1E293B; }
    .galeria img { width: 100%; height: 150px; object-fit: cover; display: block; }
    .galeria figcaption { padding: 8px; font-size: .75rem; color: #94A3B8; }
    .agenda { display: flex; flex-direction: column; gap: 12px; margin-top: 16px; }
    .dia { background: #1E293B; border-radius: 12px; padding: 16px; }
    .dia__cab { display: flex; align-items: baseline; gap: 10px; }
    .dia__fecha { color: #2DD4BF; font-weight: 700; }
    .dia__nombre { color: #fff; }
    .dia__esc { color: #94A3B8; font-size: .85rem; margin: 4px 0; }
    .dia ul { list-style: none; padding: 0; margin: 8px 0 0; }
    .dia li { display: flex; justify-content: space-between; padding: 6px 0; border-top: 1px solid #334155; color: #E2E8F0; }
    .acto__aforo { color: #2DD4BF; font-size: .8rem; }
    .vacio { color: #64748B; font-style: italic; font-size: .85rem; }
    .pie { text-align: center; color: #64748B; margin-top: 48px; font-size: .8rem; }
  `],
})
export class FestivalPublicoComponent implements OnInit {
  private http = inject(HttpClient);
  private cfg = inject(ConfigService);
  private route = inject(ActivatedRoute);

  loading = signal(true);
  error = signal('');
  f = signal<FichaPublica | null>(null);

  ngOnInit(): void {
    const slug = this.route.snapshot.paramMap.get('slug');
    if (!slug) { this.error.set('Festival no válido.'); this.loading.set(false); return; }
    this.http.get<FichaPublica>(this.cfg.url(`/festivales/api/publico/${slug}/`)).subscribe({
      next: (d) => { this.f.set(d); this.loading.set(false); },
      error: (e) => { this.loading.set(false); this.error.set(e?.error?.detail || 'Festival no encontrado o no publicado.'); },
    });
  }

  url(path: string): string { return this.cfg.url(path); }
}
