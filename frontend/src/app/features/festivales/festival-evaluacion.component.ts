import { CommonModule } from '@angular/common';
import { Component, Input, OnInit, inject, signal, computed } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { FestivalesApi } from './festivales.api';
import { FestivalArtista, FestivalDia, RankingData } from './festivales.types';

/**
 * Lineup + jurados + criterios + planilla de evaluación + ranking (PR-E).
 * El funcionario transcribe las calificaciones. Consolidado = promedio
 * ponderado por peso. Se cierra cuando el festival pasa a 'cerrado'.
 */
@Component({
  standalone: true,
  selector: 'app-festival-evaluacion',
  imports: [CommonModule, FormsModule],
  template: `
    <section class="eval">
      <div class="eval__head">
        <h2><i class="fa fa-star"></i> Lineup y evaluación</h2>
        @if (data()?.cerrado) { <span class="cerrado">Festival cerrado — solo lectura</span> }
      </div>
      @if (flash()) { <div class="ui-info-bar ui-info-bar--success">{{ flash() }}</div> }
      @if (error()) { <div class="ui-info-bar ui-info-bar--danger">{{ error() }}</div> }

      @if (data(); as d) {
        <div class="cols">
          <!-- Lineup -->
          <div class="bloque">
            <h3>Lineup ({{ d.artistas.length }})</h3>
            @if (!d.cerrado) {
              <div class="add">
                <input [(ngModel)]="naNombre" placeholder="Nombre artista/grupo">
                <select [(ngModel)]="naTipo">
                  <option value="artista">Artista</option>
                  <option value="grupo">Grupo</option>
                  <option value="invitado">Invitado</option>
                </select>
                <select [(ngModel)]="naDia">
                  <option [ngValue]="null">Sin día</option>
                  @for (dd of dias; track dd.id) { <option [ngValue]="dd.id">{{ dd.fecha }}</option> }
                </select>
                <button class="ui-btn ui-btn--primary ui-btn--sm" (click)="addArtista()"><i class="fa fa-plus"></i></button>
              </div>
            }
            <ul class="lista">
              @for (a of d.artistas; track a.id) {
                <li><span><strong>{{ a.nombre }}</strong> <small>{{ a.tipo_display }}</small>@if (a.dia_fecha) { <small> · {{ a.dia_fecha }}</small> }</span>
                  @if (!d.cerrado) { <button class="x" (click)="delArtista(a)"><i class="fa fa-trash"></i></button> }</li>
              }
              @if (d.artistas.length === 0) { <li class="vacio">Sin artistas aún.</li> }
            </ul>
          </div>

          <!-- Jurados -->
          <div class="bloque">
            <h3>Jurados ({{ d.jurados.length }})</h3>
            @if (!d.cerrado) {
              <div class="add">
                <input [(ngModel)]="njNombre" placeholder="Nombre jurado">
                <input [(ngModel)]="njPerfil" placeholder="Perfil (opcional)">
                <button class="ui-btn ui-btn--primary ui-btn--sm" (click)="addJurado()"><i class="fa fa-plus"></i></button>
              </div>
            }
            <ul class="lista">
              @for (j of d.jurados; track j.id) {
                <li><span><strong>{{ j.nombre }}</strong>@if (j.perfil) { <small> · {{ j.perfil }}</small> }</span>
                  @if (!d.cerrado) { <button class="x" (click)="delJurado(j)"><i class="fa fa-trash"></i></button> }</li>
              }
              @if (d.jurados.length === 0) { <li class="vacio">Sin jurados aún.</li> }
            </ul>
          </div>

          <!-- Criterios -->
          <div class="bloque">
            <h3>Criterios ({{ d.criterios.length }})</h3>
            @if (!d.cerrado) {
              <div class="add">
                <input [(ngModel)]="ncNombre" placeholder="Criterio">
                <input type="number" [(ngModel)]="ncPeso" placeholder="Peso" min="0" step="0.5" class="peso">
                <button class="ui-btn ui-btn--primary ui-btn--sm" (click)="addCriterio()"><i class="fa fa-plus"></i></button>
              </div>
            }
            <ul class="lista">
              @for (c of d.criterios; track c.id) {
                <li><span><strong>{{ c.nombre }}</strong> <small>peso {{ c.peso }}</small></span>
                  @if (!d.cerrado) { <button class="x" (click)="delCriterio(c)"><i class="fa fa-trash"></i></button> }</li>
              }
              @if (d.criterios.length === 0) { <li class="vacio">Sin criterios aún.</li> }
            </ul>
          </div>
        </div>

        <!-- Planilla de evaluación -->
        @if (d.artistas.length && d.jurados.length && d.criterios.length) {
          <div class="planilla">
            <div class="planilla__head">
              <h3>Planilla de calificación</h3>
              <label>Jurado:
                <select [(ngModel)]="juradoSel">
                  @for (j of d.jurados; track j.id) { <option [ngValue]="j.id">{{ j.nombre }}</option> }
                </select>
              </label>
            </div>
            <div class="tabla-wrap">
              <table class="tabla">
                <thead>
                  <tr><th>Artista</th>@for (c of d.criterios; track c.id) { <th>{{ c.nombre }}<small> ({{ c.peso }})</small></th> }</tr>
                </thead>
                <tbody>
                  @for (a of d.artistas; track a.id) {
                    <tr>
                      <td>{{ a.nombre }}</td>
                      @for (c of d.criterios; track c.id) {
                        <td>
                          <input type="number" min="0" max="100" step="0.5"
                                 [disabled]="d.cerrado"
                                 [ngModel]="celda(a.id, juradoSel, c.id)"
                                 (change)="guardar(a.id, c.id, $event)">
                        </td>
                      }
                    </tr>
                  }
                </tbody>
              </table>
            </div>
          </div>

          <!-- Ranking -->
          <div class="ranking">
            <h3><i class="fa fa-trophy"></i> Consolidado (promedio ponderado)</h3>
            <table class="tabla">
              <thead><tr><th>#</th><th>Artista</th><th>Tipo</th><th>Jurados</th><th>Puntaje</th></tr></thead>
              <tbody>
                @for (r of d.ranking; track r.artista_id) {
                  <tr [class.podio]="r.posicion && r.posicion <= 3">
                    <td>{{ r.posicion || '—' }}</td>
                    <td>{{ r.nombre }}</td>
                    <td>{{ r.tipo }}</td>
                    <td>{{ r.n_jurados_calificaron }}</td>
                    <td><strong>{{ r.consolidado !== null ? r.consolidado : 'sin calificar' }}</strong></td>
                  </tr>
                }
              </tbody>
            </table>
          </div>
        } @else {
          <p class="muted">Agrega artistas, jurados y criterios para habilitar la planilla de evaluación.</p>
        }
      }
    </section>
  `,
  styles: [`
    @use '../../../styles/tokens' as *;
    :host { display: block; }
    .eval { background: #fff; border: 1px solid $color-border; border-radius: $radius-lg; padding: $space-4; margin-top: $space-3; }
    .eval__head { display: flex; justify-content: space-between; align-items: center; }
    .eval__head h2 { margin: 0; color: $color-primary; font-size: 1.1rem; }
    .cerrado { color: #92400E; background: #FEF3C7; padding: 2px 10px; border-radius: 99px; font-size: .72rem; font-weight: 600; }
    h3 { font-size: .95rem; color: $color-text; margin: 0 0 $space-2; }
    .cols { display: grid; grid-template-columns: repeat(3, 1fr); gap: $space-3; margin-top: $space-3; }
    @media (max-width: 850px) { .cols { grid-template-columns: 1fr; } }
    .bloque { border: 1px solid $color-border; border-radius: $radius-md; padding: $space-3; }
    .add { display: flex; gap: 4px; margin-bottom: $space-2; flex-wrap: wrap; }
    .add input, .add select { padding: 5px 7px; border: 1px solid $color-border; border-radius: $radius-sm; font-size: $font-size-sm; min-width: 0; flex: 1; }
    .add .peso { max-width: 70px; flex: none; }
    .lista { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: 4px; }
    .lista li { display: flex; justify-content: space-between; align-items: center; font-size: $font-size-sm; padding: 4px 0; border-bottom: 1px dashed $color-border; }
    .lista small { color: $color-text-muted; }
    .lista .vacio { color: $color-text-muted; font-style: italic; border: none; }
    .x { background: none; border: none; color: #DC2626; cursor: pointer; padding: 2px 6px; }
    .planilla, .ranking { margin-top: $space-4; }
    .planilla__head { display: flex; justify-content: space-between; align-items: center; gap: $space-2; flex-wrap: wrap; }
    .planilla__head select { padding: 5px 8px; border: 1px solid $color-border; border-radius: $radius-sm; }
    .tabla-wrap { overflow-x: auto; }
    .tabla { width: 100%; border-collapse: collapse; font-size: $font-size-sm; }
    .tabla th, .tabla td { border: 1px solid $color-border; padding: 6px 8px; text-align: left; }
    .tabla th { background: #F8FAFC; color: $color-text-muted; }
    .tabla th small { font-weight: 400; }
    .tabla input { width: 64px; padding: 4px 6px; border: 1px solid $color-border; border-radius: $radius-sm; }
    .ranking .podio { background: #F0FDF4; }
    .muted { color: $color-text-muted; margin-top: $space-3; }
  `],
})
export class FestivalEvaluacionComponent implements OnInit {
  @Input({ required: true }) festivalId!: number;
  @Input() dias: FestivalDia[] = [];

  private api = inject(FestivalesApi);

  data = signal<RankingData | null>(null);
  error = signal('');
  flash = signal('');
  juradoSel: number | null = null;

  // forms
  naNombre = ''; naTipo: 'artista' | 'grupo' | 'invitado' = 'artista'; naDia: number | null = null;
  njNombre = ''; njPerfil = '';
  ncNombre = ''; ncPeso = 1;

  private mapa = computed(() => {
    const m: Record<string, number> = {};
    for (const e of this.data()?.evaluaciones ?? []) m[`${e.artista_id}-${e.jurado_id}-${e.criterio_id}`] = e.puntaje;
    return m;
  });

  ngOnInit(): void { this.cargar(); }

  private cargar(): void {
    this.api.ranking(this.festivalId).subscribe({
      next: (d) => {
        this.data.set(d);
        if (this.juradoSel === null && d.jurados.length) this.juradoSel = d.jurados[0].id;
      },
      error: (e) => this.error.set(this.msg(e)),
    });
  }

  celda(artistaId: number, juradoId: number | null, criterioId: number): number | null {
    if (juradoId === null) return null;
    const v = this.mapa()[`${artistaId}-${juradoId}-${criterioId}`];
    return v ?? null;
  }

  guardar(artistaId: number, criterioId: number, ev: Event): void {
    if (this.juradoSel === null) return;
    const val = Number((ev.target as HTMLInputElement).value);
    if (isNaN(val)) return;
    this.api.evaluar(artistaId, this.juradoSel, criterioId, val).subscribe({
      next: () => { this.notify('Calificación guardada.'); this.cargar(); },
      error: (e) => this.error.set(this.msg(e)),
    });
  }

  addArtista(): void {
    if (!this.naNombre.trim()) return;
    this.api.crearArtista(this.festivalId, { nombre: this.naNombre.trim(), tipo: this.naTipo, festival_dia: this.naDia }).subscribe({
      next: () => { this.naNombre = ''; this.naDia = null; this.notify('Artista agregado.'); this.cargar(); },
      error: (e) => this.error.set(this.msg(e)),
    });
  }
  delArtista(a: FestivalArtista): void {
    if (!confirm(`¿Quitar a ${a.nombre} del lineup?`)) return;
    this.api.eliminarArtista(a.id).subscribe({ next: () => this.cargar(), error: (e) => this.error.set(this.msg(e)) });
  }
  addJurado(): void {
    if (!this.njNombre.trim()) return;
    this.api.crearJurado(this.festivalId, { nombre: this.njNombre.trim(), perfil: this.njPerfil.trim() || null }).subscribe({
      next: () => { this.njNombre = ''; this.njPerfil = ''; this.notify('Jurado agregado.'); this.cargar(); },
      error: (e) => this.error.set(this.msg(e)),
    });
  }
  delJurado(j: { id: number; nombre: string }): void {
    if (!confirm(`¿Quitar al jurado ${j.nombre}?`)) return;
    this.api.eliminarJurado(j.id).subscribe({ next: () => this.cargar(), error: (e) => this.error.set(this.msg(e)) });
  }
  addCriterio(): void {
    if (!this.ncNombre.trim()) return;
    this.api.crearCriterio(this.festivalId, { nombre: this.ncNombre.trim(), peso: this.ncPeso }).subscribe({
      next: () => { this.ncNombre = ''; this.ncPeso = 1; this.notify('Criterio agregado.'); this.cargar(); },
      error: (e) => this.error.set(this.msg(e)),
    });
  }
  delCriterio(c: { id: number; nombre: string }): void {
    if (!confirm(`¿Quitar el criterio ${c.nombre}?`)) return;
    this.api.eliminarCriterio(c.id).subscribe({ next: () => this.cargar(), error: (e) => this.error.set(this.msg(e)) });
  }

  private notify(m: string): void { this.flash.set(m); setTimeout(() => this.flash.set(''), 2500); }
  private msg(e: { error?: { detail?: string }; message?: string }): string {
    return e?.error?.detail || e?.message || 'Error inesperado.';
  }
}
