import { Routes } from '@angular/router';

/**
 * Rutas PÚBLICAS (sin authGuard). Las llena el ciudadano por QR sin login.
 * Endpoints DRF AllowAny. Importante (Alex 2026-06-04): mantener público.
 */
export const PUBLICO_ROUTES: Routes = [
  {
    // Formulario público de inscripción al Banco de Iniciativas.
    path: 'banco/:eventoId',
    loadComponent: () =>
      import('./banco-publico.component').then((m) => m.BancoPublicoComponent),
  },
  {
    // Formulario público de caracterización ciudadana (6 sectores dinámicos).
    // Sin authGuard — lo llena el ciudadano por QR sin login.
    path: 'caracterizacion/:eventoId',
    loadComponent: () =>
      import('./caracterizacion-publico.component').then(
        (m) => m.CaracterizacionPublicoComponent,
      ),
  },
  {
    // Formulario público de beca Jóvenes a la E.
    // Sin authGuard — lo llena el beneficiario por QR sin login.
    path: 'jovenes/:eventoId',
    loadComponent: () =>
      import('./jovenes-publico.component').then(
        (m) => m.JovenesPublicoComponent,
      ),
  },
  {
    // Formulario público de entrega de insumos/utensilios.
    // Sin authGuard — lo llena el beneficiario por QR sin login.
    path: 'entrega/:eventoId',
    loadComponent: () =>
      import('./entregas-publico.component').then(
        (m) => m.EntregasPublicoComponent,
      ),
  },
  {
    // Formulario público de inscripción genérica de participante a un evento
    // (flujo por defecto, eventos sin tipo de captura específico).
    // Sin authGuard — lo llena el participante por QR sin login.
    path: 'inscripcion/:eventoId',
    loadComponent: () =>
      import('./inscripcion-publico.component').then(
        (m) => m.InscripcionPublicoComponent,
      ),
  },
  {
    // Confirmación pública de llegada a terreno (INFO_TERRENO): GPS + fotos.
    // Sin authGuard — la confirma el funcionario por QR desde el celular.
    path: 'info-terreno/:eventoId',
    loadComponent: () =>
      import('./info-terreno-publico.component').then(
        (m) => m.InfoTerrenoPublicoComponent,
      ),
  },
];
