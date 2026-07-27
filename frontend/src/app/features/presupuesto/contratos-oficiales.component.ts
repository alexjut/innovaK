import { CommonModule } from '@angular/common';
import { Component, OnInit, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { HttpClient } from '@angular/common/http';
import { RouterLink } from '@angular/router';
import { firstValueFrom } from 'rxjs';
import { ConfigService } from '../../core/config/config.service';
import { LayoutService } from '../../core/layout/layout.service';

interface Contrato {
  referencia: string; estado: string; tipo: string; modalidad: string; objeto: string;
  proveedor: string; valor: number; pagado: number; fecha_firma: string; anio: number | null;
  url_proceso: string; en_innovak: boolean;
}

/**
 * Lista general de contratos ADJUDICADOS de Kennedy (SECOP II), paginada en
 * servidor (miles de filas) con buscador. Enlace directo a SECOP. JWT-first.
 */
@Component({
  standalone: true,
  selector: 'app-contratos-oficiales',
  imports: [CommonModule, FormsModule, RouterLink],
  template: `
    <div class="page">
      <header class="page__header">
        <h1><i class="fa fa-file-signature"></i> Contratos <span class="of">· oficial (SECOP)</span></h1>
        <p class="page__subtitle">
          Contratos adjudicados de la Alcaldía Local de Kennedy en SECOP II. Marca cuáles
          ya están en innovaK. Clic en el número abre el proceso en SECOP.
        </p>
      </header>

      <div class="barra">
        <input class="buscador" type="search" [(ngModel)]="q"
               (keyup.enter)="buscar()" placeholder="Buscar referencia, objeto o proveedor… (Enter)" />
        <button class="btn" (click)="buscar()">Buscar</button>
        <span class="conteo">{{ count() | number }} contratos</span>
      </div>

      @if (cargando()) {
        <p class="muted">Cargando…</p>
      } @else if (!items().length) {
        <div class="ui-empty-state"><i class="fa fa-info-circle"></i><p>Sin resultados.</p></div>
      } @else {
        <div class="lista">
          @for (ct of items(); track ct.referencia) {
            <article class="cc">
              <div class="cc__head">
                @if (ct.url_proceso) {
                  <a class="ref" [href]="ct.url_proceso" target="_blank" rel="noopener">{{ ct.referencia }} ↗</a>
                } @else { <span class="ref">{{ ct.referencia }}</span> }
                <span class="estado" [class]="'e-' + slug(ct.estado)">{{ ct.estado }}</span>
                @if (ct.en_innovak) { <span class="badge badge--ok">en innovaK</span> }
              </div>
              <p class="cc__obj">{{ ct.objeto }}</p>
              <div class="cc__stats">
                <div class="st"><span class="st__n">\${{ ct.valor | number:'1.0-0' }}</span><span class="st__l">Valor</span></div>
                <div class="st"><span class="st__n">\${{ ct.pagado | number:'1.0-0' }}</span><span class="st__l">Pagado</span></div>
                <div class="st"><span class="st__n">{{ ct.anio || '—' }}</span><span class="st__l">Año</span></div>
                <div class="st st--prov"><span class="st__n">{{ ct.proveedor || '—' }}</span><span class="st__l">{{ ct.modalidad }}</span></div>
              </div>
            </article>
          }
        </div>

        <div class="pager">
          <button (click)="ir(page() - 1)" [disabled]="page() === 1">← Anterior</button>
          <span>Página {{ page() }} de {{ pages() }}</span>
          <button (click)="ir(page() + 1)" [disabled]="page() >= pages()">Siguiente →</button>
        </div>
      }

      <a routerLink="/presupuesto" class="ui-back-link">← Volver a Presupuesto</a>
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
    .barra { display: flex; align-items: center; gap: $space-2; margin-bottom: $space-3; flex-wrap: wrap; }
    .buscador { flex: 1; min-width: 220px; max-width: 460px; padding: $space-2 $space-3; border: 1px solid rgba(0,0,0,.15); border-radius: 8px; }
    .btn { padding: $space-2 $space-3; border: 1px solid $color-primary; background: $color-primary; color: #fff; border-radius: 8px; cursor: pointer; }
    .conteo { color: $color-text-muted; font-size: $font-size-sm; }
    .lista { display: flex; flex-direction: column; gap: $space-3; }
    .cc { border: 1px solid rgba(0,0,0,.1); border-radius: 12px; padding: $space-3 $space-4; background: #fff; }
    .cc__head { display: flex; align-items: center; gap: $space-2; flex-wrap: wrap; }
    .ref { font-weight: 700; color: $color-primary; text-decoration: none; }
    .estado { border-radius: 999px; padding: 1px 9px; font-size: .72rem; background: rgba(0,0,0,.08); white-space: nowrap; }
    .e-en-ejecucion { background: #dbeafe; color: #1e40af; }
    .e-terminado, .e-cerrado { background: #dcfce7; color: #166534; }
    .e-modificado { background: #fef3c7; color: #92400e; }
    .cc__obj { margin: $space-1 0 $space-3; color: $color-text; font-size: $font-size-sm; }
    .cc__stats { display: grid; grid-template-columns: repeat(auto-fit, minmax(120px, 1fr)); gap: $space-2; }
    .st { background: rgba(0,0,0,.03); border-radius: 8px; padding: $space-2; text-align: center; }
    .st--prov { text-align: left; }
    .st__n { display: block; font-weight: 700; font-variant-numeric: tabular-nums; color: $color-text; font-size: $font-size-sm; }
    .st--prov .st__n { font-weight: 600; }
    .st__l { font-size: .72rem; color: $color-text-muted; }
    .badge { border-radius: 999px; padding: 1px 9px; font-size: .72rem; }
    .badge--ok { background: #dcfce7; color: #166534; }
    .pager { display: flex; align-items: center; gap: $space-3; margin-top: $space-4; justify-content: center; flex-wrap: wrap; }
    .pager button { padding: $space-1 $space-3; border: 1px solid rgba(0,0,0,.15); border-radius: 8px; background: #fff; cursor: pointer; }
    .pager button:disabled { opacity: .4; cursor: default; }
    .ui-back-link { display: inline-block; margin-top: $space-4; color: $color-primary; }
  `],
})
export class ContratosOficialesComponent implements OnInit {
  private http = inject(HttpClient);
  private cfg = inject(ConfigService);
  private layout = inject(LayoutService);

  items = signal<Contrato[]>([]);
  count = signal<number>(0);
  page = signal<number>(1);
  pages = signal<number>(1);
  cargando = signal<boolean>(true);
  q = '';

  buscar(): void { this.ir(1); }

  async ir(p: number): Promise<void> {
    if (p < 1 || (this.pages() && p > this.pages())) return;
    this.cargando.set(true);
    try {
      const url = `/dashboard/api/v2/presupuesto/contratos-oficiales/?page=${p}&q=${encodeURIComponent(this.q)}`;
      const r: any = await firstValueFrom(this.http.get(this.cfg.url(url)));
      this.items.set(r?.items ?? []);
      this.count.set(r?.count ?? 0);
      this.page.set(r?.page ?? 1);
      this.pages.set(r?.pages ?? 1);
    } catch {
      this.items.set([]);
    } finally {
      this.cargando.set(false);
    }
  }

  slug(s: string): string {
    return (s || '').toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g, '').replace(/\s+/g, '-');
  }

  ngOnInit(): void {
    this.layout.setBreadcrumb([
      { label: 'Inicio', url: '/' },
      { label: 'Presupuesto', url: '/presupuesto' },
      { label: 'Contratos' },
    ]);
    this.ir(1);
  }
}
