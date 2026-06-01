import { CommonModule } from '@angular/common';
import { Component, OnInit, inject, signal } from '@angular/core';
import { RouterLink } from '@angular/router';
import { LayoutService } from '../../core/layout/layout.service';
import { VotacionesApi } from './votaciones.api';
import { EventoVotacion } from './votaciones.types';

@Component({
  standalone: true,
  selector: 'app-votaciones-list',
  imports: [CommonModule, RouterLink],
  template: `
    <div class="page">
      <header class="page__header">
        <h1>Votaciones</h1>
        <p class="page__subtitle">Gestión de eventos de votación. Los QRs y votos públicos siguen sirviéndose desde la versión actual.</p>
      </header>

      @if (loading()) {
        <div class="ui-info-bar ui-info-bar--info">Cargando…</div>
      }
      @if (!loading() && errorMsg()) {
        <div class="ui-info-bar ui-info-bar--danger">{{ errorMsg() }}</div>
      }
      @if (!loading() && !errorMsg() && eventos().length === 0) {
        <div class="ui-empty-state">
          <i class="fa fa-vote-yea" aria-hidden="true"></i>
          <p>No hay eventos de votación activos.</p>
        </div>
      }
      @if (!loading() && !errorMsg() && eventos().length > 0) {
        <div class="hub-grid">
          @for (ev of eventos(); track ev.id) {
            <a [routerLink]="['/votaciones', ev.id]" class="hub-card"
               [class.hub-card--success]="ev.is_open"
               [class.hub-card--warning]="!ev.is_open">
              <div class="hub-card__icon">
                <i class="fa fa-vote-yea" aria-hidden="true"></i>
              </div>
              <h3 class="hub-card__title">{{ ev.name }}</h3>
              <p class="hub-card__subtitle">{{ ev.status_message }}</p>
              <small class="dates">
                @if (ev.starts_at) {
                  {{ ev.starts_at | date:'shortDate' }} → {{ ev.ends_at | date:'shortDate' }}
                }
              </small>
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
    .page__header h1 { margin: 0; color: $color-primary; }
    .page__subtitle { color: $color-text-muted; margin: $space-1 0 $space-4; }
    .dates {
      display: block;
      margin-top: $space-2;
      color: $color-text-muted;
      font-size: $font-size-xs;
    }
  `],
})
export class VotacionesListComponent implements OnInit {
  private api = inject(VotacionesApi);
  private layout = inject(LayoutService);

  loading = signal<boolean>(true);
  errorMsg = signal<string>('');
  eventos = signal<EventoVotacion[]>([]);

  ngOnInit(): void {
    this.layout.setBreadcrumb([
      { label: 'Inicio', url: '/' },
      { label: 'Votaciones' },
    ]);
    this.api.eventos().subscribe({
      next: (r) => {
        this.eventos.set(r.results);
        this.loading.set(false);
      },
      error: (e) => {
        this.loading.set(false);
        this.errorMsg.set(
          e.status === 401 ? 'Sesión expirada.' :
          e.status === 0 ? 'No se pudo conectar.' :
          `Error ${e.status}.`
        );
      },
    });
  }
}
