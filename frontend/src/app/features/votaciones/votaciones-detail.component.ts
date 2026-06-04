import { CommonModule } from '@angular/common';
import {
  Component, ElementRef, OnDestroy, OnInit, ViewChild, effect, inject, signal,
} from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { Chart, registerables } from 'chart.js';
import { LayoutService } from '../../core/layout/layout.service';
import { VotacionesApi } from './votaciones.api';
import {
  CandidatosResponse, EventoVotacion, RankingItem, Resultados,
} from './votaciones.types';

Chart.register(...registerables);

type EventoLite = Partial<EventoVotacion> & { id: number; name: string };

@Component({
  standalone: true,
  selector: 'app-votaciones-detail',
  imports: [CommonModule, FormsModule, RouterLink],
  template: `
    <div class="page">
      @if (loading()) {
        <div class="ui-info-bar ui-info-bar--info">Cargando…</div>
      }
      @if (!loading() && fatalMsg()) {
        <div class="ui-info-bar ui-info-bar--danger">{{ fatalMsg() }}</div>
        <a routerLink="/votaciones" class="ui-btn ui-btn--ghost">↩ Volver</a>
      }

      @if (!loading() && !fatalMsg() && evento(); as ev) {
        <header class="page__header">
          <div>
            <h1><i class="fa fa-vote-yea" aria-hidden="true"></i> {{ ev.name }}</h1>
            @if (ev.status) {
              <p class="page__subtitle">
                <span class="vot-badge" [style.background]="estado(ev).color">
                  <i class="fa" [class]="estado(ev).icon"></i> {{ estado(ev).label }}
                </span>
                @if (ev.starts_at) {
                  · {{ ev.starts_at | date:'medium' }} → {{ ev.ends_at | date:'medium' }}
                }
              </p>
            }
          </div>
          <a routerLink="/votaciones" class="ui-btn ui-btn--ghost ui-btn--sm">
            <i class="fa fa-arrow-left"></i> Listado
          </a>
        </header>

        @if (resultados(); as r) {
          <!-- KPI strip -->
          <div class="kpis">
            <article class="kpi kpi--total">
              <span class="kpi__val">{{ r.total_votes }}</span>
              <span class="kpi__lbl">Votos emitidos</span>
            </article>
            <article class="kpi kpi--voters">
              <span class="kpi__val">{{ r.unique_voters }}</span>
              <span class="kpi__lbl">Votantes únicos</span>
            </article>
            <article class="kpi kpi--id">
              <span class="kpi__val">{{ r.total_identidades_votes }}</span>
              <span class="kpi__lbl">Votos Identidades</span>
            </article>
            <article class="kpi kpi--der">
              <span class="kpi__val">{{ r.total_derechos_votes }}</span>
              <span class="kpi__lbl">Votos Derechos</span>
            </article>
          </div>

          <div class="cols">
            <article class="ui-card">
              <header class="ui-card__header">
                <h2 class="ui-card__title"><i class="fa fa-id-badge" aria-hidden="true"></i> Identidades</h2>
                <p class="ui-card__subtitle">{{ r.total_identidades_votes }} votos</p>
              </header>
              <div class="chart-wrap"><canvas #chartId></canvas></div>
              @for (item of r.ranking_identidades; track $index) {
                <ng-container *ngTemplateOutlet="rankRow;
                  context: { $implicit: item, idx: $index, total: r.total_identidades_votes }" />
              }
            </article>

            <article class="ui-card">
              <header class="ui-card__header">
                <h2 class="ui-card__title"><i class="fa fa-scale-balanced" aria-hidden="true"></i> Derechos</h2>
                <p class="ui-card__subtitle">{{ r.total_derechos_votes }} votos</p>
              </header>
              <div class="chart-wrap"><canvas #chartDer></canvas></div>
              @for (item of r.ranking_derechos; track $index) {
                <ng-container *ngTemplateOutlet="rankRow;
                  context: { $implicit: item, idx: $index, total: r.total_derechos_votes }" />
              }
            </article>
          </div>

          <ng-template #rankRow let-item let-idx="idx" let-total="total">
            <div class="rank-row" [class.rank-row--win]="idx === 0 && item.votes > 0">
              <div class="rank-who">
                @if (idx === 0 && item.votes > 0) { <i class="fa fa-trophy win-ico"></i> }
                @if (item.photo_url) {
                  <img class="rank-photo" [src]="item.photo_url" alt="" loading="lazy">
                } @else {
                  <span class="rank-photo rank-photo--ph"><i class="fa fa-user"></i></span>
                }
                <span class="rank-name">
                  @if (item.candidate_id) { {{ item.candidate_name }} }
                  @else { <em>Voto en blanco</em> }
                </span>
              </div>
              <div class="rank-bar">
                <div class="rank-bar__fill" [style.width.%]="item.percentage"></div>
              </div>
              <span class="rank-pct">{{ item.percentage }}% · {{ item.votes }}</span>
            </div>
          </ng-template>
        } @else {
          <div class="ui-info-bar ui-info-bar--info">
            Aún no hay resultados para este evento.
          </div>
        }

        @if (candidatos(); as c) {
          <div class="cols">
            <article class="ui-card ui-card--info">
              <header class="ui-card__header">
                <h2 class="ui-card__title"><i class="fa fa-id-badge" aria-hidden="true"></i> Roster Identidades ({{ c.count_identidades }})</h2>
              </header>
              <ul class="cand-list">
                @for (cand of c.identidades; track cand.id) {
                  <li>
                    @if (cand.photo_url) { <img class="rank-photo" [src]="cand.photo_url" alt="" loading="lazy"> }
                    <strong>{{ cand.name }}</strong>
                    <span class="ui-badge ui-badge--neutral">{{ cand.curul }}</span>
                  </li>
                }
              </ul>
            </article>
            <article class="ui-card ui-card--accent">
              <header class="ui-card__header">
                <h2 class="ui-card__title"><i class="fa fa-scale-balanced" aria-hidden="true"></i> Roster Derechos ({{ c.count_derechos }})</h2>
              </header>
              <ul class="cand-list">
                @for (cand of c.derechos; track cand.id) {
                  <li>
                    @if (cand.photo_url) { <img class="rank-photo" [src]="cand.photo_url" alt="" loading="lazy"> }
                    <strong>{{ cand.name }}</strong>
                    <span class="ui-badge ui-badge--neutral">{{ cand.curul }}</span>
                  </li>
                }
              </ul>
            </article>
          </div>
        }

        <!-- ── Gestión (organizador) ───────────────────────────── -->
        <article class="ui-card admin-card">
          <header class="ui-card__header admin-head" (click)="toggleGestion()">
            <h2 class="ui-card__title"><i class="fa fa-screwdriver-wrench"></i> Gestión del evento</h2>
            <i class="fa" [class.fa-chevron-down]="!gestion()" [class.fa-chevron-up]="gestion()"></i>
          </header>
          @if (gestion()) {
            <!-- Editar evento -->
            <div class="adm-block">
              <h3>Editar evento</h3>
              <div class="grid">
                <label class="full"><span>Nombre</span><input type="text" [(ngModel)]="evForm.name"></label>
                <label><span>Inicio</span><input type="datetime-local" [(ngModel)]="evForm.starts_at"></label>
                <label><span>Fin</span><input type="datetime-local" [(ngModel)]="evForm.ends_at"></label>
                <label><span>Votos permitidos</span><input type="number" min="1" max="20" [(ngModel)]="evForm.votos_permitidos"></label>
              </div>
              <div class="acts">
                <button class="ui-btn ui-btn--ghost ui-btn--sm" (click)="toggleEvento()">
                  {{ evForm.is_active ? 'Desactivar' : 'Activar' }}
                </button>
                <button class="ui-btn ui-btn--primary ui-btn--sm" (click)="guardarEvento()">Guardar evento</button>
              </div>
            </div>

            <!-- QR del evento -->
            <div class="adm-block qr-block">
              <h3>Código QR de votación</h3>
              <p class="muted">Escanéalo para abrir la votación pública.</p>
              <img class="qr-img" [src]="qrEventoUrl()" alt="QR del evento">
              <a class="ui-btn ui-btn--ghost ui-btn--sm" [href]="qrEventoUrl()" download>
                <i class="fa fa-download"></i> Descargar QR
              </a>
            </div>

            <!-- Candidatos admin -->
            <div class="adm-block">
              <h3>Candidatos ({{ candAdmin().length }})</h3>
              <table class="adm-tbl">
                <tbody>
                  @for (cand of candAdmin(); track cand.id) {
                    <tr [class.off]="!cand.is_active">
                      <td>{{ cand.name }}</td>
                      <td><span class="ui-badge ui-badge--neutral">{{ cand.group }} · {{ cand.curul }}</span></td>
                      <td class="r">
                        <button class="ui-btn ui-btn--ghost ui-btn--xs" (click)="toggleCand(cand)">
                          {{ cand.is_active ? 'Desactivar' : 'Activar' }}
                        </button>
                        <button class="ui-btn ui-btn--ghost ui-btn--xs danger" (click)="eliminarCand(cand)">Eliminar</button>
                      </td>
                    </tr>
                  }
                </tbody>
              </table>

              <h4>Agregar candidato</h4>
              <div class="grid">
                <label class="full"><span>Nombre *</span><input type="text" [(ngModel)]="candForm.name"></label>
                <label class="full"><span>Curul *</span>
                  <select [(ngModel)]="candForm.genre">
                    <option value="">— elegir curul —</option>
                    @for (cu of curules(); track cu.value) { <option [value]="cu.value">{{ cu.label }}</option> }
                  </select>
                </label>
                <label class="full"><span>Bio</span><textarea rows="2" [(ngModel)]="candForm.bio"></textarea></label>
                <label class="full"><span>Foto (opcional)</span>
                  <input type="file" accept="image/*" (change)="onFoto($event)"></label>
              </div>
              <div class="acts">
                <button class="ui-btn ui-btn--primary ui-btn--sm" [disabled]="guardandoCand()" (click)="agregarCand()">
                  @if (guardandoCand()) { Agregando… } @else { Agregar candidato }
                </button>
              </div>
              @if (msgAdmin()) { <p class="msg" [class.err]="errAdmin()">{{ msgAdmin() }}</p> }
            </div>
          }
        </article>
      }
    </div>
  `,
  styles: [`
    @use '../../../styles/tokens' as *;
    :host { display: block; }
    .page { max-width: 1200px; margin: 0 auto; }
    .page__header {
      display: flex; justify-content: space-between; align-items: flex-start;
      gap: $space-3; flex-wrap: wrap; margin-bottom: $space-4;
    }
    .page__header h1 { margin: 0; color: $color-primary; i { margin-right: $space-2; } }
    .page__subtitle { margin: $space-1 0 0; color: $color-text-muted; display: flex; align-items: center; gap: $space-2; flex-wrap: wrap; }
    .vot-badge {
      display: inline-flex; align-items: center; gap: 4px; color: #fff;
      font-size: $font-size-xs; font-weight: 600; padding: 2px 10px; border-radius: $radius-pill;
    }

    .kpis {
      display: grid; grid-template-columns: repeat(4, 1fr); gap: $space-3; margin-bottom: $space-4;
      @media (max-width: 640px) { grid-template-columns: repeat(2, 1fr); }
    }
    .kpi {
      background: #fff; border: 1px solid $color-border; border-left: 4px solid $color-primary;
      border-radius: $radius-md; padding: $space-3; display: flex; flex-direction: column;
      &--voters { border-left-color: #2563eb; }
      &--id { border-left-color: #0D9488; }
      &--der { border-left-color: #d97706; }
      &__val { font-size: 1.8rem; font-weight: 700; color: $color-text; line-height: 1; }
      &__lbl { font-size: $font-size-xs; color: $color-text-muted; text-transform: uppercase; letter-spacing: 0.04em; }
    }

    .cols {
      display: grid; grid-template-columns: repeat(auto-fit, minmax(380px, 1fr));
      gap: $space-4; margin-top: $space-4;
    }
    .chart-wrap { height: 200px; margin-bottom: $space-3; }

    .rank-row {
      display: grid; grid-template-columns: 1.4fr 1.6fr max-content;
      gap: $space-2; align-items: center; padding: $space-2 0;
      border-bottom: 1px solid $color-border;
      &--win { background: rgba(22,163,74,0.07); border-radius: $radius-sm; }
    }
    .rank-who { display: flex; align-items: center; gap: $space-2; min-width: 0; }
    .win-ico { color: #f59e0b; }
    .rank-photo {
      width: 30px; height: 30px; border-radius: 50%; object-fit: cover;
      border: 1px solid $color-border; flex-shrink: 0;
      &--ph { display: inline-flex; align-items: center; justify-content: center;
              background: $color-bg-subtle; color: $color-text-muted; }
    }
    .rank-name { font-weight: $font-weight-semibold; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
    .rank-bar { background: $color-bg-muted; border-radius: $radius-pill; height: 8px; overflow: hidden; }
    .rank-bar__fill { background: $color-primary; height: 100%; transition: width 0.6s ease; }
    .rank-pct { font-size: $font-size-sm; color: $color-text-muted; white-space: nowrap; }

    .cand-list { list-style: none; padding: 0; margin: 0; }
    .cand-list li { display: flex; gap: $space-2; align-items: center; padding: $space-2 0; border-bottom: 1px solid $color-border; }
    .cand-list li:last-child { border-bottom: 0; }

    .admin-card { margin-top: $space-4; }
    .admin-head { cursor: pointer; user-select: none; display: flex; justify-content: space-between; align-items: center; }
    .adm-block { padding: $space-3 0; border-top: 1px solid $color-border;
      h3 { margin: 0 0 $space-2; color: $color-primary; font-size: 1rem; }
      h4 { margin: $space-3 0 $space-2; color: $color-text-muted; font-size: $font-size-sm; } }
    .adm-block .grid { display: grid; grid-template-columns: 1fr 1fr; gap: $space-2;
      @media (max-width: 600px) { grid-template-columns: 1fr; } }
    .adm-block label { display: block; &.full { grid-column: 1 / -1; }
      span { display: block; font-size: $font-size-xs; color: $color-text-muted; }
      input, select, textarea { width: 100%; padding: 6px 8px; border: 1px solid $color-border; border-radius: $radius-sm; font: inherit; } }
    .acts { display: flex; gap: $space-2; justify-content: flex-end; margin-top: $space-2; }
    .adm-tbl { width: 100%; border-collapse: collapse;
      td { padding: 6px 4px; border-bottom: 1px solid $color-border; font-size: $font-size-sm; }
      .r { text-align: right; white-space: nowrap; }
      tr.off { opacity: 0.5; } }
    .ui-btn--xs { padding: 2px 8px; font-size: $font-size-xs; }
    .danger { color: $color-danger; }
    .msg { margin: $space-2 0 0; color: $color-success; &.err { color: $color-danger; } }
    .qr-block { text-align: center; }
    .qr-img { width: 180px; height: 180px; border: 1px solid $color-border; border-radius: $radius-md; padding: $space-2; background: #fff; display: block; margin: $space-2 auto; }
  `],
})
export class VotacionesDetailComponent implements OnInit, OnDestroy {
  private api = inject(VotacionesApi);
  private route = inject(ActivatedRoute);
  private layout = inject(LayoutService);

  @ViewChild('chartId') private chartIdRef?: ElementRef<HTMLCanvasElement>;
  @ViewChild('chartDer') private chartDerRef?: ElementRef<HTMLCanvasElement>;
  private charts: Chart[] = [];

  loading = signal<boolean>(true);
  fatalMsg = signal<string>('');
  evento = signal<EventoLite | null>(null);
  candidatos = signal<CandidatosResponse | null>(null);
  resultados = signal<Resultados | null>(null);

  constructor() {
    effect(() => {
      const r = this.resultados();
      if (r) queueMicrotask(() => this.dibujar(r));
    });
  }

  estado(ev: EventoLite): { color: string; icon: string; label: string } {
    switch (ev.status) {
      case 'open': return { color: '#16a34a', icon: 'fa-circle-play', label: 'Abierta' };
      case 'upcoming': return { color: '#2563eb', icon: 'fa-clock', label: 'Próxima' };
      case 'finished': return { color: '#6b7280', icon: 'fa-flag-checkered', label: 'Finalizada' };
      default: return { color: '#d97706', icon: 'fa-pause', label: 'Inactiva' };
    }
  }

  ngOnInit(): void {
    const id = Number(this.route.snapshot.paramMap.get('id'));
    if (!id) { this.fatalMsg.set('ID inválido.'); this.loading.set(false); return; }
    this.layout.setBreadcrumb([
      { label: 'Inicio', url: '/' },
      { label: 'Votaciones', url: '/votaciones' },
      { label: `Evento #${id}` },
    ]);

    // Candidatos: si está cerrado da 403 con el evento en el body.
    this.api.candidatos(id).subscribe({
      next: (c) => {
        this.candidatos.set(c);
        this.evento.set(c.event);
        this.loading.set(false);
      },
      error: (e) => {
        this.loading.set(false);
        if (e.status === 403 && e.error?.event) {
          this.evento.set(e.error.event);   // evento cerrado: igual mostramos resultados
        } else if (!this.evento()) {
          this.fatalMsg.set(`Error ${e.status}.`);
        }
      },
    });

    // Resultados (organizador): se muestran siempre, abierto o cerrado.
    this.api.resultados(id).subscribe({
      next: (r) => {
        this.resultados.set(r);
        if (!this.evento() && r.event) this.evento.set(r.event as EventoLite);
        this.loading.set(false);
      },
      error: () => { /* sin resultados, el template muestra aviso */ },
    });
  }

  // ── Gestión organizador ─────────────────────────────────────────
  gestion = signal<boolean>(false);
  curules = signal<{ value: string; label: string; group: string }[]>([]);
  candAdmin = signal<any[]>([]);
  guardandoCand = signal<boolean>(false);
  msgAdmin = signal<string>('');
  errAdmin = signal<boolean>(false);
  evForm: any = { name: '', starts_at: '', ends_at: '', votos_permitidos: 1, is_active: true };
  candForm: any = { name: '', genre: '', bio: '' };
  candFoto: File | null = null;

  qrEventoUrl(): string {
    return `/votaciones/qr/event/${this.eventoId}.png`;
  }

  onFoto(ev: Event): void {
    const input = ev.target as HTMLInputElement;
    this.candFoto = input.files?.[0] || null;
  }

  private get eventoId(): number {
    return Number(this.route.snapshot.paramMap.get('id'));
  }

  toggleGestion(): void {
    const next = !this.gestion();
    this.gestion.set(next);
    if (next) {
      const ev = this.evento();
      if (ev) this.evForm = {
        name: ev.name, starts_at: this.toLocal(ev.starts_at), ends_at: this.toLocal(ev.ends_at),
        votos_permitidos: (ev as any).votos_permitidos || 1, is_active: ev.status !== 'inactive',
      };
      if (!this.curules().length) this.api.curules().subscribe(r => this.curules.set(r.results));
      this.cargarCandAdmin();
    }
  }

  private toLocal(iso: string | null | undefined): string {
    return iso ? String(iso).slice(0, 16) : '';
  }

  private cargarCandAdmin(): void {
    this.api.candidatosAdmin(this.eventoId).subscribe({
      next: (r: any) => this.candAdmin.set(r.results || []),
    });
  }

  guardarEvento(): void {
    this.api.editarEvento(this.eventoId, this.evForm).subscribe({
      next: () => { this.msgAdmin.set('✓ Evento actualizado.'); this.errAdmin.set(false); this.recargar(); },
      error: (e) => { this.errAdmin.set(true); this.msgAdmin.set(e?.error?.detail || 'Error al guardar.'); },
    });
  }

  toggleEvento(): void {
    this.api.toggleEvento(this.eventoId).subscribe(() => this.recargar());
  }

  agregarCand(): void {
    if (!this.candForm.name?.trim() || !this.candForm.genre) {
      this.errAdmin.set(true); this.msgAdmin.set('Nombre y curul son obligatorios.'); return;
    }
    this.guardandoCand.set(true); this.msgAdmin.set(''); this.errAdmin.set(false);
    // multipart si hay foto, JSON si no.
    let body: any;
    if (this.candFoto) {
      body = new FormData();
      body.append('evento_id', String(this.eventoId));
      body.append('name', this.candForm.name);
      body.append('genre', this.candForm.genre);
      body.append('bio', this.candForm.bio || '');
      body.append('photo', this.candFoto);
    } else {
      body = { ...this.candForm, evento_id: this.eventoId };
    }
    this.api.crearCandidato(body).subscribe({
      next: () => {
        this.guardandoCand.set(false);
        this.candForm = { name: '', genre: '', bio: '' };
        this.candFoto = null;
        this.msgAdmin.set('✓ Candidato agregado.');
        this.cargarCandAdmin();
        this.recargarResultados();
      },
      error: (e) => {
        this.guardandoCand.set(false); this.errAdmin.set(true);
        this.msgAdmin.set(e?.error?.detail || 'Error al agregar candidato.');
      },
    });
  }

  toggleCand(cand: any): void {
    this.api.toggleCandidato(cand.id).subscribe(() => { this.cargarCandAdmin(); this.recargarResultados(); });
  }

  eliminarCand(cand: any): void {
    if (!confirm(`¿Eliminar a ${cand.name}?`)) return;
    this.api.eliminarCandidato(cand.id).subscribe({
      next: () => { this.cargarCandAdmin(); this.recargarResultados(); },
      error: (e) => { this.errAdmin.set(true); this.msgAdmin.set(e?.error?.detail || 'No se pudo eliminar.'); },
    });
  }

  private recargar(): void {
    this.api.candidatos(this.eventoId).subscribe({ next: (c) => { this.candidatos.set(c); this.evento.set(c.event); } });
    this.recargarResultados();
    this.cargarCandAdmin();
  }
  private recargarResultados(): void {
    this.api.resultados(this.eventoId).subscribe({ next: (r) => this.resultados.set(r) });
  }

  ngOnDestroy(): void {
    this.charts.forEach(c => c.destroy());
  }

  private dibujar(r: Resultados): void {
    this.charts.forEach(c => c.destroy());
    this.charts = [];
    const cId = this.chartIdRef?.nativeElement;
    const cDer = this.chartDerRef?.nativeElement;
    if (cId) this.charts.push(this.doughnut(cId, r.ranking_identidades));
    if (cDer) this.charts.push(this.doughnut(cDer, r.ranking_derechos));
  }

  private doughnut(canvas: HTMLCanvasElement, ranking: RankingItem[]): Chart {
    const palette = ['#D6001C', '#0D9488', '#2563eb', '#d97706', '#7c3aed', '#16a34a', '#db2777', '#64748b'];
    const items = ranking.filter(i => i.votes > 0);
    return new Chart(canvas, {
      type: 'doughnut',
      data: {
        labels: items.map(i => i.candidate_id ? i.candidate_name : 'En blanco'),
        datasets: [{
          data: items.map(i => i.votes),
          backgroundColor: items.map((_, i) => palette[i % palette.length]),
          borderWidth: 2, borderColor: '#fff',
        }],
      },
      options: {
        responsive: true, maintainAspectRatio: false,
        plugins: { legend: { position: 'bottom', labels: { boxWidth: 10, font: { size: 10 } } } },
      },
    });
  }
}
