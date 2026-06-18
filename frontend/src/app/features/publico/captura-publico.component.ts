import { HttpClient } from '@angular/common/http';
import { Component, OnInit, inject, signal } from '@angular/core';
import { ActivatedRoute } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { ConfigService } from '../../core/config/config.service';

// ---------------------------------------------------------------------------
// Motor genérico de captura — formulario data-driven.
// Lee el esquema de GET /api/captura/<id>/schema/ y renderiza por field.type.
// Reusable por CULTURA_ORG, ESTIMULO_CULTURAL, PROYECTO_CULTURAL y futuros.
// ---------------------------------------------------------------------------

interface CampoDef {
  name: string;
  label: string;
  type: 'text' | 'textarea' | 'number' | 'money' | 'select' | 'checkbox';
  required?: boolean;
  options?: string[];
  catalogo?: string;
}
interface CatItem { value: string; label: string; }
interface CapturaSchema {
  evento: { id: number; nombre: string; fecha_fin?: string; abierto: boolean };
  tipo_codigo: string;
  titulo: string;
  icono: string;
  campos: CampoDef[];
  catalogos: Record<string, CatItem[]>;
}
interface ApiError { detail?: string; errors?: Record<string, string[]>; }

@Component({
  standalone: true,
  selector: 'app-captura-publico',
  imports: [FormsModule],
  template: `
    @if (cargando()) {
      <div class="loading-wrap" role="status"><div class="loading-spinner"></div><p>Cargando formulario…</p></div>
    }

    @if (!cargando() && cerrado()) {
      <div class="estado-wrap"><div class="estado-card estado-card--cerrado">
        <div class="estado-icono"><i class="fa fa-lock"></i></div>
        <h1 class="estado-titulo">Registro cerrado</h1>
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
        <h1 class="exito-titulo">¡Registro guardado!</h1>
        <p class="exito-desc">La información fue registrada exitosamente.</p>
        @if (exitoId()) { <div class="exito-num"><span class="exito-num__label">Número de registro</span><span class="exito-num__val"># {{ exitoId() }}</span></div> }
        <div class="estado-brand"><span aria-hidden="true">🏛</span> Alcaldía Local de Kennedy</div>
      </div></div>
    }

    @if (!cargando() && !cerrado() && !errorCarga() && !exito() && schema()) {
      <header class="form-header">
        <div class="form-banner">
          <div class="form-banner__left">
            <div class="form-banner__escudo">🏛</div>
            <div>
              <p class="form-banner__institucion">Alcaldía Local de Kennedy · Más Cultura Local</p>
              <h1 class="form-banner__titulo">{{ schema()!.titulo }}</h1>
            </div>
          </div>
          <div class="form-banner__badge"><i class="fa" [class]="schema()!.icono"></i></div>
        </div>
        <div class="form-header__evento"><i class="fa fa-calendar"></i> {{ schema()!.evento.nombre }}
          @if (schema()!.evento.fecha_fin) { <span class="form-header__fecha">· Cierre: {{ schema()!.evento.fecha_fin }}</span> }
        </div>
      </header>

      @if (erroresServidor().length) {
        <div class="server-errors" role="alert"><i class="fa fa-exclamation-circle"></i>
          <div><strong>Corrige antes de enviar:</strong><ul>@for (e of erroresServidor(); track e) { <li>{{ e }}</li> }</ul></div>
        </div>
      }

      <main class="form-main">
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
                    @for (opt of opcionesDe(campo); track opt.value) { <option [value]="opt.value">{{ opt.label }}</option> }
                  </select>
                }
                @case ('checkbox') {
                  <label class="check"><input type="checkbox" [ngModel]="form[campo.name]" (ngModelChange)="set(campo.name,$event)"> Sí</label>
                }
                @case ('money') {
                  <input [id]="campo.name" type="number" inputmode="numeric" step="1000" class="field__input"
                         [ngModel]="form[campo.name]" (ngModelChange)="set(campo.name,$event)" placeholder="0">
                }
                @case ('number') {
                  <input [id]="campo.name" type="number" class="field__input"
                         [ngModel]="form[campo.name]" (ngModelChange)="set(campo.name,$event)">
                }
                @default {
                  <input [id]="campo.name" type="text" class="field__input"
                         [ngModel]="form[campo.name]" (ngModelChange)="set(campo.name,$event)">
                }
              }
              @if (fieldError(campo.name)) { <p class="field__error" role="alert">{{ fieldError(campo.name) }}</p> }
            </div>
          }

          <!-- Firma -->
          <div class="field">
            <label class="field__label">Firma <span class="field__optional">opcional</span></label>
            @if (!firmaPreview()) {
              <label for="firma" class="firma-btn"><i class="fa fa-camera"></i> 📸 Tomar foto de la firma</label>
            } @else {
              <div class="firma-preview"><img [src]="firmaPreview()!" alt="firma"></div>
              <button type="button" class="btn-outline-sm" (click)="quitarFirma()"><i class="fa fa-times"></i> Quitar</button>
            }
            <input id="firma" type="file" accept="image/*" capture="environment" class="oculto" (change)="onFirma($event)">
          </div>
        </div>

        <div class="form-submit-wrap">
          <button type="button" class="btn-brand btn-submit" (click)="enviar()" [disabled]="enviando()">
            @if (enviando()) { Enviando… } @else { <i class="fa fa-paper-plane"></i> Registrar }
          </button>
        </div>
      </main>
    }
  `,
  styles: [`
    @use '../../../styles/tokens' as *;
    $rojo: #D6001C;
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
    .exito-num { display:inline-flex; flex-direction:column; gap:$space-1; background:rgba($rojo,.06); border:2px solid rgba($rojo,.2); border-radius:$radius-xl; padding:$space-4 $space-8; margin-bottom:$space-5; }
    .exito-num__label { font-size:$font-size-xs; color:$color-text-muted; }
    .exito-num__val { font-size:$font-size-2xl; font-weight:$font-weight-bold; color:$rojo; }
    .form-header { background:$color-bg; box-shadow:$shadow-sm; position:sticky; top:0; z-index:$z-sticky; }
    .form-banner { display:flex; align-items:center; justify-content:space-between; background:$grad; color:#fff; padding:$space-5; gap:$space-3; }
    .form-banner__left { display:flex; align-items:center; gap:$space-3; }
    .form-banner__escudo { font-size:2.2rem; }
    .form-banner__institucion { font-size:$font-size-xs; opacity:.85; margin:0 0 $space-1; }
    .form-banner__titulo { font-size:$font-size-lg; font-weight:$font-weight-bold; margin:0; }
    .form-banner__badge { font-size:2.2rem; opacity:.25; }
    .form-header__evento { display:flex; align-items:center; gap:$space-2; padding:$space-2 $space-5; font-size:$font-size-xs; color:$color-text-muted; border-bottom:1px solid $color-border; }
    .form-header__fecha { color:$rojo; font-weight:$font-weight-semibold; }
    .server-errors { display:flex; gap:$space-3; background:$color-danger-bg; border-left:4px solid $color-danger; border-radius:$radius-md; padding:$space-4; margin:$space-4 $space-4 0; color:$color-danger; font-size:$font-size-sm; ul{margin:$space-2 0 0; padding-left:$space-5;} }
    .form-main { max-width:100%; margin:0 auto; padding:$space-4; @media (min-width:#{$bp-md}) { max-width:680px; padding:$space-6 $space-4; } }
    .card { background:$color-bg; border:1.5px solid $color-border; border-radius:$radius-xl; padding:$space-5; box-shadow:$shadow-sm; }
    .field { margin-bottom:$space-4; &--required .field__label::after { content:' *'; color:$rojo; font-weight:$font-weight-bold; } }
    .field__label { display:block; font-size:$font-size-sm; font-weight:$font-weight-semibold; margin-bottom:$space-2; }
    .field__optional { font-size:$font-size-xs; font-weight:$font-weight-regular; color:$color-text-muted; margin-left:$space-1; }
    .field__input, .field__select { display:block; width:100%; min-height:$touch-target-min; padding:$space-3 $space-4; font-size:$font-size-base; font-family:$font-family-base; color:$color-text; background:$color-bg; border:1.5px solid $color-border-strong; border-radius:$radius-lg;
      &:focus { outline:none; border-color:$rojo; box-shadow:0 0 0 3px rgba($rojo,.15); } }
    textarea.field__input { resize:vertical; }
    .field__error { color:$color-danger; font-size:$font-size-xs; margin:$space-1 0 0; }
    .check { display:flex; align-items:center; gap:$space-2; input{width:20px;height:20px;accent-color:$rojo;} }
    .firma-btn { display:flex; align-items:center; justify-content:center; gap:$space-2; width:100%; min-height:80px; padding:$space-5; background:$grad; color:#fff; border:3px dashed rgba(255,255,255,.35); border-radius:$radius-xl; cursor:pointer; font-weight:$font-weight-bold; }
    .firma-preview img { max-width:100%; max-height:200px; border:1.5px solid $color-border; border-radius:$radius-lg; }
    .oculto { position:absolute; left:-9999px; width:1px; height:1px; opacity:0; }
    .btn-outline-sm { margin-top:$space-2; padding:$space-1 $space-3; font-size:$font-size-sm; font-weight:$font-weight-semibold; background:$color-bg; color:$rojo; border:1.5px solid $rojo; border-radius:$radius-lg; cursor:pointer; }
    .form-submit-wrap { text-align:center; padding:$space-6 0 $space-10; }
    .btn-brand { display:inline-flex; align-items:center; justify-content:center; gap:$space-2; min-height:$touch-target-min; padding:$space-3 $space-6; background:$grad; color:#fff; border:none; border-radius:$radius-lg; font-size:$font-size-base; font-weight:$font-weight-semibold; cursor:pointer; box-shadow:0 4px 14px rgba($rojo,.35); &[disabled]{opacity:.65;cursor:not-allowed;} }
    .btn-submit { width:100%; max-width:400px; font-size:$font-size-md; padding:$space-4 $space-8; border-radius:$radius-xl; }
    @keyframes spin { to { transform:rotate(360deg); } }
  `],
})
export class CapturaPublicoComponent implements OnInit {
  private route = inject(ActivatedRoute);
  private http = inject(HttpClient);
  private cfg = inject(ConfigService);

  cargando = signal(true);
  errorCarga = signal('');
  cerrado = signal(false);
  cerradoMsg = signal('');
  exito = signal(false);
  exitoId = signal<number | null>(null);
  enviando = signal(false);
  schema = signal<CapturaSchema | null>(null);

  private erroresCampo = signal<Record<string, string[]>>({});
  erroresServidor = signal<string[]>([]);

  firmaPreview = signal<string | null>(null);
  private firmaFile: File | null = null;

  form: Record<string, any> = {};

  ngOnInit(): void { this.cargar(); }

  private eventoId(): number { return Number(this.route.snapshot.paramMap.get('eventoId') ?? '0'); }

  cargar(): void {
    this.cargando.set(true); this.errorCarga.set(''); this.cerrado.set(false);
    this.http.get<CapturaSchema>(this.cfg.url(`/api/captura/${this.eventoId()}/schema/`)).subscribe({
      next: (d) => {
        if (!d.evento.abierto) { this.cerrado.set(true); this.cerradoMsg.set('Este registro ya no está activo.'); this.cargando.set(false); return; }
        this.schema.set(d); this.cargando.set(false);
      },
      error: (err) => { this.cargando.set(false); this.errorCarga.set(err.error?.detail || 'No se pudo cargar el formulario.'); },
    });
  }

  set(name: string, value: any): void { this.form[name] = value; }

  opcionesDe(campo: CampoDef): CatItem[] {
    if (campo.catalogo) return this.schema()?.catalogos?.[campo.catalogo] ?? [];
    return (campo.options ?? []).map((o) => ({ value: o, label: o }));
  }

  fieldError(name: string): string { const e = this.erroresCampo()[name]; return e?.length ? e[0] : ''; }

  onFirma(ev: Event): void {
    const file = (ev.target as HTMLInputElement).files?.[0];
    if (!file) return;
    if (file.size > 2 * 1024 * 1024) { this.erroresServidor.set(['La firma pesa más de 2 MB.']); return; }
    this.firmaFile = file;
    const reader = new FileReader();
    reader.onload = (e) => this.firmaPreview.set(e.target?.result as string);
    reader.readAsDataURL(file);
  }
  quitarFirma(): void { this.firmaFile = null; this.firmaPreview.set(null); }

  private validar(): boolean {
    const faltan = (this.schema()?.campos ?? []).filter((c) => c.required && !String(this.form[c.name] ?? '').trim());
    if (faltan.length) {
      const errs: Record<string, string[]> = {};
      faltan.forEach((c) => (errs[c.name] = ['Este campo es obligatorio.']));
      this.erroresCampo.set(errs);
      this.erroresServidor.set(['Completa los campos obligatorios.']);
      window.scrollTo({ top: 0, behavior: 'smooth' });
      return false;
    }
    return true;
  }

  enviar(): void {
    if (!this.validar()) return;
    this.enviando.set(true); this.erroresCampo.set({}); this.erroresServidor.set([]);
    const fd = new globalThis.FormData();
    for (const [k, v] of Object.entries(this.form)) {
      if (v !== null && v !== undefined && v !== '') fd.append(k, typeof v === 'boolean' ? (v ? 'true' : '') : String(v));
    }
    if (this.firmaFile) fd.append('firma_imagen', this.firmaFile, this.firmaFile.name);

    this.http.post<{ id: number }>(this.cfg.url(`/api/captura/${this.eventoId()}/`), fd).subscribe({
      next: (r) => { this.enviando.set(false); this.exitoId.set(r.id); this.exito.set(true); window.scrollTo({ top: 0, behavior: 'smooth' }); },
      error: (err) => {
        this.enviando.set(false);
        const body = err.error as ApiError | null;
        if (err.status === 410) { this.cerrado.set(true); this.cerradoMsg.set(body?.detail || 'Cerró mientras llenabas.'); return; }
        if (err.status === 400 && body?.errors) {
          this.erroresCampo.set(body.errors);
          this.erroresServidor.set(Object.entries(body.errors).map(([k, v]) => `${k}: ${v[0]}`));
        } else { this.erroresServidor.set([body?.detail || 'Error al enviar.']); }
        window.scrollTo({ top: 0, behavior: 'smooth' });
      },
    });
  }
}
