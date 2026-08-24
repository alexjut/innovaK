import { CommonModule } from '@angular/common';
import { HttpClient } from '@angular/common/http';
import {
  ChangeDetectionStrategy, Component, OnInit, computed, inject, signal,
} from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { ConfigService } from '../../core/config/config.service';
import { LayoutService } from '../../core/layout/layout.service';
import { formatNumero } from '../../shared/format/format.util';

interface ColDef { key: string; label: string; pipe?: 'money' | 'badge' | 'num'; type?: 'bar'; }

type FieldType = 'text' | 'number' | 'date' | 'textarea' | 'select';
interface FieldDef {
  key: string;
  label: string;
  type: FieldType;
  required?: boolean;
  /** Opciones estáticas (p.ej. tipo INV/FUN/MIX). */
  options?: { value: any; label: string }[];
  /** Endpoint de catálogo (string fijo o función del form para cascadas). */
  optionsEndpoint?: string | ((form: Record<string, any>) => string | null);
  optionValue?: string;                 // key del value (default 'id')
  optionLabel?: (o: any) => string;     // texto visible (default o.nombre)
  dependsOn?: string;                   // recarga opciones cuando cambia este campo
  omit?: boolean;                       // se muestra pero NO se envía (solo filtra)
  default?: any;
  placeholder?: string;
  /** Para vigencias: preselecciona la opción del año actual tras cargar. */
  preselectCurrentYear?: boolean;
}

interface EntidadConfig {
  titulo: string;
  endpoint: string;          // GET (lista)
  createEndpoint?: string;   // POST (crear) si difiere del de lista
  itemKey: string;
  cols: ColDef[];
  formFields: FieldDef[];
  detalleRuta?: (id: any) => string;
  deleteEndpoint?: (id: any) => string;   // DELETE (eliminar) si la entidad lo soporta
  paginated?: boolean;
  /** Deja fuera lo cerrado sin esconderlo: la pantalla filtra desde este año y
   *  ofrece ver el histórico. Se usa donde conviven vigencias viejas con la
   *  operación de hoy — contratos tiene una de 2015 y otra de 2024. */
  vigenciaDesde?: number;
}

const PROY_LABEL = (o: any) => `${o.codigo}${o.nombre && o.nombre !== o.codigo ? ' — ' + o.nombre : ''}`;
const TIPO_CONCEPTO = [
  { value: 'INV', label: 'Inversión' },
  { value: 'FUN', label: 'Funcionamiento' },
  { value: 'MIX', label: 'Mixto' },
];
const TIPO_AGREGACION = [
  { value: 'SUMA', label: 'Suma' },
  { value: 'ULTIMO', label: 'Último' },
  { value: 'PROMEDIO', label: 'Promedio' },
  { value: 'MAX', label: 'Máximo' },
];

const CONFIGS: Record<string, EntidadConfig> = {
  proyectos: {
    titulo: 'Proyectos del plan',
    endpoint: '/presupuesto/api/proyectos/',
    itemKey: 'id',
    cols: [
      { key: 'codigo', label: 'Código' },
      { key: 'nombre', label: 'Nombre' },
      { key: 'subgrupo', label: 'Subgrupo' },
      { key: 'dependencia', label: 'Dependencia' },
    ],
    formFields: [
      { key: 'codigo', label: 'Código', type: 'text', required: true },
      { key: 'nombre', label: 'Nombre', type: 'text', required: true },
      {
        key: 'programa_id', label: 'Programa', type: 'select',
        optionsEndpoint: '/presupuesto/api/programas/', optionLabel: o => o.nombre,
      },
      {
        key: 'dependencia_id', label: 'Dependencia', type: 'select', omit: true,
        optionsEndpoint: '/presupuesto/api/dependencias/', optionLabel: o => o.nombre,
      },
      {
        key: 'subgrupo_id', label: 'Subgrupo', type: 'select', dependsOn: 'dependencia_id',
        optionsEndpoint: f => f['dependencia_id']
          ? `/presupuesto/api/subgrupos/?dep_id=${f['dependencia_id']}` : null,
        optionLabel: o => o.nombre,
      },
    ],
    detalleRuta: id => `/presupuesto/proyectos/${id}`,
    paginated: true,
  },
  programas: {
    titulo: 'Programas',
    endpoint: '/presupuesto/api/programas/',
    itemKey: 'id',
    cols: [
      { key: 'id', label: '#' },
      { key: 'nombre', label: 'Nombre' },
      { key: 'descripcion', label: 'Descripción' },
    ],
    formFields: [
      { key: 'nombre', label: 'Nombre', type: 'text', required: true },
      { key: 'descripcion', label: 'Descripción', type: 'textarea' },
    ],
    detalleRuta: id => `/presupuesto/programas/${id}`,
  },
  objetivos: {
    titulo: 'Objetivos estratégicos',
    endpoint: '/presupuesto/api/objetivos/',
    itemKey: 'id',
    cols: [{ key: 'id', label: '#' }, { key: 'nombre', label: 'Nombre' }],
    formFields: [
      { key: 'nombre', label: 'Nombre', type: 'text', required: true },
    ],
  },
  metas: {
    titulo: 'Catálogo de Metas',
    endpoint: '/presupuesto/api/metas/',
    itemKey: 'codigo',
    cols: [
      { key: 'codigo', label: 'Código' },
      { key: 'nombre', label: 'Nombre' },
      { key: 'codigo_meta', label: 'SEGPLAN (oficial)' },
      { key: 'avance_oficial', label: 'Avance oficial' },
    ],
    formFields: [
      { key: 'nombre', label: 'Nombre', type: 'text', required: true },
      { key: 'descripcion', label: 'Descripción', type: 'textarea' },
    ],
  },
  conceptos: {
    titulo: 'Conceptos de gasto',
    endpoint: '/presupuesto/api/conceptos-gasto/',
    itemKey: 'id',
    cols: [
      { key: 'codigo', label: 'Código' },
      { key: 'nombre', label: 'Nombre' },
      { key: 'tipo', label: 'Tipo' },
      { key: 'programa', label: 'Programa' },
    ],
    formFields: [
      { key: 'nombre', label: 'Nombre', type: 'text', required: true },
      { key: 'tipo', label: 'Tipo', type: 'select', options: TIPO_CONCEPTO, default: 'INV' },
      {
        key: 'programa_id', label: 'Programa', type: 'select', required: true,
        optionsEndpoint: '/presupuesto/api/programas/', optionLabel: o => o.nombre,
      },
      {
        key: 'vigencia_id', label: 'Vigencia (año)', type: 'select', required: true,
        optionsEndpoint: '/presupuesto/api/vigencias/',
        optionLabel: o => String(o.anio), preselectCurrentYear: true,
      },
      { key: 'descripcion', label: 'Descripción', type: 'textarea' },
    ],
    deleteEndpoint: id => `/presupuesto/api/conceptos-gasto/${id}/`,
  },
  cdps: {
    titulo: 'CDPs',
    endpoint: '/presupuesto/api/cdps/',
    createEndpoint: '/presupuesto/api/cdps/crear/',
    detalleRuta: (id: any) => `/presupuesto/cdps/${id}`,
    itemKey: 'id',
    cols: [
      { key: 'numero', label: 'Número' },
      { key: 'fecha', label: 'Fecha' },
      { key: 'valor', label: 'Valor', pipe: 'money' },
      { key: 'proyecto_codigo', label: 'Proyecto' },
    ],
    formFields: [
      {
        key: 'proyecto_id', label: 'Proyecto', type: 'select', required: true,
        optionsEndpoint: '/presupuesto/api/proyectos/', optionLabel: PROY_LABEL,
      },
      { key: 'numero', label: 'Número de CDP', type: 'text', required: true },
      { key: 'valor', label: 'Valor', type: 'number', required: true },
      { key: 'fecha', label: 'Fecha', type: 'date' },
      { key: 'descripcion', label: 'Descripción', type: 'textarea' },
    ],
    paginated: true,
  },
  contratos: {
    titulo: 'Contratos',
    endpoint: '/presupuesto/api/contratos/',
    vigenciaDesde: 2025,
    createEndpoint: '/presupuesto/api/contratos/crear/',
    detalleRuta: (id: any) => `/presupuesto/contratos/${id}`,
    itemKey: 'id',
    cols: [
      { key: 'contrato_numero', label: 'Número' },
      { key: 'contrato_vigencia', label: 'Vigencia' },
      { key: 'valor', label: 'Valor', pipe: 'money' },
      { key: 'cdp_numero', label: 'CDP' },
    ],
    formFields: [
      {
        key: 'proyecto_id', label: 'Proyecto', type: 'select', required: true, omit: true,
        optionsEndpoint: '/presupuesto/api/proyectos/', optionLabel: PROY_LABEL,
      },
      {
        key: 'cdp_id', label: 'CDP', type: 'select', required: true, dependsOn: 'proyecto_id',
        optionsEndpoint: f => f['proyecto_id']
          ? `/presupuesto/api/cdps/?proyecto_id=${f['proyecto_id']}` : null,
        optionLabel: o => `CDP ${o.numero} — $${Number(o.valor || 0).toLocaleString('es-CO')}`,
      },
      { key: 'numero', label: 'Número de contrato', type: 'number', required: true },
      { key: 'valor', label: 'Valor', type: 'number', required: true },
      { key: 'objeto', label: 'Objeto', type: 'textarea' },
      { key: 'fecha_inicio', label: 'Fecha inicio', type: 'date' },
      { key: 'fecha_fin', label: 'Fecha fin', type: 'date' },
    ],
    paginated: true,
  },
  indicadores: {
    titulo: 'Metas del proyecto',
    endpoint: '/presupuesto/api/indicadores/',
    // Alta en UN paso: crea Meta + asociación + meta medible atómicamente.
    createEndpoint: '/presupuesto/api/metas-medibles/crear/',
    detalleRuta: (id: any) => `/presupuesto/indicadores/${id}`,
    itemKey: 'id',
    cols: [
      { key: 'nombre', label: 'Meta' },
      { key: 'meta_magnitud', label: 'Objetivo', pipe: 'num' },
      { key: 'unidad_medida', label: 'Unidad' },
      { key: 'progreso', label: 'Avance', type: 'bar' },
    ],
    formFields: [
      {
        key: 'proyecto_id', label: 'Proyecto', type: 'select', required: true,
        optionsEndpoint: '/presupuesto/api/proyectos/', optionLabel: PROY_LABEL,
      },
      { key: 'nombre', label: 'Nombre de la meta', type: 'text', required: true },
      { key: 'meta_magnitud', label: 'Cantidad objetivo', type: 'number', required: true },
      { key: 'unidad_medida', label: 'Unidad (personas, talleres, kits…)', type: 'text', default: 'unidades' },
      { key: 'tipo_agregacion', label: 'Cómo se acumula', type: 'select', options: TIPO_AGREGACION, default: 'SUMA' },
      { key: 'descripcion', label: 'Descripción (opcional)', type: 'textarea' },
    ],
    paginated: true,
  },
  avances: {
    titulo: 'Avances de KPIs',
    endpoint: '/presupuesto/api/avances/',
    createEndpoint: '/presupuesto/api/avances/crear/',
    itemKey: 'id',
    cols: [
      { key: 'indicador', label: 'KPI' },
      { key: 'magnitud_aportada', label: 'Magnitud', pipe: 'num' },
      { key: 'fecha_aporte', label: 'Fecha' },
      { key: 'periodo', label: 'Periodo' },
      { key: 'origen', label: 'Origen' },
    ],
    formFields: [
      {
        key: 'indicador_id', label: 'KPI / Indicador', type: 'select', required: true,
        optionsEndpoint: '/presupuesto/api/indicadores/',
        optionLabel: o => `${o.nombre}${o.unidad_medida ? ' (' + o.unidad_medida + ')' : ''}`,
      },
      { key: 'magnitud_aportada', label: 'Magnitud aportada', type: 'number', required: true },
      { key: 'fecha_aporte', label: 'Fecha de aporte', type: 'date' },
      { key: 'periodo', label: 'Periodo (YYYY-MM)', type: 'text', placeholder: 'Ej: 2026-06 (por defecto: mes actual)' },
      { key: 'observaciones', label: 'Observaciones', type: 'textarea' },
    ],
    paginated: true,
  },
  'meta-proyecto': {
    titulo: 'Meta ↔ Proyecto',
    endpoint: '/presupuesto/api/metas-proyecto/',
    itemKey: 'id',
    cols: [
      { key: 'id', label: '#' },
      { key: 'meta_codigo', label: 'Meta' },
      { key: 'meta_nombre', label: 'Meta nombre' },
      { key: 'proyecto_id', label: 'Proyecto' },
    ],
    formFields: [
      {
        key: 'meta_id', label: 'Meta', type: 'select', required: true,
        optionsEndpoint: '/presupuesto/api/metas/', optionValue: 'codigo',
        optionLabel: o => `${o.codigo} — ${o.nombre || ''}`,
      },
      {
        key: 'proyecto_id', label: 'Proyecto', type: 'select', required: true,
        optionsEndpoint: '/presupuesto/api/proyectos/', optionLabel: PROY_LABEL,
      },
    ],
  },
  'actividad-indicador': {
    titulo: 'Vinculación Actividad ↔ KPI',
    endpoint: '/presupuesto/api/actividad-indicador/',
    itemKey: 'id',
    cols: [
      { key: 'id', label: '#' },
      { key: 'actividad_plan_id', label: 'Actividad #' },
      { key: 'actividad_descripcion', label: 'Actividad' },
      { key: 'indicador_id', label: 'KPI #' },
      { key: 'indicador_nombre', label: 'KPI nombre' },
    ],
    formFields: [
      {
        key: 'proyecto_id', label: 'Proyecto', type: 'select', required: true, omit: true,
        optionsEndpoint: '/presupuesto/api/proyectos/', optionLabel: PROY_LABEL,
      },
      {
        key: 'actividad_plan_id', label: 'Actividad del plan', type: 'select', required: true,
        dependsOn: 'proyecto_id',
        optionsEndpoint: f => f['proyecto_id']
          ? `/presupuesto/api/plan-actividades-por-proyecto/${f['proyecto_id']}/` : null,
        optionLabel: o => o.nombre || o.descripcion || `#${o.id}`,
      },
      {
        key: 'indicador_id', label: 'KPI / Indicador', type: 'select', required: true,
        optionsEndpoint: '/presupuesto/api/indicadores/',
        optionLabel: o => o.nombre,
      },
    ],
  },
};

@Component({
  standalone: true,
  selector: 'app-presupuesto-entidad',
  imports: [CommonModule, FormsModule, RouterLink],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <div class="page">
      @if (!cfg()) {
        <div class="page__error">Entidad no soportada.</div>
      } @else {
        @let c = cfg()!;
        <header class="page__header">
          <div>
            <h1>
              <i class="fa" [class]="iconoEntidad()" aria-hidden="true"></i>
              {{ c.titulo }}
            </h1>
            @if (data()) {
              <p class="page__subtitle">
                {{ count() }} registro{{ count() === 1 ? '' : 's' }}
                @if (c.vigenciaDesde) {
                  @if (verHistorico()) {
                    · todas las vigencias
                    <button type="button" class="ui-btn ui-btn--ghost ui-btn--sm"
                            (click)="alternarHistorico(c)">Ver solo {{ c.vigenciaDesde }} en adelante</button>
                  } @else {
                    · vigencia {{ c.vigenciaDesde }} en adelante
                    <button type="button" class="ui-btn ui-btn--ghost ui-btn--sm"
                            (click)="alternarHistorico(c)">Ver también las anteriores</button>
                  }
                }
              </p>
            }
          </div>
          @if (c.formFields.length) {
            <button class="ui-btn ui-btn--primary" (click)="toggleForm()">
              <i class="fa fa-plus-circle" aria-hidden="true"></i> Crear
            </button>
          }
        </header>

        @if (formAbierto() && c.formFields.length) {
          <div class="form-create">
            @for (f of c.formFields; track f.key) {
              <label [class.full]="f.type === 'textarea'">
                <span>{{ f.label }}{{ f.required ? ' *' : '' }}</span>

                @switch (f.type) {
                  @case ('select') {
                    <select [ngModel]="form[f.key]"
                            (ngModelChange)="onChange(f, $event)">
                      <option [ngValue]="undefined" disabled>— elegir —</option>
                      @for (opt of optionsFor(f.key); track opt.value) {
                        <option [ngValue]="opt.value">{{ opt.label }}</option>
                      }
                    </select>
                    @if (loadingOpts()[f.key]) { <em class="hint">cargando…</em> }
                    @else if (f.dependsOn && !form[f.dependsOn]) {
                      <em class="hint">elige {{ labelOf(f.dependsOn) }} primero</em>
                    }
                  }
                  @case ('textarea') {
                    <textarea rows="2" [ngModel]="form[f.key]"
                              (ngModelChange)="form[f.key] = $event"></textarea>
                  }
                  @default {
                    <input [type]="f.type" [placeholder]="f.placeholder || ''"
                           [ngModel]="form[f.key]"
                           (ngModelChange)="form[f.key] = $event">
                  }
                }
              </label>
            }
            <div class="form-actions">
              <button class="ui-btn ui-btn--ghost" (click)="formAbierto.set(false)">Cancelar</button>
              <button class="ui-btn ui-btn--primary"
                      [disabled]="!validar() || guardando()"
                      (click)="crear()">
                @if (guardando()) { Guardando… } @else { Crear }
              </button>
            </div>
            @if (msg()) { <p class="msg" [class.err]="errorCrear()">{{ msg() }}</p> }
          </div>
        }

        @if (editId() !== null) {
          <div class="form-create">
            <h3 style="grid-column:1/-1;margin:0 0 8px;">Editar registro #{{ editId() }}</h3>
            @for (f of camposEdit(); track f.key) {
              <label>
                <span>{{ f.label }}</span>
                @if (f.type === 'select') {
                  <select [ngModel]="editForm[f.key]" (ngModelChange)="editForm[f.key] = $event">
                    @for (o of f.options || []; track o.value) { <option [ngValue]="o.value">{{ o.label }}</option> }
                  </select>
                } @else {
                  <input [type]="f.type" [ngModel]="editForm[f.key]" (ngModelChange)="editForm[f.key] = $event">
                }
              </label>
            }
            <div class="form-actions">
              <button class="ui-btn ui-btn--ghost" (click)="editId.set(null)">Cancelar</button>
              <button class="ui-btn ui-btn--primary" [disabled]="guardando()" (click)="guardarEdit()">
                @if (guardando()) { Guardando… } @else { Guardar cambios }
              </button>
            </div>
            @if (msg()) { <p class="msg" [class.err]="errorCrear()">{{ msg() }}</p> }
          </div>
        }

        @if (rows().length && (c.paginated || rows().length > pageSize)) {
          <div class="list-toolbar">
            <div class="list-toolbar__search">
              <i class="fa fa-search" aria-hidden="true"></i>
              <input type="search" [ngModel]="search()"
                     (ngModelChange)="onSearch($event)"
                     [placeholder]="'Buscar en ' + c.titulo.toLowerCase() + '…'"
                     [attr.aria-label]="'Buscar en ' + c.titulo">
            </div>
            <span class="list-toolbar__count">
              {{ filteredRows().length }} de {{ rows().length }}
            </span>
          </div>
        }

        @if (loading()) { <div class="page__loading">Cargando…</div> }
        @else if (filteredRows().length) {
          <div class="ui-table-responsive">
            <table class="ui-table">
              <thead>
                <tr>@for (col of c.cols; track col.key) { <th>{{ col.label }}</th> }
                  @if (esEditable() || c.deleteEndpoint) { <th></th> }</tr>
              </thead>
              <tbody>
                @for (row of pagedRows(); track $index) {
                  <tr [class.row--link]="!!c.detalleRuta" (click)="navegar(row)">
                    @for (col of c.cols; track col.key) {
                      @if (col.type === 'bar') {
                        <td class="bar-cell">
                          @if (row['avance_pct'] != null) {
                            <div class="prog">
                              <div class="prog__track">
                                <div class="prog__fill" [class]="barClase(row['avance_pct'])"
                                     [style.width.%]="clampPct(row['avance_pct'])"></div>
                              </div>
                              <span class="prog__txt">
                                {{ formatNumero(row['avance_acumulado'] || 0) }} / {{ formatNumero(row['meta_magnitud'] || 0) }}
                                ({{ formatNumero(row['avance_pct']) }}%)
                              </span>
                            </div>
                          } @else { <span class="muted">sin objetivo</span> }
                        </td>
                      } @else {
                        <td>{{ celda(row, col) }}</td>
                      }
                    }
                    @if (esEditable() || c.deleteEndpoint) {
                      <td class="r" (click)="$event.stopPropagation()">
                        @if (esEditable()) {
                          <button class="ui-btn ui-btn--ghost ui-btn--sm" (click)="editar(row)">
                            <i class="fa fa-edit" aria-hidden="true"></i> Editar
                          </button>
                        }
                        @if (c.deleteEndpoint) {
                          <button class="ui-btn ui-btn--ghost ui-btn--sm"
                                  [disabled]="eliminandoId() === row[c.itemKey]"
                                  (click)="eliminar(row)" title="Eliminar">
                            <i class="fa fa-trash" aria-hidden="true"></i>
                          </button>
                        }
                      </td>
                    }
                  </tr>
                }
              </tbody>
            </table>
          </div>

          @if (totalPages() > 1) {
            <nav class="pager" aria-label="Paginación">
              <button class="ui-btn ui-btn--ghost ui-btn--sm"
                      [disabled]="page() === 1" (click)="irPagina(page() - 1)"
                      aria-label="Página anterior">
                <i class="fa fa-chevron-left" aria-hidden="true"></i> Anterior
              </button>
              <span class="pager__info">Página {{ page() }} de {{ totalPages() }}</span>
              <button class="ui-btn ui-btn--ghost ui-btn--sm"
                      [disabled]="page() === totalPages()" (click)="irPagina(page() + 1)"
                      aria-label="Página siguiente">
                Siguiente <i class="fa fa-chevron-right" aria-hidden="true"></i>
              </button>
            </nav>
          }
        } @else {
          <div class="ui-empty-state">
            @if (search()) { Sin coincidencias para «{{ search() }}». }
            @else { Sin resultados. }
          </div>
        }
      }
    </div>
  `,
  styles: [`
    @use '../../../styles/tokens' as *;
    :host { display: block; }
    .page { max-width: 1300px; margin: 0 auto; }
    .page__header {
      display: flex; justify-content: space-between;
      align-items: flex-start; gap: $space-3; flex-wrap: wrap;
      h1 { margin: 0; color: $color-primary; i { margin-right: $space-2; } }
    }
    .page__subtitle { color: $color-text-muted; margin: $space-1 0 $space-3; }
    .page__loading, .page__error {
      padding: $space-4; text-align: center; color: $color-text-muted;
    }
    .form-create {
      background: $color-bg-subtle; padding: $space-3;
      border-radius: $radius-md; margin-bottom: $space-3;
      display: grid; grid-template-columns: repeat(3, 1fr); gap: $space-3;
      @media (max-width: 720px) { grid-template-columns: 1fr; }
      label {
        display: block;
        &.full { grid-column: 1 / -1; }
        span { display: block; font-size: $font-size-xs; color: $color-text-muted; margin-bottom: 2px; }
        input, select, textarea {
          width: 100%; padding: $space-1 $space-2;
          border: 1px solid $color-border; border-radius: $radius-sm;
          font: inherit; background: #fff;
        }
        textarea { resize: vertical; }
        .hint { font-size: $font-size-xs; color: $color-text-muted; }
      }
      .form-actions {
        grid-column: 1 / -1;
        display: flex; gap: $space-2; justify-content: flex-end;
        margin-top: $space-1;
      }
      .msg {
        grid-column: 1 / -1;
        padding: $space-1 $space-2; border-radius: $radius-sm;
        background: rgba(22,163,74,0.10); color: $color-success;
        &.err { background: rgba(220,38,38,0.10); color: $color-danger; }
      }
    }
    .list-toolbar {
      display: flex; align-items: center; gap: $space-3;
      margin-bottom: $space-3; flex-wrap: wrap;
      &__search {
        position: relative; flex: 1; min-width: 220px; max-width: 420px;
        i { position: absolute; left: $space-2; top: 50%; transform: translateY(-50%);
            color: $color-text-muted; font-size: $font-size-sm; pointer-events: none; }
        input {
          width: 100%; padding: $space-1 $space-2 $space-1 calc(#{$space-2} + 18px);
          border: 1px solid $color-border; border-radius: $radius-sm;
          font: inherit; background: #fff;
          &:focus-visible { outline: 2px solid $color-primary; outline-offset: 1px; }
        }
      }
      &__count { font-size: $font-size-xs; color: $color-text-muted; }
    }
    .pager {
      display: flex; align-items: center; justify-content: center;
      gap: $space-3; margin-top: $space-3;
      &__info { font-size: $font-size-sm; color: $color-text-muted; }
    }
    .row--link { cursor: pointer; }
    .row--link:hover { background: rgba(214,0,28,0.04); }
    .muted { color: $color-text-muted; font-size: $font-size-xs; }
    .bar-cell { min-width: 200px; }
    .prog { display: flex; flex-direction: column; gap: 3px; }
    .prog__track { height: 8px; background: $color-bg-muted; border-radius: $radius-pill; overflow: hidden; }
    .prog__fill { height: 100%; border-radius: $radius-pill; transition: width .5s ease;
      &.is-ok { background: #16a34a; } &.is-mid { background: #d97706; } &.is-low { background: #dc2626; } }
    .prog__txt { font-size: $font-size-xs; color: $color-text-muted; }
  `],
})
export class PresupuestoEntidadComponent implements OnInit {
  private http = inject(HttpClient);
  private cfg2 = inject(ConfigService);
  private route = inject(ActivatedRoute);
  private layout = inject(LayoutService);

  cfg = signal<EntidadConfig | null>(null);
  data = signal<any | null>(null);
  loading = signal<boolean>(true);
  formAbierto = signal<boolean>(false);
  guardando = signal<boolean>(false);
  msg = signal<string>('');
  errorCrear = signal<boolean>(false);
  form: Record<string, any> = {};
  entidadSlug = signal<string>('');
  editId = signal<any>(null);
  editForm: Record<string, any> = {};

  // Campos editables (texto/número/select simple) por entidad.
  private static CAMPOS_EDIT: Record<string, { key: string; label: string; type: string; options?: { value: any; label: string }[] }[]> = {
    proyectos: [{ key: 'codigo', label: 'Código', type: 'text' }, { key: 'nombre', label: 'Nombre', type: 'text' }],
    programas: [{ key: 'nombre', label: 'Nombre', type: 'text' }, { key: 'descripcion', label: 'Descripción', type: 'text' }],
    objetivos: [{ key: 'nombre', label: 'Nombre', type: 'text' }],
    metas: [{ key: 'nombre', label: 'Nombre', type: 'text' }, { key: 'descripcion', label: 'Descripción', type: 'text' }],
    conceptos: [{ key: 'nombre', label: 'Nombre', type: 'text' }, { key: 'tipo', label: 'Tipo', type: 'select', options: [{ value: 'INV', label: 'Inversión' }, { value: 'FUN', label: 'Funcionamiento' }, { value: 'MIX', label: 'Mixto' }] }, { key: 'descripcion', label: 'Descripción', type: 'text' }],
    avances: [{ key: 'magnitud_aportada', label: 'Magnitud', type: 'number' }, { key: 'periodo', label: 'Periodo (YYYY-MM)', type: 'text' }, { key: 'observaciones', label: 'Observaciones', type: 'text' }],
    cdps: [{ key: 'numero', label: 'Número', type: 'text' }, { key: 'valor', label: 'Valor', type: 'number' }, { key: 'descripcion', label: 'Descripción', type: 'text' }],
    indicadores: [{ key: 'nombre', label: 'Nombre', type: 'text' }, { key: 'meta_magnitud', label: 'Meta', type: 'number' }, { key: 'unidad_medida', label: 'Unidad', type: 'text' }],
  };

  camposEdit(): { key: string; label: string; type: string; options?: { value: any; label: string }[] }[] {
    return PresupuestoEntidadComponent.CAMPOS_EDIT[this.entidadSlug()] || [];
  }
  esEditable(): boolean { return this.camposEdit().length > 0; }
  selectOptions = signal<Record<string, { value: any; label: string }[]>>({});
  loadingOpts = signal<Record<string, boolean>>({});

  private static ICONOS_ENTIDAD: Record<string, string> = {
    proyectos: 'fa-diagram-project',
    programas: 'fa-layer-group',
    objetivos: 'fa-bullseye',
    metas: 'fa-flag-checkered',
    cdps: 'fa-file-invoice-dollar',
    contratos: 'fa-file-signature',
    conceptos: 'fa-tags',
    indicadores: 'fa-gauge-high',
    avances: 'fa-arrow-trend-up',
    'meta-proyecto': 'fa-link',
    'actividad-indicador': 'fa-calendar-check',
  };

  iconoEntidad(): string {
    return PresupuestoEntidadComponent.ICONOS_ENTIDAD[this.entidadSlug()] || 'fa-table-list';
  }

  rows = computed<any[]>(() => {
    const d = this.data();
    if (!d) return [];
    return d.results || d.items || (Array.isArray(d) ? d : []);
  });
  count = computed<number>(() => {
    const d = this.data();
    return d?.count ?? this.rows().length;
  });

  // GEN-UX-13 / GEN-A-07: búsqueda + paginación client-side.
  readonly pageSize = 20;
  /** Falso = solo desde `vigenciaDesde`. La pantalla dice cuál está mostrando. */
  verHistorico = signal<boolean>(false);
  search = signal<string>('');
  page = signal<number>(1);

  filteredRows = computed<any[]>(() => {
    const term = this.search().trim().toLowerCase();
    const rows = this.rows();
    if (!term) return rows;
    const cols = this.cfg()?.cols || [];
    return rows.filter(r =>
      cols.some(col => {
        const v = r[col.key];
        return v != null && String(v).toLowerCase().includes(term);
      }),
    );
  });

  totalPages = computed<number>(() =>
    Math.max(1, Math.ceil(this.filteredRows().length / this.pageSize)),
  );

  pagedRows = computed<any[]>(() => {
    const start = (this.page() - 1) * this.pageSize;
    return this.filteredRows().slice(start, start + this.pageSize);
  });

  onSearch(term: string): void {
    this.search.set(term);
    this.page.set(1);
  }

  irPagina(n: number): void {
    this.page.set(Math.max(1, Math.min(n, this.totalPages())));
  }

  ngOnInit(): void {
    this.route.paramMap.subscribe(p => {
      // La entidad llega por el parámetro de la ruta catch-all (`:entidad`) o,
      // cuando la ruta es fija, por su `data`. Lo segundo existe para
      // `contratos-internos`: necesita ruta propia porque `contratos` la ocupa
      // la lista de SECOP, pero la pantalla es la misma.
      const entidad = p.get('entidad') || this.route.snapshot.data['entidad'] || '';
      const cfg = CONFIGS[entidad] || null;
      this.cfg.set(cfg);
      this.entidadSlug.set(entidad);
      this.editId.set(null);
      this.form = {};
      this.formAbierto.set(false);
      this.selectOptions.set({});
      this.msg.set('');
      this.search.set('');
      this.page.set(1);
      this.layout.setBreadcrumb([
        { label: 'Inicio', url: '/' },
        { label: 'Presupuesto', url: '/presupuesto' },
        { label: cfg?.titulo || entidad },
      ]);
      if (cfg) this.cargar(cfg);
    });
  }

  /** Cambia entre la operación de hoy y el histórico completo. */
  alternarHistorico(cfg: EntidadConfig): void {
    this.verHistorico.set(!this.verHistorico());
    this.page.set(1);
    this.cargar(cfg);
  }

  cargar(cfg: EntidadConfig): void {
    this.loading.set(true);
    let url = cfg.endpoint;
    if (cfg.vigenciaDesde && !this.verHistorico()) {
      url += `${url.includes('?') ? '&' : '?'}vigencia_desde=${cfg.vigenciaDesde}`;
    }
    this.http.get<any>(this.cfg2.url(url)).subscribe({
      next: r => { this.data.set(r); this.loading.set(false); },
      error: () => this.loading.set(false),
    });
  }

  toggleForm(): void {
    const next = !this.formAbierto();
    this.formAbierto.set(next);
    if (next) this.abrirForm();
  }

  private abrirForm(): void {
    const c = this.cfg(); if (!c) return;
    this.form = {};
    this.msg.set('');
    // Defaults estáticos.
    for (const f of c.formFields) {
      if (f.default !== undefined) this.form[f.key] = f.default;
    }
    // Cargar opciones de los selects sin dependencia.
    for (const f of c.formFields) {
      if (f.type === 'select' && !f.dependsOn) this.loadOptions(f);
    }
  }

  onChange(f: FieldDef, value: any): void {
    this.form[f.key] = value;
    const c = this.cfg(); if (!c) return;
    // Recargar selects que dependen de este campo + limpiar su valor.
    for (const child of c.formFields) {
      if (child.dependsOn === f.key) {
        this.form[child.key] = undefined;
        this.patchOptions(child.key, []);
        this.loadOptions(child);
      }
    }
  }

  private loadOptions(f: FieldDef): void {
    if (f.options) { this.patchOptions(f.key, f.options); return; }
    const ep = typeof f.optionsEndpoint === 'function'
      ? f.optionsEndpoint(this.form) : f.optionsEndpoint;
    if (!ep) { this.patchOptions(f.key, []); return; }
    this.patchLoading(f.key, true);
    this.http.get<any>(this.cfg2.url(ep)).subscribe({
      next: r => {
        const arr: any[] = r?.results || r?.items || (Array.isArray(r) ? r : []);
        const vKey = f.optionValue || 'id';
        const opts = arr.map(o => ({
          value: o[vKey],
          label: f.optionLabel ? f.optionLabel(o) : (o.nombre ?? String(o[vKey])),
        }));
        this.patchOptions(f.key, opts);
        this.patchLoading(f.key, false);
        if (f.preselectCurrentYear) this.preselectYear(f, arr);
      },
      error: () => { this.patchOptions(f.key, []); this.patchLoading(f.key, false); },
    });
  }

  private preselectYear(f: FieldDef, arr: any[]): void {
    const year = new Date().getFullYear();
    const match = arr.find(o => Number(o.anio) === year) || arr[0];
    if (match) this.form[f.key] = match[f.optionValue || 'id'];
  }

  private patchOptions(key: string, opts: { value: any; label: string }[]): void {
    this.selectOptions.update(m => ({ ...m, [key]: opts }));
  }
  private patchLoading(key: string, v: boolean): void {
    this.loadingOpts.update(m => ({ ...m, [key]: v }));
  }
  optionsFor(key: string): { value: any; label: string }[] {
    return this.selectOptions()[key] || [];
  }
  labelOf(key: string): string {
    const f = this.cfg()?.formFields.find(x => x.key === key);
    return (f?.label || key).toLowerCase();
  }

  validar(): boolean {
    const c = this.cfg(); if (!c) return false;
    return c.formFields.filter(f => f.required)
      .every(f => this.form[f.key] !== undefined && this.form[f.key] !== '');
  }

  eliminandoId = signal<any>(null);

  eliminar(row: any): void {
    const c = this.cfg(); if (!c || !c.deleteEndpoint) return;
    const id = row[c.itemKey];
    const nombre = row['nombre'] || row['codigo'] || `#${id}`;
    if (!confirm(`¿Eliminar "${nombre}"? Esta acción no se puede deshacer.`)) return;
    this.eliminandoId.set(id);
    this.msg.set(''); this.errorCrear.set(false);
    this.http.delete(this.cfg2.url(c.deleteEndpoint(id))).subscribe({
      next: () => {
        this.eliminandoId.set(null);
        this.msg.set('✓ Eliminado.');
        this.cargar(c);
      },
      error: e => {
        this.eliminandoId.set(null);
        this.errorCrear.set(true);
        this.msg.set(e?.error?.detail || 'No se pudo eliminar.');
      },
    });
  }

  editar(row: any): void {
    const c = this.cfg(); if (!c) return;
    this.formAbierto.set(false);
    this.editForm = {};
    for (const f of this.camposEdit()) this.editForm[f.key] = row[f.key];
    this.editId.set(row[c.itemKey]);
    this.msg.set(''); this.errorCrear.set(false);
  }

  /** URL de PATCH según entidad (endpoints específicos o el genérico). */
  private editUrl(id: any): string {
    const slug = this.entidadSlug();
    if (slug === 'cdps') return `/presupuesto/api/cdps/${id}/`;
    if (slug === 'indicadores') return `/presupuesto/api/indicadores/${id}/editar/`;
    return `/presupuesto/api/editar/${slug}/${id}/`;
  }

  guardarEdit(): void {
    const c = this.cfg(); const id = this.editId();
    if (!c || id === null) return;
    this.guardando.set(true); this.msg.set(''); this.errorCrear.set(false);
    const payload: Record<string, any> = {};
    for (const k of Object.keys(this.editForm)) {
      if (this.editForm[k] !== undefined && this.editForm[k] !== '') payload[k] = this.editForm[k];
    }
    this.http.patch(this.cfg2.url(this.editUrl(id)), payload).subscribe({
      next: () => {
        this.msg.set('✓ Cambios guardados.');
        this.guardando.set(false);
        this.editId.set(null);
        this.cargar(c);
      },
      error: e => {
        this.errorCrear.set(true);
        this.msg.set(e?.error?.detail || 'Error al guardar.');
        this.guardando.set(false);
      },
    });
  }

  crear(): void {
    const c = this.cfg(); if (!c) return;
    this.guardando.set(true);
    this.msg.set(''); this.errorCrear.set(false);
    // Payload sin campos omit (solo-filtro).
    const omit = new Set(c.formFields.filter(f => f.omit).map(f => f.key));
    const payload: Record<string, any> = {};
    for (const k of Object.keys(this.form)) {
      if (!omit.has(k) && this.form[k] !== undefined && this.form[k] !== '') {
        payload[k] = this.form[k];
      }
    }
    this.http.post(this.cfg2.url(c.createEndpoint || c.endpoint), payload).subscribe({
      next: () => {
        this.msg.set('✓ Creado.');
        this.guardando.set(false);
        this.formAbierto.set(false);
        this.cargar(c);
      },
      error: e => {
        this.errorCrear.set(true);
        this.msg.set(e?.error?.detail || 'Error al crear.');
        this.guardando.set(false);
      },
    });
  }

  formatNumero = formatNumero;
  clampPct(v: any): number { const n = Number(v) || 0; return Math.max(0, Math.min(100, n)); }
  barClase(v: any): string { const n = Number(v) || 0; return n >= 80 ? 'is-ok' : n >= 50 ? 'is-mid' : 'is-low'; }

  celda(row: any, col: ColDef): string {
    const v = row[col.key];
    if (v == null || v === '') return '—';
    if (col.pipe === 'money') {
      return '$' + Number(v).toLocaleString('es-CO', { maximumFractionDigits: 0 });
    }
    if (col.pipe === 'num') {
      return formatNumero(v);
    }
    return String(v);
  }

  navegar(row: any): void {
    const c = this.cfg();
    if (!c?.detalleRuta) return;
    window.location.href = '/app' + c.detalleRuta(row[c.itemKey]);
  }
}
