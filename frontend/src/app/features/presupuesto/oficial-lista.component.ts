import { CommonModule } from '@angular/common';
import { Component, OnInit, inject, signal, computed } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { HttpClient } from '@angular/common/http';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { firstValueFrom } from 'rxjs';
import { ConfigService } from '../../core/config/config.service';
import { LayoutService } from '../../core/layout/layout.service';

const POR_PAGINA = 10;

const META = {
  metas: { titulo: 'Metas', icono: 'fa-flag-checkered',
    subt: 'Metas del Plan de Desarrollo Local. Fuente: Matriz de Seguimiento PDL de la Alcaldía Local.' },
  proyectos: { titulo: 'Proyectos', icono: 'fa-folder-tree',
    subt: 'Proyectos de inversión del Plan. Fuente: Matriz de Seguimiento PDL de la Alcaldía Local.' },
  programas: { titulo: 'Programas', icono: 'fa-diagram-project',
    subt: 'Programas del Plan, bajo su objetivo estratégico. Fuente: Matriz de Seguimiento PDL.' },
} as const;

type Tipo = keyof typeof META;

/**
 * Metas, proyectos o programas del Plan, en tarjetas con buscador y paginación.
 *
 * LA FUENTE ES LA MATRIZ PDL DE LA ALK desde el 2026-09-07. Antes salía de
 * `sdp_meta_oficial`, el espejo de Datos Abiertos, que lleva parado desde
 * febrero: mostraba 70 metas cuando el Plan tiene 78, 28 proyectos de 31 y 21
 * programas de 22. Una pantalla rotulada «oficial» que muestra ocho metas
 * menos de las que existen es peor que no tenerla.
 *
 * El espejo NO se retiró: cada fila trae su contraste, y las que no aparecen
 * allá se marcan. Que una meta esté en la Matriz y no en Datos Abiertos es
 * justamente lo que Planeación necesita ver.
 *
 * El `tipo` viene de `data.tipo` de la ruta.
 */
@Component({
  standalone: true,
  selector: 'app-oficial-lista',
  imports: [CommonModule, FormsModule, RouterLink],
  template: `
    <div class="page">
      <header class="page__header">
        <h1><i class="fa" [class]="cfgMeta.icono" aria-hidden="true"></i> {{ cfgMeta.titulo }} <span class="of">· del Plan</span></h1>
        <p class="page__subtitle">{{ cfgMeta.subt }}</p>
      </header>

      @if (cargando()) {
        <p class="muted">Cargando…</p>
      } @else if (!items().length) {
        <div class="ui-empty-state"><i class="fa fa-info-circle" aria-hidden="true"></i>
          <p>Todavía no hay Plan cargado. Entra con la Matriz PDL.</p></div>
      } @else {
        <div class="barra">
          <input class="buscador" type="search" [(ngModel)]="busqueda"
                 (ngModelChange)="pagina.set(1)" placeholder="Buscar…" />
          <span class="conteo">{{ filtradas().length }} {{ cfgMeta.titulo.toLowerCase() }}</span>
        </div>

        <div class="lista">
          @for (it of paginaActual(); track it.codigo) {
            <article class="mc">
              <div class="mc__head">
                <span class="chip">{{ it.codigo }}</span>
                <h3 class="mc__title">{{ it.nombre }}</h3>
                @if (tipo === 'metas' && !it.espejo) {
                  <span class="badge badge--no" title="Está en la Matriz de la ALK pero no en Datos Abiertos del Distrito">sin par en SDP</span>
                }
                @if (tipo === 'proyectos') {
                  @if (!it.en_innovak) { <span class="badge badge--no">no cargado en innovaK</span> }
                  @else if (!it.en_espejo) { <span class="badge badge--no">sin par en SDP</span> }
                }
              </div>

              @if (tipo === 'metas') {
                <p class="mc__ruta">
                  {{ it.objetivo_nombre }} <span class="sep">›</span>
                  {{ it.programa_nombre }} <span class="sep">›</span>
                  {{ it.proyecto_codigo }} {{ it.proyecto_nombre }}
                </p>
                <div class="mc__stats">
                  <div class="st"><span class="st__n">{{ mill(it.apropiacion_poai) }}</span><span class="st__l">Apropiación POAI</span></div>
                  <div class="st"><span class="st__n">{{ mill(it.comprometido) }}</span><span class="st__l">Comprometido</span></div>
                  <div class="st"><span class="st__n">{{ mill(it.girado) }}</span><span class="st__l">Girado</span></div>
                  <div class="st">
                    <span class="st__n st__n--txt">{{ it.alerta || 'Sin alerta' }}</span>
                    <span class="st__l">Avance de metas</span>
                  </div>
                </div>
                <!-- El contraste con Datos Abiertos, en la misma tarjeta: es la
                     comparación que antes obligaba a abrir dos pantallas. -->
                @if (it.espejo) {
                  <p class="mc__espejo">
                    <span class="rotulo">Datos Abiertos SDP</span>
                    {{ it.espejo.programado | number:'1.0-0' }} programado ·
                    {{ it.espejo.entregado | number:'1.0-0' }} entregado
                    @if (it.espejo.tipo_anualizacion) { · {{ it.espejo.tipo_anualizacion }} }
                  </p>
                }
              } @else if (tipo === 'proyectos') {
                <p class="mc__ruta">
                  {{ it.objetivo }} <span class="sep">·</span> {{ it.sector }}
                  @if (it.subgrupo) { <span class="sep">·</span> {{ it.subgrupo }} }
                </p>
                <div class="mc__stats">
                  <div class="st"><span class="st__n">{{ it.n_metas }}</span><span class="st__l">Metas</span></div>
                  <div class="st"><span class="st__n">{{ mill(it.apropiacion_poai) }}</span><span class="st__l">Apropiación POAI</span></div>
                  <div class="st"><span class="st__n">{{ mill(it.comprometido) }}</span><span class="st__l">Comprometido</span></div>
                  <div class="st"><span class="st__n">{{ mill(it.girado) }}</span><span class="st__l">Girado</span></div>
                </div>
              } @else {
                <p class="mc__ruta">{{ it.objetivo }}</p>
                <div class="mc__stats">
                  <div class="st"><span class="st__n">{{ it.n_proyectos }}</span><span class="st__l">Proyectos</span></div>
                  <div class="st"><span class="st__n">{{ it.n_metas }}</span><span class="st__l">Metas</span></div>
                  <div class="st"><span class="st__n">{{ mill(it.apropiacion_poai) }}</span><span class="st__l">Apropiación POAI</span></div>
                  <div class="st"><span class="st__n">{{ mill(it.comprometido) }}</span><span class="st__l">Comprometido</span></div>
                </div>
              }
            </article>
          }
        </div>

        <div class="pager">
          <button (click)="prev()" [disabled]="pagina() === 1">← Anterior</button>
          <span>Página {{ pagina() }} de {{ totalPaginas() }}</span>
          <button (click)="next()" [disabled]="pagina() >= totalPaginas()">Siguiente →</button>
        </div>
      }

      <a routerLink="/plan" class="ui-back-link">← Volver a Presupuesto</a>
    </div>
  `,
  styles: [`
    @use '../../../styles/tokens' as *;
    :host { display: block; }
    .page { max-width: 1100px; margin: 0 auto; }
    .page__header h1 { margin: 0; color: $color-primary; i { margin-right: $space-2; } }
    .of { color: $color-text-muted; font-weight: 400; font-size: $font-size-base; }
    .page__subtitle { color: $color-text-muted; margin: $space-1 0 $space-4; }
    .muted { color: $color-text-muted; }
    .barra { display: flex; align-items: center; gap: $space-3; margin-bottom: $space-3; flex-wrap: wrap; }
    .buscador { flex: 1; min-width: 220px; max-width: 460px; padding: $space-2 $space-3; border: 1px solid rgba(0,0,0,.15); border-radius: 8px; }
    .conteo { color: $color-text-muted; font-size: $font-size-sm; }
    .lista { display: flex; flex-direction: column; gap: $space-3; }
    .mc { border: 1px solid rgba(0,0,0,.1); border-radius: 12px; padding: $space-3 $space-4; background: #fff; }
    .mc__head { display: flex; align-items: center; gap: $space-2; flex-wrap: wrap; }
    .mc__title { margin: 0; font-size: $font-size-base; color: $color-text; flex: 1; min-width: 200px; }
    .mc__ruta { margin: $space-1 0 $space-3; color: $color-text-muted; font-size: $font-size-sm; }
    .mc__ruta .sep { opacity: .5; margin: 0 4px; }
    .mc__stats { display: grid; grid-template-columns: repeat(auto-fit, minmax(110px, 1fr)); gap: $space-2; }
    .st { background: rgba(0,0,0,.03); border-radius: 8px; padding: $space-2; text-align: center; }
    .st__n { display: block; font-weight: 700; font-variant-numeric: tabular-nums; color: $color-text; }
    .st__l { font-size: .72rem; color: $color-text-muted; }
    .p-alto { color: #16a34a; } .p-medio { color: #f59e0b; } .p-bajo { color: #dc2626; }
    .chip { border-radius: 999px; padding: 1px 9px; font-size: .75rem; background: $color-primary; color: #fff; font-variant-numeric: tabular-nums; white-space: nowrap; }
    .badge { border-radius: 999px; padding: 1px 9px; font-size: .72rem; white-space: nowrap; }
    .badge--ok { background: #dcfce7; color: #166534; } .badge--no { background: #fee2e2; color: #991b1b; }
    /* El contraste con Datos Abiertos: presente pero secundario. Es dato de
       apoyo, no la cifra del Plan — y el peso visual tiene que decirlo. */
    .mc__espejo {
      margin: $space-2 0 0;
      padding-top: $space-2;
      border-top: 1px dashed $color-border;
      font-size: $font-size-sm;
      color: $color-text-muted;
      .rotulo { display: block; font-size: 10px; letter-spacing: .08em;
                text-transform: uppercase; color: $color-text-muted; }
    }
    /* La alerta es una frase, no una cifra: no puede heredar el tamaño de un
       número de seis dígitos o se sale de la tarjeta. */
    .st__n--txt { font-size: $font-size-sm; line-height: 1.25; }
    .pager { display: flex; align-items: center; gap: $space-3; margin-top: $space-4; justify-content: center; flex-wrap: wrap; }
    .pager button { padding: $space-1 $space-3; border: 1px solid rgba(0,0,0,.15); border-radius: 8px; background: #fff; cursor: pointer; }
    .pager button:disabled { opacity: .4; cursor: default; }
    .ui-back-link { display: inline-block; margin-top: $space-4; color: $color-primary; }
  `],
})
export class OficialListaComponent implements OnInit {
  private http = inject(HttpClient);
  private cfg = inject(ConfigService);
  private layout = inject(LayoutService);
  private ruta = inject(ActivatedRoute);

  tipo: Tipo = 'metas';
  get cfgMeta() { return META[this.tipo]; }

  items = signal<any[]>([]);

  /** Pesos a «$N,N M». La Matriz trae PESOS —el Excel los da así— y el espejo
   *  venía en millones; mostrar los dos con el mismo formato sin convertir era
   *  lo que hacía ver una cifra un millón de veces más chica. `null` no es 0:
   *  un proyecto sin apropiación reportada no apropió «cero pesos». */
  mill(v: number | null | undefined): string {
    if (v == null) return 'Sin dato';
    return `$${(v / 1e6).toLocaleString('es-CO', { maximumFractionDigits: 0 })} M`;
  }
  cargando = signal<boolean>(true);
  busqueda = signal<string>('');
  pagina = signal<number>(1);

  filtradas = computed(() => {
    const q = this.busqueda().trim().toLowerCase();
    if (!q) return this.items();
    return this.items().filter(it =>
      JSON.stringify(it).toLowerCase().includes(q));
  });
  totalPaginas = computed(() => Math.max(1, Math.ceil(this.filtradas().length / POR_PAGINA)));
  paginaActual = computed(() => {
    const ini = (this.pagina() - 1) * POR_PAGINA;
    return this.filtradas().slice(ini, ini + POR_PAGINA);
  });

  prev(): void { if (this.pagina() > 1) this.pagina.update(p => p - 1); }
  next(): void { if (this.pagina() < this.totalPaginas()) this.pagina.update(p => p + 1); }
  nivel(pct: number): 'alto' | 'medio' | 'bajo' { return pct >= 80 ? 'alto' : pct >= 50 ? 'medio' : 'bajo'; }

  async ngOnInit(): Promise<void> {
    this.tipo = (this.ruta.snapshot.data['tipo'] as Tipo) || 'metas';
    this.layout.setBreadcrumb([
      { label: 'Inicio', url: '/' },
      { label: 'Plan de Desarrollo', url: '/plan' },
      { label: this.cfgMeta.titulo },
    ]);
    try {
      const r: any = await firstValueFrom(
        this.http.get(this.cfg.url(`/dashboard/api/v2/presupuesto/oficial/${this.tipo}/`)));
      this.items.set(r?.items ?? []);
    } catch {
      this.items.set([]);
    } finally {
      this.cargando.set(false);
    }
  }
}
