import { CommonModule } from '@angular/common';
import { Component, OnInit, computed, inject, signal } from '@angular/core';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { ConfigService } from '../../core/config/config.service';
import { LayoutService } from '../../core/layout/layout.service';

type AdminArea = 'roles' | 'org' | 'personas';

interface AreaMeta {
  label: string;
  icon: string;
  color: string;
  description: string;
  /** Path en Django legacy a donde lleva el botón principal. */
  legacyPath: string;
  /** Sub-secciones del módulo en el legacy. */
  subsections: { label: string; path: string }[];
}

const AREAS: Record<AdminArea, AreaMeta> = {
  roles: {
    label: 'Roles y permisos',
    icon: 'fa-user-shield',
    color: 'accent',
    description:
      'Sistema N15 de roles dinámicos. Cada rol agrupa permisos por módulo. Los cambios aplican en tiempo real (caché Redis con INCR).',
    legacyPath: '/org/roles/',
    subsections: [
      { label: 'Listar roles', path: '/org/roles/' },
      { label: 'Crear rol', path: '/org/roles/nuevo/' },
    ],
  },
  org: {
    label: 'Organización',
    icon: 'fa-building',
    color: 'primary',
    description:
      'Estructura organizativa de la Alcaldía: dependencias, subgrupos, funcionarios y catálogo de beneficiarios/proveedores/organizaciones.',
    legacyPath: '/org/dependencias/',
    subsections: [
      { label: 'Dependencias', path: '/org/dependencias/' },
      { label: 'Subgrupos', path: '/org/subgrupos/' },
      { label: 'Funcionarios', path: '/org/funcionarios/' },
      { label: 'Organizaciones', path: '/org/organizaciones/' },
      { label: 'Proveedores', path: '/org/proveedores/' },
      { label: 'Beneficiarios', path: '/org/beneficiarios/' },
    ],
  },
  personas: {
    label: 'Personas',
    icon: 'fa-user-plus',
    color: 'info',
    description:
      'Catálogo central de personas. Una persona sirve para múltiples roles: participante, beneficiario, contratista, funcionario.',
    legacyPath: '/crear-persona/',
    subsections: [{ label: 'Crear persona', path: '/crear-persona/' }],
  },
};

/**
 * Vista de área de administración. Por ahora todas las áreas son
 * placeholders con link al CRUD HTML Django (los endpoints DRF
 * todavía no existen). Cuando se construyan, esta vista se reemplaza
 * por el componente específico.
 */
@Component({
  standalone: true,
  selector: 'app-admin-legacy',
  imports: [CommonModule, RouterLink],
  template: `
    <div class="page">
      @if (meta(); as m) {
        <header class="page__header">
          <h1>
            <i class="fa" [class]="m.icon" aria-hidden="true"></i>
            {{ m.label }}
          </h1>
          <p class="page__subtitle">{{ m.description }}</p>
        </header>

        <article class="ui-card" [class]="'ui-card--' + m.color">
          <header class="ui-card__header">
            <h2 class="ui-card__title">Próximamente en Angular</h2>
            <p class="ui-card__subtitle">Acceso al CRUD actual en la versión Django.</p>
          </header>
          <div class="ui-card__body">
            <div class="actions">
              @for (s of m.subsections; track s.path) {
                <a [href]="absoluteUrl(s.path)" target="_blank" rel="noopener"
                   class="ui-btn ui-btn--outline">
                  <i class="fa fa-external-link-alt" aria-hidden="true"></i>
                  {{ s.label }}
                </a>
              }
            </div>
            <p>
              <small class="muted">
                Cuando se construyan los endpoints DRF de {{ m.label.toLowerCase() }},
                esta vista se reemplazará por el CRUD completo en Angular.
              </small>
            </p>
          </div>
        </article>
      }
    </div>
  `,
  styles: [`
    @use '../../../styles/tokens' as *;
    :host { display: block; }
    .page { max-width: 900px; margin: 0 auto; }
    .page__header h1 { margin: 0; color: $color-primary; }
    .page__header h1 i { margin-right: $space-2; }
    .page__subtitle { color: $color-text-muted; margin: $space-1 0 $space-4; }
    .actions { display: flex; flex-wrap: wrap; gap: $space-2; margin-bottom: $space-3; }
    .muted { color: $color-text-muted; }
  `],
})
export class AdminLegacyComponent implements OnInit {
  private cfg = inject(ConfigService);
  private route = inject(ActivatedRoute);
  private layout = inject(LayoutService);

  area = signal<AdminArea>('roles');
  meta = computed<AreaMeta | null>(() => AREAS[this.area()] ?? null);

  ngOnInit(): void {
    this.route.paramMap.subscribe((pm) => {
      const a = (pm.get('area') || 'roles') as AdminArea;
      this.area.set(a);
      this.layout.setBreadcrumb([
        { label: 'Inicio', url: '/' },
        { label: 'Administración', url: '/admin' },
        { label: AREAS[a]?.label || a },
      ]);
    });
  }

  absoluteUrl(path: string): string {
    return this.cfg.url(path);
  }
}
