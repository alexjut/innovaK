import { Injectable, computed, signal } from '@angular/core';

/**
 * Estado global del layout: sidebar abierto/cerrado y breadcrumb actual.
 *
 * Cada feature/componente puede:
 *   - llamar `setBreadcrumb([...])` cuando se monta para indicar dónde
 *     está el usuario.
 *   - leer `sidebarOpen()` y `toggleSidebar()` para abrir/cerrar.
 *
 * El servicio es singleton (providedIn: 'root') así que todo el árbol
 * comparte el mismo estado.
 */

export interface BreadcrumbItem {
  label: string;
  /** Si viene, el item es link; si no, es la posición actual. */
  url?: string | null;
}

@Injectable({ providedIn: 'root' })
export class LayoutService {
  /** Visibilidad del sidebar overlay. Default: cerrado. */
  readonly sidebarOpen = signal<boolean>(false);

  /** Ruta de migas. La última no debe llevar url (posición actual). */
  readonly breadcrumb = signal<BreadcrumbItem[]>([]);

  /** Helper: ¿hay breadcrumb visible? */
  readonly hasBreadcrumb = computed(() => this.breadcrumb().length > 0);

  toggleSidebar(): void {
    this.sidebarOpen.update((v) => !v);
  }

  openSidebar(): void {
    this.sidebarOpen.set(true);
  }

  closeSidebar(): void {
    this.sidebarOpen.set(false);
  }

  setBreadcrumb(items: BreadcrumbItem[]): void {
    this.breadcrumb.set(items);
  }

  clearBreadcrumb(): void {
    this.breadcrumb.set([]);
  }
}
