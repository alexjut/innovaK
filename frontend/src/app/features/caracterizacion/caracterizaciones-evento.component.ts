import { CommonModule } from '@angular/common';
import { HttpClient } from '@angular/common/http';
import {
  ChangeDetectionStrategy, Component, OnInit, inject, signal,
} from '@angular/core';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { ConfigService } from '../../core/config/config.service';
import { LayoutService } from '../../core/layout/layout.service';

interface CaracterizacionItem {
  id: number;
  persona_id: number;
  doc_numero: string;
  doc_tipo: string;
  nombre_completo: string;
  created_at: string | null;
}

interface CaracterizacionesResponse {
  evento: {
    id: number;
    nombre: string | null;
    tipo_codigo: string | null;
    tipo_nombre: string | null;
    subgrupo: string | null;
  };
  sector: string | null;
  sector_label: string | null;
  total: number;
  items: CaracterizacionItem[];
}

@Component({
  standalone: true,
  selector: 'app-caracterizaciones-evento',
  imports: [CommonModule, RouterLink],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <div class="page">
      @if (loading()) {
        <div class="page__loading">Cargando…</div>
      } @else if (errorMsg()) {
        <div class="page__error">⚠ {{ errorMsg() }}</div>
      } @else if (data()) {
        @let d = data()!;
        <header class="page__header">
          <h1>
            <i class="fa fa-clipboard-list"></i>
            Caracterizaciones · {{ d.evento.nombre || ('Evento #' + d.evento.id) }}
          </h1>
          <p class="page__subtitle">
            @if (d.sector_label) {
              Sector: <strong>{{ d.sector_label }}</strong> ·
            }
            <strong>{{ d.total }}</strong> persona{{ d.total === 1 ? '' : 's' }} caracterizada{{ d.total === 1 ? '' : 's' }}
            @if (d.evento.subgrupo) { · {{ d.evento.subgrupo }} }
          </p>
        </header>

        @if (!d.sector) {
          <div class="ui-info-bar ui-info-bar--warning">
            Este evento no tiene un sector de caracterización definido.
            Edítalo y asigna un sector para empezar a capturar.
          </div>
        } @else if (d.items.length) {
          <div class="ui-table-responsive">
            <table class="ui-table">
              <thead>
                <tr>
                  <th>#</th>
                  <th>Tipo doc</th>
                  <th>Documento</th>
                  <th>Nombre completo</th>
                  <th>Fecha captura</th>
                </tr>
              </thead>
              <tbody>
                @for (it of d.items; track it.id) {
                  <tr>
                    <td>{{ it.id }}</td>
                    <td>{{ it.doc_tipo }}</td>
                    <td>{{ it.doc_numero }}</td>
                    <td>{{ it.nombre_completo }}</td>
                    <td>{{ it.created_at ? fmtDate(it.created_at) : '—' }}</td>
                  </tr>
                }
              </tbody>
            </table>
          </div>
        } @else {
          <div class="ui-empty-state">
            <i class="fa fa-clipboard"></i>
            <p>Este evento aún no tiene caracterizaciones capturadas.
              Las personas se caracterizan vía el QR público del evento.</p>
          </div>
        }
      }
    </div>
  `,
  styles: [`
    @use '../../../styles/tokens' as *;
    :host { display: block; }
    .page { max-width: 1200px; margin: 0 auto; }
    .page__header h1 { margin: 0; color: $color-primary; i { margin-right: $space-2; } }
    .page__subtitle { color: $color-text-muted; margin: $space-1 0 $space-3; }
    .page__loading, .page__error { padding: $space-4; text-align: center; color: $color-text-muted; }
    .page__error { color: $color-danger; }
  `],
})
export class CaracterizacionesEventoComponent implements OnInit {
  private http = inject(HttpClient);
  private cfg = inject(ConfigService);
  private route = inject(ActivatedRoute);
  private layout = inject(LayoutService);

  data = signal<CaracterizacionesResponse | null>(null);
  loading = signal<boolean>(true);
  errorMsg = signal<string>('');

  ngOnInit(): void {
    this.route.paramMap.subscribe((p) => {
      const id = Number(p.get('id') || 0);
      this.cargar(id);
    });
  }

  private cargar(eventoId: number): void {
    this.loading.set(true);
    this.errorMsg.set('');
    this.http.get<CaracterizacionesResponse>(
      this.cfg.url(`/api/eventos/${eventoId}/caracterizaciones/`),
    ).subscribe({
      next: (r) => {
        this.data.set(r);
        this.loading.set(false);
        this.layout.setBreadcrumb([
          { label: 'Inicio', url: '/' },
          { label: 'Actividades', url: '/actividades' },
          { label: r.evento.tipo_nombre || 'Caracterización',
            url: `/actividades/tipo/${r.evento.tipo_codigo || ''}` },
          { label: `Caracterizaciones #${r.evento.id}` },
        ]);
      },
      error: (err) => {
        if (err.status === 404) {
          this.errorMsg.set('Este evento no es de tipo Caracterización.');
        } else {
          this.errorMsg.set('No se pudieron cargar las caracterizaciones.');
        }
        this.loading.set(false);
      },
    });
  }

  fmtDate(iso: string): string {
    if (!iso) return '—';
    return iso.replace('T', ' ').slice(0, 16);
  }
}
