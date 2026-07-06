import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';
import { ConfigService } from '../../core/config/config.service';

export interface EstadoOnboarding {
  completados: string[];
}

@Injectable({ providedIn: 'root' })
export class OnboardingApi {
  private readonly http = inject(HttpClient);
  private readonly cfg = inject(ConfigService);

  estado(): Observable<EstadoOnboarding> {
    return this.http.get<EstadoOnboarding>(this.cfg.url('/api/onboarding/estado/'));
  }

  completar(tourId: string): Observable<{ tour_id: string; completado: boolean }> {
    return this.http.post<{ tour_id: string; completado: boolean }>(
      this.cfg.url('/api/onboarding/completado/'),
      { tour_id: tourId },
    );
  }
}
