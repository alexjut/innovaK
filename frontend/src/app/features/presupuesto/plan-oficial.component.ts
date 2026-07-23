import { CommonModule } from '@angular/common';
import { Component, OnInit, inject, signal } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { RouterLink } from '@angular/router';
import { firstValueFrom } from 'rxjs';
import { ConfigService } from '../../core/config/config.service';
import { LayoutService } from '../../core/layout/layout.service';

interface MetaOf { codigo_meta: string; nombre: string; programado_cuatrienio: number; tipo_anualizacion: string | null; }
interface ProyOf { codigo: string; nombre: string; interno: boolean; metas: MetaOf[]; }
interface ObjOf { codigo: string; nombre: string; proyectos: ProyOf[]; }
interface ProgOf { codigo: string; nombre: string; objetivos: ObjOf[]; }

/**
 * Estructura OFICIAL del Plan de Desarrollo (SEGPLAN) para Kennedy:
 * Programa → Objetivo → Proyecto → Meta, tal como lo reporta el Distrito.
 * Reemplaza en la UI la vista de los datos internos viejos. JWT-first.
 */
@Component({
  standalone: true,
  selector: 'app-plan-oficial',
  imports: [CommonModule, RouterLink],
  template: `
    <div class="page">
      <header class="page__header">
        <h1><i class="fa fa-sitemap" aria-hidden="true"></i> Plan oficial (SEGPLAN)</h1>
        <p class="page__subtitle">
          Estructura del Plan de Desarrollo Local de Kennedy tal como la reporta el Distrito:
          Programa → Objetivo → Proyecto → Meta. Los proyectos ya cargados en innovaK van marcados.
        </p>
      </header>

      @if (cargando()) {
        <p class="muted">Cargando…</p>
      } @else if (!programas().length) {
        <div class="ui-empty-state">
          <i class="fa fa-info-circle"></i>
          <p>Sin estructura oficial aún. Aplica el ALTER 009 y re-corre la ingesta SDP.</p>
        </div>
      } @else {
        @for (prog of programas(); track prog.codigo) {
          <section class="prog">
            <h2 class="prog__t"><span class="chip chip--prog">{{ prog.codigo }}</span> {{ prog.nombre }}</h2>
            @for (obj of prog.objetivos; track obj.codigo) {
              <div class="obj">
                <h3 class="obj__t"><span class="chip chip--obj">{{ obj.codigo }}</span> {{ obj.nombre }}</h3>
                @for (py of obj.proyectos; track py.codigo) {
                  <div class="proy">
                    <div class="proy__h">
                      <span class="chip chip--proy">{{ py.codigo }}</span>
                      <strong>{{ py.nombre }}</strong>
                      @if (py.interno) { <span class="badge badge--ok">en innovaK</span> }
                      @else { <span class="badge badge--no">no cargado</span> }
                    </div>
                    <ul class="metas">
                      @for (m of py.metas; track m.codigo_meta) {
                        <li>
                          <span class="chip chip--meta">{{ m.codigo_meta }}</span>
                          {{ m.nombre }}
                          <small>· {{ m.programado_cuatrienio | number:'1.0-0' }} ({{ m.tipo_anualizacion || '—' }})</small>
                        </li>
                      }
                    </ul>
                  </div>
                }
              </div>
            }
          </section>
        }
      }

      <a routerLink="/presupuesto" class="ui-back-link">← Volver a Presupuesto</a>
    </div>
  `,
  styles: [`
    @use '../../../styles/tokens' as *;
    :host { display: block; }
    .page { max-width: 1100px; margin: 0 auto; }
    .page__header h1 { margin: 0; color: $color-primary; i { margin-right: $space-2; } }
    .page__subtitle { color: $color-text-muted; margin: $space-1 0 $space-4; }
    .muted { color: $color-text-muted; }
    .prog { margin-top: $space-4; padding-top: $space-3; border-top: 2px solid rgba(0,0,0,.08); }
    .prog__t { font-size: $font-size-lg; color: $color-primary; margin: 0 0 $space-2; }
    .obj { margin: $space-2 0 $space-3 $space-3; }
    .obj__t { font-size: $font-size-base; color: $color-text; margin: 0 0 $space-2; }
    .proy { margin: $space-1 0 $space-2 $space-4; padding: $space-2 $space-3; background: rgba(0,0,0,.03); border-radius: 8px; }
    .proy__h { display: flex; align-items: center; gap: $space-2; flex-wrap: wrap; }
    .metas { margin: $space-2 0 0; padding-left: $space-4; }
    .metas li { margin: 2px 0; color: $color-text; small { color: $color-text-muted; } }
    .chip { border-radius: 999px; padding: 1px 8px; font-size: .75rem; font-variant-numeric: tabular-nums; color: #fff; }
    .chip--prog { background: #7c3aed; } .chip--obj { background: #0ea5e9; }
    .chip--proy { background: $color-primary; } .chip--meta { background: #64748b; }
    .badge { border-radius: 999px; padding: 1px 8px; font-size: .7rem; }
    .badge--ok { background: #dcfce7; color: #166534; } .badge--no { background: #fee2e2; color: #991b1b; }
    .ui-back-link { display: inline-block; margin-top: $space-4; color: $color-primary; }
  `],
})
export class PlanOficialComponent implements OnInit {
  private http = inject(HttpClient);
  private cfg = inject(ConfigService);
  private layout = inject(LayoutService);

  programas = signal<ProgOf[]>([]);
  cargando = signal<boolean>(true);

  async ngOnInit(): Promise<void> {
    this.layout.setBreadcrumb([
      { label: 'Inicio', url: '/' },
      { label: 'Presupuesto', url: '/presupuesto' },
      { label: 'Plan oficial' },
    ]);
    try {
      const r: any = await firstValueFrom(
        this.http.get(this.cfg.url('/dashboard/api/v2/presupuesto/plan-oficial/')),
      );
      this.programas.set(r?.programas ?? []);
    } catch {
      this.programas.set([]);
    } finally {
      this.cargando.set(false);
    }
  }
}
