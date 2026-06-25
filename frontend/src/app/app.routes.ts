import { Routes } from '@angular/router';
import { authGuard } from './core/auth/auth.guard';
import { AuthLayoutComponent } from './core/layout/auth-layout/auth-layout.component';
import { LayoutComponent } from './core/layout/layout.component';

/**
 * Rutas top-level con dos layouts:
 *   - LayoutComponent: con topbar + sidebar + footer (área autenticada).
 *   - AuthLayoutComponent: gradiente institucional sin menú (login, etc.).
 *
 * El authGuard protege la ruta raíz: si el visitante no tiene token,
 * va a /auth/login automáticamente.
 */
export const routes: Routes = [
  {
    path: '',
    component: LayoutComponent,
    canActivate: [authGuard],
    children: [
      {
        path: '',
        pathMatch: 'full',
        loadComponent: () =>
          import('./features/dashboard/hub.component').then((m) => m.HubComponent),
      },
      {
        path: 'showcase',
        loadComponent: () =>
          import('./features/dashboard/showcase.component').then((m) => m.ShowcaseComponent),
      },
      {
        path: 'landing',
        loadComponent: () =>
          import('./features/dashboard/landing.component').then((m) => m.LandingComponent),
      },
      {
        // Hub central de Actividades. Reorganización: Banco / Jóvenes /
        // Caracterización / Cursos / Eventos NO son cards top-level — son
        // sub-flujos accesibles desde dentro de una actividad según su
        // tipo_evento y subgrupo. El hub Django ya gestiona esa lógica.
        path: 'actividades',
        loadChildren: () =>
          import('./features/actividades/actividades.routes').then(
            (m) => m.ACTIVIDADES_ROUTES,
          ),
      },
      {
        // RBAC B4 — panel operativo por subgrupo (landing del rol operativo).
        // Tronco evento-céntrico: subgrupo → actividad_plan → eventos → contratos.
        path: 'subgrupo',
        loadChildren: () =>
          import('./features/subgrupo/subgrupo.routes').then((m) => m.SUBGRUPO_ROUTES),
      },
      {
        // PR-9 Etapa D: Presupuesto (proyectos, indicadores, CDPs, contratos).
        path: 'presupuesto',
        loadChildren: () =>
          import('./features/presupuesto/presupuesto.routes').then(
            (m) => m.PRESUPUESTO_ROUTES,
          ),
      },

      {
        // Banco de Iniciativas — feature organizador Angular nativo.
        // No es card top-level (decisión 2026-06-01) pero se llega
        // desde Actividades → tipo BANCO_INICIATIVAS → evento → "Beneficiarios".
        path: 'banco',
        loadChildren: () =>
          import('./features/banco-iniciativas/banco.routes').then((m) => m.BANCO_ROUTES),
      },
      {
        // Jóvenes a la E — feature organizador Angular nativo.
        path: 'jovenes',
        loadChildren: () =>
          import('./features/jovenes-a-la-e/jovenes.routes').then((m) => m.JOVENES_ROUTES),
      },
      {
        // Entregas de insumos — organizador Angular nativo.
        // Llega desde Actividades → tipo ENTREGA → evento → "Beneficiarios".
        path: 'entregas',
        loadChildren: () =>
          import('./features/entregas/entregas.routes').then((m) => m.ENTREGAS_ROUTES),
      },
      {
        // Festivales de Cultura (proyecto 2780, Meta 4) — panel de festivales.
        path: 'festivales',
        loadChildren: () =>
          import('./features/festivales/festivales.routes').then((m) => m.FESTIVALES_ROUTES),
      },
      {
        // Infraestructura — contratos de obra (vías + parques) en el Mapa Kennedy.
        path: 'infraestructura',
        loadChildren: () =>
          import('./features/infraestructura/infraestructura.routes').then(
            (m) => m.INFRAESTRUCTURA_ROUTES,
          ),
      },
      {
        // Capturas genéricas (motor data-driven): organizador + insights de
        // CULTURA_ORG / ESTIMULO_CULTURAL / PROYECTO_CULTURAL y tipos futuros.
        path: 'captura',
        loadChildren: () =>
          import('./features/captura/captura.routes').then((m) => m.CAPTURA_ROUTES),
      },
      {
        // Caracterizaciones — feature Angular nativo (hub, list, detail,
        // evento). NO es card top-level pero los enlaces internos llegan
        // aquí: /caracterizacion/evento/<id> desde Actividades.
        path: 'caracterizacion',
        loadChildren: () =>
          import('./features/caracterizacion/caracterizacion.routes')
            .then((m) => m.CARACTERIZACION_ROUTES),
      },
      {
        // PR Cursos: Angular nativo (mis cursos + panel docente).
        path: 'cursos',
        loadChildren: () =>
          import('./features/cursos/cursos.routes').then((m) => m.CURSOS_ROUTES),
      },
      {
        // Eventos — listado y editor Angular nativo.
        path: 'eventos',
        loadChildren: () =>
          import('./features/eventos/eventos.routes').then((m) => m.EVENTOS_ROUTES),
      },
      {
        // PR-12 Etapa D: Mapa Kennedy (iframe al mapa Django).
        path: 'mapa',
        loadChildren: () =>
          import('./features/mapa/mapa.routes').then((m) => m.MAPA_ROUTES),
      },
      {
        // PR-13 Etapa D: Administración (roles, organización, personas).
        path: 'admin',
        loadChildren: () =>
          import('./features/admin/admin.routes').then((m) => m.ADMIN_ROUTES),
      },
      {
        // PR-14 Etapa D: Votaciones (organizador).
        path: 'votaciones',
        loadChildren: () =>
          import('./features/votaciones/votaciones.routes').then((m) => m.VOTACIONES_ROUTES),
      },
      {
        // Consulta IA: lenguaje natural sobre beneficiarios.
        path: 'ia',
        loadComponent: () =>
          import('./features/ia/ia.component').then((m) => m.IaComponent),
      },
      {
        // Tablero analítico de beneficiarios (Power BI style).
        path: 'analitica',
        loadComponent: () =>
          import('./features/ia/analitica.component').then((m) => m.AnaliticaComponent),
      },
      {
        // Mi perfil + cambiar contraseña.
        path: 'perfil',
        loadComponent: () =>
          import('./features/perfil/perfil.component').then((m) => m.PerfilComponent),
      },
    ],
  },

  // Rutas sin sidebar/topbar (login, reset, etc.).
  {
    path: 'auth',
    component: AuthLayoutComponent,
    children: [
      {
        path: 'login',
        loadComponent: () =>
          import('./features/auth/login.component').then((m) => m.LoginComponent),
      },
    ],
  },

  // Compat: /login → /auth/login.
  { path: 'login', redirectTo: 'auth/login', pathMatch: 'full' },

  // ── PÚBLICO (SIN authGuard) ───────────────────────────────────────
  // Formularios que llena el ciudadano por QR (Banco, caracterización,
  // Jóvenes) y vistas públicas (mapa). NO requieren login.
  {
    path: 'p',
    loadChildren: () =>
      import('./features/publico/publico.routes').then((m) => m.PUBLICO_ROUTES),
  },

  // Fallback.
  { path: '**', redirectTo: '' },
];
