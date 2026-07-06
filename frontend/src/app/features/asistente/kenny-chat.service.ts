import { Injectable, computed, inject, signal } from '@angular/core';
import { Router } from '@angular/router';
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
    if (this.inputMode() === 'pqrs-asunto') {
      this.inputMode.set('free');
      this.inputPlaceholder.set('Escribe tu mensaje…');
      this.confirmarPqrs(txt);
      return;
    }
    this.routeText(txt);
  }

  /** Texto libre → keywords; sin match, ofrece el menú (hook de IA en task IA). */
  routeText(txt: string): void {
    this.ctx.ultimoTexto = txt;
    const match = KEYWORDS.find((k) => k.test.test(txt));
    if (match) {
      this.procesar(match.action);
      return;
    }
    this.pushBotDiferido(
      'Aún estoy aprendiendo a responder eso. Puedo ayudarte con estas opciones:',
      'alegre',
      { chips: MENU_CHIPS },
    );
  }

  // ── Núcleo: resolver una acción ────────────────────────────
  private procesar(action: string): void {
    // Pasos dinámicos (no están en ACCIONES).
    if (action.startsWith('pqrs:')) return this.pqrsPedirAsunto(action.slice(5));
    if (action.startsWith('cita:dep:')) return this.citaDia(action.slice(9));
    if (action.startsWith('cita:date:')) return this.citaHora(action.slice(10));
    if (action.startsWith('cita:time:')) return this.citaConfirmar(action.slice(10));

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

  // ── PQRS ───────────────────────────────────────────────────
  private pqrsPedirAsunto(tipo: string): void {
    this.ctx.pqrsTipo = tipo;
    this.setTyping(true);
    this.diferido(() => {
      this.pushBot(`Perfecto, una ${tipo}. Describe tu solicitud y la radico.`, 'atento');
      this.inputMode.set('pqrs-asunto');
      this.inputPlaceholder.set(`Describe tu ${tipo.toLowerCase()}…`);
    });
  }

  private confirmarPqrs(_asunto: string): void {
    const rad = 'KEN-' + Math.floor(100000 + Math.random() * 899999);
    this.setTyping(true);
    this.diferido(() => {
      this.pushBot(
        `¡Listo! Radiqué tu ${this.ctx.pqrsTipo}. Número de radicado: ${rad}. Recibirás respuesta en los términos de ley.`,
        'orgulloso',
        { chips: [{ label: 'Radicar otra', action: 'pqrs' }, { label: 'Volver al menú', action: 'menu' }] },
      );
    });
  }

  // ── Cita ───────────────────────────────────────────────────
  private citaDia(dep: string): void {
    this.ctx.citaDep = dep;
    this.setTyping(true);
    this.diferido(() => {
      this.pushBot(`Genial, ${dep}. ¿Qué día te queda bien?`, 'atento', {
        chips: ['Lunes', 'Martes', 'Miércoles', 'Jueves'].map((d) => ({ label: d, action: 'cita:date:' + d })),
      });
    });
  }

  private citaHora(date: string): void {
    this.ctx.citaDate = date;
    this.setTyping(true);
    this.diferido(() => {
      this.pushBot(`${date}. ¿A qué hora?`, 'atento', {
        chips: ['8:00', '10:00', '14:00', '16:00'].map((h) => ({ label: h, action: 'cita:time:' + h })),
      });
    });
  }

  private citaConfirmar(time: string): void {
    this.ctx.citaTime = time;
    const cod = 'CITA-' + Math.floor(1000 + Math.random() * 8999);
    this.setTyping(true);
    this.diferido(() => {
      this.pushBot(
        `¡Cita agendada! 📅\n${this.ctx.citaDep} · ${this.ctx.citaDate} · ${time}\nCódigo: ${cod}`,
        'orgulloso',
        { chips: [{ label: 'Agendar otra', action: 'cita' }, { label: 'Volver al menú', action: 'menu' }] },
      );
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
