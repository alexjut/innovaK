import { CommonModule } from '@angular/common';
import { Component, OnInit, inject } from '@angular/core';
import { RouterLink } from '@angular/router';
import { LucideAngularModule } from 'lucide-angular';
import { LayoutService } from '../../core/layout/layout.service';
import { TourService } from '../onboarding/tour.service';

interface Card {
  titulo: string;
  subtitulo: string;
  icono: string;
  color: string;
  ruta: string;
}
interface Seccion {
  titulo: string;
  subtitulo: string;
  cards: Card[];
}

const SECCIONES: Seccion[] = [
  {
    titulo: 'Planeación',
    subtitulo: 'Proyectos, programas y metas que estructuran el plan.',
    cards: [
      { titulo: 'Proyectos', subtitulo: 'Proyectos del plan',
        icono: 'fa-folder-tree', color: 'primary', ruta: '/presupuesto/proyectos' },
      { titulo: 'Programas', subtitulo: 'Programas del plan',
        icono: 'fa-diagram-project', color: 'info', ruta: '/presupuesto/programas' },
      { titulo: 'Objetivos', subtitulo: 'Objetivos estratégicos',
        icono: 'fa-bullseye', color: 'warning', ruta: '/presupuesto/objetivos' },
      { titulo: 'Metas', subtitulo: 'Catálogo de metas',
        icono: 'fa-flag-checkered', color: 'accent', ruta: '/presupuesto/metas' },
      { titulo: 'Meta-Proyecto', subtitulo: 'Asociar metas a proyectos',
        icono: 'fa-link', color: 'primary', ruta: '/presupuesto/meta-proyecto' },
      { titulo: 'Actividades SIPSE', subtitulo: 'Por subgrupo, con migración a catálogo',
        icono: 'fa-list-check', color: 'info', ruta: '/presupuesto/actividades' },
    ],
  },
  {
    titulo: 'Ejecución',
    subtitulo: 'Dinero comprometido: CDPs, contratos y catálogo de gasto.',
    cards: [
      { titulo: 'CDPs', subtitulo: 'Certificados de disponibilidad',
        icono: 'fa-file-invoice-dollar', color: 'info', ruta: '/presupuesto/cdps' },
      { titulo: 'Contratos', subtitulo: 'Contratos y vinculaciones a actividades',
        icono: 'fa-file-signature', color: 'info', ruta: '/presupuesto/contratos' },
      { titulo: 'Conceptos de gasto', subtitulo: 'Catálogo presupuestal',
        icono: 'fa-tags', color: 'warning', ruta: '/presupuesto/conceptos' },
    ],
  },
  {
    titulo: 'Seguimiento',
    subtitulo: 'Dashboards, indicadores y avances de KPIs.',
    cards: [
      { titulo: 'Dashboard de KPIs', subtitulo: 'Indicadores y avances',
        icono: 'fa-chart-pie', color: 'primary', ruta: '/presupuesto/dashboard' },
      { titulo: 'Metas del proyecto', subtitulo: 'Metas medibles con cantidad y avance',
        icono: 'fa-gauge-high', color: 'accent', ruta: '/presupuesto/indicadores' },
      { titulo: 'Avances', subtitulo: 'Registro de avances de KPIs',
        icono: 'fa-chart-line', color: 'accent', ruta: '/presupuesto/avances' },
      { titulo: 'Vinculación Act↔KPI', subtitulo: 'Asociar actividades a indicadores',
        icono: 'fa-link', color: 'info', ruta: '/presupuesto/actividad-indicador' },
    ],
  },
];

@Component({
  standalone: true,
  selector: 'app-presupuesto-hub',
  imports: [CommonModule, RouterLink, LucideAngularModule],
  template: `
    <div class="page">
      <header class="page__header" data-tour="presupuesto-titulo">
        <h1><i class="fa fa-coins" aria-hidden="true"></i> Presupuesto</h1>
        <p class="page__subtitle">Operaciones del módulo presupuestal.</p>
      </header>

      @for (s of secciones; track s.titulo; let first = $first) {
        <section class="hub-section" [attr.data-tour]="first ? 'presupuesto-cards' : null">
          <h2 class="hub-section__title">
            <lucide-icon [name]="lucideDe(seccionIcono(s.titulo))" [size]="18"></lucide-icon>
            {{ s.titulo }}
          </h2>
          <p class="hub-section__subtitle">{{ s.subtitulo }}</p>
          <div class="hub-grid">
            @for (c of s.cards; track c.titulo) {
              <a [routerLink]="c.ruta"
                 class="ui-card ui-card--interactive"
                 [class]="'ui-card--' + c.color">
                <div class="hub-card__icon"><lucide-icon [name]="lucideDe(c.icono)" [size]="22"></lucide-icon></div>
                <div class="ui-card__body">
                  <h3 class="ui-card__title">{{ c.titulo }}</h3>
                  <p class="ui-card__subtitle">{{ c.subtitulo }}</p>
                </div>
              </a>
            }
          </div>
        </section>
      }
    </div>
  `,
  styles: [`
    @use '../../../styles/tokens' as *;
    :host { display: block; }
    .page { max-width: 1200px; margin: 0 auto; }
    .page__header h1 { margin: 0; color: $color-primary; i { margin-right: $space-2; } }
    .page__subtitle { color: $color-text-muted; margin: $space-1 0 $space-4; }
    .hub-section { margin-top: $space-5; }
    .hub-section__title {
      margin: 0 0 $space-1; font-size: $font-size-lg;
      color: $color-text;
      i { margin-right: $space-2; color: $color-primary; }
    }
    .hub-section__subtitle {
      color: $color-text-muted; margin: 0 0 $space-3;
      font-size: $font-size-sm;
    }
  `],
})
export class PresupuestoHubComponent implements OnInit {
  private layout = inject(LayoutService);
  private tour = inject(TourService);
  secciones = SECCIONES;

  seccionIcono(titulo: string): string {
    if (titulo === 'Planeación') return 'fa-diagram-project';
    if (titulo === 'Ejecución') return 'fa-file-invoice-dollar';
    if (titulo === 'Seguimiento') return 'fa-gauge-high';
    return 'fa-folder';
  }

  /** Mapea el icono fa-* del backend a un icono lucide por palabra clave. */
  lucideDe(fa: string | null | undefined): string {
    const s = fa || '';
    if (/diagram|project|proyecto|kanban|folder/i.test(s)) return 'folder-kanban';
    if (/gauge|seguim|kpi|indicad|trend/i.test(s)) return 'gauge';
    if (/invoice|receipt|contrato|factura/i.test(s)) return 'receipt';
    if (/dollar|cdp|coin|money|dinero/i.test(s)) return 'coins';
    if (/wallet/i.test(s)) return 'wallet';
    if (/target|meta|bullseye/i.test(s)) return 'target';
    if (/chart|line|analiz|dashboard/i.test(s)) return 'trending-up';
    if (/file|document/i.test(s)) return 'file-text';
    if (/tag|concepto/i.test(s)) return 'tags';
    if (/list/i.test(s)) return 'list';
    if (/plus|nuev|crear|add/i.test(s)) return 'plus';
    if (/cog|gear|ajuste|settings/i.test(s)) return 'settings';
    return 'wallet';
  }

  ngOnInit(): void {
    this.layout.setBreadcrumb([
      { label: 'Inicio', url: '/' },
      { label: 'Presupuesto' },
    ]);
    setTimeout(() => this.tour.iniciarSiProcede('presupuesto'), 700);
  }
}
