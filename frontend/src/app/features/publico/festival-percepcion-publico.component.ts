import { HttpClient } from '@angular/common/http';
import { Component, OnInit, inject, signal } from '@angular/core';
import { ActivatedRoute } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { ConfigService } from '../../core/config/config.service';

// ---------------------------------------------------------------------------
// Encuesta de percepción del festival — formulario público (por QR).
// Data-driven: lee GET /festivales/api/percepcion/<slug>/schema/ y renderiza
// por field.type. Se activa solo si el festival está publicado.
// ---------------------------------------------------------------------------

interface CampoDef {
  name: string;
  label: string;
  type: 'text' | 'textarea' | 'select' | 'checkbox';
  required?: boolean;
  options?: string[];
}
interface PercepcionSchema {
  festival: { id: number; nombre: string; tipo?: string | null; vigencia: number; abierto: boolean };
  mensaje?: string | null;
  titulo: string;
  objetivo: string;
  campos: CampoDef[];
}
interface ApiError { detail?: string; errors?: Record<string, string[]>; }

@Component({
  standalone: true,
  selector: 'app-festival-percepcion-publico',
  imports: [FormsModule],
  template: `
    @if (cargando()) {
      <div class="loading-wrap" role="status"><div class="loading-spinner"></div><p>Cargando encuesta…</p></div>
    }

    @if (!cargando() && cerrado()) {
      <div class="estado-wrap"><div class="estado-card estado-card--cerrado">
        <div class="estado-icono"><i class="fa fa-lock"></i></div>
        <h1 class="estado-titulo">Encuesta no disponible</h1>
        <p class="estado-msg">{{ cerradoMsg() }}</p>
        <div class="estado-brand"><span aria-hidden="true">🏛</span> Alcaldía Local de Kennedy</div>
      </div></div>
    }

    @if (!cargando() && !cerrado() && errorCarga()) {
      <div class="estado-wrap"><div class="estado-card">
        <div class="estado-icono"><i class="fa fa-exclamation-triangle"></i></div>
        <h1 class="estado-titulo">Error al cargar</h1>
        <p class="estado-msg">{{ errorCarga() }}</p>
        <button class="btn-brand" (click)="cargar()"><i class="fa fa-refresh"></i> Reintentar</button>
      </div></div>
    }

    @if (!cargando() && exito()) {
      <div class="estado-wrap"><div class="estado-card estado-card--exito">
        <div class="exito-check"><svg viewBox="0 0 80 80" xmlns="http://www.w3.org/2000/svg">
          <circle cx="40" cy="40" r="40" fill="#DCFCE7"/>
          <path d="M24 40l12 12 20-24" stroke="#16A34A" stroke-width="4" fill="none" stroke-linecap="round" stroke-linejoin="round"/></svg></div>
        <h1 class="exito-titulo">¡Gracias por participar!</h1>
        <p class="exito-desc">Tu percepción ayuda a fortalecer la cultura en Kennedy.</p>
        <div class="estado-brand"><span aria-hidden="true">🏛</span> Alcaldía Local de Kennedy</div>
      </div></div>
    }

    @if (!cargando() && !cerrado() && !errorCarga() && !exito() && schema()) {
      <header class="form-header">
        <div class="form-banner">
          <div class="form-banner__left">
            <div class="form-banner__escudo">🏛</div>
            <div>
              <p class="form-banner__institucion">Alcaldía Local de Kennedy · Cultura</p>
              <h1 class="form-banner__titulo">{{ schema()!.titulo }}</h1>
            </div>
          </div>
          <div class="form-banner__badge"><i class="fa fa-masks-theater"></i></div>
        </div>
        <div class="form-header__evento"><i class="fa fa-music"></i> {{ schema()!.festival.nombre }}
          @if (schema()!.festival.tipo) { <span class="form-header__fecha">· {{ schema()!.festival.tipo }}</span> }
        </div>
      </header>

      @if (erroresServidor().length) {
        <div class="server-errors" role="alert"><i class="fa fa-exclamation-circle"></i>
          <div><strong>Corrige antes de enviar:</strong><ul>@for (e of erroresServidor(); track e) { <li>{{ e }}</li> }</ul></div>
        </div>
      }

      <main class="form-main">
        @if (schema()!.objetivo) { <p class="objetivo">{{ schema()!.objetivo }}</p> }
        <div class="card">
          @for (campo of schema()!.campos; track campo.name) {
            <div class="field" [class.field--required]="campo.required">
              <label class="field__label" [attr.for]="campo.name">
                {{ campo.label }} @if (!campo.required) { <span class="field__optional">opcional</span> }
              </label>

              @switch (campo.type) {
                @case ('textarea') {
                  <textarea [id]="campo.name" class="field__input" rows="3"
                            [ngModel]="form[campo.name]" (ngModelChange)="set(campo.name,$event)"></textarea>
                }
                @case ('select') {
                  <select [id]="campo.name" class="field__select"
                          [ngModel]="form[campo.name]" (ngModelChange)="set(campo.name,$event)">
                    <option value="">Selecciona…</option>
                    @for (opt of campo.options ?? []; track opt) { <option [value]="opt">{{ opt }}</option> }
                  </select>
                }
                @case ('checkbox') {
                  <label class="check"><input type="checkbox" [ngModel]="form[campo.name]" (ngModelChange)="set(campo.name,$event)"> Acepto</label>
                }
                @default {
                  <input [id]="campo.name" type="text" class="field__input"
                         [ngModel]="form[campo.name]" (ngModelChange)="set(campo.name,$event)">
                }
              }
              @if (fieldError(campo.name)) { <p class="field__error" role="alert">{{ fieldError(campo.name) }}</p> }
            </div>
          }
        </div>

        <div class="form-submit-wrap">
          <button type="button" class="btn-brand btn-submit" (click)="enviar()" [disabled]="enviando()">
            @if (enviando()) { Enviando… } @else { <i class="fa fa-paper-plane"></i> Enviar respuesta }
          </button>
        </div>
      </main>
    }
  `,
  styles: [`
    @use '../../../styles/tokens' as *;
    $rojo: #D6001C;
    $amarillo: #FFC72C;
    $grad: linear-gradient(135deg, #B50015 0%, #D6001C 60%, #FF1F38 100%);
    :host { display:block; background:$color-bg-subtle; min-height:100vh; font-family:$font-family-base; }
    .loading-wrap { display:flex; flex-direction:column; align-items:center; justify-content:center; min-height:100vh; gap:$space-4; color:$color-text-muted; }
    .loading-spinner { width:44px; height:44px; border:4px solid $color-border; border-top-color:$rojo; border-radius:50%; animation:spin .8s linear infinite; }
    .estado-wrap { display:flex; align-items:center; justify-content:center; min-height:100vh; padding:$space-6; }
    .estado-card { background:$color-bg; border-radius:$radius-2xl; padding:$space-10 $space-8; text-align:center; max-width:480px; width:100%; box-shadow:$shadow-lg;
      &--cerrado { border-top:6px solid $rojo; } &--exito { border-top:6px solid $color-success; } }
    .estado-icono { font-size:3.5rem; margin-bottom:$space-4; color:$rojo; }
    .estado-titulo { font-size:$font-size-2xl; font-weight:$font-weight-bold; margin:0 0 $space-3; }
    .estado-msg { color:$color-text; margin-bottom:$space-4; }
    .estado-brand { display:inline-flex; gap:$space-2; font-size:$font-size-xs; color:$color-text-muted; font-weight:$font-weight-semibold; }
    .exito-check { width:80px; height:80px; margin:0 auto $space-5; svg{width:100%;height:100%;} }
    .exito-titulo { font-size:$font-size-2xl; font-weight:$font-weight-bold; color:$color-success; margin:0 0 $space-3; }
    .exito-desc { margin-bottom:$space-4; }
    .form-header { background:$color-bg; box-shadow:$shadow-sm; position:sticky; top:0; z-index:$z-sticky; }
    .form-banner { display:flex; align-items:center; justify-content:space-between; background:$grad; color:#fff; padding:$space-5; gap:$space-3; border-bottom:4px solid $amarillo; }
    .form-banner__left { display:flex; align-items:center; gap:$space-3; }
    .form-banner__escudo { font-size:2.2rem; }
    .form-banner__institucion { font-size:$font-size-xs; opacity:.85; margin:0 0 $space-1; }
    .form-banner__titulo { font-size:$font-size-lg; font-weight:$font-weight-bold; margin:0; }
    .form-banner__badge { font-size:2.2rem; opacity:.3; }
    .form-header__evento { display:flex; align-items:center; gap:$space-2; padding:$space-2 $space-5; font-size:$font-size-xs; color:$color-text-muted; border-bottom:1px solid $color-border; }
    .form-header__fecha { color:$rojo; font-weight:$font-weight-semibold; }
    .server-errors { display:flex; gap:$space-3; background:$color-danger-bg; border-left:4px solid $color-danger; border-radius:$radius-md; padding:$space-4; margin:$space-4 $space-4 0; color:$color-danger; font-size:$font-size-sm; ul{margin:$space-2 0 0; padding-left:$space-5;} }
    .form-main { max-width:100%; margin:0 auto; padding:$space-4; @media (min-width:#{$bp-md}) { max-width:680px; padding:$space-6 $space-4; } }
    .objetivo { color:$color-text-muted; font-size:$font-size-sm; margin:0 0 $space-4; padding-left:$space-3; border-left:3px solid $amarillo; }
    .card { background:$color-bg; border:1.5px solid $color-border; border-radius:$radius-xl; padding:$space-5; box-shadow:$shadow-sm; }
    .field { margin-bottom:$space-4; &--required .field__label::after { content:' *'; color:$rojo; font-weight:$font-weight-bold; } }
    .field__label { display:block; font-size:$font-size-sm; font-weight:$font-weight-semibold; margin-bottom:$space-2; }
    .field__optional { font-size:$font-size-xs; font-weight:$font-weight-regular; color:$color-text-muted; margin-left:$space-1; }
    .field__input, .field__select { display:block; width:100%; min-height:$touch-target-min; padding:$space-3 $space-4; font-size:$font-size-base; font-family:$font-family-base; color:$color-text; background:$color-bg; border:1.5px solid $color-border-strong; border-radius:$radius-lg;
      &:focus { outline:none; border-color:$rojo; box-shadow:0 0 0 3px rgba($rojo,.15); } }
    textarea.field__input { resize:vertical; }
    .field__error { color:$color-danger; font-size:$font-size-xs; margin:$space-1 0 0; }
    .check { display:flex; align-items:flex-start; gap:$space-2; padding:$space-3; background:$color-secondary-bg; border:1.5px solid $color-secondary; border-radius:$radius-lg; input{width:22px;height:22px;accent-color:$rojo;flex:0 0 auto;} }
    .form-submit-wrap { text-align:center; padding:$space-6 0 $space-10; }
    .btn-brand { display:inline-flex; align-items:center; justify-content:center; gap:$space-2; min-height:$touch-target-min; padding:$space-3 $space-6; background:$grad; color:#fff; border:none; border-radius:$radius-lg; font-size:$font-size-base; font-weight:$font-weight-semibold; cursor:pointer; box-shadow:0 4px 14px rgba($rojo,.35); &[disabled]{opacity:.65;cursor:not-allowed;} }
    .btn-submit { width:100%; max-width:400px; font-size:$font-size-md; padding:$space-4 $space-8; border-radius:$radius-xl; }
    @keyframes spin { to { transform:rotate(360deg); } }
  `],
})
export class FestivalPercepcionPublicoComponent implements OnInit {
  private route = inject(ActivatedRoute);
  private http = inject(HttpClient);
  private cfg = inject(ConfigService);

  cargando = signal(true);
  errorCarga = signal('');
  cerrado = signal(false);
  cerradoMsg = signal('');
  exito = signal(false);
  enviando = signal(false);
  schema = signal<PercepcionSchema | null>(null);

  private erroresCampo = signal<Record<string, string[]>>({});
  erroresServidor = signal<string[]>([]);

  form: Record<string, any> = {};

  ngOnInit(): void { this.cargar(); }

  private slug(): string { return this.route.snapshot.paramMap.get('slug') ?? ''; }

  cargar(): void {
    this.cargando.set(true); this.errorCarga.set(''); this.cerrado.set(false);
    this.http.get<PercepcionSchema>(this.cfg.url(`/festivales/api/percepcion/${this.slug()}/schema/`)).subscribe({
      next: (d) => {
        if (!d.festival?.abierto) { this.cerrado.set(true); this.cerradoMsg.set(d.mensaje || 'Esta encuesta no está disponible.'); this.cargando.set(false); return; }
        this.schema.set(d); this.cargando.set(false);
      },
      error: (err) => {
        this.cargando.set(false);
        if (err.status === 404) { this.cerrado.set(true); this.cerradoMsg.set(err.error?.detail || 'Este festival no está publicado.'); return; }
        this.errorCarga.set(err.error?.detail || 'No se pudo cargar la encuesta.');
      },
    });
  }

  set(name: string, value: any): void { this.form[name] = value; }

  fieldError(name: string): string { const e = this.erroresCampo()[name]; return e?.length ? e[0] : ''; }

  private validar(): boolean {
    const faltan = (this.schema()?.campos ?? []).filter((c) => c.required && !String(this.form[c.name] ?? '').trim());
    if (faltan.length) {
      const errs: Record<string, string[]> = {};
      faltan.forEach((c) => (errs[c.name] = ['Este campo es obligatorio.']));
      this.erroresCampo.set(errs);
      this.erroresServidor.set(['Completa los campos obligatorios (incluida la autorización de datos).']);
      window.scrollTo({ top: 0, behavior: 'smooth' });
      return false;
    }
    return true;
  }

  enviar(): void {
    if (!this.validar()) return;
    this.enviando.set(true); this.erroresCampo.set({}); this.erroresServidor.set([]);
    const payload: Record<string, any> = {};
    for (const [k, v] of Object.entries(this.form)) {
      if (v !== null && v !== undefined && v !== '') payload[k] = typeof v === 'boolean' ? (v ? 'true' : '') : v;
    }
    this.http.post<{ id: number }>(this.cfg.url(`/festivales/api/percepcion/${this.slug()}/`), payload).subscribe({
      next: () => { this.enviando.set(false); this.exito.set(true); window.scrollTo({ top: 0, behavior: 'smooth' }); },
      error: (err) => {
        this.enviando.set(false);
        const body = err.error as ApiError | null;
        if (err.status === 410) { this.cerrado.set(true); this.cerradoMsg.set(body?.detail || 'La encuesta se cerró.'); return; }
        if (err.status === 400 && body?.errors) {
          this.erroresCampo.set(body.errors);
          this.erroresServidor.set(Object.entries(body.errors).map(([, v]) => v[0]));
        } else { this.erroresServidor.set([body?.detail || 'Error al enviar.']); }
        window.scrollTo({ top: 0, behavior: 'smooth' });
      },
    });
  }
}
