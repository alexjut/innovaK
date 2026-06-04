import { CommonModule } from '@angular/common';
import { Component, OnInit, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { LayoutService } from '../../core/layout/layout.service';
import { VotacionesApi } from './votaciones.api';
import { EventoVotacion } from './votaciones.types';

@Component({
  standalone: true,
  selector: 'app-votaciones-list',
  imports: [CommonModule, FormsModule, RouterLink],
  template: `
    <div class="page">
      <header class="page__header page__header--row">
        <div>
          <h1><i class="fa fa-vote-yea" aria-hidden="true"></i> Votaciones</h1>
          <p class="page__subtitle">Gestión de eventos de votación.</p>
        </div>
        <div class="head-acts">
          <a routerLink="/votaciones/votantes" class="ui-btn ui-btn--ghost">
            <i class="fa fa-users"></i> Votantes
          </a>
          <button class="ui-btn ui-btn--primary" (click)="abrirCrear.set(!abrirCrear())">
            <i class="fa fa-plus-circle"></i> Crear evento
          </button>
        </div>
      </header>

      @if (abrirCrear()) {
        <div class="crear-form">
          <h3>Nuevo evento de votación</h3>
          <div class="grid">
            <label class="full"><span>Nombre *</span>
              <input type="text" [(ngModel)]="nuevo.name" placeholder="Ej. Elecciones del Consejo"></label>
            <label><span>Inicio *</span>
              <input type="datetime-local" [(ngModel)]="nuevo.starts_at"></label>
            <label><span>Fin *</span>
              <input type="datetime-local" [(ngModel)]="nuevo.ends_at"></label>
            <label><span>Votos permitidos</span>
              <input type="number" min="1" max="20" [(ngModel)]="nuevo.votos_permitidos"></label>
          </div>
          <div class="acts">
            <button class="ui-btn ui-btn--ghost" (click)="abrirCrear.set(false)">Cancelar</button>
            <button class="ui-btn ui-btn--primary" [disabled]="guardando()" (click)="crear()">
              @if (guardando()) { Creando… } @else { Crear evento }
            </button>
          </div>
          @if (msgCrear()) { <p class="msg" [class.err]="errCrear()">{{ msgCrear() }}</p> }
        </div>
      }

      @if (loading()) {
        <div class="ui-info-bar ui-info-bar--info">Cargando…</div>
      }
      @if (!loading() && errorMsg()) {
        <div class="ui-info-bar ui-info-bar--danger">{{ errorMsg() }}</div>
      }
      @if (!loading() && !errorMsg() && eventos().length === 0) {
        <div class="ui-empty-state">
          <i class="fa fa-vote-yea" aria-hidden="true"></i>
          <p>No hay eventos de votación registrados.</p>
        </div>
      }
      @if (!loading() && !errorMsg() && eventos().length > 0) {
        <div class="vot-grid">
          @for (ev of eventos(); track ev.id) {
            <a [routerLink]="['/votaciones', ev.id]" class="vot-card"
               [style.border-top-color]="estado(ev).color">
              <div class="vot-card__head">
                <span class="vot-badge" [style.background]="estado(ev).color">
                  <i class="fa" [class]="estado(ev).icon"></i> {{ estado(ev).label }}
                </span>
              </div>
              <h3 class="vot-card__title">{{ ev.name }}</h3>
              <small class="dates">
                @if (ev.starts_at) {
                  {{ ev.starts_at | date:'shortDate' }} → {{ ev.ends_at | date:'shortDate' }}
                }
              </small>
              <div class="vot-stats">
                <div class="vot-stat">
                  <span class="vot-stat__val">{{ ev.total_votes ?? 0 }}</span>
                  <span class="vot-stat__lbl">votos</span>
                </div>
                <div class="vot-stat">
                  <span class="vot-stat__val">{{ ev.candidate_count ?? 0 }}</span>
                  <span class="vot-stat__lbl">candidatos</span>
                </div>
              </div>
            </a>
          }
        </div>
      }
    </div>
  `,
  styles: [`
    @use '../../../styles/tokens' as *;
    :host { display: block; }
    .page { max-width: 1100px; margin: 0 auto; }
    .page__header h1 { margin: 0; color: $color-primary; i { margin-right: $space-2; } }
    .page__subtitle { color: $color-text-muted; margin: $space-1 0 $space-4; }
    .vot-grid {
      display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
      gap: $space-4;
    }
    .vot-card {
      display: block; text-decoration: none; color: inherit;
      background: #fff; border: 1px solid $color-border; border-top: 4px solid;
      border-radius: $radius-lg; padding: $space-4;
      transition: transform 0.15s ease, box-shadow 0.15s ease;
      &:hover { transform: translateY(-3px); box-shadow: 0 8px 20px rgba(0,0,0,0.10); }
    }
    .vot-card__head { margin-bottom: $space-2; }
    .vot-badge {
      display: inline-flex; align-items: center; gap: 4px;
      color: #fff; font-size: $font-size-xs; font-weight: 600;
      padding: 2px 10px; border-radius: $radius-pill;
    }
    .vot-card__title { margin: $space-1 0; color: $color-text; font-size: 1.05rem; }
    .dates { display: block; color: $color-text-muted; font-size: $font-size-xs; }
    .vot-stats { display: flex; gap: $space-4; margin-top: $space-3; }
    .vot-stat { display: flex; flex-direction: column; }
    .vot-stat__val { font-size: 1.5rem; font-weight: 700; color: $color-primary; line-height: 1; }
    .vot-stat__lbl { font-size: $font-size-xs; color: $color-text-muted; text-transform: uppercase; }
    .page__header--row { display: flex; justify-content: space-between; align-items: flex-start; gap: $space-3; flex-wrap: wrap; }
    .crear-form {
      background: $color-bg-subtle; border: 1px solid $color-border;
      border-radius: $radius-md; padding: $space-4; margin-bottom: $space-4;
      h3 { margin: 0 0 $space-3; color: $color-primary; }
      .grid { display: grid; grid-template-columns: 1fr 1fr; gap: $space-3;
        @media (max-width: 600px) { grid-template-columns: 1fr; } }
      label { display: block; &.full { grid-column: 1 / -1; }
        span { display: block; font-size: $font-size-xs; color: $color-text-muted; margin-bottom: 2px; }
        input { width: 100%; padding: $space-2; border: 1px solid $color-border; border-radius: $radius-sm; font: inherit; } }
      .acts { display: flex; gap: $space-2; justify-content: flex-end; margin-top: $space-3; }
      .msg { margin: $space-2 0 0; color: $color-success; &.err { color: $color-danger; } }
    }
  `],
})
export class VotacionesListComponent implements OnInit {
  private api = inject(VotacionesApi);
  private layout = inject(LayoutService);

  loading = signal<boolean>(true);
  errorMsg = signal<string>('');
  eventos = signal<EventoVotacion[]>([]);
  abrirCrear = signal<boolean>(false);
  guardando = signal<boolean>(false);
  msgCrear = signal<string>('');
  errCrear = signal<boolean>(false);
  nuevo: any = { name: '', starts_at: '', ends_at: '', votos_permitidos: 1 };

  crear(): void {
    if (!this.nuevo.name?.trim()) {
      this.errCrear.set(true); this.msgCrear.set('El nombre es obligatorio.'); return;
    }
    this.guardando.set(true); this.msgCrear.set(''); this.errCrear.set(false);
    this.api.crearEvento(this.nuevo).subscribe({
      next: () => {
        this.guardando.set(false);
        this.abrirCrear.set(false);
        this.nuevo = { name: '', starts_at: '', ends_at: '', votos_permitidos: 1 };
        this.cargar();
      },
      error: (e) => {
        this.guardando.set(false);
        this.errCrear.set(true);
        this.msgCrear.set(e?.error?.detail || 'Error al crear el evento.');
      },
    });
  }

  cargar(): void {
    this.api.eventos().subscribe({
      next: (r) => { this.eventos.set(r.results); this.loading.set(false); },
      error: (e) => {
        this.loading.set(false);
        this.errorMsg.set(e.status === 401 ? 'Sesión expirada.' : `Error ${e.status}.`);
      },
    });
  }

  /** Color + icono + etiqueta por estado del evento. */
  estado(ev: EventoVotacion): { color: string; icon: string; label: string } {
    switch (ev.status) {
      case 'open': return { color: '#16a34a', icon: 'fa-circle-play', label: 'Abierta' };
      case 'upcoming': return { color: '#2563eb', icon: 'fa-clock', label: 'Próxima' };
      case 'finished': return { color: '#6b7280', icon: 'fa-flag-checkered', label: 'Finalizada' };
      default: return { color: '#d97706', icon: 'fa-pause', label: 'Inactiva' };
    }
  }

  ngOnInit(): void {
    this.layout.setBreadcrumb([
      { label: 'Inicio', url: '/' },
      { label: 'Votaciones' },
    ]);
    this.cargar();
  }
}
