import { CommonModule } from '@angular/common';
import { Component, OnInit, inject, signal } from '@angular/core';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { LayoutService } from '../../core/layout/layout.service';
import { VotacionesApi } from './votaciones.api';
import {
  CandidatosResponse,
  RankingItem,
  Resultados,
} from './votaciones.types';

@Component({
  standalone: true,
  selector: 'app-votaciones-detail',
  imports: [CommonModule, RouterLink],
  template: `
    <div class="page">
      @if (loading()) {
        <div class="ui-info-bar ui-info-bar--info">Cargando…</div>
      }
      @if (!loading() && errorMsg()) {
        <div class="ui-info-bar ui-info-bar--danger">{{ errorMsg() }}</div>
        <a routerLink="/votaciones" class="ui-btn ui-btn--ghost">↩ Volver</a>
      }
      @if (!loading() && !errorMsg() && candidatos(); as c) {
        <header class="page__header">
          <div>
            <h1>{{ c.event.name }}</h1>
            <p class="page__subtitle">
              <span class="ui-badge"
                    [class.ui-badge--success]="c.event.is_open"
                    [class.ui-badge--warning]="!c.event.is_open">
                {{ c.event.status_message }}
              </span>
              @if (c.event.starts_at) {
                · {{ c.event.starts_at | date:'medium' }} → {{ c.event.ends_at | date:'medium' }}
              }
            </p>
          </div>
          <a routerLink="/votaciones" class="ui-btn ui-btn--ghost ui-btn--sm">
            <i class="fa fa-arrow-left" aria-hidden="true"></i> Listado
          </a>
        </header>

        @if (resultados(); as r) {
          <article class="ui-card ui-card--primary">
            <header class="ui-card__header">
              <h2 class="ui-card__title">Resultados</h2>
              <p class="ui-card__subtitle">
                <strong>{{ r.total_votes }}</strong> votos emitidos ·
                <strong>{{ r.unique_voters }}</strong> votantes únicos
              </p>
            </header>

            <div class="rank-grid">
              <div>
                <h3>Identidades ({{ r.total_identidades_votes }} votos)</h3>
                @for (item of r.ranking_identidades; track $index) {
                  <ng-container *ngTemplateOutlet="rankRow; context: { $implicit: item }" />
                }
              </div>
              <div>
                <h3>Derechos ({{ r.total_derechos_votes }} votos)</h3>
                @for (item of r.ranking_derechos; track $index) {
                  <ng-container *ngTemplateOutlet="rankRow; context: { $implicit: item }" />
                }
              </div>
            </div>
          </article>

          <ng-template #rankRow let-item>
            <div class="rank-row">
              <span class="rank-name">
                @if (item.candidate_id) {
                  {{ item.candidate_name }}
                } @else {
                  <em>Voto en blanco</em>
                }
              </span>
              <div class="rank-bar">
                <div class="rank-bar__fill" [style.width.%]="item.percentage"></div>
              </div>
              <span class="rank-pct">{{ item.percentage }}% · {{ item.votes }}</span>
            </div>
          </ng-template>
        }

        <div class="cand-grid">
          <article class="ui-card ui-card--info">
            <header class="ui-card__header">
              <h2 class="ui-card__title">Candidatos Identidades ({{ c.count_identidades }})</h2>
            </header>
            <ul class="cand-list">
              @for (cand of c.identidades; track cand.id) {
                <li>
                  <strong>{{ cand.name }}</strong>
                  <span class="ui-badge ui-badge--neutral">{{ cand.curul }}</span>
                  @if (cand.code) { <code class="small">{{ cand.code }}</code> }
                </li>
              }
            </ul>
          </article>

          <article class="ui-card ui-card--accent">
            <header class="ui-card__header">
              <h2 class="ui-card__title">Candidatos Derechos ({{ c.count_derechos }})</h2>
            </header>
            <ul class="cand-list">
              @for (cand of c.derechos; track cand.id) {
                <li>
                  <strong>{{ cand.name }}</strong>
                  <span class="ui-badge ui-badge--neutral">{{ cand.curul }}</span>
                  @if (cand.code) { <code class="small">{{ cand.code }}</code> }
                </li>
              }
            </ul>
          </article>
        </div>
      }
    </div>
  `,
  styles: [`
    @use '../../../styles/tokens' as *;
    :host { display: block; }
    .page { max-width: 1200px; margin: 0 auto; }
    .page__header {
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      gap: $space-3;
      flex-wrap: wrap;
      margin-bottom: $space-4;
    }
    .page__header h1 { margin: 0; color: $color-primary; }
    .page__subtitle { margin: $space-1 0 0; color: $color-text-muted; }

    .rank-grid, .cand-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(380px, 1fr));
      gap: $space-4;
      margin-top: $space-4;
    }
    .rank-grid h3, .cand-grid h2 { margin: 0 0 $space-2; }

    .rank-row {
      display: grid;
      grid-template-columns: 1fr 2fr max-content;
      gap: $space-2;
      align-items: center;
      padding: $space-2 0;
      border-bottom: 1px solid $color-border;
    }
    .rank-name { font-weight: $font-weight-semibold; }
    .rank-bar {
      background: $color-bg-muted;
      border-radius: $radius-pill;
      height: 8px;
      overflow: hidden;
    }
    .rank-bar__fill {
      background: $color-primary;
      height: 100%;
      transition: width $transition-base;
    }
    .rank-pct {
      font-size: $font-size-sm;
      color: $color-text-muted;
      white-space: nowrap;
    }

    .cand-list {
      list-style: none;
      padding: 0;
      margin: 0;
    }
    .cand-list li {
      display: flex;
      gap: $space-2;
      align-items: center;
      padding: $space-2 0;
      border-bottom: 1px solid $color-border;
    }
    .cand-list li:last-child { border-bottom: 0; }
    .small { font-size: $font-size-xs; }
  `],
})
export class VotacionesDetailComponent implements OnInit {
  private api = inject(VotacionesApi);
  private route = inject(ActivatedRoute);
  private layout = inject(LayoutService);

  loading = signal<boolean>(true);
  errorMsg = signal<string>('');
  candidatos = signal<CandidatosResponse | null>(null);
  resultados = signal<Resultados | null>(null);

  ngOnInit(): void {
    const id = Number(this.route.snapshot.paramMap.get('id'));
    if (!id) {
      this.errorMsg.set('ID inválido.');
      this.loading.set(false);
      return;
    }
    this.layout.setBreadcrumb([
      { label: 'Inicio', url: '/' },
      { label: 'Votaciones', url: '/votaciones' },
      { label: `Evento #${id}` },
    ]);

    this.api.candidatos(id).subscribe({
      next: (c) => {
        this.candidatos.set(c);
        this.loading.set(false);
      },
      error: (e) => {
        this.loading.set(false);
        if (e.status === 403) {
          this.errorMsg.set('La votación no está abierta o no tienes permiso.');
        } else {
          this.errorMsg.set(`Error ${e.status}.`);
        }
      },
    });

    this.api.resultados(id).subscribe({
      next: (r) => this.resultados.set(r),
      error: () => this.resultados.set(null),
    });
  }
}
