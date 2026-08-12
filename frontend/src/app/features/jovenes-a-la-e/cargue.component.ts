import { CommonModule } from '@angular/common';
import { HttpClient } from '@angular/common/http';
import { Component, OnInit, computed, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';

interface FilaReporte {
  fila: number;
  estado: 'ok' | 'aviso' | 'error';
  errores: string[];
  avisos: string[];
  datos: Record<string, any>;
}

interface NivelResumen {
  nivel: string;
  etiqueta: string;
  es_superior: boolean;
  matriculas: number;
  personas: number;
}

interface OpcionMatricula {
  fila: number;
  programa: string | null;
  snies_programa: string | null;
  institucion: string | null;
  snies_ies: string | null;
  nivel: string | null;
}

interface DocumentoRepetido {
  documento: string;
  nombre: string;
  opciones: OpcionMatricula[];
}

interface EventoCargue {
  id: number;
  nombre: string;
  fecha_inicio: string | null;
  actividad_plan_id: number | null;
  cargable: boolean;
}

interface Lote {
  id: number;
  evento_nombre: string | null;
  vigencia: number;
  archivo_nombre: string;
  estado: 'validado' | 'procesado' | 'anulado';
  filas_total: number;
  filas_ok: number;
  filas_error: number;
}

interface Prevalidacion {
  resumen: {
    archivo: string;
    hoja: string;
    fila_encabezado: number;
    titulo: string | null;
    vigencia: number | null;
    total: number;
    ok: number;
    con_aviso: number;
    con_error: number;
    personas_distintas: number;
    trae_cumplimiento: boolean;
    columnas_ignoradas: string[];
    avisos_globales: string[];
    desglose_nivel: {
      niveles: NivelResumen[];
      superior: { matriculas: number; personas: number };
      etdh: { matriculas: number; personas: number };
      personas_en_ambos_grupos: number;
    };
  };
  filas: FilaReporte[];
  repetidos: DocumentoRepetido[];
  puede_procesar: boolean;
  siguiente_paso: string;
}

/**
 * Cargue masivo de beneficiarios desde el Excel del área.
 *
 * Tres tiempos, con la compuerta humana en el medio:
 *
 *   1. Revisar   → lee el archivo y muestra qué trae. NO guarda nada.
 *   2. Preparar  → crea el lote con su hash y las elecciones.
 *   3. Procesar  → escribe personas y entregas. Pide confirmación.
 *
 * Entre el 1 y el 2 está la decisión que el sistema no toma solo: cuando una
 * persona aparece con dos matrículas, **se carga una sola y cuál lo elige quien
 * carga** (decisión de Alex, 2026-08-12). El botón de preparar queda bloqueado
 * mientras falte alguna elección.
 *
 * Backend: `apps/jovenes_a_la_e/api/cargues.py`.
 *
 * La tabla muestra el NÚMERO DE FILA REAL del Excel — con el título arriba, el
 * primer dato es la fila 3 —, que es lo único que le sirve a quien abre el
 * archivo a corregir.
 */
@Component({
  standalone: true,
  selector: 'app-jovenes-cargue',
  imports: [CommonModule, FormsModule, RouterLink],
  template: `
    <div class="page">
      <header class="page__header">
        <h1><i class="fa fa-file-import" aria-hidden="true"></i> Cargue de beneficiarios</h1>
        <p class="page__subtitle">
          Suba el Excel del área para revisarlo antes de cargarlo.
          <a routerLink="/jovenes">Volver a las entregas</a>
        </p>
      </header>

      <article class="ui-card">
        <div class="ui-card__body">
          <div class="campos">
            <label class="campo">
              <span class="campo__label">Archivo (.xlsx)</span>
              <input type="file" accept=".xlsx" (change)="onArchivo($event)">
            </label>
            <label class="campo campo--corto">
              <span class="campo__label">Vigencia</span>
              <input type="number" min="2024" max="2100" [(ngModel)]="vigencia"
                     name="vigencia" placeholder="2025">
            </label>
            <label class="campo">
              <span class="campo__label">Evento de captura</span>
              <select [(ngModel)]="eventoId" name="evento">
                <option [ngValue]="null">— elija el evento —</option>
                @for (e of eventos(); track e.id) {
                  <option [ngValue]="e.id" [disabled]="!e.cargable">
                    {{ e.nombre }}{{ e.cargable ? '' : ' (sin actividad del plan)' }}
                  </option>
                }
              </select>
            </label>
            <button class="ui-btn ui-btn--primary" [disabled]="!archivo() || cargando()"
                    (click)="prevalidar()">
              {{ cargando() ? 'Revisando…' : 'Revisar archivo' }}
            </button>
          </div>
          <p class="nota">
            Revisar <strong>no guarda nada</strong>. Solo después de revisar aparece el
            botón para cargar de verdad.
          </p>
          @if (!eventos().length) {
            <p class="alerta alerta--aviso">
              No hay ningún evento de entrega de becas creado todavía. Cree uno en
              Actividades (tipo «Entrega de becas») y asígnele su actividad del plan:
              sin eso los beneficiarios no le suman a ninguna meta.
            </p>
          }
          @if (error()) {
            <p class="alerta alerta--error">{{ error() }}</p>
          }
        </div>
      </article>

      <!-- El lote, una vez creado -->
      @if (lote(); as l) {
        <article class="ui-card" [class.ui-card--primary]="l.estado === 'validado'">
          <div class="ui-card__body">
            <h2>Lote #{{ l.id }} · {{ l.estado }}</h2>
            <p class="nota">
              {{ l.archivo_nombre }} · vigencia {{ l.vigencia }} ·
              {{ l.filas_ok }} de {{ l.filas_total }} matrículas se cargarían
              @if (l.evento_nombre) { · evento: {{ l.evento_nombre }} }
            </p>
            @if (l.estado === 'validado') {
              <p class="alerta alerta--aviso">
                Todavía <strong>no se ha escrito nada</strong>. Al procesar se crean las
                personas y las entregas — es el paso que no se deshace solo.
              </p>
              <button class="ui-btn ui-btn--primary" [disabled]="cargando()"
                      (click)="procesar()">
                Procesar y cargar {{ l.filas_ok }} beneficiarios
              </button>
            }
            @if (l.estado === 'procesado') {
              <p class="alerta alerta--ok">
                Cargado. {{ hecho()?.creadas }} entregas nuevas,
                {{ hecho()?.enriquecidas }} completadas sobre capturas del QR,
                {{ hecho()?.descartadas }} descartadas por elección.
              </p>
              @for (a of hecho()?.avisos || []; track a) {
                <p class="alerta alerta--aviso">{{ a }}</p>
              }
              <button class="ui-btn ui-btn--ghost ui-btn--sm" (click)="anular()">
                Deshacer este cargue
              </button>
            }
            @if (l.estado === 'anulado') {
              <p class="nota">Lote anulado: se borró lo que había escrito y el archivo
                 se puede volver a cargar.</p>
            }
          </div>
        </article>
      }

      @if (resultado(); as r) {
        <!-- Personas con más de una matrícula: hay que elegir -->
        @if (r.repetidos.length && !lote()) {
          <article class="ui-card ui-card--warn">
            <div class="ui-card__body">
              <h2>Personas con más de una matrícula</h2>
              <p class="nota">
                Estas personas aparecen varias veces en el archivo con programas
                distintos. <strong>Se carga una sola por persona</strong>: elija cuál.
                Las otras quedan registradas como descartadas, con el motivo.
              </p>
              @for (rep of r.repetidos; track rep.documento) {
                <div class="repetido">
                  <h3>{{ rep.nombre }} <small>· {{ rep.documento }}</small></h3>
                  @for (o of rep.opciones; track o.fila) {
                    <label class="opcion">
                      <input type="radio" [name]="'rep-' + rep.documento" [value]="o.fila"
                             [checked]="elecciones[rep.documento] === o.fila"
                             (change)="elegir(rep.documento, o.fila)">
                      <span>
                        <strong>Fila {{ o.fila }}</strong> — {{ o.programa || 'sin programa' }}
                        <small>({{ o.institucion || 'sin institución' }})</small>
                      </span>
                    </label>
                  }
                </div>
              }
              @if (faltanElecciones()) {
                <p class="alerta alerta--aviso">
                  Falta elegir en {{ faltanElecciones() }} persona(s).
                </p>
              }
            </div>
          </article>
        }

        <!-- Botón de cargar -->
        @if (!lote()) {
          <article class="ui-card">
            <div class="ui-card__body">
              <button class="ui-btn ui-btn--primary" (click)="crearLote()"
                      [disabled]="!puedeCargar() || cargando()">
                {{ cargando() ? 'Preparando…' : 'Preparar cargue' }}
              </button>
              <p class="nota">
                @if (!r.puede_procesar) { Hay filas con error: corrija el archivo y vuelva a revisarlo. }
                @else if (!eventoId) { Elija el evento de captura arriba. }
                @else if (faltanElecciones()) { Elija una matrícula por cada persona repetida. }
                @else { {{ r.siguiente_paso }} }
              </p>
            </div>
          </article>
        }

        <!-- Resumen -->
        <div class="kpi-grid">
          <article class="ui-card ui-card--primary">
            <div class="ui-card__body kpi">
              <span class="kpi__label">Matrículas en el archivo</span>
              <span class="kpi__value">{{ r.resumen.total }}</span>
            </div>
          </article>
          <article class="ui-card ui-card--info">
            <div class="ui-card__body kpi">
              <span class="kpi__label">Personas distintas</span>
              <span class="kpi__value">{{ r.resumen.personas_distintas }}</span>
            </div>
          </article>
          <article class="ui-card">
            <div class="ui-card__body kpi">
              <span class="kpi__label">Sin problemas</span>
              <span class="kpi__value">{{ r.resumen.ok }}</span>
            </div>
          </article>
          <article class="ui-card" [class.ui-card--warn]="r.resumen.con_aviso > 0">
            <div class="ui-card__body kpi">
              <span class="kpi__label">Con aviso</span>
              <span class="kpi__value">{{ r.resumen.con_aviso }}</span>
            </div>
          </article>
          <article class="ui-card" [class.ui-card--danger]="r.resumen.con_error > 0">
            <div class="ui-card__body kpi">
              <span class="kpi__label">Con error</span>
              <span class="kpi__value">{{ r.resumen.con_error }}</span>
            </div>
          </article>
        </div>

        <!-- Desglose por nivel: las dos lecturas del mismo dato -->
        <article class="ui-card">
          <div class="ui-card__body">
            <h2>Nivel de formación</h2>
            <p class="nota">
              <strong>{{ r.resumen.personas_distintas }} beneficiarios</strong> ·
              {{ r.resumen.desglose_nivel.superior.personas }} en educación superior ·
              {{ r.resumen.desglose_nivel.etdh.personas }} en ETDH
            </p>
            @if (r.resumen.desglose_nivel.personas_en_ambos_grupos > 0) {
              <p class="alerta alerta--aviso">
                {{ r.resumen.desglose_nivel.personas_en_ambos_grupos }} persona(s) tienen
                matrícula en los dos grupos, así que aparecen contadas en ambos: por eso
                la suma da más que el total de personas.
              </p>
            }
            <table class="tabla">
              <thead>
                <tr><th>Nivel</th><th>Grupo</th><th class="num">Matrículas</th><th class="num">Personas</th></tr>
              </thead>
              <tbody>
                @for (n of r.resumen.desglose_nivel.niveles; track n.nivel) {
                  <tr>
                    <td>{{ n.etiqueta }}</td>
                    <td>{{ n.es_superior ? 'Educación superior' : 'ETDH' }}</td>
                    <td class="num">{{ n.matriculas }}</td>
                    <td class="num">{{ n.personas }}</td>
                  </tr>
                }
              </tbody>
            </table>
          </div>
        </article>

        <!-- Lo que hay que saber del archivo -->
        <article class="ui-card">
          <div class="ui-card__body">
            <h2>Sobre el archivo</h2>
            <ul class="lista">
              <li>Hoja <strong>{{ r.resumen.hoja }}</strong>, encabezado en la fila
                  {{ r.resumen.fila_encabezado }}.</li>
              @if (r.resumen.titulo) { <li>Título: «{{ r.resumen.titulo }}»</li> }
              <li>
                Acceso / permanencia:
                @if (r.resumen.trae_cumplimiento) { <strong>sí los trae</strong> }
                @else { <strong>no los trae</strong> }
              </li>
              @if (r.resumen.columnas_ignoradas.length) {
                <li>Columnas que no se leyeron: {{ r.resumen.columnas_ignoradas.join(', ') }}</li>
              }
            </ul>
            @for (a of r.resumen.avisos_globales; track a) {
              <p class="alerta alerta--aviso">{{ a }}</p>
            }
            <p class="nota">{{ r.siguiente_paso }}</p>
          </div>
        </article>

        <!-- Reporte fila a fila -->
        <article class="ui-card">
          <div class="ui-card__body">
            <h2>Detalle por fila</h2>
            <div class="filtros">
              <label><input type="checkbox" [(ngModel)]="soloProblemas" name="soloProblemas">
                Ver solo las filas con error o aviso</label>
            </div>
            <table class="tabla">
              <thead>
                <tr>
                  <th class="num">Fila</th><th>Estado</th><th>Documento</th>
                  <th>Nombre</th><th>Programa</th><th>Qué pasa</th>
                </tr>
              </thead>
              <tbody>
                @for (f of filasVisibles(); track f.fila) {
                  <tr [class.fila--error]="f.estado === 'error'"
                      [class.fila--aviso]="f.estado === 'aviso'">
                    <td class="num">{{ f.fila }}</td>
                    <td><span class="chip chip--{{ f.estado }}">{{ f.estado }}</span></td>
                    <td>{{ f.datos['documento'] || '—' }}</td>
                    <td>{{ nombre(f) }}</td>
                    <td>{{ f.datos['programa'] || '—' }}</td>
                    <td>
                      @for (e of f.errores; track e) { <div class="msg msg--error">{{ e }}</div> }
                      @for (a of f.avisos; track a) { <div class="msg msg--aviso">{{ a }}</div> }
                    </td>
                  </tr>
                }
              </tbody>
            </table>
            @if (!filasVisibles().length) {
              <p class="nota">No hay filas con problemas. </p>
            }
          </div>
        </article>
      }
    </div>
  `,
  styles: [`
    .campos { display: flex; gap: 16px; align-items: flex-end; flex-wrap: wrap; }
    .campo { display: flex; flex-direction: column; gap: 4px; }
    .campo--corto input { width: 110px; }
    .campo__label { font-size: .82rem; font-weight: 600; }
    .nota { font-size: .86rem; color: var(--text-muted, #666); margin-top: 12px; }
    .alerta { padding: 8px 12px; border-radius: 6px; margin: 8px 0; font-size: .88rem; }
    .alerta--error { background: #fdecea; color: #a4291c; }
    .alerta--aviso { background: #fff6e5; color: #8a5a00; }
    .tabla { width: 100%; border-collapse: collapse; margin-top: 12px; font-size: .88rem; }
    .tabla th, .tabla td { padding: 6px 8px; border-bottom: 1px solid #eee; text-align: left;
                           vertical-align: top; }
    .tabla .num { text-align: right; }
    .fila--error { background: #fdf3f2; }
    .fila--aviso { background: #fffaf0; }
    .chip { padding: 1px 8px; border-radius: 10px; font-size: .76rem; text-transform: uppercase; }
    .chip--ok { background: #e6f4ea; color: #1e7b34; }
    .chip--aviso { background: #fff0d0; color: #8a5a00; }
    .chip--error { background: #fbdedb; color: #a4291c; }
    .msg { font-size: .82rem; }
    .msg--error { color: #a4291c; }
    .msg--aviso { color: #8a5a00; }
    .lista { margin: 8px 0 0 18px; font-size: .9rem; }
    .filtros { margin-top: 8px; font-size: .88rem; }
  `],
})
export class JovenesCargueComponent implements OnInit {
  private http = inject(HttpClient);
  private readonly base = '/jovenes-a-la-e/api/cargues';

  archivo = signal<File | null>(null);
  vigencia: number | null = null;
  eventoId: number | null = null;
  eventos = signal<EventoCargue[]>([]);
  cargando = signal(false);
  error = signal<string | null>(null);
  resultado = signal<Prevalidacion | null>(null);
  lote = signal<Lote | null>(null);
  hecho = signal<{ creadas: number; enriquecidas: number; descartadas: number;
                   avisos: string[] } | null>(null);
  elecciones: Record<string, number> = {};
  soloProblemas = false;

  ngOnInit(): void {
    this.http.get<{ eventos: EventoCargue[] }>(`${this.base}/eventos/`).subscribe({
      next: (r) => this.eventos.set(r.eventos),
      error: () => this.eventos.set([]),
    });
  }

  elegir(documento: string, fila: number): void {
    this.elecciones = { ...this.elecciones, [documento]: fila };
  }

  faltanElecciones(): number {
    const r = this.resultado();
    if (!r) return 0;
    return r.repetidos.filter((rep) => !this.elecciones[rep.documento]).length;
  }

  puedeCargar(): boolean {
    const r = this.resultado();
    return !!r && r.puede_procesar && !!this.eventoId && !!this.vigencia
      && this.faltanElecciones() === 0;
  }

  filasVisibles = computed(() => {
    const r = this.resultado();
    if (!r) return [];
    return this.soloProblemas ? r.filas.filter((f) => f.estado !== 'ok') : r.filas;
  });

  nombre(f: FilaReporte): string {
    return ['nombre1', 'nombre2', 'apellido1', 'apellido2']
      .map((k) => f.datos[k]).filter(Boolean).join(' ') || '—';
  }

  onArchivo(ev: Event): void {
    const input = ev.target as HTMLInputElement;
    this.archivo.set(input.files?.[0] ?? null);
    // Cambiar de archivo invalida todo lo anterior: el reporte, las elecciones
    // (que apuntan a números de fila de OTRO archivo) y el lote en curso.
    this.resultado.set(null);
    this.lote.set(null);
    this.hecho.set(null);
    this.elecciones = {};
    this.error.set(null);
  }

  prevalidar(): void {
    const f = this.archivo();
    if (!f) return;
    const body = new FormData();
    body.append('archivo', f);
    if (this.vigencia) body.append('vigencia', String(this.vigencia));

    this.cargando.set(true);
    this.error.set(null);
    this.http.post<Prevalidacion>(`${this.base}/prevalidar/`, body).subscribe({
      next: (r) => {
        this.resultado.set(r);
        this.elecciones = {};
        this.cargando.set(false);
      },
      error: (e) => {
        this.error.set(e?.error?.detail || 'No se pudo revisar el archivo.');
        this.cargando.set(false);
      },
    });
  }

  /** Paso 2: guarda el lote con su hash y las elecciones. Aún no escribe entregas. */
  crearLote(): void {
    const f = this.archivo();
    if (!f || !this.puedeCargar()) return;
    const body = new FormData();
    body.append('archivo', f);
    body.append('vigencia', String(this.vigencia));
    body.append('evento_id', String(this.eventoId));
    body.append('elecciones', JSON.stringify(this.elecciones));

    this.cargando.set(true);
    this.error.set(null);
    this.http.post<Lote>(`${this.base}/`, body).subscribe({
      next: (l) => { this.lote.set(l); this.cargando.set(false); },
      error: (e) => {
        this.error.set(e?.error?.detail || 'No se pudo preparar el cargue.');
        this.cargando.set(false);
      },
    });
  }

  /** Paso 3: el que escribe. Con confirmación, porque no se deshace solo. */
  procesar(): void {
    const l = this.lote();
    if (!l) return;
    if (!confirm(`Se van a crear ${l.filas_ok} beneficiarios en la vigencia `
                 + `${l.vigencia}. ¿Continuar?`)) return;

    this.cargando.set(true);
    this.error.set(null);
    this.http.post<any>(`${this.base}/${l.id}/procesar/`, {}).subscribe({
      next: (r) => {
        this.hecho.set(r);
        this.lote.set(r.lote);
        this.cargando.set(false);
      },
      error: (e) => {
        this.error.set(e?.error?.detail || 'No se pudo procesar el cargue.');
        this.cargando.set(false);
      },
    });
  }

  anular(): void {
    const l = this.lote();
    if (!l) return;
    if (!confirm('Se van a borrar las entregas que creó este cargue. ¿Continuar?')) return;
    this.cargando.set(true);
    this.http.post<any>(`${this.base}/${l.id}/anular/`, {}).subscribe({
      next: (r) => { this.lote.set(r.lote); this.hecho.set(null); this.cargando.set(false); },
      error: (e) => {
        this.error.set(e?.error?.detail || 'No se pudo anular el cargue.');
        this.cargando.set(false);
      },
    });
  }
}
