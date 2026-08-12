import { CommonModule } from '@angular/common';
import { HttpClient } from '@angular/common/http';
import { Component, computed, inject, signal } from '@angular/core';
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
  puede_procesar: boolean;
  siguiente_paso: string;
}

/**
 * Cargue masivo de beneficiarios desde el Excel del área.
 *
 * Hoy solo PREVALIDA: sube el archivo, lo lee y muestra qué trae, sin escribir
 * nada. El procesamiento definitivo espera el DDL 004 (tabla del lote).
 *
 * Backend: `apps/jovenes_a_la_e/api/cargues.py::CarguePrevalidarView`.
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
            <button class="ui-btn ui-btn--primary" [disabled]="!archivo() || cargando()"
                    (click)="prevalidar()">
              {{ cargando() ? 'Revisando…' : 'Revisar archivo' }}
            </button>
          </div>
          <p class="nota">
            Esta pantalla <strong>no guarda nada todavía</strong>: solo lee el archivo y
            le dice qué trae y qué habría que corregir.
          </p>
          @if (error()) {
            <p class="alerta alerta--error">{{ error() }}</p>
          }
        </div>
      </article>

      @if (resultado(); as r) {
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
export class JovenesCargueComponent {
  private http = inject(HttpClient);

  archivo = signal<File | null>(null);
  vigencia: number | null = null;
  cargando = signal(false);
  error = signal<string | null>(null);
  resultado = signal<Prevalidacion | null>(null);
  soloProblemas = false;

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
    this.resultado.set(null);
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
    this.http.post<Prevalidacion>('/jovenes-a-la-e/api/cargues/prevalidar/', body).subscribe({
      next: (r) => { this.resultado.set(r); this.cargando.set(false); },
      error: (e) => {
        this.error.set(e?.error?.detail || 'No se pudo revisar el archivo.');
        this.cargando.set(false);
      },
    });
  }
}
