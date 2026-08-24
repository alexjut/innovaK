import { provideHttpClient, withInterceptors, withXsrfConfiguration } from '@angular/common/http';
import { ApplicationConfig, importProvidersFrom, provideZoneChangeDetection } from '@angular/core';
import { provideRouter } from '@angular/router';
import {
  LucideAngularModule,
  CalendarCheck, Wallet, PartyPopper, MapPin, Vote, Sparkles, Shield, LayoutDashboard,
  GraduationCap, HandHeart, Package, ClipboardList, Users, FileText, List, Plus, Tags, Settings, Music,
  RotateCcw, ChevronDown, Mic, Send, Building2, BookOpen, HelpCircle, Compass,
  FolderKanban, Gauge, Target, TrendingUp, Coins, Receipt,
  Search, Filter, LayoutGrid, Landmark, Scale,
} from 'lucide-angular';

import { jwtInterceptor } from './core/auth/jwt.interceptor';
import { qrTokenInterceptor } from './core/auth/qr-token.interceptor';
import { routes } from './app.routes';

/**
 * Providers globales del app.
 *
 * - HttpClient con el interceptor JWT registrado (Etapa D PR-1) y el
 *   interceptor del token HMAC de QR públicos (hardening fase 1).
 * - Router con las rutas top-level.
 * - Change detection con coalescing de eventos.
 */
export const appConfig: ApplicationConfig = {
  providers: [
    provideZoneChangeDetection({ eventCoalescing: true }),
    provideRouter(routes),
    // El XSRF va con los nombres de DJANGO, no con los de Angular por
    // omisión (`XSRF-TOKEN` / `X-XSRF-TOKEN`).
    //
    // Por qué hace falta si el SPA manda Bearer: el access token dura 15
    // minutos. Cuando vence y el refresh no alcanza a rescatarlo, la petición
    // sale SIN Authorization y DRF cae a `SessionAuthentication` —la sesión
    // Django sí sigue viva, la crea `MeView`—, que EXIGE CSRF en POST. El
    // usuario veía «CSRF Failed: CSRF token missing» en mitad de un formulario
    // largo, sin ninguna pista de que lo que pasó fue que expiró un token.
    //
    // Con esto, esa caída a sesión funciona en vez de fallar. La cookie la
    // emite `MeView`, que el SPA llama al arrancar.
    provideHttpClient(
      withInterceptors([jwtInterceptor, qrTokenInterceptor]),
      withXsrfConfiguration({ cookieName: 'csrftoken', headerName: 'X-CSRFToken' }),
    ),
    importProvidersFrom(
      LucideAngularModule.pick({
        CalendarCheck, Wallet, PartyPopper, MapPin, Vote, Sparkles, Shield, LayoutDashboard,
        GraduationCap, HandHeart, Package, ClipboardList, Users, FileText, List, Plus, Tags, Settings, Music,
        RotateCcw, ChevronDown, Mic, Send, Building2, BookOpen, HelpCircle, Compass,
        FolderKanban, Gauge, Target, TrendingUp, Coins, Receipt,
        Search, Filter, LayoutGrid, Landmark, Scale,
      }),
    ),
  ],
};
