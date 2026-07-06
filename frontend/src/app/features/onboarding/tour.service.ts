import { Injectable, PLATFORM_ID, inject, signal } from '@angular/core';
import { isPlatformBrowser } from '@angular/common';
import { driver } from 'driver.js';
import { MascotStateService } from './mascot-state.service';
import { OnboardingApi } from './onboarding.api';
import { TOURS } from './tours.data';

type DriverInstance = ReturnType<typeof driver>;

const LS_KEY = 'kenny_tours_completados';

/**
 * Motor del onboarding. Envuelve driver.js y expone una API estable
 * (startTour/next/prev/skip). No conoce el render de la mascota: solo escribe
 * en MascotStateService. Persiste "completado" por usuario en el backend
 * (fuente de verdad) con respaldo en localStorage, y no repite un tour ya
 * visto (salvo forzar).
 */
@Injectable({ providedIn: 'root' })
export class TourService {
  private readonly api = inject(OnboardingApi);
  private readonly mascot = inject(MascotStateService);
  private readonly esBrowser = isPlatformBrowser(inject(PLATFORM_ID));

  private drv: DriverInstance | null = null;
  private tourActual: string | null = null;

  private readonly completados = signal<string[]>([]);

  yaCompletado(tourId: string): boolean {
    return this.completados().includes(tourId);
  }

  /**
   * Arranca el tour si el usuario no lo ha visto. Hidrata desde localStorage
   * (sync) y confirma con el backend antes de decidir. Robusto si el endpoint
   * aún no existe (tabla pendiente): cae al respaldo local.
   */
  iniciarSiProcede(tourId: string): void {
    this.completados.set(this.leerLocal());
    if (this.yaCompletado(tourId)) return;

    this.api.estado().subscribe({
      next: (r) => {
        const union = new Set([...(r.completados ?? []), ...this.leerLocal()]);
        this.completados.set([...union]);
        if (!this.yaCompletado(tourId)) this.startTour(tourId);
      },
      error: () => {
        if (!this.yaCompletado(tourId)) this.startTour(tourId);
      },
    });
  }

  startTour(tourId: string, opts: { forzar?: boolean } = {}): void {
    const tour = TOURS[tourId];
    if (!tour || !this.esBrowser) return;
    if (!opts.forzar && this.yaCompletado(tourId)) return;

    this.tourActual = tourId;
    this.mascot.mostrar('saludo', tour.saludo ?? '');

    this.drv = driver({
      showProgress: true,
      nextBtnText: 'Siguiente',
      prevBtnText: 'Atrás',
      doneBtnText: 'Listo',
      steps: tour.pasos.map((p) => ({
        element: p.selector,
        popover: {
          description: p.texto,
          side: p.posicion === 'over' ? undefined : p.posicion,
          align: 'start',
        },
        onHighlightStarted: () => {
          this.mascot.setEstado(p.estadoMascota);
          this.mascot.setTexto(p.texto);
        },
      })),
      onDestroyed: () => this.finalizar(),
    });

    this.drv.drive();
  }

  next(): void {
    this.drv?.moveNext();
  }

  prev(): void {
    this.drv?.movePrevious();
  }

  skip(): void {
    this.drv?.destroy();
  }

  private finalizar(): void {
    const id = this.tourActual;
    this.mascot.setEstado('celebrando');
    if (id) {
      this.completados.update((c) => (c.includes(id) ? c : [...c, id]));
      this.guardarLocal(id);
      this.api.completar(id).subscribe({ error: () => {} });
    }
    this.tourActual = null;
    this.drv = null;
    setTimeout(() => this.mascot.ocultar(), 2500);
  }

  private leerLocal(): string[] {
    if (!this.esBrowser) return [];
    try {
      return JSON.parse(localStorage.getItem(LS_KEY) ?? '[]');
    } catch {
      return [];
    }
  }

  private guardarLocal(tourId: string): void {
    if (!this.esBrowser) return;
    const set = new Set([...this.leerLocal(), tourId]);
    localStorage.setItem(LS_KEY, JSON.stringify([...set]));
  }
}
