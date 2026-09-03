import { CommonModule } from '@angular/common';
import {
  ChangeDetectionStrategy, Component, ElementRef, OnDestroy, OnInit,
  ViewChild, inject, signal,
} from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { RouterLink } from '@angular/router';
import { Chart, registerables } from 'chart.js';
import { ConfigService } from '../../core/config/config.service';
import { LayoutService } from '../../core/layout/layout.service';

Chart.register(...registerables);
const PAL = ['#D6001C', '#0D9488', '#2563eb', '#d97706', '#7c3aed', '#16a34a', '#db2777', '#0ea5e9', '#84cc16', '#64748b'];
const AREA_COLORS: Record<string, string> = {
  'Relacionamiento Interinstitucional': '#E11D48',
  'Desarrollo Estratégico y Mejora': '#2563EB',
  'Seguridad': '#DC2626',
  'Cultura': '#8B5CF6',
  'Deporte': '#10B981',
  'Educación': '#0EA5E9',
  'Infraestructura': '#DB2777',
  'CPS y Planta': '#0891B2',
  'Subsidio tipo C': '#16A34A',
};
const AREA_ICONS: Record<string, string> = {
  'Relacionamiento Interinstitucional': 'fa-handshake',
  'Desarrollo Estratégico y Mejora': 'fa-chart-line',
  'Seguridad': 'fa-shield-halved',
  'Cultura': 'fa-music',
  'Deporte': 'fa-futbol',
  'Educación': 'fa-book',
  'Infraestructura': 'fa-building',
  'CPS y Planta': 'fa-users',
  'Subsidio tipo C': 'fa-sack-dollar',
};

@Component({
  standalone: true,
  selector: 'app-eventos-insights',
  imports: [CommonModule, RouterLink],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <div class="page">
      <header class="page__header">
        <div>
          <div class="page__title-row">
            <span class="page__title-icon"><i class="fa fa-chart-line"></i></span>
            <h1>Insights — {{ selArea() ? selArea()!.nombre : 'Actividades' }}</h1>
          </div>
          @if (selArea()) { <p class="page__sub">Área seleccionada: {{ selArea()!.nombre }} · {{ areaData()?.total ?? '…' }} actividades</p> }
        </div>
        <a routerLink="/eventos" class="ui-btn ui-btn--primary"><i class="fa fa-arrow-left"></i> Ver lista</a>
      </header>

      @if (loading()) { <div class="ui-info-bar ui-info-bar--info">Cargando...</div> }
      @else if (d()) { @if (d(); as i) {
        <div class="insights-body">
          <aside class="side">
            <div class="side-item side-item--todos" [class.active]="!selArea()" (click)="selectArea(null)">
              <span class="side-item__ic"><i class="fa fa-layer-group"></i></span>
              <span class="side-item__name">Todos · vista general</span>
              <span class="side-item__cnt">{{ i.total }}</span>
            </div>
            @for (s of i.por_subgrupo; track s.subgrupo__id) {
              <div class="side-item" [class.active]="selArea()?.id === s.subgrupo__id" (click)="selectArea({ id: s.subgrupo__id, nombre: s.subgrupo__nombre })">
                <span class="side-item__ic" [style.background]="areaColor(s.subgrupo__nombre)"><i [class]="'fa ' + areaIcon(s.subgrupo__nombre)"></i></span>
                <span class="side-item__name">{{ s.subgrupo__nombre }}</span>
                <span class="side-item__cnt">{{ s.c }}</span>
              </div>
            }
          </aside>

          <div class="insights-main">
            @if (!selArea()) {
              <div class="section-label">Resumen general</div>
              <div class="kpis">
                <article class="kpi"><span class="kpi__v">{{ i.total | number }}</span><span class="kpi__l">Actividades activas</span></article>
                <article class="kpi kpi--b"><span class="kpi__v">{{ i.proximos | number }}</span><span class="kpi__l">Próximas</span></article>
                <article class="kpi kpi--c"><span class="kpi__v">{{ i.en_curso | number }}</span><span class="kpi__l">En curso</span></article>
                <article class="kpi kpi--d"><span class="kpi__v">{{ i.ejecutados | number }}</span><span class="kpi__l">Ejecutadas</span></article>
              </div>

              <div class="section-label">Por área (subgrupo)</div>
              <div class="areas-grid">
                @for (s of i.por_subgrupo; track s.subgrupo_id) {
                  <div class="area-card" [style.border-top-color]="areaColor(s.subgrupo__nombre)" (click)="selectArea({ id: s.subgrupo_id, nombre: s.subgrupo__nombre })">
                    <div class="ac-top">
                      <span class="ac-icon" [style.background]="areaColor(s.subgrupo__nombre)"><i [class]="'fa ' + areaIcon(s.subgrupo__nombre)"></i></span>
                      <span class="ac-count">{{ s.c }}</span>
                    </div>
                    <div class="ac-name">{{ s.subgrupo__nombre }}</div>
                    <div class="ac-bar-bg"><div class="ac-bar-fill" [style.width.%]="i.total ? (s.c / i.total * 100) : 0" [style.background]="areaColor(s.subgrupo__nombre)"></div></div>
                    <div class="ac-share">{{ (i.total ? s.c / i.total * 100 : 0) | number:'1.0-1' }}% del total</div>
                  </div>
                }
              </div>

              <div class="section-label">Evolución y tipo</div>
              <div class="two-col">
                <article class="card"><h3>Evolución mensual</h3><div class="cbox cbox--tall"><canvas #chartMes></canvas></div></article>
                <article class="card"><h3>Por tipo</h3><div class="cbox"><canvas #chartTipo></canvas></div></article>
              </div>

              <div class="section-label">Detalle</div>
              <div class="grid2">
                <article class="card"><h3>Top funcionarios (carga)</h3><div class="cbox"><canvas #chartFunc></canvas></div></article>
                <article class="card">
                  <h3>Calidad del dato</h3>
                  <div class="cal"><span>Con KPI</span><div class="bar"><div class="bar__fill" [style.width.%]="i.pct_kpi"></div></div><b>{{ i.pct_kpi }}%</b></div>
                  <div class="cal"><span>Con ubicación</span><div class="bar"><div class="bar__fill" [style.width.%]="i.pct_lugar"></div></div><b>{{ i.pct_lugar }}%</b></div>
                  <div class="cal"><span>Caracterización</span><div class="bar"><div class="bar__fill" [style.width.%]="i.pct_caract"></div></div><b>{{ i.pct_caract }}%</b></div>
                  @if (i.subgrupos_sin_proximos?.length) {
                    <div class="alerta"><i class="fa fa-triangle-exclamation"></i> Sin actividades próximas:
                      @for (s of i.subgrupos_sin_proximos; track s) { <span class="ui-badge ui-badge--warning">{{ s }}</span> }
                    </div>
                  }
                </article>
              </div>
            } @else {
              @if (areaLoading()) { <div class="ui-info-bar ui-info-bar--info">Cargando datos del área...</div> }
              @else {
                @if (areaData(); as a) {
                <article class="card"><h3>Evolución mensual — {{ selArea()!.nombre }}</h3><div class="cbox cbox--tall"><canvas #chartMes></canvas></div></article>

                <div class="grid2">
                  <article class="card"><h3>Por tipo — {{ selArea()!.nombre }}</h3><div class="cbox"><canvas #chartTipo></canvas></div></article>
                  <article class="card"><h3>Top funcionarios — {{ selArea()!.nombre }}</h3><div class="cbox"><canvas #chartFunc></canvas></div></article>
                </div>

                <div class="area-note">El desglose “Próximas / En curso / Ejecutadas” y “Calidad del dato” todavía se calculan solo a nivel global — mostrarlos por área requeriría un ajuste en el backend que no se hizo en este cambio, exclusivamente de frontend.</div>
                }
              }
            }
          </div>
        </div>
      } }
    </div>
  `,
  styles: [`
    @use '../../../styles/tokens' as *;
    :host { display: block; }
    .page { max-width: 1200px; margin: 0 auto; }
    .page__title-row { display: flex; align-items: center; gap: $space-3; }
    .page__title-icon { display: flex; align-items: center; justify-content: center; width: 40px; height: 40px; border-radius: $radius-md; background: $color-primary; color: #fff; flex-shrink: 0; }
    .page__header { display: flex; justify-content: space-between; align-items: center; gap: $space-3; flex-wrap: wrap; margin-bottom: $space-4; h1 { margin: 0; color: $color-text; &::after { content: ''; display: block; margin-top: $space-2; width: 48px; height: 4px; border-radius: $radius-pill; background: $color-secondary; } } }
    .kpis { display: grid; grid-template-columns: repeat(4,1fr); gap: $space-3; margin-bottom: $space-4; @media (max-width: 700px){ grid-template-columns: repeat(2,1fr); } }
    .kpi { background: #fff; border: 1px solid $color-border; border-left: 5px solid $color-primary; border-radius: $radius-md; padding: $space-3; display: flex; flex-direction: column;
      &--b { border-left-color: #2563eb; } &--c { border-left-color: #16a34a; } &--d { border-left-color: #6b7280; }
      &__v { font-size: 1.8rem; font-weight: 700; line-height: 1; } &__l { font-size: $font-size-xs; color: $color-text-muted; } }
    .card { background: #fff; border: 1px solid $color-border; border-radius: $radius-lg; padding: $space-4; margin-bottom: $space-4; h3 { margin: 0 0 $space-3; color: $color-primary; font-size: 1rem; } }
    .grid2 { display: grid; grid-template-columns: 1fr 1fr; gap: $space-4; margin-bottom: 0; @media (max-width: 800px){ grid-template-columns: 1fr; } }
    .grid2 .card { margin-bottom: $space-4; }
    .cbox { height: 250px; } .cbox--tall { height: 300px; }
    .cal { display: flex; align-items: center; gap: $space-2; margin-bottom: $space-2; span { width: 110px; font-size: $font-size-sm; color: $color-text-muted; } b { width: 48px; text-align: right; } }
    .bar { flex: 1; height: 10px; background: $color-bg-muted; border-radius: $radius-pill; overflow: hidden; }
    .bar__fill { height: 100%; background: $color-primary; transition: width .6s; }
    .alerta { margin-top: $space-3; display: flex; flex-wrap: wrap; gap: $space-1; align-items: center; color: $color-text-muted; font-size: $font-size-sm; i { color: #d97706; } }
    .insights-body { display:grid; grid-template-columns:230px 1fr; gap:$space-4; align-items:start; }
    .side { background:#fff; border:1px solid $color-border; border-radius:$radius-lg; padding:$space-2; }
    .side-item { display:flex; align-items:center; gap:$space-2; padding:$space-2; border-radius:$radius-md; cursor:pointer; margin-bottom:2px; }
    .side-item:hover { background:$color-bg-muted; }
    .side-item.active { background:rgba(214,0,28,.08); }
    .side-item.active .side-item__name { color:$color-primary; font-weight:700; }
    .side-item__ic { width:22px; height:22px; border-radius:6px; flex-shrink:0; display:flex; align-items:center; justify-content:center; color:#fff; font-size:11px; }
    .side-item__name { flex:1; font-size:.82rem; color:$color-text; }
    .side-item__cnt { font-size:.72rem; color:$color-text-muted; font-weight:600; }
    .side-item--todos { margin-bottom:$space-3; padding-bottom:$space-3; border-bottom:1px dashed $color-border; border-radius:0; }
    .side-item--todos .side-item__ic { background:#374151; }
    .insights-main { min-width:0; }
    .page__sub { font-size:.8rem; color:$color-text-muted; margin-top:4px; }
    .area-note { background:$color-bg-muted; border:1px dashed $color-border; border-radius:$radius-md; padding:$space-3; font-size:.78rem; color:$color-text-muted; margin-top:$space-1; }
    .section-label { display:flex; align-items:center; gap:$space-2; font-size:.72rem; letter-spacing:.06em; text-transform:uppercase; color:$color-primary; font-weight:700; margin:$space-4 0 $space-2; }
    .section-label::after { content:''; flex:1; height:1px; background:$color-border; }
    .section-label:first-child { margin-top:0; }
    .kpi__l { text-transform:uppercase; letter-spacing:.04em; }
    .two-col { display:grid; grid-template-columns:1.3fr 1fr; gap:$space-4; margin-bottom:$space-4; @media (max-width:900px){ grid-template-columns:1fr; } }
    .two-col .card { margin-bottom:0; }
    .areas-grid { display:grid; grid-template-columns:repeat(3,1fr); gap:$space-3; margin-bottom:$space-4; @media (max-width:900px){ grid-template-columns:repeat(2,1fr); } @media (max-width:600px){ grid-template-columns:1fr; } }
    .area-card { background:#fff; border:1px solid $color-border; border-top:5px solid transparent; border-radius:$radius-md; padding:$space-3; cursor:pointer; transition:box-shadow .15s ease; }
    .area-card:hover { box-shadow:0 2px 10px rgba(0,0,0,.08); }
    .ac-top { display:flex; align-items:center; justify-content:space-between; margin-bottom:$space-2; }
    .ac-icon { width:28px; height:28px; border-radius:7px; display:flex; align-items:center; justify-content:center; color:#fff; font-size:12px; flex-shrink:0; }
    .ac-count { font-size:1.15rem; font-weight:700; color:$color-text; }
    .ac-name { font-size:.82rem; font-weight:600; color:$color-text; margin-bottom:$space-2; min-height:2.2em; }
    .ac-bar-bg { height:6px; border-radius:$radius-pill; background:$color-bg-muted; overflow:hidden; }
    .ac-bar-fill { height:100%; border-radius:$radius-pill; }
    .ac-share { font-size:.7rem; color:$color-text-muted; margin-top:4px; }
    @media (max-width:860px) { .insights-body { grid-template-columns:1fr; } }
  `],
})
export class EventosInsightsComponent implements OnInit, OnDestroy {
  private http = inject(HttpClient);
  private cfg = inject(ConfigService);
  private layout = inject(LayoutService);
  @ViewChild('chartMes') private rM?: ElementRef<HTMLCanvasElement>;
  @ViewChild('chartTipo') private rT?: ElementRef<HTMLCanvasElement>;
  @ViewChild('chartFunc') private rF?: ElementRef<HTMLCanvasElement>;
  private charts: Chart[] = [];

  loading = signal<boolean>(true);
  d = signal<any | null>(null);
  selArea = signal<{ id: number; nombre: string } | null>(null);
  areaData = signal<{ total: number; porTipo: any[]; topFunc: any[]; meses: [string, number][] } | null>(null);
  areaLoading = signal<boolean>(false);

  ngOnInit(): void {
    this.layout.setBreadcrumb([{ label: 'Inicio', url: '/' }, { label: 'Actividades', url: '/eventos' }, { label: 'Insights' }]);
    this.http.get<any>(this.cfg.url('/api/eventos/insights/')).subscribe({
      next: i => { this.d.set(i); this.loading.set(false); setTimeout(() => this.draw(i), 60); },
      error: () => this.loading.set(false),
    });
  }
  ngOnDestroy(): void { this.charts.forEach(c => c.destroy()); }

  private bar(c: HTMLCanvasElement | undefined, labels: string[], vals: number[]): void {
    if (!c || !labels.length) return;
    this.charts.push(new Chart(c, {
      type: 'bar',
      data: { labels, datasets: [{ data: vals, backgroundColor: labels.map((_, i) => PAL[i % PAL.length]), borderRadius: 4 }] },
      options: { indexAxis: 'y', responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false } }, scales: { x: { beginAtZero: true, ticks: { precision: 0 } } } },
    }));
  }

  private draw(i: any): void {
    this.charts.forEach(c => c.destroy()); this.charts = [];
    if (this.rM && i.timeline?.length) this.charts.push(new Chart(this.rM.nativeElement, {
      type: 'line',
      data: { labels: i.timeline.map((t: any) => t.mes), datasets: [{ data: i.timeline.map((t: any) => t.c), borderColor: '#D6001C', backgroundColor: 'rgba(214,0,28,0.12)', fill: true, tension: 0.3, pointRadius: 3 }] },
      options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false } }, scales: { y: { beginAtZero: true, ticks: { precision: 0 } } } },
    }));
    // por tipo con color del catálogo
    const pt = i.por_tipo || [];
    if (this.rT && pt.length) this.charts.push(new Chart(this.rT.nativeElement, {
      type: 'doughnut',
      data: { labels: pt.map((x: any) => x.tipo_evento__nombre || '—'), datasets: [{ data: pt.map((x: any) => x.c), backgroundColor: pt.map((x: any, idx: number) => x.tipo_evento__color || PAL[idx % PAL.length]), borderWidth: 2, borderColor: '#fff' }] },
      options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { position: 'bottom', labels: { boxWidth: 10, font: { size: 10 } } } } },
    }));
    this.bar(this.rF?.nativeElement, (i.top_funcionarios || []).map((x: any) => x.nombre || '—'), (i.top_funcionarios || []).map((x: any) => x.c));
  }

  selectArea(a: { id: number; nombre: string } | null): void {
    this.selArea.set(a);
    this.areaData.set(null);
    if (!a) {
      const i = this.d();
      if (i) setTimeout(() => this.draw(i), 60);
      return;
    }
    this.areaLoading.set(true);
    this.http.get<any>(this.cfg.url(`/api/eventos/lista/?subgrupo_id=${a.id}&activo=1&page_size=200`)).subscribe({
      next: (r: any) => {
        const results = r.results || [];
        const tiposMap = new Map<string, number>();
        const funcMap = new Map<string, number>();
        const mesesMap = new Map<string, number>();
        for (const e of results) {
          const t = e.tipo_nombre || '—';
          tiposMap.set(t, (tiposMap.get(t) || 0) + 1);
          const f = e.funcionario_nombre || 'Sin asignar';
          funcMap.set(f, (funcMap.get(f) || 0) + 1);
          const m = e.fecha_inicio ? String(e.fecha_inicio).slice(0, 7) : 'Sin fecha';
          mesesMap.set(m, (mesesMap.get(m) || 0) + 1);
        }
        const porTipo = [...tiposMap.entries()].map(([nombre, c]) => ({ nombre, c })).sort((x, y) => y.c - x.c);
        const topFunc = [...funcMap.entries()].map(([nombre, c]) => ({ nombre, c })).sort((x, y) => y.c - x.c).slice(0, 8);
        const meses = [...mesesMap.entries()].sort((x, y) => x[0].localeCompare(y[0]));
        this.areaData.set({ total: r.count, porTipo, topFunc, meses });
        this.areaLoading.set(false);
        setTimeout(() => this.drawArea(this.areaData()), 60);
      },
      error: () => this.areaLoading.set(false),
    });
  }

  private drawArea(a: any): void {
    this.charts.forEach(c => c.destroy()); this.charts = [];
    if (!a) return;
    if (this.rM && a.meses.length) this.charts.push(new Chart(this.rM.nativeElement, {
      type: 'line',
      data: { labels: a.meses.map((m: any) => m[0]), datasets: [{ data: a.meses.map((m: any) => m[1]), borderColor: '#D6001C', backgroundColor: 'rgba(214,0,28,0.12)', fill: true, tension: .3, pointRadius: 3 }] },
      options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false } }, scales: { y: { beginAtZero: true, ticks: { precision: 0 } } } },
    }));
    if (this.rT && a.porTipo.length) this.charts.push(new Chart(this.rT.nativeElement, {
      type: 'doughnut',
      data: { labels: a.porTipo.map((x: any) => x.nombre), datasets: [{ data: a.porTipo.map((x: any) => x.c), backgroundColor: a.porTipo.map((_: any, idx: number) => PAL[idx % PAL.length]), borderWidth: 2, borderColor: '#fff' }] },
      options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { position: 'bottom', labels: { boxWidth: 10, font: { size: 10 } } } } },
    }));
    this.bar(this.rF?.nativeElement, a.topFunc.map((x: any) => x.nombre), a.topFunc.map((x: any) => x.c));
  }

  areaColor(nombre: string): string {
    return AREA_COLORS[nombre] || '#6B7280';
  }

  areaIcon(nombre: string): string {
    return AREA_ICONS[nombre] || 'fa-circle';
  }
}
