import { CommonModule, CurrencyPipe, DecimalPipe } from '@angular/common';
import { Component, OnInit, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { LayoutService } from '../../core/layout/layout.service';
import { ToastService } from '../../shared/ui/toast.service';
import { PageHeaderComponent } from '../../shared/ui/page-header.component';
import { StatGridComponent, StatItem } from '../../shared/ui/stat-grid.component';
import { ActionNoticeComponent } from '../../shared/ui/action-notice.component';
import { EducacionApi } from './educacion.api';
import { ColegioDetalle, EntregaInput, Insumo } from './educacion.types';

/**
 * Vista 360° de una sede: su ficha oficial y todo lo que se le ha entregado,
 * más el formulario para registrar una entrega nueva.
 *
 * El formulario está en la misma pantalla que la lista de entregas y que las
 * sedes hermanas — es lo que evita el error más caro del cargue: anotar en la
 * sede equivocada de un colegio que tiene cuatro.
 */
@Component({
  standalone: true,
  selector: 'app-colegio-detalle',
  imports: [
    CommonModule, FormsModule, RouterLink,
    PageHeaderComponent, StatGridComponent, ActionNoticeComponent,
  ],
  providers: [CurrencyPipe, DecimalPipe],
  template: `
    @if (loading()) {
      <div class="ui-info-bar ui-info-bar--info" role="status">Cargando…</div>
    }
    @if (error()) {
      <div class="ui-info-bar ui-info-bar--danger" role="alert">{{ error() }}</div>
    }

    @if (d(); as det) {
      <div class="page">
        <!-- Sin back-link: el breadcrumb global (Inicio › Educación › {colegio})
             ya resuelve esa navegación — no se duplica. -->
        <app-page-header [title]="det.sede.colegio" [description]="descripcionSede(det)" />

        <app-stat-grid [stats]="kpiStats(det)" />

        <section class="ficha">
          <h2>Ficha oficial</h2>
          <dl>
            <dt>DANE de la sede</dt><dd>{{ det.sede.dane_sede }}</dd>
            <dt>DANE del colegio</dt><dd>{{ det.sede.dane_establecimiento }}</dd>
            <dt>Barrio</dt><dd>{{ det.sede.barrio || '—' }}</dd>
            <dt>UPZ</dt><dd>{{ det.sede.upz_codigo || '—' }}</dd>
            <dt>Estrato</dt><dd>{{ det.sede.estrato_ideca ?? '—' }}</dd>
            <dt>Teléfono</dt><dd>{{ det.sede.telefono || '—' }}</dd>
            <dt>Corte de la fuente</dt><dd>{{ det.sede.fecha_corte || '—' }}</dd>
          </dl>
        </section>

        @if (det.sedes_hermanas.length) {
          <section class="hermanas">
            <app-action-notice variant="info"
              [title]="'Este colegio tiene ' + (det.sedes_hermanas.length + 1) + ' sedes'"
              description="Verifica que estás registrando la entrega en la sede correcta." />
            <h2>Otras sedes de este colegio</h2>
            <ul>
              @for (h of det.sedes_hermanas; track h.id) {
                <li>
                  <a [routerLink]="['/educacion', h.id]">
                    Sede {{ h.orden_sede }} — {{ h.sede }}
                  </a>
                  @if (h.matricula_total != null) {
                    <small>· {{ h.matricula_total | number:'1.0-0' }} alumnos</small>
                  }
                  @if (h.direccion) { <small>· {{ h.direccion }}</small> }
                </li>
              }
            </ul>
          </section>
        }

        <section class="entregas">
          <h2>Insumos entregados</h2>
          <div class="ui-table-responsive">
          <table class="ui-table">
            <thead>
              <tr>
                <th scope="col">Insumo</th><th scope="col" class="num">Cantidad</th>
                <th scope="col" class="num">Valor</th>
                <th scope="col" class="num">Benef.</th><th scope="col">Fecha</th>
                <th scope="col">Acta</th>
                <th scope="col">Contrato</th>
                <!-- La columna de acciones necesita nombre igual: una celda de
                     cabecera vacía deja la columna sin anunciar. -->
                <th scope="col"><span class="ui-sr-only">Acciones</span></th>
              </tr>
            </thead>
            <tbody>
              @for (e of det.entregas; track e.id) {
                <tr>
                  <td>{{ e.insumo }}</td>
                  <td class="num">{{ e.cantidad | number:'1.0-2' }} {{ e.unidad || '' }}</td>
                  <td class="num">
                    @if (e.valor_total != null) {
                      {{ e.valor_total | currency:'COP':'symbol-narrow':'1.0-0' }}
                    } @else { <span class="muted">—</span> }
                  </td>
                  <td class="num">{{ e.beneficiarios ?? '—' }}</td>
                  <td>{{ e.fecha_entrega || '—' }}</td>
                  <td>{{ e.acta_numero || '—' }}</td>
                  <td>{{ e.contrato || '—' }}</td>
                  <td>
                    <!-- Texto visible, no un icono: Font Awesome no está
                         instalado en el proyecto (solo lucide-angular), así que
                         el <i class="fa fa-trash"> dejaba un botón sin ningún
                         contenido a la vista. El aria-label ya estaba bien. -->
                    <button type="button" class="ui-btn ui-btn--sm ui-btn--ghost"
                            [attr.aria-label]="'Borrar entrega de ' + e.insumo"
                            (click)="borrar(e.id)">
                      Borrar
                    </button>
                  </td>
                </tr>
              } @empty {
                <tr><td colspan="8" class="muted">Todavía no se ha registrado ninguna entrega.</td></tr>
              }
            </tbody>
          </table>
          </div>
        </section>

        <section class="registrar">
          <h2>Registrar una entrega</h2>
          <div class="form-grid">
            <label class="ui-field">
              <span>Insumo (catálogo)</span>
              <select class="ui-input" [(ngModel)]="form.implemento_codigo">
                <option [ngValue]="null">— sin catálogo —</option>
                @for (i of insumos(); track i.codigo) {
                  <option [ngValue]="i.codigo">{{ i.nombre }} ({{ i.categoria }})</option>
                }
              </select>
            </label>
            <label class="ui-field">
              <span>O descríbelo como dice el acta</span>
              <input class="ui-input" [(ngModel)]="form.descripcion"
                     placeholder="Ej. 40 pupitres bipersonales">
            </label>
            <label class="ui-field">
              <span>Vigencia</span>
              <input class="ui-input" type="number" [(ngModel)]="form.vigencia">
            </label>
            <label class="ui-field">
              <span>Cantidad</span>
              <input class="ui-input" type="number" step="0.01" [(ngModel)]="form.cantidad">
            </label>
            <label class="ui-field">
              <span>Unidad</span>
              <input class="ui-input" [(ngModel)]="form.unidad" placeholder="unidades, kits…">
            </label>
            <label class="ui-field">
              <span>Valor unitario</span>
              <input class="ui-input" type="number" [(ngModel)]="form.valor_unitario">
            </label>
            <label class="ui-field">
              <span>Valor total</span>
              <input class="ui-input" type="number" [(ngModel)]="form.valor_total"
                     placeholder="se calcula si lo dejas vacío">
            </label>
            <label class="ui-field">
              <span>Alumnos beneficiados</span>
              <input class="ui-input" type="number" [(ngModel)]="form.beneficiarios">
            </label>
            <label class="ui-field">
              <span>Fecha de entrega</span>
              <input class="ui-input" type="date" [(ngModel)]="form.fecha_entrega">
            </label>
            <label class="ui-field">
              <span>N.° de acta</span>
              <input class="ui-input" [(ngModel)]="form.acta_numero">
            </label>
            <label class="ui-field">
              <span>Contrato (id)</span>
              <input class="ui-input" type="number" [(ngModel)]="form.contrato_id"
                     placeholder="opcional">
            </label>
            <label class="ui-field ui-field--wide">
              <span>Observación</span>
              <input class="ui-input" [(ngModel)]="form.observacion">
            </label>
          </div>
          @if (formError()) {
            <div class="ui-info-bar ui-info-bar--danger" role="alert">{{ formError() }}</div>
          }
          <div class="page__actions">
            <button class="ui-btn ui-btn--primary" [disabled]="guardando()"
                    (click)="guardar()">
              <i class="fa fa-plus" aria-hidden="true"></i> Registrar entrega
            </button>
          </div>
        </section>
      </div>
    }
  `,
  styles: [`
    @use '../../../styles/tokens' as *;
    .form-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
      gap: 1rem;
      margin-bottom: 1rem;
    }
    .ui-field--wide { grid-column: 1 / -1; }
    .num { text-align: right; }
    .muted { color: $color-text-muted; }
    dl { display: grid; grid-template-columns: max-content 1fr; gap: .35rem 1rem; }
    dt { font-weight: 600; }
    section { margin-bottom: 2rem; }
    .hermanas ul { margin: .5rem 0 0 1rem; }
  `],
})
export class ColegioDetalleComponent implements OnInit {
  private api = inject(EducacionApi);
  private route = inject(ActivatedRoute);
  private layout = inject(LayoutService);
  private toast = inject(ToastService);
  private currencyPipe = inject(CurrencyPipe);
  private decimalPipe = inject(DecimalPipe);

  d = signal<ColegioDetalle | null>(null);
  insumos = signal<Insumo[]>([]);
  loading = signal<boolean>(true);
  error = signal<string>('');
  formError = signal<string>('');
  guardando = signal<boolean>(false);

  private sedeId = 0;
  form: EntregaInput = this.formVacio();

  ngOnInit(): void {
    this.sedeId = Number(this.route.snapshot.paramMap.get('id'));
    this.cargar();
    this.api.insumos().subscribe({
      next: (r) => this.insumos.set(r.items),
      // El catálogo es una comodidad: si no carga, la descripción libre sigue
      // permitiendo registrar. No se bloquea el formulario por esto.
      error: () => this.insumos.set([]),
    });
  }

  descripcionSede(det: ColegioDetalle): string {
    const s = det.sede;
    const ubicacion = s.es_principal ? 'Sede principal' : `Sede ${s.orden_sede} — ${s.sede}`;
    return `${ubicacion} · ${s.clase_nombre}` + (s.direccion ? ` · ${s.direccion}` : '');
  }

  kpiStats(det: ColegioDetalle): StatItem[] {
    return [
      {
        value: det.sede.matricula_total != null
          ? (this.decimalPipe.transform(det.sede.matricula_total, '1.0-0') ?? '0') : '—',
        label: 'Alumnos',
        sublabel: det.sede.matricula_corte ? `corte ${det.sede.matricula_corte}` : undefined,
      },
      { value: det.totales.entregas, label: 'Entregas registradas' },
      {
        value: this.currencyPipe.transform(det.totales.valor, 'COP', 'symbol-narrow', '1.0-0') ?? '—',
        label: 'Valor entregado',
        variant: 'ok',
      },
      {
        value: this.decimalPipe.transform(det.totales.beneficiarios, '1.0-0') ?? '0',
        label: 'Beneficiarios',
        sublabel: 'los reportados por entrega, no la matrícula',
      },
    ];
  }

  cargar(): void {
    this.loading.set(true);
    this.api.detalle(this.sedeId).subscribe({
      next: (d) => {
        this.d.set(d);
        this.layout.setBreadcrumb([
          { label: 'Inicio', url: '/' },
          { label: 'Educación', url: '/educacion' },
          { label: d.sede.colegio },
        ]);
        this.loading.set(false);
      },
      error: () => {
        this.error.set('No se pudo cargar la sede.');
        this.loading.set(false);
      },
    });
  }

  guardar(): void {
    this.formError.set('');
    if (!this.form.implemento_codigo && !(this.form.descripcion || '').trim()) {
      this.formError.set('Indica qué se entregó: escoge un insumo del catálogo o descríbelo.');
      return;
    }
    if (!this.form.vigencia) {
      this.formError.set('Falta la vigencia.');
      return;
    }
    this.guardando.set(true);
    this.api.crearEntrega({ ...this.form, colegio_sede_id: this.sedeId }).subscribe({
      next: () => {
        this.guardando.set(false);
        this.form = this.formVacio();
        this.toast.success('Entrega registrada.');
        this.cargar();
      },
      error: (e) => {
        this.guardando.set(false);
        this.formError.set(e?.error?.error || 'No se pudo registrar la entrega.');
      },
    });
  }

  borrar(id: number): void {
    this.api.eliminarEntrega(id).subscribe({
      next: () => { this.toast.success('Entrega borrada.'); this.cargar(); },
      error: (e) => this.toast.error(e?.error?.error || 'No se pudo borrar.'),
    });
  }

  private formVacio(): EntregaInput {
    return {
      colegio_sede_id: 0,
      vigencia: new Date().getFullYear(),
      implemento_codigo: null,
      descripcion: '',
      cantidad: 0,
      unidad: '',
      valor_unitario: null,
      valor_total: null,
      beneficiarios: null,
      fecha_entrega: null,
      acta_numero: '',
      contrato_id: null,
      observacion: '',
    };
  }
}
