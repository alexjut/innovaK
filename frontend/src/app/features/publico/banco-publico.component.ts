import { HttpClient } from '@angular/common/http';
import { Component, OnInit, inject, signal, computed } from '@angular/core';
import { ActivatedRoute } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { ConfigService } from '../../core/config/config.service';

// ---------------------------------------------------------------------------
// Tipos del catálogo devuelto por GET /banco-iniciativas/api/publico/<id>/catalogos/
// ---------------------------------------------------------------------------

interface CatalogoItem {
  codigo: string | number;
  nombre: string;
}

interface EscenarioItem {
  codigo: string | number;
  nombre: string;
  categoria_pot?: string;
}

interface RangoEtarioItem {
  codigo: string | number;
  nombre: string;
  edad_min?: number;
  edad_max?: number;
}

interface ImplementoItem {
  codigo: string | number;
  nombre: string;
  categoria?: string;
}

interface ImpactoChoice {
  valor: string;
  etiqueta: string;
}

interface BancoCatalogos {
  evento: { id: number; nombre: string; fecha_fin?: string };
  tipos_organizacion: CatalogoItem[];
  tipos_documento: CatalogoItem[];
  rangos_experiencia: CatalogoItem[];
  niveles_educativos: CatalogoItem[];
  upls: CatalogoItem[];
  barrios: CatalogoItem[];
  escenarios: EscenarioItem[];
  rangos_poblacion: CatalogoItem[];
  caracteristicas_poblacion: CatalogoItem[];
  rangos_etarios: RangoEtarioItem[];
  enfoques_diferenciales: CatalogoItem[];
  tipos_beneficio_alk: CatalogoItem[];
  disciplinas_deportivas: CatalogoItem[];
  implementos: ImplementoItem[];
  estratos: number[];
  impacto_politicas_choices: ImpactoChoice[];
}

interface ApiError {
  detail?: string;
  errors?: Record<string, string[]>;
}

// ---------------------------------------------------------------------------
// Tipos del modelo del formulario (estado interno del wizard)
// ---------------------------------------------------------------------------

interface FormData {
  // Paso 1 — Organización
  nombre_organizacion: string;
  tipo_organizacion: string;
  numero_soporte_legal: string;
  soporte_legal_url: string;
  correo: string;
  telefono: string;
  redes_facebook: string;
  redes_instagram: string;
  redes_otra: string;
  upl: string;
  barrio: string;          // M-02: select legacy (sin uso en el wizard)
  barrio_texto: string;    // M-02: barrio como texto libre (lo que se envía)
  direccion: string;
  // Paso 2 — Representante
  rep_tipo_doc: string;
  rep_numero_doc: string;
  rep_nombre1: string;
  rep_nombre2: string;
  rep_apellido1: string;
  rep_apellido2: string;
  // Paso 3 — Experiencia / formación
  anios_experiencia: string;
  nivel_educativo: string;
  titulos_obtenidos: string;
  // Paso 4 — Ubicación (ya en paso 1 para organización)
  // Paso 5 — Escenarios
  escenarios: Set<string>;
  escenarios_actuales: Set<string>;
  // Paso 6 — Población
  rango_poblacion: string;
  estrato: string;
  caracteristica_pob: string;
  rango_etarios: Set<string>;
  enfoques: Set<string>;
  // Paso 7 — Beneficios ALK + impacto + propuesta
  beneficiada_alk: boolean;
  beneficios_alk: Set<string>;
  uso_beneficio: string;
  impacto_politicas: string;
  impacto_justificacion: string;
  disciplina_principal: string;
  otros_deportes: string;
  implementos: Set<string>;
  propuesta_url: string;
  propuesta_descripcion: string;
  // Paso 8 — Firma + compromisos
  compromiso_redes: boolean;
  compromiso_carta_1ano: boolean;
  compromiso_actualizacion: boolean;
  firma_cedula: string;
  firma_fecha: string;
  firma_imagen: File | null;
  firma_imagen_url: string;  // B-04: alternativa por URL de Drive (escritorio)
}

// ---------------------------------------------------------------------------
// Helpers de agrupación de escenarios por categoría
// ---------------------------------------------------------------------------

interface EscenarioGrupo {
  categoria: string;
  items: EscenarioItem[];
}

// B-01: mapa valor técnico (categoria_pot) → etiqueta legible. El ciudadano
// nunca debe ver "red_proximidad" y similares.
const CATEGORIA_POT_LABELS: Record<string, string> = {
  red_estructurante: 'Red estructurante (parques metropolitanos y zonales)',
  red_proximidad: 'Red de proximidad (parques vecinales y de bolsillo)',
  otros_dotacionales: 'Otros espacios dotacionales y ambientales',
  otros_practica: 'Otros espacios de práctica',
};

function labelCategoriaPot(valor: string | null | undefined): string {
  if (!valor) return 'Otros espacios';
  return CATEGORIA_POT_LABELS[valor] ?? valor;
}

function groupEscenarios(escenarios: EscenarioItem[]): EscenarioGrupo[] {
  const map = new Map<string, EscenarioItem[]>();
  for (const e of escenarios) {
    const cat = e.categoria_pot || 'otros';
    if (!map.has(cat)) map.set(cat, []);
    map.get(cat)!.push(e);
  }
  // `categoria` ya sale como etiqueta legible (B-01).
  return Array.from(map.entries())
    .map(([clave, items]) => ({ categoria: labelCategoriaPot(clave), items }));
}

// ---------------------------------------------------------------------------
// Definición de pasos del wizard
// ---------------------------------------------------------------------------

const PASO_LABELS = [
  'Organización',
  'Representante',
  'Experiencia',
  'Escenarios',
  'Población',
  'Beneficios ALK',
  'Propuesta',
  'Firma',
] as const;

const TOTAL_PASOS = PASO_LABELS.length;

// ---------------------------------------------------------------------------
// Componente
// ---------------------------------------------------------------------------

@Component({
  standalone: true,
  selector: 'app-banco-publico',
  imports: [FormsModule],
  template: `
    <!-- ══ PÁGINA: CONVOCATORIA CERRADA ══ -->
    @if (cerrado()) {
      <div class="cerrado-wrap">
        <div class="cerrado-card">
          <div class="cerrado-icon" aria-hidden="true">🔒</div>
          <h1 class="cerrado-title">Convocatoria cerrada</h1>
          <p class="cerrado-msg">{{ cerradoMsg() }}</p>
          <p class="cerrado-sub">
            Esta convocatoria ya no acepta nuevas postulaciones.
            Contacta a la Alcaldía Local de Kennedy para más información.
          </p>
        </div>
      </div>
    }

    <!-- ══ PÁGINA: CARGANDO CATÁLOGOS ══ -->
    @if (!cerrado() && cargandoCatalogos()) {
      <div class="loading-wrap" role="status" aria-live="polite">
        <div class="loading-spinner" aria-hidden="true"></div>
        <p>Cargando formulario…</p>
      </div>
    }

    <!-- ══ PÁGINA: ERROR AL CARGAR ══ -->
    @if (!cerrado() && !cargandoCatalogos() && errorCarga()) {
      <div class="error-wrap" role="alert">
        <div class="error-card">
          <div class="error-icon" aria-hidden="true">⚠️</div>
          <h1>Error al cargar</h1>
          <p>{{ errorCarga() }}</p>
          <button class="btn-brand btn-lg" (click)="cargarCatalogos()">
            Reintentar
          </button>
        </div>
      </div>
    }

    <!-- ══ PÁGINA: ÉXITO ══ -->
    @if (exito()) {
      <div class="exito-wrap">
        <div class="exito-card">
          <div class="exito-icono" aria-hidden="true">
            <svg viewBox="0 0 80 80" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
              <circle cx="40" cy="40" r="40" fill="#DCFCE7"/>
              <path d="M24 40l12 12 20-24" stroke="#16A34A" stroke-width="4"
                    stroke-linecap="round" stroke-linejoin="round"/>
            </svg>
          </div>
          <h1 class="exito-title">¡Postulación enviada!</h1>
          <p class="exito-desc">
            Tu postulación fue registrada exitosamente.
          </p>
          @if (exitoId()) {
            <div class="exito-num">
              <span class="exito-num__label">Número de postulación</span>
              <span class="exito-num__val"># {{ exitoId() }}</span>
            </div>
          }
          <p class="exito-footer">
            Guarda este número. El equipo de la Alcaldía Local de Kennedy
            revisará tu postulación y te contactará.
          </p>
        </div>
      </div>
    }

    <!-- ══ PASO 0: BIENVENIDA (U-01, sin campos de datos) ══ -->
    @if (!cerrado() && !cargandoCatalogos() && !errorCarga() && !exito() && catalogos() && intro()) {
      <div class="intro">
        <div class="wiz-banner">
          <div class="wiz-banner__icon" aria-hidden="true">🏆</div>
          <div>
            <h1 class="wiz-banner__title">Banco de Iniciativas Recreodeportivas</h1>
            <p class="wiz-banner__sub">{{ catalogos()!.evento.nombre }}</p>
          </div>
        </div>

        <div class="intro__card">
          <p class="intro__lead">
            Bienvenido(a). Este formulario registra tu iniciativa recreo-deportiva
            ante la Alcaldía Local de Kennedy. El proceso tiene <strong>dos fases</strong>:
            (1) esta postulación en línea y (2) la revisión por parte del equipo de Deportes.
          </p>

          <ul class="intro__list">
            <li>⏱️ Tiempo estimado: <strong>30 a 45 minutos</strong>.</li>
            <li>💻 Recomendamos diligenciarlo desde un <strong>computador de escritorio</strong> con <strong>internet estable</strong>.</li>
            <li>📎 Los soportes se adjuntan como <strong>enlace de Google Drive</strong> (no se suben archivos).</li>
          </ul>

          <p class="intro__docs-title">Ten listos, como enlace de Drive:</p>
          <ul class="intro__list">
            <li>Cédula del representante legal.</li>
            <li>RUT / NIT, o Reconocimiento Deportivo, o Aval, según tu tipo de organización.</li>
            <li>Documento técnico de la propuesta.</li>
          </ul>

          <button type="button" class="wiz-nav__btn wiz-nav__btn--next intro__btn" (click)="comenzar()">
            Comenzar →
          </button>
        </div>
      </div>
    }

    <!-- ══ WIZARD ══ -->
    @if (!cerrado() && !cargandoCatalogos() && !errorCarga() && !exito() && catalogos() && !intro()) {
      <!-- Header fijo -->
      <header class="wiz-header" role="banner">
        <div class="wiz-banner">
          <div class="wiz-banner__icon" aria-hidden="true">🏆</div>
          <div>
            <h1 class="wiz-banner__title">Banco de Iniciativas Recreodeportivas</h1>
            <p class="wiz-banner__sub">{{ catalogos()!.evento.nombre }}</p>
          </div>
        </div>

        <!-- Barra de progreso -->
        <div class="wiz-progress" aria-label="Progreso del formulario">
          <div class="wiz-progress__meta">
            <span>Paso <strong>{{ pasoActual() }}</strong> de <strong>{{ totalPasos }}</strong></span>
            <span class="wiz-progress__title-mobile">{{ tituloPasoActual() }}</span>
            <span>{{ progresoPct() }}%</span>
          </div>
          <div class="wiz-progress__bar-bg"
               role="progressbar"
               [attr.aria-valuenow]="progresoPct()"
               aria-valuemin="0"
               aria-valuemax="100">
            <div class="wiz-progress__bar-fill"
                 [style.width.%]="progresoPct()">
            </div>
          </div>
        </div>

        <!-- Pills de pasos (desktop) -->
        <nav class="wiz-pills" aria-label="Pasos del formulario">
          @for (label of pasoLabels; track label; let i = $index) {
            <button type="button"
                    class="wiz-pill"
                    [class.wiz-pill--active]="pasoActual() === i + 1"
                    [class.wiz-pill--done]="pasoActual() > i + 1"
                    [disabled]="pasoActual() < i + 1"
                    (click)="irAPaso(i + 1)"
                    [attr.aria-current]="pasoActual() === i + 1 ? 'step' : null">
              <span class="wiz-pill__num">{{ i + 1 }}</span>
              <span class="wiz-pill__lbl">{{ label }}</span>
            </button>
          }
        </nav>
      </header>

      <!-- Errores generales del server -->
      @if (erroresServidor().length > 0) {
        <div class="wiz-server-errors" role="alert">
          <strong>Por favor corrige los siguientes errores:</strong>
          <ul>
            @for (err of erroresServidor(); track err) {
              <li>{{ err }}</li>
            }
          </ul>
        </div>
      }

      <!-- Contenido del paso activo -->
      <main class="wiz-main">

        <!-- ══ PASO 1: ORGANIZACIÓN ══ -->
        @if (pasoActual() === 1) {
          <section class="wiz-step" aria-labelledby="s1-title">
            <h2 id="s1-title" class="wiz-step__title">1. Datos de la organización</h2>
            <p class="wiz-step__hint">Información básica de tu colectivo u organización.</p>

            <div class="field field--required">
              <label class="field__label" for="nombre_organizacion">Nombre de la organización</label>
              <input id="nombre_organizacion" type="text" class="field__input"
                     [(ngModel)]="form.nombre_organizacion"
                     autocomplete="organization"
                     required maxlength="200"
                     placeholder="Nombre completo de tu colectivo u organización">
              @if (fieldError('nombre_organizacion')) {
                <p class="field__error" role="alert">{{ fieldError('nombre_organizacion') }}</p>
              }
            </div>

            <div class="field-row">
              <div class="field field--required">
                <label class="field__label" for="tipo_organizacion">Tipo de organización</label>
                <select id="tipo_organizacion" class="field__select"
                        [(ngModel)]="form.tipo_organizacion" required>
                  <option value="">Selecciona…</option>
                  @for (t of catalogos()!.tipos_organizacion; track t.codigo) {
                    <option [value]="t.codigo">{{ t.nombre }}</option>
                  }
                </select>
                @if (fieldError('tipo_organizacion')) {
                  <p class="field__error" role="alert">{{ fieldError('tipo_organizacion') }}</p>
                }
              </div>

              <div class="field">
                <label class="field__label" for="numero_soporte_legal">
                  {{ labelSoporteLegal() }}
                </label>
                <input id="numero_soporte_legal" type="text" class="field__input"
                       [(ngModel)]="form.numero_soporte_legal"
                       [placeholder]="placeholderSoporteLegal()">
                @if (fieldError('numero_soporte_legal')) {
                  <p class="field__error" role="alert">{{ fieldError('numero_soporte_legal') }}</p>
                }
              </div>
            </div>

            <div class="field">
              <label class="field__label" for="soporte_legal_url">
                Soporte legal (URL)
                <span class="field__optional">opcional</span>
              </label>
              <input id="soporte_legal_url" type="url" class="field__input"
                     [(ngModel)]="form.soporte_legal_url"
                     placeholder="https://drive.google.com/…">
              <p class="field__hint">Sube el PDF a Google Drive y pega el enlace compartido.</p>
              @if (fieldError('soporte_legal_url')) {
                <p class="field__error" role="alert">{{ fieldError('soporte_legal_url') }}</p>
              }
            </div>

            <div class="field-row">
              <div class="field">
                <label class="field__label" for="correo">Correo electrónico</label>
                <input id="correo" type="email" class="field__input"
                       [(ngModel)]="form.correo"
                       autocomplete="email"
                       placeholder="correo@ejemplo.com">
                @if (fieldError('correo')) {
                  <p class="field__error" role="alert">{{ fieldError('correo') }}</p>
                }
              </div>
              <div class="field">
                <label class="field__label" for="telefono">Teléfono</label>
                <input id="telefono" type="tel" class="field__input"
                       [(ngModel)]="form.telefono"
                       autocomplete="tel"
                       placeholder="3001234567">
                @if (fieldError('telefono')) {
                  <p class="field__error" role="alert">{{ fieldError('telefono') }}</p>
                }
              </div>
            </div>

            <h3 class="wiz-section-title">
              <span aria-hidden="true">📍</span> Sede administrativa
              <span class="field__optional">opcional</span>
            </h3>
            <p class="wiz-step__hint">Mantén el orden: UPL → Barrio → Dirección.</p>

            <div class="field-row">
              <div class="field">
                <label class="field__label" for="upl">UPL</label>
                <select id="upl" class="field__select" [(ngModel)]="form.upl">
                  <option value="">Selecciona UPL…</option>
                  @for (u of catalogos()!.upls; track u.codigo) {
                    <option [value]="u.codigo">{{ u.nombre }}</option>
                  }
                </select>
              </div>
              <div class="field">
                <label class="field__label" for="barrio_texto">Barrio</label>
                <input id="barrio_texto" type="text" class="field__input"
                       [(ngModel)]="form.barrio_texto"
                       maxlength="100"
                       placeholder="Escriba el nombre de su barrio">
              </div>
            </div>

            <div class="field">
              <label class="field__label" for="direccion">Dirección</label>
              <input id="direccion" type="text" class="field__input"
                     [(ngModel)]="form.direccion"
                     placeholder="Calle 40 # 70-15">
            </div>

            <h3 class="wiz-section-title">
              <span aria-hidden="true">🔗</span> Redes sociales
              <span class="field__optional">opcional</span>
            </h3>
            <div class="field-row field-row--3">
              <div class="field">
                <label class="field__label" for="redes_facebook">Facebook (URL)</label>
                <input id="redes_facebook" type="url" class="field__input"
                       [(ngModel)]="form.redes_facebook"
                       placeholder="https://facebook.com/…">
              </div>
              <div class="field">
                <label class="field__label" for="redes_instagram">Instagram (URL)</label>
                <input id="redes_instagram" type="url" class="field__input"
                       [(ngModel)]="form.redes_instagram"
                       placeholder="https://instagram.com/…">
              </div>
              <div class="field">
                <label class="field__label" for="redes_otra">Otra red (URL)</label>
                <input id="redes_otra" type="url" class="field__input"
                       [(ngModel)]="form.redes_otra"
                       placeholder="https://…">
              </div>
            </div>
          </section>
        }

        <!-- ══ PASO 2: REPRESENTANTE ══ -->
        @if (pasoActual() === 2) {
          <section class="wiz-step" aria-labelledby="s2-title">
            <h2 id="s2-title" class="wiz-step__title">2. Representante legal</h2>
            <p class="wiz-step__hint">Datos de quien firma esta postulación.</p>

            <div class="field-row">
              <div class="field field--required">
                <label class="field__label" for="rep_tipo_doc">Tipo de documento</label>
                <select id="rep_tipo_doc" class="field__select"
                        [(ngModel)]="form.rep_tipo_doc" required>
                  <option value="">Selecciona…</option>
                  @for (t of catalogos()!.tipos_documento; track t.codigo) {
                    <option [value]="t.codigo">{{ t.nombre }}</option>
                  }
                </select>
                @if (fieldError('rep_tipo_doc')) {
                  <p class="field__error" role="alert">{{ fieldError('rep_tipo_doc') }}</p>
                }
              </div>

              <div class="field field--required">
                <label class="field__label" for="rep_numero_doc">Número de documento</label>
                <input id="rep_numero_doc" type="text" class="field__input"
                       [(ngModel)]="form.rep_numero_doc"
                       (blur)="autollenarRepresentante()"
                       inputmode="numeric"
                       minlength="5" maxlength="15"
                       required
                       placeholder="12345678">
                @if (autollenadoStatus()) {
                  <p class="field__status" [class.field__status--ok]="autollenadoStatus() === 'ok'"
                     role="status" aria-live="polite">
                    @if (autollenadoStatus() === 'ok') {
                      ✓ Representante ya registrado — datos cargados.
                    }
                    @if (autollenadoStatus() === 'nuevo') {
                      Persona nueva — completa los datos del representante.
                    }
                  </p>
                }
                @if (fieldError('rep_numero_doc')) {
                  <p class="field__error" role="alert">{{ fieldError('rep_numero_doc') }}</p>
                }
              </div>
            </div>

            <div class="field-row">
              <div class="field field--required">
                <label class="field__label" for="rep_nombre1">Primer nombre</label>
                <input id="rep_nombre1" type="text" class="field__input"
                       [(ngModel)]="form.rep_nombre1"
                       autocomplete="given-name"
                       required maxlength="50"
                       placeholder="Juan">
                @if (fieldError('rep_nombre1')) {
                  <p class="field__error" role="alert">{{ fieldError('rep_nombre1') }}</p>
                }
              </div>
              <div class="field">
                <label class="field__label" for="rep_nombre2">Segundo nombre</label>
                <input id="rep_nombre2" type="text" class="field__input"
                       [(ngModel)]="form.rep_nombre2"
                       autocomplete="additional-name"
                       maxlength="50"
                       placeholder="Carlos">
              </div>
            </div>

            <div class="field-row">
              <div class="field field--required">
                <label class="field__label" for="rep_apellido1">Primer apellido</label>
                <input id="rep_apellido1" type="text" class="field__input"
                       [(ngModel)]="form.rep_apellido1"
                       autocomplete="family-name"
                       required maxlength="50"
                       placeholder="García">
                @if (fieldError('rep_apellido1')) {
                  <p class="field__error" role="alert">{{ fieldError('rep_apellido1') }}</p>
                }
              </div>
              <div class="field">
                <label class="field__label" for="rep_apellido2">Segundo apellido</label>
                <input id="rep_apellido2" type="text" class="field__input"
                       [(ngModel)]="form.rep_apellido2"
                       maxlength="50"
                       placeholder="López">
              </div>
            </div>
          </section>
        }

        <!-- ══ PASO 3: EXPERIENCIA Y FORMACIÓN ══ -->
        @if (pasoActual() === 3) {
          <section class="wiz-step" aria-labelledby="s3-title">
            <h2 id="s3-title" class="wiz-step__title">3. Experiencia y formación</h2>
            <p class="wiz-step__hint">Información sobre la trayectoria de tu organización y la formación de su representante.</p>

            <div class="field-row">
              <div class="field field--required">
                <label class="field__label" for="anios_experiencia">Años de experiencia</label>
                <select id="anios_experiencia" class="field__select"
                        [(ngModel)]="form.anios_experiencia" required>
                  <option value="">Selecciona rango…</option>
                  @for (r of catalogos()!.rangos_experiencia; track r.codigo) {
                    <option [value]="r.codigo">{{ r.nombre }}</option>
                  }
                </select>
                @if (fieldError('anios_experiencia')) {
                  <p class="field__error" role="alert">{{ fieldError('anios_experiencia') }}</p>
                }
              </div>

              <div class="field">
                <label class="field__label" for="nivel_educativo">Nivel educativo del representante</label>
                <select id="nivel_educativo" class="field__select" [(ngModel)]="form.nivel_educativo">
                  <option value="">Selecciona…</option>
                  @for (n of catalogos()!.niveles_educativos; track n.codigo) {
                    <option [value]="n.codigo">{{ n.nombre }}</option>
                  }
                </select>
              </div>
            </div>

            <div class="field">
              <label class="field__label" for="titulos_obtenidos">Títulos obtenidos</label>
              <textarea id="titulos_obtenidos" class="field__textarea"
                        [(ngModel)]="form.titulos_obtenidos"
                        rows="3"
                        placeholder="Ej. Técnico en deporte, Licenciado en educación física…"></textarea>
            </div>
          </section>
        }

        <!-- ══ PASO 4: ESCENARIOS ══ -->
        @if (pasoActual() === 4) {
          <section class="wiz-step" aria-labelledby="s4-title">
            <h2 id="s4-title" class="wiz-step__title">4. Escenarios de actividades</h2>
            <p class="wiz-step__hint">Selecciona los espacios donde tu organización desarrolla actividades y los que solicitas para el proyecto.</p>

            <h3 class="wiz-section-title">
              <span aria-hidden="true">📌</span>
              Escenarios que actualmente usa tu organización
              <span class="field__optional">opcional</span>
            </h3>
            @for (grupo of escenarioGruposActuales(); track grupo.categoria) {
              <h4 class="wiz-grupo-title">{{ grupo.categoria }}</h4>
              <div class="chips-grid">
                @for (e of grupo.items; track e.codigo) {
                  <button type="button"
                          class="chip"
                          [class.chip--active]="form.escenarios_actuales.has(codigoStr(e.codigo))"
                          (click)="toggleSet(form.escenarios_actuales, codigoStr(e.codigo))">
                    {{ e.nombre }}
                  </button>
                }
              </div>
            }

            <h3 class="wiz-section-title" style="margin-top: 1.5rem;">
              <span aria-hidden="true">🎯</span>
              Escenarios que solicita tu proyecto
              <span class="required-mark">*</span>
            </h3>
            @for (grupo of escenarioGruposSolicitados(); track grupo.categoria) {
              <h4 class="wiz-grupo-title">{{ grupo.categoria }}</h4>
              <div class="chips-grid">
                @for (e of grupo.items; track e.codigo) {
                  <button type="button"
                          class="chip"
                          [class.chip--active]="form.escenarios.has(codigoStr(e.codigo))"
                          (click)="toggleSet(form.escenarios, codigoStr(e.codigo))">
                    {{ e.nombre }}
                  </button>
                }
              </div>
            }
            @if (fieldError('escenarios')) {
              <p class="field__error" role="alert">{{ fieldError('escenarios') }}</p>
            }
            @if (pasosConError.has(4) && form.escenarios.size === 0) {
              <p class="field__error" role="alert">Debes seleccionar al menos un escenario solicitado.</p>
            }
          </section>
        }

        <!-- ══ PASO 5: POBLACIÓN ══ -->
        @if (pasoActual() === 5) {
          <section class="wiz-step" aria-labelledby="s5-title">
            <h2 id="s5-title" class="wiz-step__title">5. Población que atiende tu organización</h2>
            <p class="wiz-step__hint">Caracterización de las personas a las que tu organización atiende actualmente.</p>

            <div class="field-row field-row--3">
              <div class="field field--required">
                <label class="field__label" for="rango_poblacion">Cantidad de personas atendidas</label>
                <select id="rango_poblacion" class="field__select"
                        [(ngModel)]="form.rango_poblacion" required>
                  <option value="">Selecciona rango…</option>
                  @for (r of catalogos()!.rangos_poblacion; track r.codigo) {
                    <option [value]="r.codigo">{{ r.nombre }}</option>
                  }
                </select>
                @if (fieldError('rango_poblacion')) {
                  <p class="field__error" role="alert">{{ fieldError('rango_poblacion') }}</p>
                }
              </div>

              <div class="field">
                <label class="field__label" for="estrato">Estrato predominante</label>
                <select id="estrato" class="field__select" [(ngModel)]="form.estrato">
                  <option value="">Selecciona…</option>
                  @for (e of catalogos()!.estratos; track e) {
                    <option [value]="e">Estrato {{ e }}</option>
                  }
                </select>
              </div>

              <div class="field">
                <label class="field__label" for="caracteristica_pob">Característica especial</label>
                <select id="caracteristica_pob" class="field__select" [(ngModel)]="form.caracteristica_pob">
                  <option value="">Ninguna / N/A</option>
                  @for (c of catalogos()!.caracteristicas_poblacion; track c.codigo) {
                    <option [value]="c.codigo">{{ c.nombre }}</option>
                  }
                </select>
              </div>
            </div>

            <div class="field">
              <label class="field__label">
                Rangos etarios atendidos
                <span class="required-mark">*</span>
              </label>
              <div class="chips-grid">
                @for (r of catalogos()!.rangos_etarios; track r.codigo) {
                  <button type="button"
                          class="chip chip--etario"
                          [class.chip--active]="form.rango_etarios.has(codigoStr(r.codigo))"
                          (click)="toggleSet(form.rango_etarios, codigoStr(r.codigo))">
                    {{ r.nombre }}
                    @if (r.edad_min != null && r.edad_max != null) {
                      <small>({{ r.edad_min }}–{{ r.edad_max }} años)</small>
                    }
                  </button>
                }
              </div>
              @if (fieldError('rango_etarios')) {
                <p class="field__error" role="alert">{{ fieldError('rango_etarios') }}</p>
              }
              @if (pasosConError.has(5) && form.rango_etarios.size === 0) {
                <p class="field__error" role="alert">Debes seleccionar al menos un rango etario.</p>
              }
            </div>

            <div class="field">
              <label class="field__label">
                Enfoques diferenciales
                <span class="field__optional">opcional</span>
              </label>
              <div class="chips-grid">
                @for (e of catalogos()!.enfoques_diferenciales; track e.codigo) {
                  <button type="button"
                          class="chip"
                          [class.chip--active]="form.enfoques.has(codigoStr(e.codigo))"
                          (click)="toggleSet(form.enfoques, codigoStr(e.codigo))">
                    {{ e.nombre }}
                  </button>
                }
              </div>
            </div>
          </section>
        }

        <!-- ══ PASO 6: BENEFICIOS ALK E IMPACTO ══ -->
        @if (pasoActual() === 6) {
          <section class="wiz-step" aria-labelledby="s6-title">
            <h2 id="s6-title" class="wiz-step__title">6. Beneficios y políticas públicas</h2>
            <p class="wiz-step__hint">Cuéntanos si tu organización ya recibió apoyos de la Alcaldía y cómo las políticas han impactado tu trabajo.</p>

            <div class="field">
              <label class="checkbox-label">
                <input type="checkbox" class="checkbox-input"
                       [(ngModel)]="form.beneficiada_alk">
                <span class="checkbox-text">
                  Mi organización ya fue beneficiada por la Alcaldía Local de Kennedy
                </span>
              </label>
            </div>

            @if (form.beneficiada_alk) {
              <div class="conditional-block">
                <div class="field">
                  <label class="field__label">
                    ¿Qué beneficios recibió?
                    <span class="required-mark">*</span>
                  </label>
                  <div class="chips-grid">
                    @for (b of catalogos()!.tipos_beneficio_alk; track b.codigo) {
                      <button type="button"
                              class="chip"
                              [class.chip--active]="form.beneficios_alk.has(codigoStr(b.codigo))"
                              (click)="toggleSet(form.beneficios_alk, codigoStr(b.codigo))">
                        {{ b.nombre }}
                      </button>
                    }
                  </div>
                  @if (fieldError('beneficios_alk')) {
                    <p class="field__error" role="alert">{{ fieldError('beneficios_alk') }}</p>
                  }
                </div>

                <div class="field">
                  <label class="field__label" for="uso_beneficio">
                    ¿Cómo usó esos beneficios?
                  </label>
                  <textarea id="uso_beneficio" class="field__textarea"
                            [(ngModel)]="form.uso_beneficio"
                            rows="3"
                            placeholder="Describe brevemente cómo fueron aprovechados…"></textarea>
                </div>
              </div>
            }

            <div class="field" style="margin-top: 1.5rem;">
              <label class="field__label" for="impacto_politicas">
                Impacto de políticas públicas en tu organización
              </label>
              <select id="impacto_politicas" class="field__select"
                      [(ngModel)]="form.impacto_politicas">
                <option value="">Selecciona…</option>
                @for (c of catalogos()!.impacto_politicas_choices; track c.valor) {
                  <option [value]="c.valor">{{ c.etiqueta }}</option>
                }
              </select>
            </div>

            @if (form.impacto_politicas && form.impacto_politicas !== 'no_conozco') {
              <div class="conditional-block">
                <div class="field">
                  <label class="field__label" for="impacto_justificacion">
                    Justifica el impacto
                    <span class="required-mark">*</span>
                  </label>
                  <textarea id="impacto_justificacion" class="field__textarea"
                            [(ngModel)]="form.impacto_justificacion"
                            rows="4"
                            placeholder="Explica cómo las políticas públicas deportivas o culturales han impactado tu trabajo…"></textarea>
                  @if (fieldError('impacto_justificacion')) {
                    <p class="field__error" role="alert">{{ fieldError('impacto_justificacion') }}</p>
                  }
                </div>
              </div>
            }
          </section>
        }

        <!-- ══ PASO 7: PROPUESTA ══ -->
        @if (pasoActual() === 7) {
          <section class="wiz-step" aria-labelledby="s7-title">
            <h2 id="s7-title" class="wiz-step__title">7. Presentación de la propuesta</h2>
            <p class="wiz-step__hint">Cuéntanos en qué consiste tu iniciativa recreo-deportiva, qué disciplinas abarca y a quiénes beneficia.</p>

            <div class="field">
              <label class="field__label" for="propuesta_descripcion">
                Descripción de la propuesta
              </label>
              <textarea id="propuesta_descripcion" class="field__textarea"
                        [(ngModel)]="form.propuesta_descripcion"
                        rows="4"
                        placeholder="Ej.: Escuela de formación deportiva para 40 niños y niñas de 6 a 12 años, 2 veces por semana en la cancha del barrio. Incluye objetivo, actividades principales, frecuencia, lugar y población beneficiada."></textarea>
              @if (fieldError('propuesta_descripcion')) {
                <p class="field__error" role="alert">{{ fieldError('propuesta_descripcion') }}</p>
              }
            </div>

            <div class="field-row">
              <div class="field">
                <label class="field__label" for="disciplina_principal">Disciplina principal</label>
                <select id="disciplina_principal" class="field__select"
                        [(ngModel)]="form.disciplina_principal">
                  <option value="">Selecciona…</option>
                  @for (d of catalogos()!.disciplinas_deportivas; track d.codigo) {
                    <option [value]="d.codigo">{{ d.nombre }}</option>
                  }
                </select>
              </div>
              <div class="field">
                <label class="field__label" for="otros_deportes">Otros deportes / actividades</label>
                <input id="otros_deportes" type="text" class="field__input"
                       [(ngModel)]="form.otros_deportes"
                       placeholder="Ej. Voleibol, yoga, danza…">
              </div>
            </div>

            <div class="field">
              <label class="field__label" for="propuesta_url">
                Enlace a documento de propuesta
                <span class="field__optional">opcional</span>
              </label>
              <input id="propuesta_url" type="url" class="field__input"
                     [(ngModel)]="form.propuesta_url"
                     placeholder="https://drive.google.com/…">
            </div>

            <div class="field">
              <label class="field__label">
                Implementos necesarios
                <span class="field__optional">opcional</span>
              </label>
              @for (grupo of implementoGrupos(); track grupo.categoria) {
                <h4 class="wiz-grupo-title">{{ grupo.categoria }}</h4>
                <div class="chips-grid">
                  @for (imp of grupo.items; track imp.codigo) {
                    <button type="button"
                            class="chip chip--sm"
                            [class.chip--active]="form.implementos.has(codigoStr(imp.codigo))"
                            (click)="toggleSet(form.implementos, codigoStr(imp.codigo))">
                      {{ imp.nombre }}
                    </button>
                  }
                </div>
              }
            </div>
          </section>
        }

        <!-- ══ PASO 8: COMPROMISOS Y FIRMA ══ -->
        @if (pasoActual() === 8) {
          <section class="wiz-step" aria-labelledby="s8-title">
            <h2 id="s8-title" class="wiz-step__title">8. Compromisos y firma</h2>
            <p class="wiz-step__hint">Marca los tres compromisos y firma para poder enviar la postulación.</p>

            <div class="compromiso-list">
              <label class="checkbox-label checkbox-label--lg">
                <input type="checkbox" class="checkbox-input"
                       [(ngModel)]="form.compromiso_redes">
                <span class="checkbox-text">
                  Me comprometo a difundir las actividades financiadas a través de las redes sociales de la organización.
                </span>
              </label>
              <label class="checkbox-label checkbox-label--lg">
                <input type="checkbox" class="checkbox-input"
                       [(ngModel)]="form.compromiso_carta_1ano">
                <span class="checkbox-text">
                  Me comprometo a suscribir la carta de intención de continuidad por mínimo 1 año.
                </span>
              </label>
              <label class="checkbox-label checkbox-label--lg">
                <input type="checkbox" class="checkbox-input"
                       [(ngModel)]="form.compromiso_actualizacion">
                <span class="checkbox-text">
                  Me comprometo a mantener actualizada la información de la organización durante la ejecución.
                </span>
              </label>
            </div>
            @if (!form.compromiso_redes || !form.compromiso_carta_1ano || !form.compromiso_actualizacion) {
              @if (pasosConError.has(8)) {
                <p class="field__error" role="alert">Debes marcar los tres compromisos para continuar.</p>
              }
            }

            <div class="field-row" style="margin-top: 1.5rem;">
              <div class="field field--required">
                <label class="field__label" for="firma_cedula">Cédula del firmante</label>
                <input id="firma_cedula" type="text" class="field__input"
                       [(ngModel)]="form.firma_cedula"
                       inputmode="numeric"
                       minlength="5" maxlength="15"
                       required
                       placeholder="12345678">
                @if (fieldError('firma_cedula')) {
                  <p class="field__error" role="alert">{{ fieldError('firma_cedula') }}</p>
                }
              </div>
              <div class="field field--required">
                <label class="field__label" for="firma_fecha">Fecha de firma</label>
                <input id="firma_fecha" type="date" class="field__input"
                       [(ngModel)]="form.firma_fecha"
                       required>
                @if (fieldError('firma_fecha')) {
                  <p class="field__error" role="alert">{{ fieldError('firma_fecha') }}</p>
                }
              </div>
            </div>

            <!-- Uploader de firma -->
            <div class="field">
              <label class="field__label">
                Firma — foto <span class="field__optional">o usa el enlace de Drive de abajo</span>
                <span class="required-mark">*</span>
              </label>

              @if (!firmaPreview()) {
                <label for="firma_imagen" class="firma-btn" [class.firma-btn--error]="firmaError()">
                  <span class="firma-btn__icon" aria-hidden="true">📸</span>
                  <span class="firma-btn__text">Tomar foto de la firma</span>
                  <span class="firma-btn__sub">Se abrirá la cámara de tu celular</span>
                </label>
              } @else {
                <div class="firma-preview">
                  <img [src]="firmaPreview()!" alt="Vista previa de la firma" class="firma-preview__img">
                  <div class="firma-preview__meta">
                    <span class="firma-preview__name">{{ firmaNombre() }}</span>
                    <button type="button" class="btn-outline-brand btn-sm"
                            (click)="quitarFirma()">
                      ✕ Quitar
                    </button>
                  </div>
                </div>
                <label for="firma_imagen" class="firma-cambiar">
                  📸 Cambiar foto
                </label>
              }

              <input id="firma_imagen" type="file"
                     accept="image/*"
                     capture="environment"
                     class="firma-input-hidden"
                     (change)="onFirmaChange($event)"
                     aria-label="Seleccionar imagen de firma">

              <p class="field__hint" style="margin-top: 0.5rem;">
                La firma se guarda cifrada (AES-256) y solo el organizador puede verla.
              </p>
              @if (firmaError()) {
                <p class="field__error" role="alert">{{ firmaError() }}</p>
              }
              @if (fieldError('firma_imagen')) {
                <p class="field__error" role="alert">{{ fieldError('firma_imagen') }}</p>
              }
            </div>

            <!-- B-04: alternativa por URL de Drive (apto para computador de escritorio) -->
            <div class="field">
              <label class="field__label" for="firma_imagen_url">
                ¿Diligencias desde un computador? Enlace al documento firmado
              </label>
              <input id="firma_imagen_url" type="url" class="field__input"
                     [(ngModel)]="form.firma_imagen_url"
                     placeholder="https://drive.google.com/…">
              <p class="field__hint">
                Sube a Google Drive el documento con la firma y pega aquí el enlace.
                Usa esto <strong>o</strong> la foto de arriba (al menos uno).
              </p>
              @if (fieldError('firma_imagen_url')) {
                <p class="field__error" role="alert">{{ fieldError('firma_imagen_url') }}</p>
              }
            </div>

            <div class="wiz-aviso">
              <strong>Antes de enviar:</strong> revisa rápidamente cada paso
              usando el botón <em>Anterior</em>. Una vez enviada, la postulación
              queda registrada con fecha y hora.
            </div>
          </section>
        }

        <!-- Botonera fija en el pie -->
        <div class="wiz-actions">
          <button type="button" class="btn-outline-brand btn-wiz-prev"
                  (click)="irAnterior()"
                  [disabled]="pasoActual() === 1"
                  [class.btn--hidden]="pasoActual() === 1">
            ← Anterior
          </button>

          @if (pasoActual() < totalPasos) {
            <button type="button" class="btn-brand btn-wiz-next"
                    (click)="irSiguiente()">
              Siguiente →
            </button>
          }

          @if (pasoActual() === totalPasos) {
            <button type="button"
                    class="btn-brand btn-wiz-submit"
                    (click)="enviar()"
                    [disabled]="enviando()">
              @if (enviando()) {
                <span class="spinner-inline" aria-hidden="true"></span>
                Enviando…
              } @else {
                ✉ Enviar postulación
              }
            </button>
          }
        </div>
      </main>
    }
  `,
  styles: [`
    @use '../../../styles/tokens' as *;

    // ── Variables locales ──────────────────────────────────────────────
    $brand-dark: #1d3557;
    $brand-gradient: linear-gradient(135deg, #{$brand-dark}, #{$color-primary});
    $conditional-bg: #fffbe6;
    $conditional-border: $color-secondary;

    // ── Layout base ────────────────────────────────────────────────────
    :host {
      display: block;
      background: $color-bg-subtle;
      min-height: 100vh;
      font-family: $font-family-base;
    }

    // ── Estados de carga, error y cierre ──────────────────────────────
    .loading-wrap,
    .error-wrap,
    .cerrado-wrap,
    .exito-wrap {
      display: flex;
      align-items: center;
      justify-content: center;
      min-height: 100vh;
      padding: $space-6;
    }

    .loading-spinner {
      width: 40px;
      height: 40px;
      border: 4px solid $color-border;
      border-top-color: $color-primary;
      border-radius: 50%;
      animation: spin 0.8s linear infinite;
      margin: 0 auto $space-4;

      @media (prefers-reduced-motion: reduce) {
        animation: none;
      }
    }

    .loading-wrap {
      flex-direction: column;
      gap: $space-3;
      color: $color-text-muted;
    }

    .error-card,
    .cerrado-card,
    .exito-card {
      background: $color-bg;
      border-radius: $radius-2xl;
      padding: $space-10 $space-8;
      text-align: center;
      max-width: 480px;
      box-shadow: $shadow-lg;
    }

    .error-icon, .cerrado-icon { font-size: 3rem; margin-bottom: $space-4; }

    .cerrado-title {
      font-size: $font-size-2xl;
      font-weight: $font-weight-bold;
      color: $color-primary;
      margin: 0 0 $space-3;
    }

    .cerrado-msg {
      font-size: $font-size-md;
      color: $color-text;
      font-weight: $font-weight-semibold;
      margin-bottom: $space-3;
    }

    .cerrado-sub {
      color: $color-text-muted;
      font-size: $font-size-sm;
    }

    // ── Pantalla de éxito ─────────────────────────────────────────────
    .exito-card { max-width: 520px; }

    .exito-icono {
      width: 80px;
      height: 80px;
      margin: 0 auto $space-5;

      svg { width: 100%; height: 100%; }
    }

    .exito-title {
      font-size: $font-size-2xl;
      font-weight: $font-weight-bold;
      color: $color-success;
      margin: 0 0 $space-3;
    }

    .exito-desc {
      color: $color-text;
      font-size: $font-size-md;
      margin-bottom: $space-5;
    }

    .exito-num {
      display: inline-flex;
      flex-direction: column;
      gap: $space-1;
      background: $color-bg-muted;
      border: 1px solid $color-border;
      border-radius: $radius-xl;
      padding: $space-4 $space-8;
      margin-bottom: $space-5;
    }

    .exito-num__label {
      font-size: $font-size-xs;
      letter-spacing: 0.01em;
      color: $color-text-muted;
      font-weight: $font-weight-semibold;
    }

    .exito-num__val {
      font-size: $font-size-2xl;
      font-weight: $font-weight-bold;
      color: $color-primary;
    }

    .exito-footer {
      color: $color-text-muted;
      font-size: $font-size-sm;
      margin: 0;
    }

    // ── Header del wizard (sticky) ────────────────────────────────────
    .wiz-header {
      position: sticky;
      top: 0;
      z-index: $z-sticky;
      background: $color-bg;
      box-shadow: $shadow-md;
    }

    .wiz-banner {
      display: flex;
      align-items: center;
      gap: $space-3;
      background: $brand-gradient;
      color: $color-text-inverse;
      padding: $space-4 $space-5;
    }

    /* U-01: pantalla de bienvenida (Paso 0) */
    .intro { max-width: 720px; margin: 0 auto; }
    .intro__card { background: #fff; border: 1px solid $color-border; border-radius: $radius-lg; padding: $space-4 $space-5; margin: $space-4 $space-3; }
    .intro__lead { color: $color-text; font-size: $font-size-base; line-height: 1.5; margin: 0 0 $space-3; }
    .intro__list { margin: 0 0 $space-3; padding-left: $space-4; color: $color-text; }
    .intro__list li { margin-bottom: $space-1; line-height: 1.45; }
    .intro__docs-title { font-weight: 600; color: $color-text; margin: $space-3 0 $space-1; }
    .intro__btn { margin-top: $space-3; }

    .wiz-banner__icon { font-size: 1.8rem; flex-shrink: 0; }

    .wiz-banner__title {
      font-size: $font-size-base;
      font-weight: $font-weight-bold;
      margin: 0;
      line-height: $line-height-tight;

      @media (min-width: #{$bp-md}) { font-size: $font-size-md; }
    }

    .wiz-banner__sub {
      margin: $space-1 0 0;
      font-size: $font-size-xs;
      opacity: 0.9;
    }

    // Barra de progreso
    .wiz-progress {
      padding: $space-3 $space-5;
    }

    .wiz-progress__meta {
      display: flex;
      justify-content: space-between;
      align-items: center;
      font-size: $font-size-xs;
      color: $color-text-muted;
      margin-bottom: $space-2;

      strong { color: $color-text; }
    }

    .wiz-progress__title-mobile {
      font-weight: $font-weight-semibold;
      color: $color-primary;

      @media (min-width: #{$bp-md}) { display: none; }
    }

    .wiz-progress__bar-bg {
      background: $color-border;
      height: 6px;
      border-radius: $radius-pill;
      overflow: hidden;
    }

    .wiz-progress__bar-fill {
      background: $color-primary;
      height: 100%;
      border-radius: $radius-pill;
      transition: width $transition-slow;

      @media (prefers-reduced-motion: reduce) { transition: none; }
    }

    // Pills de pasos (solo desktop)
    .wiz-pills {
      display: none;
      gap: $space-2;
      padding: $space-3 $space-5;
      flex-wrap: wrap;

      @media (min-width: #{$bp-md}) { display: flex; }
    }

    .wiz-pill {
      display: inline-flex;
      align-items: center;
      gap: $space-2;
      padding: $space-1 $space-3;
      border-radius: $radius-pill;
      font-size: $font-size-xs;
      font-weight: $font-weight-semibold;
      background: $color-bg-muted;
      color: $color-text-muted;
      border: 1px solid transparent;
      cursor: default;
      transition: background $transition-base, color $transition-base;

      &[disabled] { opacity: 0.6; }

      &:not([disabled]) { cursor: pointer; }

      &--active {
        background: $color-primary-bg;
        color: $color-primary;
        border-color: rgba($color-primary, 0.3);
      }

      &--done {
        background: $color-success-bg;
        color: $color-success;
        cursor: pointer;
      }
    }

    .wiz-pill__num {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      width: 18px;
      height: 18px;
      border-radius: 50%;
      background: rgba(0, 0, 0, 0.1);
      font-size: 0.65rem;

      .wiz-pill--active & {
        background: $color-primary;
        color: $color-text-inverse;
      }

      .wiz-pill--done & {
        background: $color-success;
        color: $color-text-inverse;
      }
    }

    // ── Errores del servidor ──────────────────────────────────────────
    .wiz-server-errors {
      background: $color-danger-bg;
      border-left: 4px solid $color-danger;
      border-radius: $radius-md;
      padding: $space-4;
      margin: $space-4 $space-4 0;
      color: $color-danger;
      font-size: $font-size-sm;

      ul { margin: $space-2 0 0; padding-left: $space-5; }
    }

    // ── Contenido principal del wizard ───────────────────────────────
    .wiz-main {
      max-width: 100%;
      margin: 0 auto;
      padding: $space-4;

      @media (min-width: #{$bp-md}) {
        max-width: 760px;
        padding: $space-6 $space-4;
      }

      @media (min-width: #{$bp-xl}) {
        max-width: 900px;
      }
    }

    // ── Sección de paso ───────────────────────────────────────────────
    .wiz-step {
      background: $color-bg;
      border-radius: $radius-xl;
      padding: $space-5 $space-4;
      box-shadow: $shadow-sm;
      margin-bottom: 5rem; // espacio para la botonera sticky

      @media (min-width: #{$bp-md}) {
        padding: $space-8 $space-10;
      }

      @media (prefers-reduced-motion: no-preference) {
        animation: step-in 0.22s ease-out both;
      }
    }

    @keyframes step-in {
      from { opacity: 0; transform: translateY(10px); }
      to   { opacity: 1; transform: translateY(0); }
    }

    @keyframes spin {
      to { transform: rotate(360deg); }
    }

    .wiz-step__title {
      font-size: $font-size-lg;
      font-weight: $font-weight-bold;
      color: $color-primary;
      margin: 0 0 $space-2;
      line-height: $line-height-tight;
    }

    .wiz-step__hint {
      font-size: $font-size-sm;
      color: $color-text-muted;
      margin: 0 0 $space-5;
      line-height: $line-height-relaxed;
    }

    .wiz-section-title {
      font-size: $font-size-sm;
      font-weight: $font-weight-semibold;
      color: $color-neutral-600;
      letter-spacing: 0.01em;
      margin: $space-6 0 $space-3;
      display: flex;
      align-items: center;
      gap: $space-2;
    }

    .wiz-grupo-title {
      font-size: $font-size-sm;
      font-weight: $font-weight-semibold;
      color: $brand-dark;
      margin: $space-4 0 $space-2;
    }

    // ── Campos de formulario ──────────────────────────────────────────
    .field {
      margin-bottom: $space-5;

      &--required .field__label::after {
        content: ' *';
        color: $color-primary;
        font-weight: $font-weight-bold;
      }
    }

    .field__label {
      display: block;
      font-size: $font-size-sm;
      font-weight: $font-weight-semibold;
      color: $color-text;
      margin-bottom: $space-2;
    }

    .field__optional {
      font-size: $font-size-xs;
      font-weight: $font-weight-regular;
      color: $color-text-muted;
      margin-left: $space-2;
    }

    .field__input,
    .field__select,
    .field__textarea {
      display: block;
      width: 100%;
      min-height: $touch-target-min;
      padding: $space-3 $space-4;
      font-size: $font-size-base;
      font-family: $font-family-base;
      color: $color-text;
      background: $color-bg;
      border: 1.5px solid $color-border-strong;
      border-radius: $radius-lg;
      transition: border-color $transition-base, box-shadow $transition-base;

      &:focus {
        outline: none;
        border-color: $color-primary;
        box-shadow: 0 0 0 $focus-ring-width $focus-ring-color;
      }

      &:focus-visible {
        outline: $focus-ring;
        outline-offset: $focus-ring-offset;
      }
    }

    .field__textarea {
      min-height: 90px;
      resize: vertical;
    }

    .field__error {
      color: $color-danger;
      font-size: $font-size-xs;
      margin: $space-1 0 0;
      font-weight: $font-weight-medium;
    }

    .field__hint {
      color: $color-text-muted;
      font-size: $font-size-xs;
      margin: $space-1 0 0;
    }

    .field__status {
      font-size: $font-size-xs;
      margin: $space-1 0 0;
      color: $color-info;

      &--ok { color: $color-success; }
    }

    .required-mark { color: $color-primary; font-weight: $font-weight-bold; }

    // Filas de campos
    .field-row {
      display: grid;
      grid-template-columns: 1fr;
      gap: $space-3;

      @media (min-width: #{$bp-sm}) { grid-template-columns: 1fr 1fr; }

      &--3 {
        @media (min-width: #{$bp-md}) { grid-template-columns: 1fr 1fr 1fr; }
      }
    }

    // ── Checkboxes ────────────────────────────────────────────────────
    .checkbox-label {
      display: flex;
      align-items: flex-start;
      gap: $space-3;
      cursor: pointer;
      margin-bottom: $space-3;

      &--lg {
        padding: $space-3 $space-4;
        border: 1.5px solid $color-border;
        border-radius: $radius-lg;
        background: $color-bg-subtle;
        transition: border-color $transition-base, background $transition-base;

        &:has(.checkbox-input:checked) {
          border-color: $color-success;
          background: $color-success-bg;
        }
      }
    }

    .checkbox-input {
      width: 20px;
      height: 20px;
      min-width: 20px;
      accent-color: $color-primary;
      cursor: pointer;
      margin-top: 2px;

      &:focus-visible {
        outline: $focus-ring;
        outline-offset: $focus-ring-offset;
      }
    }

    .checkbox-text {
      font-size: $font-size-sm;
      line-height: $line-height-normal;
      color: $color-text;
    }

    .compromiso-list { display: flex; flex-direction: column; gap: $space-3; }

    // ── Chips (M2M) ───────────────────────────────────────────────────
    .chips-grid {
      display: flex;
      flex-wrap: wrap;
      gap: $space-2;
    }

    .chip {
      display: inline-flex;
      align-items: center;
      gap: $space-1;
      padding: $space-2 $space-4;
      font-size: $font-size-sm;
      font-family: $font-family-base;
      background: $color-bg-muted;
      color: $color-text-muted;
      border: 1.5px solid $color-border;
      border-radius: $radius-pill;
      cursor: pointer;
      transition: all $transition-base;
      min-height: $touch-target-min;
      user-select: none;

      &:hover {
        border-color: $color-primary;
        color: $color-primary;
        background: $color-primary-bg;
      }

      &:focus-visible {
        outline: $focus-ring;
        outline-offset: $focus-ring-offset;
      }

      &--active {
        background: $color-primary;
        color: $color-text-inverse;
        border-color: $color-primary-dark;

        &:hover { background: $color-primary-dark; }
      }

      &--sm { padding: $space-1 $space-3; font-size: $font-size-xs; }

      &--etario {
        flex-direction: column;
        gap: 0;
        min-width: 100px;
        text-align: center;
        padding: $space-2 $space-3;

        small {
          font-size: 0.65rem;
          opacity: 0.8;
        }
      }
    }

    // ── Bloque condicional ────────────────────────────────────────────
    .conditional-block {
      border-left: 3px solid $conditional-border;
      background: $conditional-bg;
      padding: $space-4;
      border-radius: 0 $radius-md $radius-md 0;
      margin: $space-3 0 $space-4;
    }

    // ── Uploader de firma ─────────────────────────────────────────────
    .firma-input-hidden {
      position: absolute;
      left: -9999px;
      width: 1px;
      height: 1px;
      opacity: 0;
    }

    .firma-btn {
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      gap: $space-2;
      width: 100%;
      min-height: 80px;
      padding: $space-5;
      background: $color-primary;
      color: $color-text-inverse;
      border: 2px dashed rgba(255, 255, 255, 0.4);
      border-radius: $radius-xl;
      cursor: pointer;
      text-align: center;
      transition: filter $transition-base;

      &:hover { filter: brightness(0.92); }

      &:focus-within {
        outline: $focus-ring;
        outline-offset: $focus-ring-offset;
      }

      &--error { border-color: $color-danger; }
    }

    .firma-btn__icon { font-size: 2rem; }

    .firma-btn__text {
      font-size: $font-size-base;
      font-weight: $font-weight-bold;
    }

    .firma-btn__sub {
      font-size: $font-size-xs;
      opacity: 0.85;
    }

    .firma-preview {
      border: 1.5px solid $color-border;
      border-radius: $radius-lg;
      overflow: hidden;
      background: $color-bg-subtle;
    }

    .firma-preview__img {
      display: block;
      max-width: 100%;
      max-height: 240px;
      margin: 0 auto;
      background: $color-bg;
    }

    .firma-preview__meta {
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: $space-3;
      padding: $space-2 $space-3;
      background: $color-bg-muted;
    }

    .firma-preview__name {
      font-size: $font-size-xs;
      color: $color-text-muted;
      word-break: break-all;
    }

    .firma-cambiar {
      display: inline-flex;
      align-items: center;
      gap: $space-2;
      margin-top: $space-3;
      padding: $space-2 $space-4;
      font-size: $font-size-sm;
      background: $color-bg-muted;
      border: 1.5px solid $color-border;
      border-radius: $radius-lg;
      cursor: pointer;
      transition: background $transition-base;

      &:hover { background: $color-border; }
    }

    // ── Aviso final ───────────────────────────────────────────────────
    .wiz-aviso {
      background: $color-bg-muted;
      border: 1px solid $color-border;
      border-radius: $radius-lg;
      padding: $space-4;
      font-size: $font-size-sm;
      color: $color-text-muted;
      line-height: $line-height-relaxed;
      margin-top: $space-5;
    }

    // ── Botonera sticky ───────────────────────────────────────────────
    .wiz-actions {
      position: sticky;
      bottom: 0;
      display: flex;
      gap: $space-3;
      justify-content: space-between;
      align-items: center;
      background: $color-bg;
      border-top: 1px solid $color-border;
      padding: $space-4 $space-5;
      max-width: 100%;
      margin: 0 auto;
      border-radius: $radius-xl $radius-xl 0 0;
      box-shadow: 0 -4px 12px rgba(0, 0, 0, 0.08);

      @media (min-width: #{$bp-md}) {
        max-width: 760px;
        padding: $space-4 $space-8;
      }

      @media (min-width: #{$bp-xl}) { max-width: 900px; }
    }

    .btn--hidden { visibility: hidden; }

    // ── Botones compartidos ───────────────────────────────────────────
    .btn-brand {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      gap: $space-2;
      min-height: $touch-target-min;
      padding: $space-3 $space-6;
      background: $color-primary;
      color: $color-text-inverse;
      border: none;
      border-radius: $radius-lg;
      font-size: $font-size-base;
      font-family: $font-family-base;
      font-weight: $font-weight-semibold;
      cursor: pointer;
      transition: background $transition-base;
      text-decoration: none;

      &:hover { background: $color-primary-dark; }

      &:focus-visible {
        outline: $focus-ring;
        outline-offset: $focus-ring-offset;
      }

      &[disabled] {
        opacity: 0.65;
        cursor: not-allowed;
      }

      &-lg { font-size: $font-size-md; padding: $space-4 $space-8; }
    }

    .btn-wiz-prev {
      min-width: 110px;
      min-height: $touch-target-min;
    }

    .btn-wiz-next,
    .btn-wiz-submit {
      flex: 1;
    }

    .btn-outline-brand {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      gap: $space-2;
      min-height: $touch-target-min;
      padding: $space-3 $space-5;
      background: $color-bg;
      color: $color-primary;
      border: 1.5px solid $color-primary;
      border-radius: $radius-lg;
      font-size: $font-size-base;
      font-family: $font-family-base;
      font-weight: $font-weight-semibold;
      cursor: pointer;
      transition: background $transition-base;
      text-decoration: none;

      &:hover { background: $color-primary-bg; }

      &:focus-visible {
        outline: $focus-ring;
        outline-offset: $focus-ring-offset;
      }

      &[disabled] {
        opacity: 0.65;
        cursor: not-allowed;
      }
    }

    .btn-sm {
      min-height: 36px;
      padding: $space-1 $space-3;
      font-size: $font-size-sm;
    }

    .spinner-inline {
      display: inline-block;
      width: 16px;
      height: 16px;
      border: 2px solid rgba(255, 255, 255, 0.4);
      border-top-color: $color-text-inverse;
      border-radius: 50%;
      animation: spin 0.7s linear infinite;

      @media (prefers-reduced-motion: reduce) { animation: none; }
    }
  `],
})
export class BancoPublicoComponent implements OnInit {
  private route = inject(ActivatedRoute);
  private http = inject(HttpClient);
  private cfg = inject(ConfigService);

  // ── Señales de estado ──────────────────────────────────────────────
  cargandoCatalogos = signal(true);
  errorCarga = signal('');
  cerrado = signal(false);
  cerradoMsg = signal('');
  exito = signal(false);
  exitoId = signal<number | null>(null);
  enviando = signal(false);

  catalogos = signal<BancoCatalogos | null>(null);
  pasoActual = signal(1);
  intro = signal(true);  // U-01: pantalla de bienvenida (Paso 0) antes del wizard

  // Errores campo a campo (400 del servidor)
  private erroresCampo = signal<Record<string, string[]>>({});
  erroresServidor = signal<string[]>([]);

  // Firma
  firmaPreview = signal<string | null>(null);
  firmaNombre = signal('');
  firmaError = signal('');

  // Autollenado representante
  autollenadoStatus = signal<'ok' | 'nuevo' | null>(null);

  // Control de pasos visitados con error (para mostrar msgs inline)
  pasosConError = new Set<number>();

  // ── Constantes ────────────────────────────────────────────────────
  readonly totalPasos = TOTAL_PASOS;
  readonly pasoLabels = PASO_LABELS;

  // ── Modelo del formulario ─────────────────────────────────────────
  form: FormData = {
    nombre_organizacion: '',
    tipo_organizacion: '',
    numero_soporte_legal: '',
    soporte_legal_url: '',
    correo: '',
    telefono: '',
    redes_facebook: '',
    redes_instagram: '',
    redes_otra: '',
    upl: '',
    barrio: '',
    barrio_texto: '',
    direccion: '',
    rep_tipo_doc: '',
    rep_numero_doc: '',
    rep_nombre1: '',
    rep_nombre2: '',
    rep_apellido1: '',
    rep_apellido2: '',
    anios_experiencia: '',
    nivel_educativo: '',
    titulos_obtenidos: '',
    escenarios: new Set(),
    escenarios_actuales: new Set(),
    rango_poblacion: '',
    estrato: '',
    caracteristica_pob: '',
    rango_etarios: new Set(),
    enfoques: new Set(),
    beneficiada_alk: false,
    beneficios_alk: new Set(),
    uso_beneficio: '',
    impacto_politicas: '',
    impacto_justificacion: '',
    disciplina_principal: '',
    otros_deportes: '',
    implementos: new Set(),
    propuesta_url: '',
    propuesta_descripcion: '',
    compromiso_redes: false,
    compromiso_carta_1ano: false,
    compromiso_actualizacion: false,
    firma_cedula: '',
    firma_fecha: this.hoyISO(),
    firma_imagen: null,
    firma_imagen_url: '',
  };

  // ── Computados ────────────────────────────────────────────────────
  progresoPct = computed(() =>
    Math.round((this.pasoActual() / this.totalPasos) * 100),
  );

  tituloPasoActual = computed(() =>
    PASO_LABELS[this.pasoActual() - 1] ?? '',
  );

  barriosFiltrados = computed(() => {
    const cat = this.catalogos();
    if (!cat) return [];
    return cat.barrios;
  });

  escenarioGruposSolicitados = computed(() => {
    const cat = this.catalogos();
    if (!cat) return [];
    return groupEscenarios(cat.escenarios);
  });

  escenarioGruposActuales = computed(() =>
    this.escenarioGruposSolicitados(),
  );

  implementoGrupos = computed<Array<{ categoria: string; items: ImplementoItem[] }>>(() => {
    const cat = this.catalogos();
    if (!cat) return [];
    const map = new Map<string, ImplementoItem[]>();
    for (const imp of cat.implementos) {
      const cat2 = imp.categoria || 'Otros';
      if (!map.has(cat2)) map.set(cat2, []);
      map.get(cat2)!.push(imp);
    }
    return Array.from(map.entries()).map(([categoria, items]) => ({ categoria, items }));
  });

  // ── Ciclo de vida ─────────────────────────────────────────────────
  ngOnInit(): void {
    this.cargarCatalogos();
  }

  eventoId(): number {
    return Number(this.route.snapshot.paramMap.get('eventoId') ?? '0');
  }

  cargarCatalogos(): void {
    this.cargandoCatalogos.set(true);
    this.errorCarga.set('');
    this.cerrado.set(false);

    const url = this.cfg.url(
      `/banco-iniciativas/api/publico/${this.eventoId()}/catalogos/`,
    );

    this.http.get<BancoCatalogos>(url, { observe: 'response' }).subscribe({
      next: (resp) => {
        this.catalogos.set(resp.body);
        this.cargandoCatalogos.set(false);
      },
      error: (err) => {
        this.cargandoCatalogos.set(false);
        if (err.status === 410) {
          this.cerrado.set(true);
          this.cerradoMsg.set(err.error?.detail || 'Esta convocatoria ya cerró.');
        } else {
          this.errorCarga.set(
            err.error?.detail || 'No se pudo cargar el formulario. Revisa tu conexión.',
          );
        }
      },
    });
  }

  // ── Navegación del wizard ─────────────────────────────────────────
  irSiguiente(): void {
    if (!this.validarPasoActual()) return;
    if (this.pasoActual() < this.totalPasos) {
      this.pasoActual.update((p) => p + 1);
      this.scrollTop();
    }
  }

  irAnterior(): void {
    if (this.pasoActual() > 1) {
      this.pasoActual.update((p) => p - 1);
      this.scrollTop();
    }
  }

  irAPaso(n: number): void {
    if (n <= this.pasoActual()) {
      this.pasoActual.set(n);
      this.scrollTop();
    }
  }

  /** U-01: cierra la bienvenida (Paso 0) y entra al wizard. */
  comenzar(): void {
    this.intro.set(false);
    this.scrollTop();
  }

  private scrollTop(): void {
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }

  // ── Validación por paso ───────────────────────────────────────────
  private validarPasoActual(): boolean {
    const paso = this.pasoActual();
    const ok = this.validarPaso(paso);
    if (!ok) this.pasosConError.add(paso);
    return ok;
  }

  private validarPaso(paso: number): boolean {
    switch (paso) {
      case 1:
        return !!this.form.nombre_organizacion.trim() && !!this.form.tipo_organizacion;
      case 2:
        return (
          !!this.form.rep_tipo_doc &&
          !!this.form.rep_numero_doc.trim() &&
          /^\d{5,15}$/.test(this.form.rep_numero_doc.trim()) &&
          !!this.form.rep_nombre1.trim() &&
          !!this.form.rep_apellido1.trim()
        );
      case 3:
        return !!this.form.anios_experiencia;
      case 4:
        return this.form.escenarios.size > 0;
      case 5:
        return !!this.form.rango_poblacion && this.form.rango_etarios.size > 0;
      case 6:
        if (this.form.beneficiada_alk && this.form.beneficios_alk.size === 0) return false;
        if (
          this.form.impacto_politicas &&
          this.form.impacto_politicas !== 'no_conozco' &&
          !this.form.impacto_justificacion.trim()
        ) return false;
        return true;
      case 7:
        return true; // todo opcional en este paso
      case 8:
        return (
          this.form.compromiso_redes &&
          this.form.compromiso_carta_1ano &&
          this.form.compromiso_actualizacion &&
          !!this.form.firma_cedula.trim() &&
          /^\d{5,15}$/.test(this.form.firma_cedula.trim()) &&
          !!this.form.firma_fecha &&
          (this.form.firma_imagen !== null || !!this.form.firma_imagen_url.trim())
        );
      default:
        return true;
    }
  }

  // ── Envío ─────────────────────────────────────────────────────────
  enviar(): void {
    // Validar todos los pasos antes de enviar
    for (let i = 1; i <= this.totalPasos; i++) {
      if (!this.validarPaso(i)) {
        this.pasosConError.add(i);
        this.pasoActual.set(i);
        this.scrollTop();
        return;
      }
    }

    // B-04: vale la foto O el enlace de Drive (al menos uno).
    if (!this.form.firma_imagen && !this.form.firma_imagen_url.trim()) {
      this.firmaError.set('Agrega la foto de la firma o el enlace de Drive del documento firmado.');
      this.pasoActual.set(8);
      return;
    }

    this.enviando.set(true);
    this.erroresCampo.set({});
    this.erroresServidor.set([]);

    const fd = this.buildFormData();
    const url = this.cfg.url(
      `/banco-iniciativas/api/publico/${this.eventoId()}/inscribir/`,
    );

    this.http.post<{ id: number; detail: string }>(url, fd).subscribe({
      next: (resp) => {
        this.enviando.set(false);
        this.exitoId.set(resp.id);
        this.exito.set(true);
        this.scrollTop();
      },
      error: (err) => {
        this.enviando.set(false);
        const body = err.error as ApiError | null;
        if (err.status === 400 && body) {
          if (body.errors) {
            this.erroresCampo.set(body.errors);
            // Agregar mensajes en la lista del servidor para visibilidad
            const msgs: string[] = [];
            for (const [campo, errs] of Object.entries(body.errors)) {
              for (const e of errs) msgs.push(`${campo}: ${e}`);
            }
            this.erroresServidor.set(msgs);
            // Ir al primer paso con error de servidor
            this.irAlPasoConErrorServidor(Object.keys(body.errors));
          } else if (body.detail) {
            this.erroresServidor.set([body.detail]);
          }
        } else {
          this.erroresServidor.set([
            err.error?.detail || 'Error al enviar. Intenta nuevamente.',
          ]);
        }
        this.scrollTop();
      },
    });
  }

  private buildFormData(): globalThis.FormData {
    const fd = new globalThis.FormData();
    const f = this.form;

    // Escalares simples
    const scalars: Array<[string, string | boolean]> = [
      ['nombre_organizacion', f.nombre_organizacion],
      ['tipo_organizacion', f.tipo_organizacion],
      ['numero_soporte_legal', f.numero_soporte_legal],
      ['soporte_legal_url', f.soporte_legal_url],
      ['correo', f.correo],
      ['telefono', f.telefono],
      ['redes_facebook', f.redes_facebook],
      ['redes_instagram', f.redes_instagram],
      ['redes_otra', f.redes_otra],
      ['upl', f.upl],
      ['barrio_texto', f.barrio_texto],
      ['direccion', f.direccion],
      ['rep_tipo_doc', f.rep_tipo_doc],
      ['rep_numero_doc', f.rep_numero_doc],
      ['rep_nombre1', f.rep_nombre1],
      ['rep_nombre2', f.rep_nombre2],
      ['rep_apellido1', f.rep_apellido1],
      ['rep_apellido2', f.rep_apellido2],
      ['anios_experiencia', f.anios_experiencia],
      ['nivel_educativo', f.nivel_educativo],
      ['titulos_obtenidos', f.titulos_obtenidos],
      ['rango_poblacion', f.rango_poblacion],
      ['estrato', f.estrato],
      ['caracteristica_pob', f.caracteristica_pob],
      ['uso_beneficio', f.uso_beneficio],
      ['impacto_politicas', f.impacto_politicas],
      ['impacto_justificacion', f.impacto_justificacion],
      ['disciplina_principal', f.disciplina_principal],
      ['otros_deportes', f.otros_deportes],
      ['propuesta_url', f.propuesta_url],
      ['propuesta_descripcion', f.propuesta_descripcion],
      ['firma_cedula', f.firma_cedula],
      ['firma_fecha', f.firma_fecha],
      ['beneficiada_alk', f.beneficiada_alk ? 'true' : 'false'],
      ['compromiso_redes', 'true'],
      ['compromiso_carta_1ano', 'true'],
      ['compromiso_actualizacion', 'true'],
    ];

    for (const [k, v] of scalars) {
      if (v !== '' && v !== false) fd.append(k, String(v));
    }

    // Sets (M2M: append repetido por valor)
    const sets: Array<[string, Set<string>]> = [
      ['escenarios', f.escenarios],
      ['escenarios_actuales', f.escenarios_actuales],
      ['rango_etarios', f.rango_etarios],
      ['enfoques', f.enfoques],
      ['beneficios_alk', f.beneficios_alk],
      ['implementos', f.implementos],
    ];

    for (const [k, s] of sets) {
      for (const v of s) fd.append(k, v);
    }

    // Firma: foto (Mongo cifrado) o URL de Drive (B-04). El backend acepta
    // cualquiera de las dos (clean() exige al menos una).
    if (f.firma_imagen) {
      fd.append('firma_imagen', f.firma_imagen, f.firma_imagen.name);
    }
    if (f.firma_imagen_url.trim()) {
      fd.append('firma_imagen_url', f.firma_imagen_url.trim());
    }

    return fd;
  }

  private irAlPasoConErrorServidor(campos: string[]): void {
    const mapCampoPaso: Record<string, number> = {
      nombre_organizacion: 1, tipo_organizacion: 1, numero_soporte_legal: 1,
      soporte_legal_url: 1, correo: 1, telefono: 1, upl: 1, barrio: 1, barrio_texto: 1,
      redes_facebook: 1, redes_instagram: 1, redes_otra: 1,
      rep_tipo_doc: 2, rep_numero_doc: 2, rep_nombre1: 2,
      rep_nombre2: 2, rep_apellido1: 2, rep_apellido2: 2,
      anios_experiencia: 3, nivel_educativo: 3, titulos_obtenidos: 3,
      escenarios: 4, escenarios_actuales: 4,
      rango_poblacion: 5, rango_etarios: 5, enfoques: 5,
      beneficiada_alk: 6, beneficios_alk: 6, impacto_politicas: 6, impacto_justificacion: 6,
      disciplina_principal: 7, implementos: 7, propuesta_descripcion: 7,
      firma_cedula: 8, firma_fecha: 8, firma_imagen: 8,
      compromiso_redes: 8, compromiso_carta_1ano: 8, compromiso_actualizacion: 8,
    };
    const pasos = campos.map((c) => mapCampoPaso[c] ?? 1);
    const minPaso = Math.min(...pasos);
    if (minPaso >= 1) this.pasoActual.set(minPaso);
  }

  // ── Helpers ───────────────────────────────────────────────────────
  toggleSet(set: Set<string>, valor: string): void {
    if (set.has(valor)) {
      set.delete(valor);
    } else {
      set.add(valor);
    }
  }

  fieldError(campo: string): string {
    const errs = this.erroresCampo()[campo];
    return errs?.length ? errs[0] : '';
  }

  labelSoporteLegal(): string {
    const perfil: Record<string, string> = {
      '1': 'Número de la resolución IDRD',
      '5': 'Número del aval deportivo',
      '2': 'NIT',
      '3': 'Referencia de la carta de conformación',
    };
    return perfil[this.form.tipo_organizacion] ?? 'Número del soporte legal';
  }

  placeholderSoporteLegal(): string {
    const ph: Record<string, string> = {
      '1': 'Ej. Resolución 123 de 2024',
      '5': 'Ej. Aval LFB 045-2024',
      '2': 'Ej. 900.123.456-7',
      '3': 'Ej. Carta del 12/03/2026',
    };
    return ph[this.form.tipo_organizacion] ?? '';
  }

  onFirmaChange(event: Event): void {
    const input = event.target as HTMLInputElement;
    const file = input.files?.[0];
    if (!file) return;

    if (file.size > 2 * 1024 * 1024) {
      this.firmaError.set('La imagen pesa más de 2 MB. Toma otra foto con menor calidad.');
      input.value = '';
      return;
    }

    this.firmaError.set('');
    this.form.firma_imagen = file;
    this.firmaNombre.set(`${file.name} (${Math.round(file.size / 1024)} KB)`);

    const reader = new FileReader();
    reader.onload = (e) => {
      this.firmaPreview.set(e.target?.result as string);
    };
    reader.readAsDataURL(file);
  }

  quitarFirma(): void {
    this.form.firma_imagen = null;
    this.firmaPreview.set(null);
    this.firmaNombre.set('');
    this.firmaError.set('');
  }

  autollenarRepresentante(): void {
    const doc = this.form.rep_numero_doc.trim();
    if (doc.length < 4) { this.autollenadoStatus.set(null); return; }

    this.http
      .get<{
        found: boolean;
        nombre1?: string;
        nombre2?: string;
        apellido1?: string;
        apellido2?: string;
      }>(this.cfg.url(`/caracterizacion/api/persona/?doc=${encodeURIComponent(doc)}`))
      .subscribe({
        next: (data) => {
          if (!data.found) {
            this.autollenadoStatus.set('nuevo');
            return;
          }
          if (!this.form.rep_nombre1 && data.nombre1) this.form.rep_nombre1 = data.nombre1;
          if (!this.form.rep_nombre2 && data.nombre2) this.form.rep_nombre2 = data.nombre2;
          if (!this.form.rep_apellido1 && data.apellido1) this.form.rep_apellido1 = data.apellido1;
          if (!this.form.rep_apellido2 && data.apellido2) this.form.rep_apellido2 = data.apellido2;
          this.autollenadoStatus.set('ok');
        },
        error: () => this.autollenadoStatus.set(null),
      });
  }

  /** Convierte un codigo (string|number) a string para usar con Set.has(). */
  codigoStr(v: string | number): string {
    return String(v);
  }

  private hoyISO(): string {
    return new Date().toISOString().split('T')[0];
  }
}
