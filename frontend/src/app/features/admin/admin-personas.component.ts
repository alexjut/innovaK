import { CommonModule } from '@angular/common';
import {
  ChangeDetectionStrategy, Component, OnInit, inject, signal,
} from '@angular/core';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { AdminApi, PersonasResponse } from './admin.api';
import { LayoutService } from '../../core/layout/layout.service';

@Component({
  standalone: true,
  selector: 'app-admin-personas',
  imports: [CommonModule, FormsModule, RouterLink],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <div class="page">
      <header class="page__header">
        <h1><i class="fa fa-user-plus"></i> Personas</h1>
        <p class="page__subtitle">
          Buscador de personas (participantes, beneficiarios, contratistas, funcionarios).
        </p>
      </header>

      <div class="ui-filter-bar">
        <input type="search" [(ngModel)]="q" (input)="buscar()"
               placeholder="Buscar por nombre, apellido o documento…"
               class="filter-field">
      </div>

      @if (loading()) { <div class="page__loading">Cargando…</div> }
      @else if (data()) {
        @let d = data()!;
        <p class="muted">{{ d.count }} resultado{{ d.count === 1 ? '' : 's' }}</p>
        @if (d.results.length) {
          <div class="ui-table-responsive">
            <table class="ui-table">
              <thead>
                <tr><th>#</th><th>Documento</th><th>Nombre</th></tr>
              </thead>
              <tbody>
                @for (p of d.results; track p.id) {
                  <tr>
                    <td>{{ p.id }}</td>
                    <td>{{ p.documento || '—' }}</td>
                    <td>{{ p.nombre }}</td>
                  </tr>
                }
              </tbody>
            </table>
          </div>
        } @else {
          <div class="ui-empty-state">Sin resultados.</div>
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
    .page__loading { padding: $space-4; text-align: center; }
    .filter-field {
      width: 100%; max-width: 460px;
      padding: $space-2; border: 1px solid $color-border;
      border-radius: $radius-md;
    }
    .muted { color: $color-text-muted; margin: $space-2 0; }
  `],
})
export class AdminPersonasComponent implements OnInit {
  private api = inject(AdminApi);
  private layout = inject(LayoutService);

  data = signal<PersonasResponse | null>(null);
  loading = signal<boolean>(false);
  q = '';
  private debounce: any;

  ngOnInit(): void {
    this.layout.setBreadcrumb([
      { label: 'Inicio', url: '/' },
      { label: 'Administración', url: '/admin' },
      { label: 'Personas' },
    ]);
    this.cargar();
  }

  cargar(): void {
    this.loading.set(true);
    this.api.buscarPersonas(this.q, 1).subscribe({
      next: r => { this.data.set(r); this.loading.set(false); },
      error: () => this.loading.set(false),
    });
  }

  buscar(): void {
    clearTimeout(this.debounce);
    this.debounce = setTimeout(() => this.cargar(), 300);
  }
}
