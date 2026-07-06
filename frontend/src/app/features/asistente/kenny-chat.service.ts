import { HttpClient } from '@angular/common/http';
import { Injectable, computed, inject, signal } from '@angular/core';
import { Router } from '@angular/router';
import { ConfigService } from '../../core/config/config.service';
import { MascotStateService } from '../onboarding/mascot-state.service';
import { TourService } from '../onboarding/tour.service';
import {
  ACCIONES,
  KEYWORDS,
  MENU_CHIPS,
  SALUDO_INICIAL,
} from './flujos.data';
import {
  Chip,
  ChatMessage,
  EXPR_A_ESTADO,
  Expr,
  FlujoCtx,
  InputMode,
  RespuestaBot,
  Widgets,
} from './kenny-chat.types';

const TYPING_MS = 700;

/**
 * Motor del asistente KENNY. Estado + interpretación de flujos (DATA). No
 * renderiza: los componentes leen sus signals. Publica la expresión en
 * MascotStateService (una sola mascota) y ejecuta navegación/tours reales.
 */
@Injectable({ providedIn: 'root' })
export class KennyChatService {
  private readonly router = inject(Router);
  private readonly mascot = inject(MascotStateService);
  private readonly tour = inject(TourService);
  private readonly http = inject(HttpClient);
  private readonly cfg = inject(ConfigService);

  readonly open = signal(false);
  readonly showGreeting = signal(true);
  readonly messages = signal<ChatMessage[]>([]);
  readonly typing = signal(false);
  readonly widgets = signal<Widgets>({});
  readonly input = signal('');
  readonly inputMode = signal<InputMode>('free');
  readonly inputPlaceholder = signal('Escribe tu mensaje…');
  readonly listening = signal(false);
  readonly expr = signal<Expr>('alegre');

  private ctx: FlujoCtx = {};
  private timer: ReturnType<typeof setTimeout> | null = null;

  readonly tieneWidgets = computed(() => {
    const w = this.widgets();
    return !!(w.chips?.length || w.cards?.length || w.news?.length);
  });

  // ── Apertura / cierre ──────────────────────────────────────
  abrir(): void {
    this.open.set(true);
    this.showGreeting.set(false);
    if (this.messages().length === 0) this.reiniciar();
  }

  cerrar(): void {
    this.open.set(false);
  }

  descartarSaludo(): void {
    this.showGreeting.set(false);
  }

  reiniciar(): void {
    if (this.timer) clearTimeout(this.timer);
    this.ctx = {};
    this.messages.set([]);
    this.widgets.set({});
    this.inputMode.set('free');
    this.inputPlaceholder.set('Escribe tu mensaje…');
    this.setExpr('alegre');
    this.pushBot(SALUDO_INICIAL, 'alegre', { chips: MENU_CHIPS });
  }

  // ── Interacciones ──────────────────────────────────────────
  elegirChip(c: Chip): void {
    this.pushUser(c.label);
    this.procesar(c.action);
  }

  elegirAccion(action: string, etiqueta: string): void {
    this.pushUser(etiqueta);
    this.procesar(action);
  }

  enviarTexto(): void {
    const txt = this.input().trim();
    if (!txt) return;
    this.input.set('');
    this.pushUser(txt);
    if (this.inputMode() === 'ia') {
      this.consultarIA(txt);
      return;
    }
    this.routeText(txt);
  }

  /** Texto libre → keywords de navegación; sin match, consulta la IA real. */
  routeText(txt: string): void {
    this.ctx.ultimoTexto = txt;
    const match = KEYWORDS.find((k) => k.test.test(txt));
    if (match) {
      this.procesar(match.action);
      return;
    }
    this.consultarIA(txt);
  }

  /** Texto libre → Consulta IA de beneficiarios (lenguaje natural → datos). */
  private consultarIA(q: string): void {
    this.setTyping(true);
    this.http
      .post<QueryResultIA>(this.cfg.url('/dashboard/api/ia/beneficiarios'), { query: q })
      .subscribe({
        next: (r) => this.pushRespuestaIA(r),
        error: (e) => {
          const msg =
            e?.status === 401 || e?.status === 403
              ? 'Para consultar los datos con IA necesitas el módulo de Consulta IA. Mientras tanto, puedo ayudarte con esto:'
              : 'No pude resolver esa consulta. ¿Te muestro el menú?';
          this.pushBot(msg, 'alegre', { chips: MENU_CHIPS });
        },
      });
  }

  private pushRespuestaIA(r: QueryResultIA): void {
    if (!r || !r.ok) {
      this.pushBot(r?.error || 'No entendí bien la pregunta. ¿La reformulas?', 'atento', { chips: MENU_CHIPS });
      return;
    }
    const n = (x: number) => x.toLocaleString('es-CO');
    let texto = r.label ?? 'Esto encontré:';
    if (r.type === 'count') {
      texto = `${r.label ?? 'Resultado'}: ${n(r.count ?? 0)}`;
      if (r.description) texto += `\n${r.description}`;
    } else if (r.type === 'group' && r.rows?.length) {
      const top = r.rows.slice(0, 8).map((x) => `• ${x.categoria}: ${n(x.total)}`).join('\n');
      texto = `${r.label ?? 'Resultado'}:\n${top}`;
      if (r.universo) texto += `\n(sobre ${n(r.universo)} personas)`;
    }
    this.pushBot(texto, 'orgulloso', {
      chips: [
        { label: 'Abrir Consulta IA', action: 'nav:ia', primary: true },
        { label: 'Volver al menú', action: 'menu' },
      ],
    });
  }

  // ── Núcleo: resolver una acción ────────────────────────────
  private procesar(action: string): void {
    const r = ACCIONES[action];
    if (!r) return this.pushBotDiferido('No encontré esa opción.', 'alegre', { chips: MENU_CHIPS });
    this.responder(r);
  }

  private responder(r: RespuestaBot): void {
    this.setTyping(true);
    this.diferido(() => {
      const texto = typeof r.texto === 'function' ? r.texto(this.ctx) : r.texto;
      const widgets = typeof r.widgets === 'function' ? r.widgets(this.ctx) : r.widgets;
      this.pushBot(texto, r.expr, widgets);
      if (r.inputMode) {
        this.inputMode.set(r.inputMode);
        this.inputPlaceholder.set(r.inputPlaceholder ?? 'Escribe…');
      }
      if (r.navegar) {
        this.router.navigate([r.navegar]);
        this.cerrar();
        if (r.lanzarTour) {
          setTimeout(() => this.tour.startTour(r.lanzarTour!, { forzar: true }), 900);
        }
      }
    });
  }

  // ── Voz (Web Speech API) ───────────────────────────────────
  private recognition: any = null;
  readonly vozSoportada =
    typeof window !== 'undefined' &&
    !!((window as any).SpeechRecognition || (window as any).webkitSpeechRecognition);

  iniciarVoz(): void {
    if (!this.vozSoportada) return;
    const SR = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    this.recognition = new SR();
    this.recognition.lang = 'es-CO';
    this.recognition.interimResults = false;
    this.recognition.maxAlternatives = 1;
    this.listening.set(true);
    this.setExpr('atento');
    this.recognition.onresult = (e: any) => {
      const txt = e.results?.[0]?.[0]?.transcript ?? '';
      this.listening.set(false);
      if (txt) {
        this.input.set(txt);
        this.enviarTexto();
      }
    };
    this.recognition.onerror = () => this.listening.set(false);
    this.recognition.onend = () => this.listening.set(false);
    this.recognition.start();
  }

  cancelarVoz(): void {
    try {
      this.recognition?.abort();
    } catch {
      /* noop */
    }
    this.listening.set(false);
  }

  // ── Helpers de estado ──────────────────────────────────────
  private pushUser(text: string): void {
    this.messages.update((m) => [...m, { role: 'user', text }]);
    this.widgets.set({});
  }

  private pushBot(text: string, expr: Expr, widgets?: Widgets): void {
    this.setTyping(false);
    this.setExpr(expr);
    this.messages.update((m) => [...m, { role: 'bot', text, expr }]);
    this.widgets.set(widgets ?? {});
  }

  private pushBotDiferido(text: string, expr: Expr, widgets?: Widgets): void {
    this.setTyping(true);
    this.diferido(() => this.pushBot(text, expr, widgets));
  }

  private setTyping(v: boolean): void {
    this.typing.set(v);
    if (v) this.setExpr('atento');
  }

  private setExpr(e: Expr): void {
    this.expr.set(e);
    this.mascot.setEstado(EXPR_A_ESTADO[e]);
  }

  private diferido(fn: () => void): void {
    if (this.timer) clearTimeout(this.timer);
    this.timer = setTimeout(fn, TYPING_MS);
  }
}

/** Contrato del endpoint /dashboard/api/ia/beneficiarios (Consulta IA). */
interface QueryResultIA {
  ok: boolean;
  type?: 'count' | 'group';
  label?: string;
  description?: string;
  count?: number;
  rows?: { categoria: string; total: number }[];
  universo?: number;
  error?: string;
}

