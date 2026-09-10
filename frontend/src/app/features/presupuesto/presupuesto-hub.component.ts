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

//: Cuatro secciones, y cada una responde una pregunta que alguien hace de
//: verdad: qué se prometió, cuánta plata hay, qué se ha hecho y de dónde sale
//: cada cifra.
//:
//: Antes eran tres —Planeación, Ejecución, Seguimiento— y nombraban el proceso
//: interno, no la pregunta. «Comparación con Planeación (SDP)» quedaba junto a
//: «Metas», que es catálogo, y el tablero quedaba en «Seguimiento» aunque es lo
//: primero que se abre. La densidad de este hub estaba anotada como deuda desde
//: hace meses.
//:
//: El orden dentro de cada sección es el de uso: primero lo que se abre a
//: diario, después lo que se administra de vez en cuando.
const SECCIONES: Seccion[] = [
  {
    titulo: 'El Plan',
    subtitulo: 'Qué se prometió: los ejes, sus programas, sus proyectos y sus metas.',
    cards: [
      { titulo: 'Objetivos del Plan', subtitulo: 'El árbol: Objetivo → Programa → Proyecto → Meta',
        icono: 'fa-bullseye', color: 'primary', ruta: '/plan/objetivos' },
      { titulo: 'Plan oficial', subtitulo: 'La estructura completa del PDL, como la reporta la Matriz',
        icono: 'fa-sitemap', color: 'primary', ruta: '/plan/plan-oficial' },
      { titulo: 'Proyectos', subtitulo: 'Los proyectos de inversión de la localidad',
        icono: 'fa-folder-tree', color: 'primary', ruta: '/plan/proyectos' },
      { titulo: 'Metas', subtitulo: 'Catálogo de metas del Plan',
        icono: 'fa-flag-checkered', color: 'accent', ruta: '/plan/metas' },
      { titulo: 'Programas', subtitulo: 'Programas del Plan',
        icono: 'fa-diagram-project', color: 'info', ruta: '/plan/programas' },
      { titulo: 'Metas del proyecto', subtitulo: 'Metas medibles, con su cantidad y su avance',
        icono: 'fa-gauge-high', color: 'accent', ruta: '/plan/indicadores' },
      { titulo: 'Meta ↔ Proyecto', subtitulo: 'Asociar metas a proyectos',
        icono: 'fa-link', color: 'primary', ruta: '/plan/meta-proyecto' },
    ],
  },
  {
    titulo: 'La plata',
    subtitulo: 'Cuánto se apropió, cuánto se comprometió y cuánto se giró.',
    cards: [
      { titulo: 'Tablero', subtitulo: 'La cadena Apropiación → Comprometido → Girado, por año',
        icono: 'fa-chart-pie', color: 'primary', ruta: '/plan/dashboard' },
      { titulo: 'Contratos', subtitulo: 'Contratos adjudicados de Kennedy (SECOP II)',
        icono: 'fa-file-signature', color: 'info', ruta: '/plan/contratos' },
      { titulo: 'CDPs', subtitulo: 'Certificados de disponibilidad presupuestal',
        icono: 'fa-file-invoice-dollar', color: 'info', ruta: '/plan/cdps' },
      { titulo: 'Conceptos de gasto', subtitulo: 'Catálogo presupuestal',
        icono: 'fa-tags', color: 'warning', ruta: '/plan/conceptos' },
    ],
  },
  {
    titulo: 'La ejecución',
    subtitulo: 'Qué se ha hecho, y cómo suma a las metas del Plan.',
    cards: [
      { titulo: 'Avance por sector', subtitulo: 'Cómo va cada sector del Plan',
        icono: 'fa-layer-group', color: 'primary', ruta: '/plan/sectores' },
      { titulo: 'Actividades SIPSE', subtitulo: 'Por área, con migración al catálogo',
        icono: 'fa-list-check', color: 'info', ruta: '/plan/actividades' },
      { titulo: 'Avances', subtitulo: 'Registro de avances de las metas',
        icono: 'fa-chart-line', color: 'accent', ruta: '/plan/avances' },
      { titulo: 'Vinculación Actividad ↔ Meta', subtitulo: 'Qué actividad le suma a qué meta',
        icono: 'fa-link', color: 'info', ruta: '/plan/actividad-indicador' },
    ],
  },
  {
    titulo: 'Las fuentes',
    subtitulo: 'De dónde sale cada cifra, y contra qué se contrasta.',
    cards: [
      { titulo: 'Fuentes', subtitulo: 'La Matriz frente a BogData, proyecto por proyecto',
        icono: 'fa-scale-balanced', color: 'primary', ruta: '/plan/fuentes' },
      { titulo: 'Cargar Matriz PDL', subtitulo: 'Subir el corte nuevo, revisarlo y aplicarlo',
        icono: 'fa-file-arrow-up', color: 'accent', ruta: '/plan/matriz' },
      { titulo: 'Comparación con Planeación', subtitulo: 'La Matriz frente al espejo del Distrito',
        icono: 'fa-scale-balanced', color: 'primary', ruta: '/plan/comparacion-sdp' },
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
        <h1><i class="fa fa-diagram-project" aria-hidden="true"></i> Plan de Desarrollo</h1>
        <p class="page__subtitle">
          Plan de Desarrollo Local 2025-2028: el Plan, la plata, la ejecución y sus fuentes.
        </p>
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
    if (titulo === 'El Plan') return 'fa-sitemap';
    if (titulo === 'La plata') return 'fa-file-invoice-dollar';
    if (titulo === 'La ejecución') return 'fa-gauge-high';
    if (titulo === 'Las fuentes') return 'fa-scale-balanced';
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
    if (/sitemap|plan|estructura|arbol/i.test(s)) return 'folder-kanban';
    if (/scale|balance|compar/i.test(s)) return 'target';
    if (/layer|sector/i.test(s)) return 'trending-up';
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
      { label: 'Plan de Desarrollo' },
    ]);
    setTimeout(() => this.tour.iniciarSiProcede('presupuesto'), 700);
  }
}
