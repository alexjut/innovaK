import { CommonModule } from '@angular/common';
import { HttpClient } from '@angular/common/http';
import { Component, inject, signal } from '@angular/core';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { ConfigService } from '../../core/config/config.service';

interface QRData {
  evento: {
    id: number;
    nombre: string;
    fecha_inicio: string | null;
    fecha_fin: string | null;
    tipo: string | null;
    tipo_codigo: string | null;
    funcionario: string | null;
    activo: boolean;
  };
  url_publica: string;
  url_publica_path: string;
  qr_base64: string;
}

/**
 * Vista del QR del evento (reemplaza la página Django `eventos/qr_evento.html`).
 * El funcionario llega aquí desde Actividades / Eventos para imprimir o
 * compartir el QR. El código QR apunta a la URL pública del form (que para
 * Banco ya es el form Angular `/app/p/banco/<id>`).
 */
@Component({
  selector: 'app-evento-qr',
  standalone: true,
  imports: [CommonModule, RouterLink],
  template: `
    <div class="qr-page">
      @if (loading()) {
        <div class="qr-state">
          <div class="spinner"></div>
          <p>Generando código QR…</p>
        </div>
      } @else if (error()) {
        <div class="qr-state qr-state--error">
          <i class="fa fa-triangle-exclamation"></i>
          <p>{{ error() }}</p>
          <a routerLink="/actividades" class="btn btn--ghost">Volver a Actividades</a>
        </div>
      } @else if (data()) {
       @if (data(); as d) {
        <div class="qr-card">
          <header class="qr-card__head">
            <div class="qr-card__brand">
              <i class="fa fa-qrcode"></i>
              <span>Alcaldía Local de Kennedy</span>
            </div>
            @if (!d.evento.activo) {
              <span class="chip chip--off">Inactivo</span>
            } @else {
              <span class="chip chip--on">Activo</span>
            }
          </header>

          <h1 class="qr-card__title">{{ d.evento.nombre }}</h1>
          <div class="qr-card__meta">
            @if (d.evento.tipo) { <span><i class="fa fa-tag"></i> {{ d.evento.tipo }}</span> }
            @if (d.evento.fecha_inicio) {
              <span><i class="fa fa-calendar"></i> {{ d.evento.fecha_inicio }}<ng-container *ngIf="d.evento.fecha_fin"> → {{ d.evento.fecha_fin }}</ng-container></span>
            }
            @if (d.evento.funcionario) { <span><i class="fa fa-user"></i> {{ d.evento.funcionario }}</span> }
          </div>

          <div class="qr-card__img">
            <img [src]="'data:image/png;base64,' + d.qr_base64" alt="Código QR del evento" />
          </div>

          <p class="qr-card__hint">
            <i class="fa fa-mobile-screen"></i>
            Escanea este código con la cámara del celular para abrir el formulario.
          </p>

          <div class="qr-card__url">
            <input type="text" readonly [value]="d.url_publica" #urlInput />
            <button type="button" class="btn btn--icon" (click)="copiar(d.url_publica)" title="Copiar enlace">
              <i class="fa" [class.fa-copy]="!copiado()" [class.fa-check]="copiado()"></i>
            </button>
          </div>

          <div class="qr-card__actions">
            <a [href]="d.url_publica_path" target="_blank" rel="noopener" class="btn btn--primary">
              <i class="fa fa-up-right-from-square"></i> Abrir formulario
            </a>
            <button type="button" class="btn btn--ghost" (click)="imprimir()">
              <i class="fa fa-print"></i> Imprimir
            </button>
          </div>
        </div>
       }
      }
    </div>
  `,
  styles: [`
    :host { display: block; }
    .qr-page {
      min-height: 70vh; display: flex; align-items: center; justify-content: center;
      padding: 24px;
    }
    .qr-state {
      text-align: center; color: #6b7280; display: flex; flex-direction: column;
      align-items: center; gap: 14px;
    }
    .qr-state--error i { font-size: 2.4rem; color: #D6001C; }
    .spinner {
      width: 42px; height: 42px; border: 4px solid #e5e7eb; border-top-color: #B50015;
      border-radius: 50%; animation: spin 0.8s linear infinite;
    }
    @keyframes spin { to { transform: rotate(360deg); } }
    .qr-card {
      background: #fff; border-radius: 22px; max-width: 440px; width: 100%;
      padding: 28px 28px 32px; box-shadow: 0 20px 50px rgba(0,0,0,.12);
      border: 1px solid #f1f1f3;
    }
    .qr-card__head {
      display: flex; align-items: center; justify-content: space-between; margin-bottom: 18px;
    }
    .qr-card__brand {
      display: flex; align-items: center; gap: 9px; color: #B50015; font-weight: 700;
      font-size: .82rem; letter-spacing: .2px;
    }
    .qr-card__brand i { font-size: 1.15rem; }
    .chip {
      font-size: .72rem; font-weight: 700; padding: 4px 12px; border-radius: 999px;
    }
    .chip--on { background: #ECFDF3; color: #027A48; }
    .chip--off { background: #FEF3F2; color: #B42318; }
    .qr-card__title { margin: 0 0 10px; font-size: 1.3rem; color: #1f2937; line-height: 1.25; }
    .qr-card__meta {
      display: flex; flex-wrap: wrap; gap: 8px 16px; margin-bottom: 22px;
      color: #6b7280; font-size: .85rem;
    }
    .qr-card__meta i { color: #9ca3af; margin-right: 4px; }
    .qr-card__img {
      background: #fafafa; border: 1px solid #f0f0f0; border-radius: 16px;
      padding: 18px; display: flex; justify-content: center; margin-bottom: 16px;
    }
    .qr-card__img img { width: 240px; height: 240px; image-rendering: pixelated; }
    .qr-card__hint {
      text-align: center; color: #6b7280; font-size: .85rem; margin: 0 0 18px;
    }
    .qr-card__hint i { color: #B50015; margin-right: 5px; }
    .qr-card__url {
      display: flex; gap: 8px; margin-bottom: 18px;
    }
    .qr-card__url input {
      flex: 1; min-width: 0; border: 1px solid #e5e7eb; border-radius: 10px;
      padding: 10px 12px; font-size: .82rem; color: #374151; background: #f9fafb;
    }
    .qr-card__actions { display: flex; gap: 10px; }
    .btn {
      display: inline-flex; align-items: center; justify-content: center; gap: 7px;
      border: none; border-radius: 11px; padding: 11px 16px; font-size: .88rem;
      font-weight: 600; cursor: pointer; text-decoration: none; transition: .15s;
    }
    .btn--primary { background: #B50015; color: #fff; flex: 1; }
    .btn--primary:hover { background: #930011; }
    .btn--ghost { background: #f3f4f6; color: #374151; }
    .btn--ghost:hover { background: #e5e7eb; }
    .btn--icon { background: #B50015; color: #fff; padding: 10px 13px; }
    @media print {
      .qr-card__actions, .qr-card__url .btn { display: none; }
      .qr-card { box-shadow: none; border: none; }
    }
  `],
})
export class EventoQrComponent {
  private http = inject(HttpClient);
  private cfg = inject(ConfigService);
  private route = inject(ActivatedRoute);

  loading = signal(true);
  error = signal<string | null>(null);
  data = signal<QRData | null>(null);
  copiado = signal(false);

  constructor() {
    const id = this.route.snapshot.paramMap.get('id');
    this.http.get<QRData>(this.cfg.url(`/api/eventos/${id}/qr/`)).subscribe({
      next: (d) => { this.data.set(d); this.loading.set(false); },
      error: () => {
        this.error.set('No se pudo cargar el código QR de este evento.');
        this.loading.set(false);
      },
    });
  }

  copiar(url: string): void {
    navigator.clipboard?.writeText(url).then(() => {
      this.copiado.set(true);
      setTimeout(() => this.copiado.set(false), 1800);
    });
  }

  imprimir(): void {
    window.print();
  }
}
