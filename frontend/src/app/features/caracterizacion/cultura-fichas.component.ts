import { CommonModule } from '@angular/common';
import { Component, OnInit, computed, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute } from '@angular/router';
import { LayoutService } from '../../core/layout/layout.service';
import {
  FichaCampo,
  FichaEvento,
  FichaRegistro,
  FichaSchema,
  FichasCulturaApi,
} from './fichas-cultura.api';

interface FichaCard {
  target: 'individuo' | 'organizacion' | 'lugar';
  label: string;
  icon: string;
  desc: string;
  color: string;
  activa: boolean;
}

interface Grupo {
  titulo: string;
  campos: FichaCampo[];
}

const FICHAS: FichaCard[] = [
  { target: 'individuo', label: 'Individuo', icon: 'fa-user', color: 'violet',
    desc: 'Persona atendida: identificación, datos demográficos, contacto y documentos.', activa: true },
  { target: 'organizacion', label: 'Organización', icon: 'fa-people-group', color: 'teal',
    desc: 'Colectivo u organización beneficiada: NIT, tipo, contacto.', activa: true },
  { target: 'lugar', label: 'Lugar / Espacio', icon: 'fa-location-dot', color: 'amber',
    desc: 'Espacio intervenido: contratista, intervención, elementos entregados.', activa: true },
];

const SECTOR_META: Record<string, { label: string; icon: string }> = {
  cultura: { label: 'Cultura', icon: 'fa-music' },
  seguridad: { label: 'Seguridad y Convivencia', icon: 'fa-shield-halved' },
};

/**
 * Página de caracterización de Cultura: 3 fichas (Individuo / Organización /
 * Lugar). La ficha la llena el equipo de Cultura para armar sus listas e
 * informes. El encabezado (Proyecto/Meta/Contrato) se jala de la cadena del
 * evento seleccionado.
 */
@Component({
  standalone: true,
  selector: 'app-cultura-fichas',
  imports: [CommonModule, FormsModule],
  template: `
    <div class="page">
      <!-- ══ LANDING: 3 fichas ══ -->
      @if (vista() === 'landing') {
        <header class="page__header">
          <h1><i class="fa" [class]="sectorIcon()" aria-hidden="true"></i> Caracterización — {{ sectorLabel() }}</h1>
          <p class="page__subtitle">
            Tres fichas para registrar lo atendido por {{ sectorLabel() }} y sacar informes.
            Selecciona una para empezar.
          </p>
        </header>

        <div class="fichas-grid">
          @for (f of fichas; track f.target) {
            <button class="ficha-card" [class]="'ficha-card--' + f.color"
                    [class.ficha-card--soon]="!f.activa"
                    (click)="abrirFicha(f)">
              <div class="ficha-card__icon"><i class="fa" [class]="f.icon" aria-hidden="true"></i></div>
              <h3 class="ficha-card__title">{{ f.label }}</h3>
              <p class="ficha-card__desc">{{ f.desc }}</p>
              @if (f.activa) {
                <span class="ficha-card__cta">Abrir <i class="fa fa-arrow-right" aria-hidden="true"></i></span>
              } @else {
                <span class="ficha-card__soon">Próximamente</span>
              }
            </button>
          }
        </div>
      }

      <!-- ══ FICHA SELECCIONADA ══ -->
      @if (vista() === 'ficha') {
        <header class="page__header page__header--row">
          <button class="ui-btn ui-btn--ghost ui-btn--sm" (click)="volver()">
            <i class="fa fa-arrow-left" aria-hidden="true"></i> Volver
          </button>
          <h1>
            <i class="fa" [class]="fichaActual().icon" aria-hidden="true"></i>
            Ficha de {{ fichaActual().label }} — {{ sectorLabel() }}
          </h1>
        </header>

        <div class="tabs">
          <button class="tab" [class.tab--active]="tab() === 'nueva'" (click)="tab.set('nueva')">
            <i class="fa fa-plus" aria-hidden="true"></i> Nueva ficha
          </button>
          <button class="tab" [class.tab--active]="tab() === 'registros'"
                  (click)="irRegistros()">
            <i class="fa fa-table-list" aria-hidden="true"></i> Registros
          </button>
        </div>

        <!-- ── Nueva ficha ── -->
        @if (tab() === 'nueva') {
          @if (cargandoSchema()) {
            <div class="ui-info-bar ui-info-bar--info">Cargando formulario…</div>
          }

          @if (schema(); as sc) {
            <!-- Encabezado: actividad → cadena -->
            <section class="ui-card encabezado">
              <div class="ui-card__body">
                <label class="field__label" for="evento-sel">
                  Actividad / intervención de {{ sectorLabel() }} <span class="req">*</span>
                </label>
                <select id="evento-sel" class="field__input" [(ngModel)]="eventoId"
                        (ngModelChange)="onEventoChange($event)">
                  <option [ngValue]="null">— Seleccionar actividad —</option>
                  @for (ev of eventos(); track ev.id) {
                    <option [ngValue]="ev.id">{{ ev.nombre }}</option>
                  }
                </select>

                @if (eventoSel(); as ev) {
                  <div class="cadena">
                    <div class="cadena__item">
                      <span class="cadena__k">Proyecto</span>
                      <span class="cadena__v">{{ ev.encabezado.proyecto || '—' }}</span>
                    </div>
                    <div class="cadena__item">
                      <span class="cadena__k">Meta</span>
                      <span class="cadena__v">{{ ev.encabezado.meta || '—' }}</span>
                    </div>
                    <div class="cadena__item">
                      <span class="cadena__k">N° Contrato</span>
                      <span class="cadena__v">{{ ev.encabezado.numero_contrato || '—' }}</span>
                    </div>
                    <div class="cadena__item">
                      <span class="cadena__k">Proceso contractual</span>
                      <span class="cadena__v">{{ ev.encabezado.proceso_contractual || '—' }}</span>
                    </div>
                    <div class="cadena__item">
                      <span class="cadena__k">Fecha</span>
                      <span class="cadena__v">{{ ev.encabezado.fecha_intervencion || '—' }}</span>
                    </div>
                  </div>
                }
              </div>
            </section>

            <!-- Errores del servidor -->
            @if (erroresServidor().length) {
              <div class="ui-info-bar ui-info-bar--danger" role="alert">
                <strong>Revisa estos campos:</strong>
                <ul>@for (e of erroresServidor(); track e) { <li>{{ e }}</li> }</ul>
              </div>
            }

            <!-- Campos por grupo -->
            @for (g of grupos(); track g.titulo) {
              <section class="ui-card grupo">
                <div class="ui-card__header"><h2>{{ g.titulo }}</h2></div>
                <div class="ui-card__body fields-grid">
                  @for (campo of g.campos; track campo.name) {
                    <div class="field"
                         [class.field--full]="campo.type === 'textarea'">
                      @if (campo.type !== 'checkbox') {
                        <label [for]="campo.name" class="field__label">
                          {{ campo.label }}
                          @if (campo.required) { <span class="req">*</span> }
                        </label>
                      }

                      @switch (campo.type) {
                        @case ('text') {
                          <input [id]="campo.name" type="text" class="field__input"
                                 [(ngModel)]="valores[campo.name]" [name]="campo.name">
                        }
                        @case ('number') {
                          <input [id]="campo.name" type="number" class="field__input"
                                 [(ngModel)]="valores[campo.name]" [name]="campo.name">
                        }
                        @case ('date') {
                          <input [id]="campo.name" type="date" class="field__input"
                                 [(ngModel)]="valores[campo.name]" [name]="campo.name">
                        }
                        @case ('textarea') {
                          <textarea [id]="campo.name" class="field__input" rows="3"
                                    [(ngModel)]="valores[campo.name]" [name]="campo.name"></textarea>
                        }
                        @case ('select') {
                          <select [id]="campo.name" class="field__input"
                                  [(ngModel)]="valores[campo.name]" [name]="campo.name">
                            <option value="">— Seleccionar —</option>
                            @for (opt of optionsDe(campo); track opt.value) {
                              <option [value]="opt.value">{{ opt.label }}</option>
                            }
                          </select>
                        }
                        @case ('checkbox') {
                          <label class="check" [for]="campo.name">
                            <input [id]="campo.name" type="checkbox"
                                   [(ngModel)]="valores[campo.name]" [name]="campo.name">
                            <span>{{ campo.label }}</span>
                          </label>
                        }
                        @case ('file') {
                          <div class="file">
                            <label [for]="campo.name" class="file__btn">
                              <i class="fa fa-paperclip" aria-hidden="true"></i>
                              {{ archivos[campo.name] ? 'Cambiar' : 'Adjuntar' }}
                            </label>
                            <input [id]="campo.name" type="file" accept="image/*,application/pdf"
                                   class="file__hidden" (change)="onFile($event, campo.name)">
                            @if (archivos[campo.name]; as f) {
                              <span class="file__name">{{ f.name }}
                                <button type="button" class="file__x" (click)="quitarArchivo(campo.name)"
                                        aria-label="Quitar">×</button>
                              </span>
                            }
                          </div>
                        }
                      }

                      @if (errorCampo(campo.name); as e) {
                        <p class="field__error">{{ e }}</p>
                      }
                    </div>
                  }
                </div>
              </section>
            }

            <div class="acciones">
              <button class="ui-btn ui-btn--primary" (click)="enviar()" [disabled]="enviando()">
                @if (enviando()) { Guardando… } @else {
                  <i class="fa fa-floppy-disk" aria-hidden="true"></i> Guardar ficha
                }
              </button>
            </div>
          }
        }

        <!-- ── Registros ── -->
        @if (tab() === 'registros') {
          <div class="reg-toolbar">
            <input type="search" class="field__input" placeholder="Buscar por nombre o documento…"
                   [(ngModel)]="busqueda" (keyup.enter)="cargarRegistros()">
            <button class="ui-btn ui-btn--outline ui-btn--sm" (click)="cargarRegistros()">
              <i class="fa fa-search" aria-hidden="true"></i> Buscar
            </button>
          </div>

          @if (cargandoReg()) {
            <div class="ui-info-bar ui-info-bar--info">Cargando…</div>
          } @else if (registros().length === 0) {
            <div class="ui-empty-state">
              <i class="fa fa-folder-open" aria-hidden="true"></i>
              <p>Aún no hay fichas registradas.</p>
            </div>
          } @else {
            <div class="ui-table-responsive">
              <table class="ui-table">
                <thead>
                  <tr><th>#</th><th>Nombre</th><th>Documento / NIT</th><th>Actividad</th><th>Estado</th><th>Fecha</th></tr>
                </thead>
                <tbody>
                  @for (r of registros(); track r.id) {
                    <tr>
                      <td>{{ r.id }}</td>
                      <td>{{ r.nombre_legal || '—' }}</td>
                      <td>{{ r.numero_documento || '—' }}</td>
                      <td>{{ r.evento_nombre || ('Evento #' + r.evento_id) }}</td>
                      <td><span class="badge" [class]="'badge--' + r.estado">{{ r.estado }}</span></td>
                      <td>{{ (r.created_at | date: 'short') || '—' }}</td>
                    </tr>
                  }
                </tbody>
              </table>
            </div>
            <p class="reg-total">{{ regCount() }} registro(s)</p>
          }
        }
      }

      <!-- Toast de éxito -->
      @if (exitoMsg()) {
        <div class="toast" role="status">
          <i class="fa fa-check-circle" aria-hidden="true"></i> {{ exitoMsg() }}
        </div>
      }
    </div>
  `,
  styles: [`
    @use '../../../styles/tokens' as *;

    :host { display: block; }
    .page { max-width: 1100px; margin: 0 auto; }
    .page__header { margin-bottom: $space-5; }
    .page__header--row { display: flex; align-items: center; gap: $space-3; }
    .page__header h1 { margin: 0; color: $color-primary; font-size: $font-size-xl; i { margin-right: $space-2; } }
    .page__subtitle { color: $color-text-muted; margin: $space-1 0 0; }
    .req { color: $color-danger; margin-left: 2px; }

    .fichas-grid {
      display: grid; gap: $space-4;
      grid-template-columns: 1fr;
      @media (min-width: #{$bp-md}) { grid-template-columns: repeat(3, 1fr); }
    }
    .ficha-card {
      display: flex; flex-direction: column; align-items: flex-start;
      text-align: left; gap: $space-2; padding: $space-5;
      background: $color-bg; border: 1px solid $color-border;
      border-radius: $radius-xl; cursor: pointer;
      transition: transform $transition-base, box-shadow $transition-base, border-color $transition-base;
      border-top: 4px solid $color-border;
    }
    .ficha-card:hover { transform: translateY(-2px); box-shadow: $shadow-md; }
    .ficha-card--soon { cursor: not-allowed; opacity: 0.7; }
    .ficha-card--violet { border-top-color: #8B5CF6; }
    .ficha-card--teal   { border-top-color: #0D9488; }
    .ficha-card--amber  { border-top-color: #F59E0B; }
    .ficha-card__icon {
      width: 48px; height: 48px; border-radius: $radius-lg;
      display: flex; align-items: center; justify-content: center;
      font-size: 1.4rem; color: $color-text-inverse; background: $color-primary;
    }
    .ficha-card--violet .ficha-card__icon { background: #8B5CF6; }
    .ficha-card--teal   .ficha-card__icon { background: #0D9488; }
    .ficha-card--amber  .ficha-card__icon { background: #F59E0B; }
    .ficha-card__title { margin: $space-2 0 0; font-size: $font-size-lg; color: $color-text; }
    .ficha-card__desc { margin: 0; font-size: $font-size-sm; color: $color-text-muted; }
    .ficha-card__cta { margin-top: $space-2; color: $color-primary; font-weight: $font-weight-semibold; font-size: $font-size-sm; }
    .ficha-card__soon { margin-top: $space-2; font-size: $font-size-xs; text-transform: uppercase; letter-spacing: 0.05em; color: $color-text-muted; }

    .tabs { display: flex; gap: $space-2; margin-bottom: $space-4; border-bottom: 1px solid $color-border; }
    .tab {
      padding: $space-3 $space-4; background: none; border: none; cursor: pointer;
      color: $color-text-muted; font-weight: $font-weight-semibold; font-size: $font-size-sm;
      border-bottom: 2px solid transparent;
    }
    .tab--active { color: $color-primary; border-bottom-color: $color-primary; }

    .encabezado { margin-bottom: $space-4; }
    .cadena {
      display: grid; gap: $space-3; margin-top: $space-4;
      grid-template-columns: repeat(2, 1fr);
      @media (min-width: #{$bp-md}) { grid-template-columns: repeat(5, 1fr); }
    }
    .cadena__item { display: flex; flex-direction: column; gap: 2px; }
    .cadena__k { font-size: $font-size-xs; text-transform: uppercase; letter-spacing: 0.04em; color: $color-text-muted; font-weight: $font-weight-semibold; }
    .cadena__v { font-size: $font-size-sm; color: $color-text; }

    .grupo { margin-bottom: $space-4; }
    .ui-card__header h2 { margin: 0; font-size: $font-size-md; color: $color-primary; }
    .fields-grid {
      display: grid; gap: $space-4; grid-template-columns: 1fr;
      @media (min-width: #{$bp-sm}) { grid-template-columns: 1fr 1fr; }
      @media (min-width: #{$bp-lg}) { grid-template-columns: 1fr 1fr 1fr; }
    }
    .field--full { grid-column: 1 / -1; }
    .field__label { display: block; font-size: $font-size-sm; font-weight: $font-weight-semibold; margin-bottom: $space-2; color: $color-text; }
    .field__input {
      display: block; width: 100%; min-height: $touch-target-min;
      padding: $space-2 $space-3; font-size: $font-size-base; font-family: $font-family-base;
      color: $color-text; background: $color-bg; border: 1.5px solid $color-border-strong;
      border-radius: $radius-lg; box-sizing: border-box;
    }
    .field__input:focus { outline: none; border-color: $color-primary; box-shadow: 0 0 0 3px rgba(13,148,136,0.15); }
    .field__error { color: $color-danger; font-size: $font-size-xs; margin: $space-1 0 0; }
    .check { display: flex; align-items: center; gap: $space-2; cursor: pointer; min-height: $touch-target-min; }
    .check input { width: 18px; height: 18px; accent-color: $color-primary; }
    .check span { font-size: $font-size-sm; }

    .file { display: flex; align-items: center; gap: $space-2; flex-wrap: wrap; }
    .file__hidden { position: absolute; left: -9999px; opacity: 0; width: 1px; height: 1px; }
    .file__btn {
      display: inline-flex; align-items: center; gap: $space-2; cursor: pointer;
      padding: $space-2 $space-3; border: 1.5px solid $color-border-strong;
      border-radius: $radius-lg; font-size: $font-size-sm; background: $color-bg-muted;
    }
    .file__name { font-size: $font-size-xs; color: $color-text-muted; display: inline-flex; align-items: center; gap: $space-1; }
    .file__x { border: none; background: none; cursor: pointer; color: $color-danger; font-size: 1rem; }

    .acciones { display: flex; justify-content: flex-end; margin: $space-2 0 $space-8; }

    .reg-toolbar { display: flex; gap: $space-2; margin-bottom: $space-4; max-width: 480px; }
    .reg-total { color: $color-text-muted; font-size: $font-size-sm; margin-top: $space-3; }
    .badge { font-size: $font-size-xs; padding: 2px $space-2; border-radius: $radius-pill; background: $color-bg-muted; }
    .badge--validada { background: $color-success-bg; color: $color-success; }
    .badge--rechazada { background: $color-danger-bg; color: $color-danger; }

    .toast {
      position: fixed; bottom: $space-6; left: 50%; transform: translateX(-50%);
      background: $color-success; color: $color-text-inverse; padding: $space-3 $space-5;
      border-radius: $radius-lg; box-shadow: $shadow-lg; z-index: $z-sticky;
      display: flex; align-items: center; gap: $space-2; font-weight: $font-weight-semibold;
    }
  `],
})
export class CulturaFichasComponent implements OnInit {
  private api = inject(FichasCulturaApi);
  private layout = inject(LayoutService);
  private route = inject(ActivatedRoute);

  sector = signal<string>('cultura');
  sectorLabel = computed(() => SECTOR_META[this.sector()]?.label ?? this.sector());
  sectorIcon = computed(() => SECTOR_META[this.sector()]?.icon ?? 'fa-clipboard-list');

  fichas = FICHAS;

  vista = signal<'landing' | 'ficha'>('landing');
  target = signal<'individuo' | 'organizacion' | 'lugar'>('individuo');
  fichaActual = computed(() => FICHAS.find((f) => f.target === this.target()) ?? FICHAS[0]);
  tab = signal<'nueva' | 'registros'>('nueva');

  eventos = signal<FichaEvento[]>([]);
  schema = signal<FichaSchema | null>(null);
  cargandoSchema = signal(false);

  eventoId: number | null = null;
  eventoSel = computed(() => this.eventos().find((e) => e.id === this.eventoId) ?? null);

  valores: Record<string, string | boolean> = {};
  archivos: Record<string, File> = {};

  enviando = signal(false);
  erroresServidor = signal<string[]>([]);
  private erroresCampo = signal<Record<string, string[]>>({});
  exitoMsg = signal('');

  busqueda = '';
  registros = signal<FichaRegistro[]>([]);
  regCount = signal(0);
  cargandoReg = signal(false);

  grupos = computed<Grupo[]>(() => {
    const campos = this.schema()?.campos ?? [];
    const orden: string[] = [];
    const mapa: Record<string, FichaCampo[]> = {};
    for (const c of campos) {
      if (!mapa[c.grupo]) { mapa[c.grupo] = []; orden.push(c.grupo); }
      mapa[c.grupo].push(c);
    }
    return orden.map((titulo) => ({ titulo, campos: mapa[titulo] }));
  });

  ngOnInit(): void {
    const sector = (this.route.snapshot.data['sector'] as string) || 'cultura';
    this.sector.set(sector);
    this.layout.setBreadcrumb([
      { label: 'Inicio', url: '/' },
      { label: 'Caracterización', url: '/caracterizacion' },
      { label: this.sectorLabel() },
    ]);
  }

  abrirFicha(f: FichaCard): void {
    if (!f.activa) return;
    this.target.set(f.target);
    this.vista.set('ficha');
    this.tab.set('nueva');
    this.cargarContexto();
    this.cargarSchema(f.target);
  }

  volver(): void {
    this.vista.set('landing');
  }

  private cargarContexto(): void {
    this.api.contexto(this.sector()).subscribe({
      next: (r) => this.eventos.set(r.eventos),
      error: () => this.eventos.set([]),
    });
  }

  private cargarSchema(target: string): void {
    this.cargandoSchema.set(true);
    this.api.schema(this.sector(), target).subscribe({
      next: (s) => {
        this.schema.set(s);
        this.inicializarValores(s.campos ?? []);
        this.cargandoSchema.set(false);
      },
      error: () => this.cargandoSchema.set(false),
    });
  }

  private inicializarValores(campos: FichaCampo[]): void {
    this.valores = {};
    this.archivos = {};
    for (const c of campos) {
      this.valores[c.name] = c.type === 'checkbox' ? false : '';
    }
  }

  onEventoChange(id: number | null): void {
    this.eventoId = id;
  }

  optionsDe(campo: FichaCampo): { value: string; label: string }[] {
    if (campo.catalogo) return this.schema()?.catalogos?.[campo.catalogo] ?? [];
    if (campo.options) return campo.options.map((o) => ({ value: o, label: o }));
    return [];
  }

  onFile(event: Event, name: string): void {
    const input = event.target as HTMLInputElement;
    const file = input.files?.[0];
    if (file) this.archivos[name] = file;
  }

  quitarArchivo(name: string): void {
    delete this.archivos[name];
  }

  errorCampo(name: string): string {
    const e = this.erroresCampo()[name];
    return e?.length ? e[0] : '';
  }

  enviar(): void {
    this.erroresServidor.set([]);
    this.erroresCampo.set({});
    if (!this.eventoId) {
      this.erroresServidor.set(['Selecciona la actividad de Cultura.']);
      return;
    }
    const sc = this.schema();
    if (!sc?.campos) return;

    const fd = new FormData();
    fd.append('evento_id', String(this.eventoId));
    for (const c of sc.campos) {
      if (c.type === 'file') {
        const f = this.archivos[c.name];
        if (f) fd.append(c.name, f, f.name);
      } else if (c.type === 'checkbox') {
        fd.append(c.name, this.valores[c.name] ? 'true' : 'false');
      } else {
        const v = this.valores[c.name];
        if (v !== undefined && v !== null && String(v).trim() !== '') {
          fd.append(c.name, String(v));
        }
      }
    }

    this.enviando.set(true);
    this.api.crear(this.sector(), this.target(), fd).subscribe({
      next: (r) => {
        this.enviando.set(false);
        this.exitoMsg.set(`Ficha #${r.id} guardada.`);
        setTimeout(() => this.exitoMsg.set(''), 3500);
        const ev = this.eventoId;
        this.inicializarValores(sc.campos ?? []);
        this.eventoId = ev;
        window.scrollTo({ top: 0, behavior: 'smooth' });
      },
      error: (err) => {
        this.enviando.set(false);
        const body = err.error;
        if (err.status === 400 && body?.errors) {
          this.erroresCampo.set(body.errors);
          const msgs: string[] = [];
          for (const [campo, errs] of Object.entries(body.errors as Record<string, string[]>)) {
            for (const e of errs) msgs.push(`${campo}: ${e}`);
          }
          this.erroresServidor.set(msgs);
        } else {
          this.erroresServidor.set([body?.detail || 'No se pudo guardar la ficha.']);
        }
        window.scrollTo({ top: 0, behavior: 'smooth' });
      },
    });
  }

  irRegistros(): void {
    this.tab.set('registros');
    this.cargarRegistros();
  }

  cargarRegistros(): void {
    this.cargandoReg.set(true);
    this.api.registros(this.sector(), this.target(), { q: this.busqueda || undefined }).subscribe({
      next: (r) => {
        this.registros.set(r.results);
        this.regCount.set(r.count);
        this.cargandoReg.set(false);
      },
      error: () => {
        this.registros.set([]);
        this.cargandoReg.set(false);
      },
    });
  }
}
