import { CommonModule } from '@angular/common';
import { Component, OnInit, computed, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { HttpClient } from '@angular/common/http';
import { RouterLink } from '@angular/router';
import { firstValueFrom } from 'rxjs';
import { ConfigService } from '../../core/config/config.service';
import { LayoutService } from '../../core/layout/layout.service';

interface Carga {
  id: number;
  archivo_nombre: string;
  archivo_bytes: number | null;
  corte_oficial: string | null;
  estado: 'borrador' | 'aplicada' | 'descartada';
  n_altas: number; n_cambios: number; n_retiros: number;
  sin_cambios: boolean | null;
  subido_at: string | null; aplicado_at: string | null;
  nota: string | null;
  archivo_disponible: boolean;
  diff?: any;
}

/**
 * Subir la Matriz PDL: previsualizar el cambio y decidirlo.
 *
 * DOS PASOS, Y NO ES UN RODEO. Subir NO escribe: registra la carga en
 * `borrador` con su diff, y aplicar es una segunda decisión sobre algo que ya
 * se miró. Si subir aplicara, el estado `borrador` no significaría nada y esta
 * pantalla no tendría razón de existir — bastaría la consola.
 *
 * LO QUE LA CARGA NUNCA HACE: borrar. Lo que desaparece de la matriz queda
 * marcado inactivo apuntando a la carga que lo retiró, y lo que el archivo no
 * trae se queda como está. Un DELETE perdería la respuesta a «¿desde cuándo
 * dejó de existir este programa?», que es justo lo que un plan de desarrollo
 * tiene que poder contestar.
 */
@Component({
  standalone: true,
  selector: 'app-matriz-carga',
  imports: [CommonModule, FormsModule, RouterLink],
  template: `
    <div class="page">
      <header class="page__header">
        <h1><i class="fa fa-file-arrow-up" aria-hidden="true"></i> Cargar Matriz PDL</h1>
        <p class="page__subtitle">
          El Excel de seguimiento que manda la Alcaldía Local. Se sube, se
          revisa el cambio y recién ahí se aplica.
        </p>
      </header>

      <!-- La regla, escrita donde se decide y no en un manual aparte. -->
      <p class="regla">
        <i class="fa fa-shield-halved" aria-hidden="true"></i>
        <span>
          <b>La carga actualiza; no suma dos veces ni borra.</b> Una meta que ya
          está se actualiza con el valor nuevo, lo que el archivo no trae se
          queda como está, y lo que desaparece de la matriz se marca inactivo
          —nunca se elimina— apuntando a esta carga.
        </span>
      </p>

      @if (error(); as e) {
        <p class="ui-info-bar ui-info-bar--danger" role="alert">{{ e }}</p>
      }
      @if (aviso(); as a) {
        <p class="ui-info-bar ui-info-bar--success" role="status">{{ a }}</p>
      }

      <section class="subir" aria-labelledby="subir-tit">
        <h2 id="subir-tit">Subir un corte</h2>
        <div class="subir__campos">
          <label class="campo">
            <span>Archivo de la matriz (.xlsx)</span>
            <input type="file" accept=".xlsx,.xlsm" (change)="elegir($event)">
          </label>
          <label class="campo">
            <span>Fecha de corte que declara la matriz</span>
            <input type="date" [(ngModel)]="corte" [max]="hoy" name="corte">
            <small>No es la fecha de hoy: es la que la matriz dice cubrir.</small>
          </label>
          <button type="button" class="btn btn--primario"
                  [disabled]="!archivo || !corte || subiendo()"
                  (click)="subir()">
            {{ subiendo() ? 'Leyendo el archivo…' : 'Subir y previsualizar' }}
          </button>
        </div>
        @if (subiendo()) {
          <p class="muted">Se leen las cuatro hojas y se compara contra lo que hay. Puede tardar.</p>
        }
      </section>

      <!-- EL CRP DE BOGDATA, en la misma pantalla y a propósito: son dos
           archivos que alimentan el mismo tablero y los sube la misma
           persona. Separarlos obligaría a recordar cuál va dónde. -->
      <section class="subir subir--crp" aria-labelledby="crp-tit">
        <h2 id="crp-tit">Subir el CRP de BogData</h2>
        <p class="regla regla--crp">
          <i class="fa fa-circle-info" aria-hidden="true"></i>
          <span>
            <b>Acá subir SÍ escribe</b>, a diferencia de la Matriz. El CRP es un
            estado de cuenta: sus filas reemplazan el saldo anterior y no
            proponen nada que decidir. Lo que protege es el control de totales:
            si no cuadran, no entra ni una fila.
          </span>
        </p>
        <div class="subir__campos">
          <label class="campo">
            <span>Reporte de CRP (.xlsx)</span>
            <input type="file" accept=".xlsx,.xlsm" (change)="elegirCrp($event)">
          </label>
          <label class="campo campo--ancho">
            <span>Totales de control (opcional, del pie del reporte)</span>
            <input type="text" [(ngModel)]="totalesCrp" name="totCrp"
                   placeholder="valor CRP, anulaciones, reintegros, neto, girado, sin girar">
            <small>
              Separados por coma, en ese orden. Sin ellos la carga entra igual —
              pero un reporte cortado a la mitad se ve perfecto fila por fila.
            </small>
          </label>
          <button type="button" class="btn btn--primario"
                  [disabled]="!archivoCrp || subiendoCrp()"
                  (click)="subirCrp()">
            {{ subiendoCrp() ? 'Cargando…' : 'Cargar CRP' }}
          </button>
        </div>
        @if (subiendoCrp()) {
          <p class="muted">Se leen las 2.630 filas, se validan los totales y se
             cruzan los compromisos contra los contratos. Puede tardar.</p>
        }
        @if (errorCrp(); as e) {
          <p class="ui-info-bar ui-info-bar--danger" role="alert">{{ e }}</p>
        }
        @if (ultimaCrp(); as u) {
          <div class="bloque">
            <h3>Carga {{ u.id }} · corte {{ u.fecha_corte }}</h3>
            <p class="bloque__resumen">
              {{ u.filas_leidas }} filas ·
              <b>{{ u.filas_insertadas }}</b> nuevas ·
              <b>{{ u.filas_actualizadas }}</b> actualizadas ·
              {{ u.filas_no_vigentes }} marcadas no vigentes
            </p>
            @if (u.sin_totales) {
              <p class="ui-info-bar ui-info-bar--warn">
                Se cargó sin control de totales. Si el reporte venía incompleto,
                no había cómo saberlo.
              </p>
            }
            <!-- Lo que no cruzó se muestra SIEMPRE, aunque la carga fuera bien:
                 es la medida de cuánto de la contratación estamos viendo. -->
            @if (u.compromisos_sin_contrato) {
              <p class="motivo">
                <b>{{ u.compromisos_sin_contrato }}</b> compromisos no tienen
                contrato en innovaK. No se crean solos.
                @if (u.compromisos_sin_contrato_muestra?.length) {
                  <small>{{ u.compromisos_sin_contrato_muestra!.slice(0, 8).join(', ') }}…</small>
                }
              </p>
            }
            <!-- Aparte de los que se evaluaron y no cruzaron: éstos ni
                 siquiera son un número de contrato, así que nunca llegaron a
                 mirarse. Si la fuente cambia de formato, este sube y el otro
                 baja, que es la dirección tranquilizadora. -->
            @if (u.compromiso_no_parsea_filas) {
              <p class="motivo">
                <b>{{ u.compromiso_no_parsea_filas }}</b> filas traen un número de
                compromiso que no es un contrato y no se evaluaron.
                @if (u.compromiso_no_parsea_muestra?.length) {
                  <small>{{ u.compromiso_no_parsea_muestra.slice(0, 6).join(', ') }}…</small>
                }
              </p>
            }
            @if (u.rubros_sin_proyecto) {
              <p class="motivo">
                <b>{{ u.rubros_sin_proyecto }}</b> rubros de inversión sin proyecto
                en la Matriz.
              </p>
            }
            @if (u.proyecto_por_contrato) {
              <p class="motivo">
                <b>{{ u.proyecto_por_contrato }}</b> filas tomaron el proyecto del
                contrato registrado en innovaK, porque el rubro no lo identificaba
                (obligaciones por pagar).
              </p>
            }
            @if (u.compromisos_ambiguos?.length) {
              <p class="ui-info-bar ui-info-bar--danger">
                {{ u.compromisos_ambiguos.length }} números de contrato existen en
                innovaK con más de un tipo. Su CRP queda sin enganchar, en vez de
                colgarse del contrato equivocado.
              </p>
            }
            @if (u.choques_rubro_pep) {
              <p class="ui-info-bar ui-info-bar--danger">
                {{ u.choques_rubro_pep }} filas con el rubro y el PEP apuntando a
                proyectos distintos: hay que revisar la fuente.
              </p>
            }
          </div>
        }
        @if (cargasCrp().length) {
          <table class="tabla">
            <thead>
              <tr><th scope="col">#</th><th scope="col">Corte</th>
                  <th scope="col">Archivo</th><th scope="col">Filas</th>
                  <th scope="col">Neto</th></tr>
            </thead>
            <tbody>
              @for (c of cargasCrp(); track c.id) {
                <tr>
                  <td>{{ c.id }}</td>
                  <td>{{ c.fecha_corte }}</td>
                  <td class="nom">{{ c.archivo_nombre }}</td>
                  <td>{{ c.filas_leidas }}</td>
                  <td>{{ mill(c.total_valor_neto) }}</td>
                </tr>
              }
            </tbody>
          </table>
        }
      </section>

      @if (sel(); as c) {
        <section class="diff" aria-labelledby="diff-tit">
          <header class="diff__h">
            <h2 id="diff-tit">Carga {{ c.id }} · {{ c.archivo_nombre }}</h2>
            <span class="estado" [class]="'estado--' + c.estado">{{ c.estado }}</span>
          </header>
          <p class="diff__meta">
            Corte {{ c.corte_oficial }} ·
            {{ c.n_altas }} altas · {{ c.n_cambios }} cambios · {{ c.n_retiros }} retiros
          </p>

          @if (c.sin_cambios) {
            <p class="ui-info-bar ui-info-bar--info">
              Este archivo no cambia nada de lo que ya está cargado. Es un
              resultado válido: significa que la base ya refleja este corte.
            </p>
          }

          <!-- Jerarquía y cifras traen diff estructurado; estructura y alertas,
               el reporte del importador. Van separados porque no son lo mismo y
               mezclarlos aparentaría una uniformidad que no existe. -->
          @if (c.diff?.jerarquia; as j) {
            <article class="bloque">
              <h3>Jerarquía del Plan</h3>
              <div class="filas">
                @for (e of ['sector', 'objetivo', 'programa']; track e) {
                  <div class="fila">
                    <span class="fila__n">{{ e }}</span>
                    <span>{{ j[e]?.altas?.length || 0 }} altas</span>
                    <span>{{ j[e]?.cambios?.length || 0 }} cambios</span>
                    <span>{{ j[e]?.retiros?.length || 0 }} retiros</span>
                  </div>
                }
              </div>
            </article>
          }

          @if (c.diff?.cifras; as f) {
            <article class="bloque">
              <h3>Plata por meta y vigencia</h3>
              <p class="bloque__resumen">
                {{ f.filas_leidas }} filas leídas ·
                <b>{{ f.altas?.length || 0 }}</b> nuevas ·
                <b>{{ f.cambios?.length || 0 }}</b> con cambio ·
                {{ f.sin_cambio }} iguales
              </p>
              @if (f.cambios?.length) {
                <table class="tabla">
                  <thead>
                    <tr><th scope="col">Meta</th><th scope="col">Vig.</th><th scope="col">Qué cambia</th></tr>
                  </thead>
                  <tbody>
                    @for (x of f.cambios.slice(0, 40); track x.codigo_meta + '-' + x.vigencia) {
                      <tr>
                        <td>{{ x.codigo_meta }}</td>
                        <td>{{ x.vigencia }}</td>
                        <td class="campos">
                          @for (kv of pares(x.campos); track kv[0]) {
                            <span class="cambio">
                              <b>{{ kv[0] }}</b>
                              {{ money(kv[1].de) }} → {{ money(kv[1].a) }}
                            </span>
                          }
                        </td>
                      </tr>
                    }
                  </tbody>
                </table>
                @if (f.cambios.length > 40) {
                  <p class="muted">y {{ f.cambios.length - 40 }} más.</p>
                }
              }
            </article>
          }

          @for (par of reportes(c); track par[0]) {
            <article class="bloque">
              <h3>{{ par[0] }}</h3>
              @if (!par[1].ok) {
                <p class="ui-info-bar ui-info-bar--danger">
                  No va a poder correr: {{ par[1].error }}
                </p>
              }
              <pre class="reporte">{{ par[1].reporte || '(sin salida)' }}</pre>
            </article>
          }

          @if (c.estado === 'borrador') {
            <div class="acciones">
              @if (!c.archivo_disponible) {
                <p class="ui-info-bar ui-info-bar--danger">
                  El archivo ya no está en disco: hay que volver a subirlo.
                </p>
              } @else if (confirmando()) {
                <p class="confirmar">
                  Esto escribe el Plan para toda la localidad. ¿Aplicar la carga {{ c.id }}?
                  <button type="button" class="btn btn--primario" [disabled]="aplicando()"
                          (click)="aplicar(c)">{{ aplicando() ? 'Aplicando…' : 'Sí, aplicar' }}</button>
                  <button type="button" class="btn" (click)="confirmando.set(false)">Cancelar</button>
                </p>
              } @else {
                <button type="button" class="btn btn--primario"
                        (click)="confirmando.set(true)">Aplicar esta carga</button>
                <button type="button" class="btn" [disabled]="aplicando()"
                        (click)="descartar(c)">Descartar</button>
              }
            </div>
          }
        </section>
      }

      <section class="historial" aria-labelledby="hist-tit">
        <h2 id="hist-tit">Cargas anteriores</h2>
        @if (cargando()) {
          <p class="muted">Cargando…</p>
        } @else if (!cargas().length) {
          <p class="muted">
            Todavía no se ha subido ninguna matriz por acá. Los cortes que ya
            están en la base entraron por consola, antes de que existiera esta
            pantalla.
          </p>
        } @else {
          <table class="tabla">
            <thead>
              <tr>
                <th scope="col">#</th><th scope="col">Corte</th><th scope="col">Archivo</th>
                <th scope="col">Estado</th><th scope="col">Cambios</th><th scope="col"></th>
              </tr>
            </thead>
            <tbody>
              @for (c of cargas(); track c.id) {
                <tr>
                  <td>{{ c.id }}</td>
                  <td>{{ c.corte_oficial }}</td>
                  <td class="nom">{{ c.archivo_nombre }}</td>
                  <td><span class="estado" [class]="'estado--' + c.estado">{{ c.estado }}</span></td>
                  <td>{{ c.n_altas }}/{{ c.n_cambios }}/{{ c.n_retiros }}</td>
                  <td><button type="button" class="btn btn--chico" (click)="ver(c.id)">Ver</button></td>
                </tr>
              }
            </tbody>
          </table>
        }
      </section>

      <a routerLink="/presupuesto" class="ui-back-link">← Volver a Presupuesto</a>
    </div>
  `,
  styles: [`
    @use '../../../styles/tokens' as *;
    :host { display: block; }
    .page { max-width: 1100px; margin: 0 auto; padding-bottom: $space-8; }
    .page__header h1 { margin: 0; color: $color-primary; i { margin-right: $space-2; } }
    .page__subtitle { margin: $space-1 0 0; color: $color-text-muted; }
    .muted { color: $color-text-muted; }

    .subir--crp { border-top: 1px solid var(--color-border, #e5e7eb); padding-top: 1rem; }
    .regla--crp { border-left-color: #B45309; i { color: #B45309; } }
    .campo--ancho { flex: 1 1 26rem; }

    .regla {
      display: flex; gap: $space-3; align-items: flex-start;
      margin: $space-4 0; padding: $space-3 $space-4;
      background: $color-neutral-50; border-left: 3px solid #0D9488;
      border-radius: $radius-sm; font-size: $font-size-sm; line-height: 1.5;
      i { color: #0D9488; margin-top: 3px; }
    }

    section { margin-top: $space-5; }
    section > h2 { font-size: $font-size-lg; margin: 0 0 $space-3; }

    .subir__campos { display: flex; gap: $space-4; flex-wrap: wrap; align-items: flex-end; }
    .campo { display: flex; flex-direction: column; gap: 4px; font-size: $font-size-sm;
             span { font-weight: $font-weight-semibold; }
             small { color: $color-text-muted; font-size: 11px; } }
    .campo input { padding: 6px 8px; border: 1px solid $color-border; border-radius: $radius-sm; }

    .btn { padding: 7px $space-4; border: 1px solid $color-border; border-radius: $radius-sm;
           background: $color-neutral-0; cursor: pointer; font-size: $font-size-sm;
           &:disabled { opacity: .55; cursor: not-allowed; } }
    .btn--primario { background: $color-primary; color: #fff; border-color: $color-primary; }
    .btn--chico { padding: 3px $space-2; font-size: 12px; }

    .diff__h { display: flex; align-items: center; gap: $space-3; flex-wrap: wrap;
               h2 { margin: 0; font-size: $font-size-lg; } }
    .diff__meta { margin: 4px 0 $space-3; color: $color-text-muted; font-size: $font-size-sm; }
    .estado { padding: 2px 8px; border-radius: $radius-pill; font-size: 11px;
              text-transform: uppercase; letter-spacing: .06em; border: 1px solid $color-border; }
    .estado--borrador { background: #fef3c7; border-color: #fde68a; }
    .estado--aplicada { background: #dcfce7; border-color: #bbf7d0; }
    .estado--descartada { background: $color-neutral-100; }

    .bloque { margin-top: $space-4; padding: $space-3 $space-4;
              border: 1px solid $color-border; border-radius: $radius-md;
              h3 { margin: 0 0 $space-2; font-size: $font-size-base; } }
    .bloque__resumen { margin: 0 0 $space-2; font-size: $font-size-sm; }
    .filas { display: flex; flex-direction: column; gap: 4px; }
    .fila { display: flex; gap: $space-4; font-size: $font-size-sm;
            &__n { min-width: 90px; font-weight: $font-weight-semibold; text-transform: capitalize; } }

    /* Ancho propio: los reportes traen líneas largas y el ancho del contenido
       no puede empujar la página entera a scroll horizontal. */
    .reporte { max-height: 260px; overflow: auto; background: $color-neutral-50;
               padding: $space-3; border-radius: $radius-sm; font-size: 11px;
               line-height: 1.45; white-space: pre-wrap; margin: 0; }

    .tabla { width: 100%; border-collapse: collapse; font-size: $font-size-sm;
             th, td { text-align: left; padding: 5px $space-2; border-bottom: 1px solid $color-border; }
             th { font-size: 11px; text-transform: uppercase; letter-spacing: .06em;
                  color: $color-text-muted; } }
    .nom { max-width: 320px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
    .campos { display: flex; flex-direction: column; gap: 2px; }
    .cambio { font-size: 12px; b { font-weight: $font-weight-semibold; } }

    .acciones { display: flex; gap: $space-3; margin-top: $space-4; align-items: center; flex-wrap: wrap; }
    .confirmar { display: flex; gap: $space-3; align-items: center; flex-wrap: wrap;
                 margin: 0; font-size: $font-size-sm; }
  `],
})
export class MatrizCargaComponent implements OnInit {
  private http = inject(HttpClient);
  private cfg = inject(ConfigService);
  private layout = inject(LayoutService);

  cargas = signal<Carga[]>([]);
  sel = signal<Carga | null>(null);
  cargando = signal(true);
  subiendo = signal(false);
  aplicando = signal(false);
  confirmando = signal(false);
  error = signal<string | null>(null);
  aviso = signal<string | null>(null);

  archivo: File | null = null;
  corte = '';

  // ── CRP de BogData ──
  archivoCrp: File | null = null;
  totalesCrp = '';
  subiendoCrp = signal(false);
  errorCrp = signal<string | null>(null);
  ultimaCrp = signal<any | null>(null);
  cargasCrp = signal<any[]>([]);
  hoy = new Date().toISOString().slice(0, 10);

  private base = '/presupuesto/api/matriz/cargas/';
  private baseCrp = '/presupuesto/api/crp/cargas/';

  ngOnInit(): void {
    this.layout.setBreadcrumb([
      { label: 'Inicio', url: '/' },
      { label: 'Presupuesto', url: '/presupuesto' },
      { label: 'Cargar Matriz PDL' },
    ]);
    this.listar();
    this.listarCrp();
  }

  elegirCrp(ev: Event): void {
    this.archivoCrp = (ev.target as HTMLInputElement).files?.[0] ?? null;
  }

  private async listarCrp(): Promise<void> {
    try {
      const r: any = await firstValueFrom(this.http.get(this.cfg.url(this.baseCrp)));
      this.cargasCrp.set(r?.items ?? []);
    } catch {
      this.cargasCrp.set([]);
    }
  }

  async subirCrp(): Promise<void> {
    if (!this.archivoCrp) return;
    this.subiendoCrp.set(true);
    this.errorCrp.set(null);
    const fd = new FormData();
    fd.append('archivo', this.archivoCrp);
    if (this.totalesCrp.trim()) fd.append('totales', this.totalesCrp.trim());
    try {
      const r: any = await firstValueFrom(this.http.post(this.cfg.url(this.baseCrp), fd));
      this.ultimaCrp.set(r);
      await this.listarCrp();
    } catch (e: any) {
      this.errorCrp.set(e?.error?.detail ?? 'No se pudo cargar el reporte.');
    } finally {
      this.subiendoCrp.set(false);
    }
  }

  private async listar(): Promise<void> {
    this.cargando.set(true);
    try {
      const r: any = await firstValueFrom(this.http.get(this.cfg.url(this.base)));
      this.cargas.set(r?.items ?? []);
    } catch {
      this.error.set('No se pudo leer el historial de cargas.');
    } finally {
      this.cargando.set(false);
    }
  }

  elegir(ev: Event): void {
    const input = ev.target as HTMLInputElement;
    this.archivo = input.files?.[0] ?? null;
  }

  async subir(): Promise<void> {
    if (!this.archivo || !this.corte) return;
    this.subiendo.set(true);
    this.error.set(null);
    this.aviso.set(null);
    const fd = new FormData();
    fd.append('archivo', this.archivo);
    fd.append('corte_oficial', this.corte);
    try {
      const r: any = await firstValueFrom(this.http.post(this.cfg.url(this.base), fd));
      this.sel.set(r);
      this.aviso.set(`Carga ${r.id} en borrador. Revisá el cambio antes de aplicar: todavía no se escribió nada.`);
      await this.listar();
    } catch (e: any) {
      this.error.set(e?.error?.detail ?? 'No se pudo leer el archivo.');
    } finally {
      this.subiendo.set(false);
    }
  }

  async ver(id: number): Promise<void> {
    this.confirmando.set(false);
    try {
      const r: any = await firstValueFrom(this.http.get(this.cfg.url(`${this.base}${id}/`)));
      this.sel.set(r);
    } catch {
      this.error.set('No se pudo abrir esa carga.');
    }
  }

  async aplicar(c: Carga): Promise<void> {
    this.aplicando.set(true);
    this.error.set(null);
    try {
      const r: any = await firstValueFrom(
        this.http.post(this.cfg.url(`${this.base}${c.id}/`), { accion: 'aplicar' }));
      this.sel.set(r);
      this.confirmando.set(false);
      this.aviso.set(`Carga ${c.id} aplicada. El Plan quedó al corte ${c.corte_oficial}.`);
      await this.listar();
    } catch (e: any) {
      this.error.set(e?.error?.detail ?? 'No se pudo aplicar la carga.');
    } finally {
      this.aplicando.set(false);
    }
  }

  async descartar(c: Carga): Promise<void> {
    try {
      const r: any = await firstValueFrom(
        this.http.post(this.cfg.url(`${this.base}${c.id}/`), { accion: 'descartar' }));
      this.sel.set(r);
      this.aviso.set(`Carga ${c.id} descartada. Queda registrada como revisada y no aplicada.`);
      await this.listar();
    } catch (e: any) {
      this.error.set(e?.error?.detail ?? 'No se pudo descartar.');
    }
  }

  /** Los dos reportes de importador, como pares [título, contenido]. */
  reportes(c: Carga): Array<[string, any]> {
    const d = c.diff ?? {};
    const out: Array<[string, any]> = [];
    if (d.estructura) out.push(['Proyectos, metas y KPI', d.estructura]);
    if (d.alertas) out.push(['Alertas de cumplimiento', d.alertas]);
    return out;
  }

  pares(o: any): Array<[string, any]> { return Object.entries(o ?? {}); }

  /** Pesos a «$N M». `null` cuando no hay dato: en una columna de plata, un 0
   *  se lee como «no hubo», que es otra cosa. */
  mill(v: number | null | undefined): string {
    if (v == null) return 'sin dato';
    return `$${(v / 1e6).toLocaleString('es-CO', { maximumFractionDigits: 0 })} M`;
  }

  /** `null` es «no había dato», y se dice con esa palabra en vez de con un 0
   *  que se leería como «valía cero pesos». */
  money(v: number | null): string {
    if (v == null) return 'sin dato';
    return `$${(v / 1e6).toLocaleString('es-CO', { maximumFractionDigits: 1 })} M`;
  }
}
