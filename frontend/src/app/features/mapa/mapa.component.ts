import { CommonModule } from '@angular/common';
import { Component, OnInit, inject } from '@angular/core';
import { ConfigService } from '../../core/config/config.service';
import { LayoutService } from '../../core/layout/layout.service';

/**
 * Mapa Kennedy. El backend ya expone `GET /geo/api/lugares/`,
 * `/geo/api/conteos/`, `/geo/api/eventos/` con GeoJSON listo para
 * Leaflet.
 *
 * Hoy este placeholder lo embebe en iframe apuntando al Django legacy
 * (donde Leaflet ya está configurado con todas las capas: UPZ,
 * barrios, parques, escuelas). Cuando se integre Leaflet directamente
 * en Angular como componente, se reemplaza este iframe.
 *
 * Ventaja del iframe: cero deuda. El mapa Django funciona perfecto y
 * el usuario lo ve dentro del shell Angular institucional.
 */
@Component({
  standalone: true,
  selector: 'app-mapa-kennedy',
  imports: [CommonModule],
  template: `
    <div class="page">
      <header class="page__header">
        <h1>Mapa de Kennedy</h1>
        <p class="page__subtitle">
          Eventos, parques, escuelas y barrios georreferenciados.
          <a [href]="mapaUrl" target="_blank" rel="noopener">Abrir en ventana completa ↗</a>
        </p>
      </header>

      <div class="mapa-frame">
        <iframe [src]="mapaUrl"
                title="Mapa de Kennedy"
                loading="lazy"
                referrerpolicy="same-origin"></iframe>
      </div>
    </div>
  `,
  styles: [`
    @use '../../../styles/tokens' as *;
    :host { display: block; }
    .page { max-width: 100%; margin: 0; }
    .page__header h1 { margin: 0; color: $color-primary; }
    .page__subtitle { color: $color-text-muted; margin: $space-1 0 $space-3; }

    .mapa-frame {
      width: 100%;
      height: calc(100vh - 220px);
      min-height: 500px;
      border: 1px solid $color-border;
      border-radius: $radius-lg;
      overflow: hidden;
      box-shadow: $shadow-sm;
    }
    .mapa-frame iframe {
      width: 100%;
      height: 100%;
      border: 0;
      display: block;
    }
  `],
})
export class MapaKennedyComponent implements OnInit {
  private cfg = inject(ConfigService);
  private layout = inject(LayoutService);

  get mapaUrl(): string {
    return this.cfg.url('/geo/mapa-kennedy/');
  }

  ngOnInit(): void {
    this.layout.setBreadcrumb([
      { label: 'Inicio', url: '/' },
      { label: 'Mapa de Kennedy' },
    ]);
  }
}
