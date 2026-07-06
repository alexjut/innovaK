import { provideHttpClient, withInterceptors } from '@angular/common/http';
import { ApplicationConfig, importProvidersFrom, provideZoneChangeDetection } from '@angular/core';
import { provideRouter } from '@angular/router';
import {
  LucideAngularModule,
  CalendarCheck, Wallet, PartyPopper, MapPin, Vote, Sparkles, Shield, LayoutDashboard,
  GraduationCap, HandHeart, Package, ClipboardList, Users, FileText, List, Plus, Tags, Settings, Music,
  RotateCcw, ChevronDown, Mic, Send, Building2, BookOpen, HelpCircle, Compass,
  FolderKanban, Gauge, Target, TrendingUp, Coins, Receipt,
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
    provideHttpClient(withInterceptors([jwtInterceptor, qrTokenInterceptor])),
    importProvidersFrom(
      LucideAngularModule.pick({
        CalendarCheck, Wallet, PartyPopper, MapPin, Vote, Sparkles, Shield, LayoutDashboard,
        GraduationCap, HandHeart, Package, ClipboardList, Users, FileText, List, Plus, Tags, Settings, Music,
        RotateCcw, ChevronDown, Mic, Send, Building2, BookOpen, HelpCircle, Compass,
        FolderKanban, Gauge, Target, TrendingUp, Coins, Receipt,
      }),
    ),
  ],
};
