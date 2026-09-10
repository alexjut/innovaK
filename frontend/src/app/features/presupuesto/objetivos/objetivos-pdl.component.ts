import { CommonModule } from '@angular/common';
import { Component, OnInit, computed, inject, signal } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { firstValueFrom } from 'rxjs';
import { ConfigService } from '../../../core/config/config.service';
import { LayoutService } from '../../../core/layout/layout.service';
import { ObjetivosResumenComponent } from './objetivos-resumen.component';
import { PerspectivasExploradorComponent } from './perspectivas-explorador.component';
import { ObjetivoEstrategico, aplanarObjetivos } from './objetivos.types';

/**
 * Los objetivos estratégicos del PDL — la pantalla a la que apunta la card
 * «Objetivos» del hub de Presupuesto.
 *
 * POR QUÉ EXISTE. Esa card no tenía ruta propia, así que caía al catch-all
 * `:entidad` y terminaba sirviendo la tabla `objetivo`, que es el catálogo
 * del **Banco de Iniciativas**: cuatro filas llamadas «prueba» y dos de
 * seguridad, cero objetivos del Plan. Los 5 objetivos reales sí estaban en
 * el sistema —`presu_objetivo_estrategico`, DDL 024— pero solo se pintaban
 * dentro del cockpit, donde nadie los busca por ese nombre.
 *
 * NO RECALCULA NADA. Consume el mismo `/objetivos-estrategicos/` que el
 * cockpit y compone los MISMOS dos componentes, para que el resumen de un
 * objetivo no pueda decir una cifra acá y otra allá. La única diferencia es
 * el encuadre: allá es una sección de un tablero, acá es la pantalla.
 */
@Component({
  standalone: true,
  selector: 'app-objetivos-pdl',
  imports: [CommonModule, ObjetivosResumenComponent, PerspectivasExploradorComponent],
  template: `
    <div class="page">
      <header class="page__header">
        <h1><i class="fa fa-bullseye" aria-hidden="true"></i> Objetivos estratégicos</h1>
        <p class="page__subtitle">
          Los ejes del Plan de Desarrollo Local de Kennedy, con sus programas y
          proyectos. Fuente: Matriz de Seguimiento PDL de la Alcaldía Local.
        </p>
      </header>

      @if (cargando()) {
        <p class="ui-info-bar ui-info-bar--info" role="status">Cargando el Plan…</p>
      } @else if (error()) {
        <p class="ui-info-bar ui-info-bar--danger" role="alert">{{ error() }}</p>
      } @else if (!objetivos().length) {
        <div class="ui-empty-state">
          <i class="fa fa-circle-info" aria-hidden="true"></i>
          <p>
            Todavía no hay objetivos estratégicos cargados. Entran con la Matriz
            PDL; mientras no se haya subido un corte, esta pantalla queda vacía
            a propósito en vez de mostrar otro catálogo.
          </p>
        </div>
      } @else {
        <app-objetivos-resumen [objetivos]="objetivos()" />
        <app-perspectivas-explorador [objetivos]="objetivos()" />
      }
    </div>
  `,
  styles: [`
    .page { padding: 1rem 1.25rem 2.5rem; }
    .page__header { margin-bottom: 1.25rem; }
    .page__header h1 { margin: 0 0 .25rem; font-size: 1.35rem; }
    .page__subtitle { margin: 0; color: var(--muted, #6b7280); font-size: .875rem; max-width: 62ch; }
  `],
})
export class ObjetivosPdlComponent implements OnInit {
  private http = inject(HttpClient);
  private cfg = inject(ConfigService);
  private layout = inject(LayoutService);

  objetivos = signal<ObjetivoEstrategico[]>([]);
  cargando = signal(true);
  error = signal<string | null>(null);

  async ngOnInit(): Promise<void> {
    this.layout.setBreadcrumb([
      { label: 'Inicio', url: '/' },
      { label: 'Plan de Desarrollo', url: '/presupuesto' },
      { label: 'Objetivos estratégicos' },
    ]);
    try {
      const data = await firstValueFrom(
        this.http.get(this.cfg.url('/presupuesto/api/objetivos-estrategicos/')));
      this.objetivos.set(aplanarObjetivos(data));
    } catch (e: any) {
      // Un vacío y un fallo se ven igual si no se distinguen, y llevan a
      // conclusiones opuestas: «no hay Plan cargado» vs «no pude leerlo».
      this.error.set(e?.status === 401 || e?.status === 403
        ? 'No tenés permiso para ver el Plan, o se venció la sesión.'
        : 'No se pudo leer el Plan. Volvé a intentar en un momento.');
    } finally {
      this.cargando.set(false);
    }
  }
}
