import { CommonModule } from '@angular/common';
import { Component, OnInit, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { LayoutService } from '../../core/layout/layout.service';
import { VotacionesApi } from './votaciones.api';

/**
 * Administración de votantes (organizador): padrón.
 *   - Registro: busca por documento; si no existe, da de alta una Persona.
 *   - Listado: personas que ya votaron (derivado de Voto).
 */
@Component({
  standalone: true,
  selector: 'app-votaciones-votantes',
  imports: [CommonModule, FormsModule, RouterLink],
  template: `
    <div class="page">
      <header class="page__header">
        <div>
          <h1><i class="fa fa-users" aria-hidden="true"></i> Votantes</h1>
          <p class="page__subtitle">Registra personas en el padrón y consulta quiénes ya votaron.</p>
        </div>
        <a routerLink="/votaciones" class="ui-btn ui-btn--ghost ui-btn--sm">
          <i class="fa fa-arrow-left"></i> Eventos
        </a>
      </header>

      <!-- KPIs -->
      <div class="kpis">
        <article class="kpi"><span class="kpi__val">{{ totalGeneral() }}</span><span class="kpi__lbl">Han votado</span></article>
        <article class="kpi"><span class="kpi__val">{{ totalHoy() }}</span><span class="kpi__lbl">Hoy</span></article>
      </div>

      <div class="cols">
        <!-- Registro -->
        <article class="ui-card">
          <header class="ui-card__header"><h2 class="ui-card__title"><i class="fa fa-user-plus" aria-hidden="true"></i> Registrar persona en el padrón</h2></header>
          <div class="buscar">
            <input type="text" [(ngModel)]="docBuscar" placeholder="Número de documento"
                   (keyup.enter)="buscar()">
            <button class="ui-btn ui-btn--primary ui-btn--sm" (click)="buscar()">
              <i class="fa fa-magnifying-glass"></i> Buscar
            </button>
          </div>

          @if (buscado()) {
            @if (encontrada(); as p) {
              <div class="ui-info-bar ui-info-bar--success">
                Ya registrada: <strong>{{ p.full_name }}</strong> (#{{ p.persona_id }})
              </div>
            } @else {
              <div class="ui-info-bar ui-info-bar--info">
                No existe en el padrón. Complétalo para registrarla.
              </div>
              <div class="grid">
                <label><span>Tipo documento</span>
                  <select [(ngModel)]="reg.tipo_documento_codigo">
                    @for (t of tipos(); track t.codigo) { <option [value]="t.codigo">{{ t.nombre }}</option> }
                  </select>
                </label>
                <label><span>Documento *</span><input type="text" [(ngModel)]="reg.numero_documento" readonly></label>
                <label><span>Primer nombre *</span><input type="text" [(ngModel)]="reg.nombre1"></label>
                <label><span>Segundo nombre</span><input type="text" [(ngModel)]="reg.nombre2"></label>
                <label><span>Primer apellido *</span><input type="text" [(ngModel)]="reg.apellido1"></label>
                <label><span>Segundo apellido</span><input type="text" [(ngModel)]="reg.apellido2"></label>
                <label><span>Fecha nacimiento</span><input type="date" [(ngModel)]="reg.fecha_nacimiento"></label>
              </div>
              <div class="acts">
                <button class="ui-btn ui-btn--primary ui-btn--sm" [disabled]="guardando()" (click)="registrar()">
                  @if (guardando()) { Registrando… } @else { Registrar persona }
                </button>
              </div>
            }
          }
          @if (msg()) { <p class="msg" [class.err]="err()">{{ msg() }}</p> }
        </article>

        <!-- Listado -->
        <article class="ui-card">
          <header class="ui-card__header">
            <h2 class="ui-card__title"><i class="fa fa-check-to-slot" aria-hidden="true"></i> Han votado ({{ votantes().length }})</h2>
          </header>
          <div class="tbl-wrap">
            <table class="tbl">
              <thead><tr><th>Documento</th><th>Nombre</th><th>Evento</th><th>Fecha</th></tr></thead>
              <tbody>
                @for (v of votantes(); track $index) {
                  <tr>
                    <td><code>{{ v.document_number }}</code></td>
                    <td>{{ v.voter_full_name }}</td>
                    <td>{{ v.event_name }}</td>
                    <td>{{ v.created_at | date:'short' }}</td>
                  </tr>
                } @empty {
                  <tr><td colspan="4" class="muted">Aún no hay votantes.</td></tr>
                }
              </tbody>
            </table>
          </div>
        </article>
      </div>
    </div>
  `,
  styles: [`
    @use '../../../styles/tokens' as *;
    :host { display: block; }
    .page { max-width: 1200px; margin: 0 auto; }
    .page__header { display: flex; justify-content: space-between; align-items: flex-start; gap: $space-3; flex-wrap: wrap; margin-bottom: $space-4; }
    .page__header h1 { margin: 0; color: $color-primary; i { margin-right: $space-2; } }
    .page__subtitle { color: $color-text-muted; margin: $space-1 0 0; }
    .kpis { display: flex; gap: $space-3; margin-bottom: $space-4; }
    .kpi { background: #fff; border: 1px solid $color-border; border-left: 4px solid $color-primary; border-radius: $radius-md; padding: $space-3; min-width: 130px;
      &__val { display: block; font-size: 1.8rem; font-weight: 700; color: $color-primary; line-height: 1; }
      &__lbl { font-size: $font-size-xs; color: $color-text-muted; text-transform: uppercase; } }
    .cols { display: grid; grid-template-columns: 1fr 1fr; gap: $space-4; @media (max-width: 860px) { grid-template-columns: 1fr; } }
    .buscar { display: flex; gap: $space-2; margin-bottom: $space-3;
      input { flex: 1; padding: $space-2; border: 1px solid $color-border; border-radius: $radius-sm; font: inherit; } }
    .grid { display: grid; grid-template-columns: 1fr 1fr; gap: $space-2; margin-top: $space-2; }
    label { display: block; span { display: block; font-size: $font-size-xs; color: $color-text-muted; }
      input, select { width: 100%; padding: 6px 8px; border: 1px solid $color-border; border-radius: $radius-sm; font: inherit; } }
    .acts { display: flex; justify-content: flex-end; margin-top: $space-2; }
    .tbl-wrap { overflow-x: auto; }
    .tbl { width: 100%; border-collapse: collapse;
      th, td { padding: $space-2; border-bottom: 1px solid $color-border; text-align: left; font-size: $font-size-sm; }
      th { color: $color-text-muted; text-transform: uppercase; font-size: $font-size-xs; } }
    .muted { color: $color-text-muted; }
    .msg { margin: $space-2 0 0; color: $color-success; &.err { color: $color-danger; } }
  `],
})
export class VotacionesVotantesComponent implements OnInit {
  private api = inject(VotacionesApi);
  private layout = inject(LayoutService);

  tipos = signal<{ codigo: number; nombre: string }[]>([]);
  votantes = signal<any[]>([]);
  totalGeneral = signal<number>(0);
  totalHoy = signal<number>(0);
  buscado = signal<boolean>(false);
  encontrada = signal<any | null>(null);
  guardando = signal<boolean>(false);
  msg = signal<string>('');
  err = signal<boolean>(false);
  docBuscar = '';
  reg: any = {};

  ngOnInit(): void {
    this.layout.setBreadcrumb([
      { label: 'Inicio', url: '/' },
      { label: 'Votaciones', url: '/votaciones' },
      { label: 'Votantes' },
    ]);
    this.api.votantesTipos().subscribe(r => this.tipos.set(r.results));
    this.cargarLista();
  }

  cargarLista(): void {
    this.api.votantesList().subscribe(r => {
      this.votantes.set(r.results || []);
      this.totalGeneral.set(r.total_general || 0);
      this.totalHoy.set(r.total_hoy || 0);
    });
  }

  buscar(): void {
    const doc = this.docBuscar.trim();
    if (!doc) return;
    this.msg.set(''); this.err.set(false);
    this.api.votantesBuscar(doc).subscribe({
      next: (r) => {
        this.buscado.set(true);
        if (r.exists) {
          this.encontrada.set(r);
        } else {
          this.encontrada.set(null);
          this.reg = { numero_documento: doc, tipo_documento_codigo: this.tipos()[0]?.codigo };
        }
      },
      error: () => { this.err.set(true); this.msg.set('Error en la búsqueda.'); },
    });
  }

  registrar(): void {
    if (!this.reg.nombre1?.trim() || !this.reg.apellido1?.trim()) {
      this.err.set(true); this.msg.set('Primer nombre y primer apellido son obligatorios.'); return;
    }
    this.guardando.set(true); this.msg.set(''); this.err.set(false);
    this.api.votantesRegistrar(this.reg).subscribe({
      next: (r) => {
        this.guardando.set(false);
        this.msg.set(`✓ ${r.ya_existia ? 'Ya existía' : 'Registrada'}: ${r.full_name}`);
        this.buscado.set(false); this.docBuscar = ''; this.reg = {};
      },
      error: (e) => { this.guardando.set(false); this.err.set(true); this.msg.set(e?.error?.detail || 'Error al registrar.'); },
    });
  }
}
