import { Injectable, inject, signal } from '@angular/core';
import { driver } from 'driver.js';
import { MascotStateService } from './mascot-state.service';
import { OnboardingApi } from './onboarding.api';
import { TOURS } from './tours.data';

type DriverInstance = ReturnType<typeof driver>;

/**
 * Motor del onboarding. Envuelve driver.js y expone una API estable
 * (startTour/next/prev/skip). No conoce el render de la mascota: solo escribe
 * en MascotStateService. Persiste "completado" por usuario vía OnboardingApi
 * y no repite un tour ya visto (salvo forzar).
 */
@Injectable({ providedIn: 'root' })
export class TourService {
  private readonly api = inject(OnboardingApi);
  private readonly mascot = inject(MascotStateService);

  private drv: DriverInstance | null = null;
  private tourActual: string | null = null;

  private readonly completados = signal<string[]>([]);
  readonly estadoCargado = signal(false);

  /** Lee del backend qué tours ya completó el usuario (llamar tras login). */
  cargarEstado(): void {
    this.api.estado().subscribe({
      next: (r) => {
        this.completados.set(r.completados ?? []);
        this.estadoCargado.set(true);
      },
      error: () => this.estadoCargado.set(true),
    });
  }

  yaCompletado(tourId: string): boolean {
    return this.completados().includes(tourId);
  }

  startTour(tourId: string, opts: { forzar?: boolean } = {}): void {
    const tour = TOURS[tourId];
    if (!tour) return;
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
      this.api.completar(id).subscribe(() => {
        this.completados.update((c) => (c.includes(id) ? c : [...c, id]));
      });
    }
    this.tourActual = null;
    this.drv = null;
  }
}
