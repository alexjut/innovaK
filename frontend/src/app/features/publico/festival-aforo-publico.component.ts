import { HttpClient } from '@angular/common/http';
import { Component, OnInit, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { CommonModule } from '@angular/common';
import { ActivatedRoute } from '@angular/router';
import { ConfigService } from '../../core/config/config.service';

interface Opcion { value: string | number; label: string; }
interface AforoContexto {
  evento_id: number;
  acto_nombre: string;
  festival_nombre: string | null;
  fecha_inicio: string | null;
  aforo_actual: number;
  aforo_proyectado: number | null;
  sexos: Opcion[];
  rangos_etarios: Opcion[];
}

/**
 * Form público de AFORO por QR (PR-D). El ciudadano escanea el QR del acto
 * y registra su asistencia. Contador en tiempo real. Caracterización mínima
 * OPCIONAL (un toque = +1 anónimo). Sin authGuard; token QR vía interceptor.
 */
@Component({
  standalone: true,
  selector: 'app-festival-aforo-publico',
  imports: [CommonModule, FormsModule],
  template: `
    <div class="wrap">
      @if (loading()) { <p class="info">Cargando…</p> }
      @if (error()) { <div class="bar bar--err">{{ error() }}</div> }

      @if (ctx(); as c) {
        <header class="head">
          @if (c.festival_nombre) { <span class="fest">{{ c.festival_nombre }}</span> }
          <h1>{{ c.acto_nombre }}</h1>
          @if (c.fecha_inicio) { <span class="fecha"><i class="fa fa-calendar"></i> {{ c.fecha_inicio }}</span> }
        </header>

        <div class="contador">
          <span class="contador__n">{{ aforo() }}</span>
          <span class="contador__l">
            asistentes registrados
            @if (c.aforo_proyectado) { <small>de {{ c.aforo_proyectado }} proyectados</small> }
          </span>
          @if (c.aforo_proyectado) {
            <div class="bar-prog"><div class="bar-prog__fill" [style.width.%]="pct(c)"></div></div>
          }
        </div>

        @if (okMsg()) { <div class="bar bar--ok">{{ okMsg() }}</div> }

        <button class="ui-btn ui-btn--primary big" (click)="registrar(true)" [disabled]="saving()">
          <i class="fa fa-plus"></i> {{ saving() ? 'Registrando…' : 'Sumar 1 asistente' }}
        </button>

        <details class="detalle">
          <summary>Registrar con datos (opcional)</summary>
          <div class="form">
            <label>Documento
              <input type="text" inputmode="numeric" [(ngModel)]="f.documento" name="doc" placeholder="Cédula (opcional)">
            </label>
            <label>Nombre
              <input type="text" [(ngModel)]="f.nombre" name="nom" placeholder="Nombre (opcional)">
            </label>
            <label>Sexo
              <select [(ngModel)]="f.sexo" name="sexo">
                <option [ngValue]="''">— Sin especificar —</option>
                @for (s of c.sexos; track s.value) { <option [ngValue]="s.value">{{ s.label }}</option> }
              </select>
            </label>
            <label>Rango de edad
              <select [(ngModel)]="f.rango_etario_codigo" name="rango">
                <option [ngValue]="null">— Sin especificar —</option>
                @for (r of c.rangos_etarios; track r.value) { <option [ngValue]="r.value">{{ r.label }}</option> }
              </select>
            </label>
            <label>Localidad / barrio
              <input type="text" [(ngModel)]="f.localidad_texto" name="loc" placeholder="Opcional">
            </label>
            <button class="ui-btn ui-btn--primary" (click)="registrar(false)" [disabled]="saving()">
              <i class="fa fa-user-check"></i> Registrar asistente
            </button>
          </div>
        </details>
      }
    </div>
  `,
  styles: [`
    :host { display: block; }
    .wrap { max-width: 460px; margin: 0 auto; padding: 16px; }
    .head { text-align: center; margin-bottom: 16px; }
    .fest { display: block; color: #0D9488; font-weight: 600; font-size: .85rem; }
    .head h1 { margin: 4px 0; font-size: 1.4rem; color: #111827; }
    .fecha { color: #6B7280; font-size: .85rem; }
    .contador { background: #fff; border: 2px solid #0D9488; border-radius: 16px; padding: 24px; text-align: center; margin-bottom: 16px; }
    .contador__n { display: block; font-size: 3.5rem; font-weight: 800; color: #0D9488; line-height: 1; }
    .contador__l { color: #374151; font-size: .9rem; }
    .contador__l small { display: block; color: #6B7280; }
    .bar-prog { height: 10px; background: #E5E7EB; border-radius: 99px; overflow: hidden; margin-top: 12px; }
    .bar-prog__fill { height: 100%; background: #0D9488; transition: width .4s; }
    .big { width: 100%; font-size: 1.1rem; padding: 16px; margin-bottom: 16px; }
    .detalle { background: #fff; border: 1px solid #E5E7EB; border-radius: 12px; padding: 12px 16px; }
    .detalle summary { cursor: pointer; font-weight: 600; color: #374151; }
    .form { display: flex; flex-direction: column; gap: 10px; margin-top: 12px; }
    .form label { display: flex; flex-direction: column; gap: 4px; font-size: .85rem; color: #6B7280; font-weight: 600; }
    .form input, .form select { padding: 10px; border: 1px solid #D1D5DB; border-radius: 8px; font-size: 1rem; font-family: inherit; }
    .form button { margin-top: 8px; }
    .bar { padding: 10px 14px; border-radius: 8px; margin-bottom: 12px; font-size: .9rem; }
    .bar--ok { background: #DCFCE7; color: #166534; }
    .bar--err { background: #FEE2E2; color: #991B1B; }
    .info { text-align: center; color: #6B7280; }
  `],
})
export class FestivalAforoPublicoComponent implements OnInit {
  private http = inject(HttpClient);
  private cfg = inject(ConfigService);
  private route = inject(ActivatedRoute);

  loading = signal(true);
  saving = signal(false);
  error = signal('');
  okMsg = signal('');
  ctx = signal<AforoContexto | null>(null);
  aforo = signal(0);

  f: { documento: string; nombre: string; sexo: string; rango_etario_codigo: number | null; localidad_texto: string } = {
    documento: '', nombre: '', sexo: '', rango_etario_codigo: null, localidad_texto: '',
  };

  private id = 0;

  ngOnInit(): void {
    this.id = Number(this.route.snapshot.paramMap.get('eventoId'));
    if (!this.id) { this.error.set('Acto no válido.'); this.loading.set(false); return; }
    this.http.get<AforoContexto>(this.cfg.url(`/festivales/api/aforo/${this.id}/`)).subscribe({
      next: (c) => { this.ctx.set(c); this.aforo.set(c.aforo_actual); this.loading.set(false); },
      error: (e) => { this.loading.set(false); this.error.set(this.msg(e)); },
    });
  }

  pct(c: AforoContexto): number {
    if (!c.aforo_proyectado) return 0;
    return Math.min(100, Math.round((this.aforo() / c.aforo_proyectado) * 100));
  }

  registrar(rapido: boolean): void {
    this.saving.set(true);
    this.error.set('');
    this.okMsg.set('');
    const body = rapido ? {} : {
      documento: this.f.documento || undefined,
      nombre: this.f.nombre || undefined,
      sexo: this.f.sexo || undefined,
      rango_etario_codigo: this.f.rango_etario_codigo || undefined,
      localidad_texto: this.f.localidad_texto || undefined,
    };
    this.http.post<{ ok: boolean; aforo_actual: number }>(
      this.cfg.url(`/festivales/api/aforo/${this.id}/registrar/`), body,
    ).subscribe({
      next: (r) => {
        this.saving.set(false);
        this.aforo.set(r.aforo_actual);
        this.okMsg.set('¡Registrado! Gracias por asistir.');
        this.f = { documento: '', nombre: '', sexo: '', rango_etario_codigo: null, localidad_texto: '' };
        setTimeout(() => this.okMsg.set(''), 2500);
      },
      error: (e) => {
        this.saving.set(false);
        if (e?.status === 409 && e?.error?.aforo_actual != null) this.aforo.set(e.error.aforo_actual);
        this.error.set(this.msg(e));
        setTimeout(() => this.error.set(''), 3500);
      },
    });
  }

  private msg(e: { error?: { detail?: string }; status?: number; message?: string }): string {
    if (e?.error?.detail) return e.error.detail;
    if (e?.status === 404) return 'Acto no encontrado.';
    return e?.message || 'No se pudo registrar. Intenta de nuevo.';
  }
}
