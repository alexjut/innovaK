import { TitleCasePipe } from '@angular/common';
import { HttpClient } from '@angular/common/http';
import {
  Component,
  HostListener,
  OnDestroy,
  OnInit,
  computed,
  inject,
  signal,
} from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute } from '@angular/router';

import { ConfigService } from '../../core/config/config.service';
import {
  DireccionElegida,
  DireccionPickerComponent,
} from '../../shared/direccion/direccion-picker.component';

import { BancoBorradorService, BorradorRecuperado } from './banco/banco-borrador.service';
import {
  BancoAnexos,
  BancoCatalogos,
  BancoForm,
  COMPOSICION_GENERO_OPCIONES,
  FAMILIA_MUJER_GENERO_52,
  FilaPresupuesto,
  MAX_CARACTERES_METODOLOGIA,
  MAX_ENFOQUES_ADICIONALES_52,
  MIN_CARACTERES_NARRATIVA,
  MIN_PALABRAS_SUSTENTO,
  SECCIONES,
  TOPE_PRESUPUESTO_MAXIMO,
  TOTAL_SECCIONES,
  anexosVacios,
  codigoStr,
  contarPalabras,
  filaActividadVacia,
  filaEquipoVacia,
  filaPresupuestoVacia,
  formInicial,
  totalPresupuesto,
  totalRubro,
} from './banco/banco-form.model';
import { ContadorTextoComponent } from './banco/contador-texto.component';
import { CronogramaMatrizComponent } from './banco/cronograma-matriz.component';
import { EnfoquesCascadaComponent } from './banco/enfoques-cascada.component';
import { FirmaLienzoComponent } from './banco/firma-lienzo.component';
import { NivelEspacioComponent } from './banco/nivel-espacio.component';

interface ApiError {
  detail?: string;
  errors?: Record<string, string[]>;
}

/**
 * Formulario público del Banco de Iniciativas Recreodeportivas — DOCUMENTO
 * MAESTRO ESTRUCTURAL (Deportes, 2026-07-29).
 *
 * Nueve secciones con el mismo nombre en todo el aplicativo, en dos fases:
 * caracterización de la organización (§1-6) y presentación de la propuesta
 * (§7-9). Lo llena una organización de base, casi siempre desde un celular,
 * en 45 a 60 minutos.
 *
 * ── Tres reglas que no se negocian ─────────────────────────────────────
 *
 * 1. **El formulario es ciego.** No se muestra ningún puntaje, peso, ranking ni
 *    posición: el modelo autoliquida en el servidor y sin comisión revisora.
 *    Enseñar los puntos convertiría el formulario en un simulador de puntaje y
 *    premiaría a quien lo entiende, que es exactamente el sesgo que el modelo
 *    quiere erradicar. Se muestra el ORDEN de los enfoques (§7.8) porque el
 *    ciudadano lo decide, no los puntos que ese orden vale.
 *
 * 2. **Ningún dato se pierde.** 45-60 minutos sin red de seguridad, en un
 *    celular, sin login y sin etapa de subsanación, es una postulación que se
 *    pierde por una llamada entrante. El borrador se guarda solo (ver
 *    `BancoBorradorService`), y al volver se ofrece retomar donde iba.
 *
 * 3. **Las direcciones existen.** Nunca texto libre: se autocompletan contra
 *    Catastro con `app-direccion-picker` y se guardan con su coordenada. Del
 *    punto sale el estrato certificado por IDECA, y del estrato sale el
 *    puntaje territorial. Una dirección inventada es un puntaje inventado.
 */
@Component({
  standalone: true,
  selector: 'app-banco-publico',
  imports: [
    FormsModule,
    TitleCasePipe,
    DireccionPickerComponent,
    ContadorTextoComponent,
    CronogramaMatrizComponent,
    EnfoquesCascadaComponent,
    FirmaLienzoComponent,
    NivelEspacioComponent,
  ],
  template: `
    <!-- ══ CONVOCATORIA CERRADA ══ -->
    @if (cerrado()) {
      <div class="cerrado-wrap">
        <div class="cerrado-card">
          <div class="cerrado-icon" aria-hidden="true">🔒</div>
          <h1 class="cerrado-title">Convocatoria cerrada</h1>
          <p class="cerrado-msg">{{ cerradoMsg() }}</p>
          <p class="cerrado-sub">
            Esta convocatoria ya no acepta nuevas postulaciones. Contacta a la
            Alcaldía Local de Kennedy para más información.
          </p>
        </div>
      </div>
    }

    <!-- ══ CARGANDO ══ -->
    @if (!cerrado() && cargandoCatalogos()) {
      <div class="loading-wrap" role="status" aria-live="polite">
        <div class="loading-spinner" aria-hidden="true"></div>
        <p>Cargando formulario…</p>
      </div>
    }

    <!-- ══ ERROR AL CARGAR ══ -->
    @if (!cerrado() && !cargandoCatalogos() && errorCarga()) {
      <div class="error-wrap" role="alert">
        <div class="error-card">
          <div class="error-icon" aria-hidden="true">⚠️</div>
          <h1>Error al cargar</h1>
          <p>{{ errorCarga() }}</p>
          <button class="btn-brand btn-lg" (click)="cargarCatalogos()">Reintentar</button>
        </div>
      </div>
    }

    <!-- ══ RADICADO ══ -->
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
          <h1 class="exito-title">¡Postulación radicada!</h1>
          <p class="exito-desc">Tu iniciativa quedó registrada con fecha y hora.</p>
          @if (exitoId()) {
            <div class="exito-num">
              <span class="exito-num__label">Número de radicación</span>
              <span class="exito-num__val"># {{ exitoId() }}</span>
            </div>
          }
          <p class="exito-footer">
            Guarda este número: identifica tu postulación ante la Alcaldía Local
            de Kennedy.
          </p>
        </div>
      </div>
    }

    <!-- ══ BIENVENIDA Y ORIENTACIÓN AL CIUDADANO ══ -->
    @if (listo() && intro()) {
      <div class="intro">
        <div class="wiz-banner">
          <div class="wiz-banner__icon" aria-hidden="true">🏆</div>
          <div>
            <h1 class="wiz-banner__title">Banco de Iniciativas Recreodeportivas</h1>
            <p class="wiz-banner__sub">{{ catalogos()!.evento.nombre }}</p>
          </div>
        </div>

        <div class="intro__card">
          @if (hayBorrador()) {
            <div class="borrador-aviso" role="status">
              <p class="borrador-aviso__txt">
                Tienes un formulario a medio llenar, guardado el
                <strong>{{ borradorFecha() }}</strong>.
              </p>
              <p class="borrador-aviso__nota">
                Los textos y selecciones se recuperan; los <strong>archivos
                adjuntos hay que volver a seleccionarlos</strong> (el navegador
                no los puede guardar).
              </p>
              <div class="borrador-aviso__btns">
                <button type="button" class="btn-brand btn-sm" (click)="retomarBorrador()">
                  Continuar donde iba
                </button>
                <button type="button" class="btn-outline-brand btn-sm" (click)="descartarBorrador()">
                  Empezar de nuevo
                </button>
              </div>
            </div>
          }

          <p class="intro__lead">
            ¡Bienvenido al módulo de presentación de iniciativas recreodeportivas!
            Está accediendo a la plataforma oficial para el registro y postulación
            de proyectos ciudadanos liderados por colectivos y organizaciones de
            base. El aplicativo lo guía paso a paso en la estructuración
            metodológica de su propuesta.
          </p>

          <ul class="intro__list">
            <li>⏱️ Duración estimada: <strong>entre 45 y 60 minutos</strong>.</li>
            <li>💾 El formulario <strong>se guarda solo</strong> mientras lo llena; puede cerrarlo y volver en este mismo dispositivo.</li>
            <li>📶 Asegúrese de tener una <strong>conexión estable</strong>.</li>
            <li>📄 Tenga <strong>digitalizados en PDF legible</strong> los soportes de su organización.</li>
          </ul>

          <p class="intro__docs-title">Documentos que va a necesitar:</p>
          <ul class="intro__list">
            <li><strong>Sección 1:</strong> documento de identidad del representante legal y soporte legal de la organización (acta de constitución, personería jurídica o equivalente).</li>
            <li><strong>Secciones 1 y 9:</strong> RUT, reconocimiento deportivo o aval sectorial, según la naturaleza de su agrupación.</li>
          </ul>

          <p class="intro__docs-title">El formulario tiene 9 secciones:</p>
          <ol class="intro__list">
            @for (s of secciones; track s.n) {
              <li>{{ s.titulo }}</li>
            }
          </ol>

          <button type="button" class="btn-brand intro__btn" (click)="comenzar()">
            Comenzar →
          </button>
        </div>
      </div>
    }

    <!-- ══ FORMULARIO ══ -->
    @if (listo() && !intro()) {
      <header class="wiz-header" role="banner">
        <div class="wiz-banner">
          <div class="wiz-banner__icon" aria-hidden="true">🏆</div>
          <div>
            <h1 class="wiz-banner__title">Banco de Iniciativas Recreodeportivas</h1>
            <p class="wiz-banner__sub">{{ catalogos()!.evento.nombre }}</p>
          </div>
        </div>

        <div class="wiz-fases" aria-label="Fases del formulario">
          <div class="wiz-fase" [class.wiz-fase--active]="fase1Activa()">
            <span class="wiz-fase__num">Fase 1</span>
            <span class="wiz-fase__lbl">Caracterización</span>
            <span class="wiz-fase__rng">Secciones 1–6</span>
          </div>
          <div class="wiz-fase" [class.wiz-fase--active]="!fase1Activa()">
            <span class="wiz-fase__num">Fase 2</span>
            <span class="wiz-fase__lbl">Propuesta</span>
            <span class="wiz-fase__rng">Secciones 7–9</span>
          </div>
        </div>

        <div class="wiz-progress" aria-label="Progreso del formulario">
          <div class="wiz-progress__meta">
            <span>Sección <strong>{{ seccionActual() }}</strong> de <strong>{{ totalSecciones }}</strong></span>
            <span class="wiz-progress__title-mobile">{{ tituloSeccion() }}</span>
            <span>{{ progresoPct() }}%</span>
          </div>
          <div class="wiz-progress__bar-bg" role="progressbar"
               [attr.aria-valuenow]="progresoPct()" aria-valuemin="0" aria-valuemax="100">
            <div class="wiz-progress__bar-fill" [style.width.%]="progresoPct()"></div>
          </div>
        </div>

        <nav class="wiz-pills" aria-label="Secciones del formulario">
          @for (s of secciones; track s.n) {
            <button type="button" class="wiz-pill"
                    [class.wiz-pill--active]="seccionActual() === s.n"
                    [class.wiz-pill--done]="seccionActual() > s.n"
                    [disabled]="seccionActual() < s.n"
                    (click)="irASeccion(s.n)"
                    [attr.aria-current]="seccionActual() === s.n ? 'step' : null">
              <span class="wiz-pill__num">{{ s.n }}</span>
              <span class="wiz-pill__lbl">{{ s.corto }}</span>
            </button>
          }
        </nav>
      </header>

      @if (erroresServidor().length > 0) {
        <div class="wiz-server-errors" role="alert">
          <strong>El servidor rechazó la postulación:</strong>
          <ul>
            @for (err of erroresServidor(); track err) { <li>{{ err }}</li> }
          </ul>
        </div>
      }

      @if (erroresSeccion().length > 0) {
        <div class="wiz-server-errors" role="alert">
          <strong>Falta completar en esta sección:</strong>
          <ul>
            @for (err of erroresSeccion(); track err) { <li>{{ err }}</li> }
          </ul>
        </div>
      }

      <main class="wiz-main" (input)="marcarSucio()" (change)="marcarSucio()">

        <!-- ═══════════ SECCIÓN 1 · REGISTRO DE LA ORGANIZACIÓN ═══════════ -->
        @if (seccionActual() === 1) {
          <section class="wiz-step" aria-labelledby="s1">
            <h2 id="s1" class="wiz-step__title">Sección 1 · Registro de la organización</h2>
            <p class="wiz-step__hint">
              Datos básicos de registro, naturaleza jurídica de la organización y
              perfil formal de su representante autorizado ante la Alcaldía Local.
            </p>

            <div class="field field--required">
              <label class="field__label" for="nombre_organizacion">
                1.1 Nombre de la organización o colectivo
              </label>
              <input id="nombre_organizacion" type="text" class="field__input"
                     [(ngModel)]="form.nombre_organizacion"
                     autocomplete="organization" maxlength="200"
                     placeholder="Nombre completo de la organización o colectivo">
              @if (err('nombre_organizacion')) {
                <p class="field__error" role="alert">{{ err('nombre_organizacion') }}</p>
              }
            </div>

            <div class="field-row">
              <div class="field field--required">
                <label class="field__label" for="tipo_organizacion">1.2 Tipo de organización</label>
                <select id="tipo_organizacion" class="field__select" [(ngModel)]="form.tipo_organizacion">
                  <option value="">Selecciona…</option>
                  @for (t of catalogos()!.tipos_organizacion; track t.codigo) {
                    <option [value]="t.codigo">{{ t.nombre }}</option>
                  }
                </select>
                @if (err('tipo_organizacion')) {
                  <p class="field__error" role="alert">{{ err('tipo_organizacion') }}</p>
                }
              </div>

              <div class="field">
                <label class="field__label" for="numero_soporte_legal">
                  1.3 Número del soporte legal / NIT / Registro
                  <span class="field__optional">opcional</span>
                </label>
                <input id="numero_soporte_legal" type="text" class="field__input"
                       [(ngModel)]="form.numero_soporte_legal"
                       placeholder="Ej. Resolución 123 de 2024">
              </div>
            </div>

            <div class="field field--required">
              <label class="field__label" for="a_soporte_legal">
                1.4 Soporte legal de la organización
              </label>
              <p class="field__hint">
                Documento de constitución, personería jurídica o reconocimiento,
                en PDF. Queda almacenado dentro del aplicativo y se integra al
                consolidado final de su propuesta. Peso máximo: 2 MB.
              </p>
              <label class="anexo" for="a_soporte_legal"
                     [class.anexo--ok]="!!anexos.soporte_legal">
                <span class="anexo__icon" aria-hidden="true">📎</span>
                <span class="anexo__txt">
                  {{ nombreAnexo('soporte_legal') || 'Seleccionar archivo PDF' }}
                </span>
              </label>
              <input id="a_soporte_legal" type="file" class="anexo__input"
                     accept="application/pdf"
                     (change)="onAnexo('soporte_legal', $event)">
            </div>

            <h3 class="wiz-section-title">
              <span aria-hidden="true">🧑</span> Representante legal
            </h3>

            <div class="field-row">
              <div class="field field--required">
                <label class="field__label" for="rep_tipo_doc">1.6 Tipo de documento</label>
                <select id="rep_tipo_doc" class="field__select" [(ngModel)]="form.rep_tipo_doc">
                  <option value="">Selecciona…</option>
                  @for (t of catalogos()!.tipos_documento; track t.codigo) {
                    <option [value]="t.codigo">{{ t.nombre }}</option>
                  }
                </select>
              </div>
              <div class="field field--required">
                <label class="field__label" for="rep_numero_doc">1.7 Número de documento</label>
                <input id="rep_numero_doc" type="text" class="field__input"
                       [(ngModel)]="form.rep_numero_doc"
                       (blur)="autollenarRepresentante()"
                       inputmode="numeric" minlength="5" maxlength="15"
                       placeholder="12345678">
                @if (autollenado()) {
                  <p class="field__status" [class.field__status--ok]="autollenado() === 'ok'"
                     role="status" aria-live="polite">
                    @if (autollenado() === 'ok') { ✓ Representante ya registrado — datos cargados. }
                    @if (autollenado() === 'nuevo') { Persona nueva — completa los datos. }
                  </p>
                }
              </div>
            </div>

            <p class="field__label">1.5 Nombre completo del representante legal</p>
            <div class="field-row">
              <div class="field field--required">
                <label class="field__label" for="rep_nombre1">Primer nombre</label>
                <input id="rep_nombre1" type="text" class="field__input"
                       [(ngModel)]="form.rep_nombre1" autocomplete="given-name" maxlength="50">
              </div>
              <div class="field">
                <label class="field__label" for="rep_nombre2">
                  Segundo nombre <span class="field__optional">opcional</span>
                </label>
                <input id="rep_nombre2" type="text" class="field__input"
                       [(ngModel)]="form.rep_nombre2" autocomplete="additional-name" maxlength="50">
              </div>
            </div>
            <div class="field-row">
              <div class="field field--required">
                <label class="field__label" for="rep_apellido1">Primer apellido</label>
                <input id="rep_apellido1" type="text" class="field__input"
                       [(ngModel)]="form.rep_apellido1" autocomplete="family-name" maxlength="50">
              </div>
              <div class="field">
                <label class="field__label" for="rep_apellido2">
                  Segundo apellido <span class="field__optional">opcional</span>
                </label>
                <input id="rep_apellido2" type="text" class="field__input"
                       [(ngModel)]="form.rep_apellido2" maxlength="50">
              </div>
            </div>

            <div class="field field--required">
              <label class="field__label" for="a_cedula">
                1.8 Documento de identidad del representante legal
              </label>
              <p class="field__hint">Cédula en PDF, hasta 2 MB.</p>
              <label class="anexo" for="a_cedula" [class.anexo--ok]="!!anexos.cedula_representante">
                <span class="anexo__icon" aria-hidden="true">🪪</span>
                <span class="anexo__txt">
                  {{ nombreAnexo('cedula_representante') || 'Seleccionar archivo' }}
                </span>
              </label>
              <input id="a_cedula" type="file" class="anexo__input"
                     accept="application/pdf"
                     (change)="onAnexo('cedula_representante', $event)">
            </div>

            <div class="field">
              <label class="field__label" for="nivel_educativo">
                1.9 Nivel educativo del representante legal
                <span class="field__optional">opcional</span>
              </label>
              <select id="nivel_educativo" class="field__select" [(ngModel)]="form.nivel_educativo">
                <option value="">Selecciona…</option>
                @for (n of catalogos()!.niveles_educativos; track n.codigo) {
                  <option [value]="n.codigo">{{ n.nombre }}</option>
                }
              </select>
            </div>

            <div class="field">
              <label class="field__label" for="titulos_obtenidos">
                1.10 Títulos u honores obtenidos por el representante legal
                <span class="field__optional">opcional</span>
              </label>
              <textarea id="titulos_obtenidos" class="field__textarea" rows="3"
                        [(ngModel)]="form.titulos_obtenidos"
                        placeholder="Ej. Técnico en deportes SENA, licenciado en educación física, diplomado en gestión comunitaria…"></textarea>
            </div>

            <h3 class="wiz-section-title">
              <span aria-hidden="true">📁</span> Soportes complementarios
              <span class="field__optional">según su tipo de organización</span>
            </h3>

            <div class="field">
              <label class="field__label" for="a_rut">RUT</label>
              <label class="anexo" for="a_rut" [class.anexo--ok]="!!anexos.rut">
                <span class="anexo__icon" aria-hidden="true">📎</span>
                <span class="anexo__txt">{{ nombreAnexo('rut') || 'Seleccionar archivo' }}</span>
              </label>
              <input id="a_rut" type="file" class="anexo__input"
                     accept="application/pdf" (change)="onAnexo('rut', $event)">
            </div>

            <div class="field">
              <label class="field__label" for="a_recon">Reconocimiento deportivo o aval sectorial</label>
              <label class="anexo" for="a_recon" [class.anexo--ok]="!!anexos.reconocimiento_deportivo">
                <span class="anexo__icon" aria-hidden="true">📎</span>
                <span class="anexo__txt">
                  {{ nombreAnexo('reconocimiento_deportivo') || 'Seleccionar archivo' }}
                </span>
              </label>
              <input id="a_recon" type="file" class="anexo__input"
                     accept="application/pdf"
                     (change)="onAnexo('reconocimiento_deportivo', $event)">
            </div>

            <!-- Soportes de la sección 1 (Documento Guía) -->
            <div class="soportes">
              <h3 class="soportes__title">Soportes de esta sección</h3>
              <p class="soportes__hint">Documento de elegibilidad territorial. No otorga puntaje.</p>
              <div class="field">
                <label class="field__label" for="a_residencia_representante">Certificado de residencia del representante o recibo de servicio público de Kennedy</label>
                <p class="field__hint">Acredita que el representante reside en la localidad.</p>
                <label class="anexo" for="a_residencia_representante" [class.anexo--ok]="!!anexos.residencia_representante">
                  <span class="anexo__icon" aria-hidden="true">📎</span>
                  <span class="anexo__txt">{{ nombreAnexo('residencia_representante') || 'Seleccionar archivo (PDF)' }}</span>
                </label>
                <input id="a_residencia_representante" type="file" class="anexo__input"
                       accept="application/pdf" (change)="onAnexo('residencia_representante', $event)">
              </div>
            </div>

          </section>
        }

        <!-- ═══════════ SECCIÓN 2 · CONTACTO Y UBICACIÓN ═══════════ -->
        @if (seccionActual() === 2) {
          <section class="wiz-step" aria-labelledby="s2">
            <h2 id="s2" class="wiz-step__title">Sección 2 · Contacto y ubicación</h2>
            <p class="wiz-step__hint">
              Canales oficiales de comunicación digital y ubicación física de
              operaciones del colectivo en la localidad. Estructura el directorio
              de contacto para las fases de supervisión del programa.
            </p>

            <div class="field-row">
              <div class="field field--required">
                <label class="field__label" for="telefono">
                  2.1 Teléfono del colectivo o de su representante
                </label>
                <input id="telefono" type="tel" class="field__input" [(ngModel)]="form.telefono"
                       autocomplete="tel" inputmode="tel" placeholder="3001234567">
              </div>
              <div class="field field--required">
                <label class="field__label" for="correo">
                  2.2 Correo electrónico del colectivo o de su representante
                </label>
                <input id="correo" type="email" class="field__input" [(ngModel)]="form.correo"
                       autocomplete="email" inputmode="email" placeholder="correo@ejemplo.com">
              </div>
            </div>

            <div class="field field--required">
              <label class="field__label">
                ¿El colectivo u organización cuenta con sede física?
              </label>
              <div class="radio-row">
                <label class="radio-label">
                  <input type="radio" name="sede" [value]="true"
                         [(ngModel)]="form.tiene_sede_fisica">
                  <span>Sí</span>
                </label>
                <label class="radio-label">
                  <input type="radio" name="sede" [value]="false"
                         [(ngModel)]="form.tiene_sede_fisica">
                  <span>No</span>
                </label>
              </div>
              @if (form.tiene_sede_fisica === false) {
                <p class="field__hint">
                  Entendido: no se pedirán los datos de sede y se registrarán como
                  «no aplica».
                </p>
              }
            </div>

            @if (form.tiene_sede_fisica === true) {
              <div class="conditional-block">
                <div class="field-row">
                  <div class="field field--required">
                    <label class="field__label" for="barrio">
                      2.3 Barrio de la sede administrativa u operativa
                    </label>
                    <!-- Select y no texto libre: el barrio tiene que existir en
                         el catálogo de la localidad. Un barrio escrito a mano no
                         se puede cruzar con nada después. -->
                    <select id="barrio" class="field__select" [(ngModel)]="form.barrio">
                      <option value="">Selecciona el barrio…</option>
                      @for (b of catalogos()!.barrios; track b.codigo) {
                        <option [value]="b.codigo">{{ b.nombre | titlecase }}</option>
                      }
                    </select>
                  </div>
                  <div class="field">
                    <label class="field__label" for="upz">
                      UPZ <span class="field__optional">opcional</span>
                    </label>
                    <select id="upz" class="field__select" [(ngModel)]="form.upz">
                      <option value="">Selecciona UPZ…</option>
                      @for (z of catalogos()!.upzs; track z.codigo) {
                        <option [value]="z.codigo">{{ z.nombre | titlecase }}</option>
                      }
                    </select>
                  </div>
                </div>

                <div class="field field--required">
                  <!-- La dirección se ELIGE contra Catastro y queda con su punto:
                       de ahí sale el estrato certificado, no del texto escrito. -->
                  <app-direccion-picker
                    label="2.4 Dirección exacta de la sede"
                    placeholder="Escribe y elige de la lista: Calle 40 # 70-15"
                    [valor]="form.direccion"
                    (direccionElegida)="onDireccionSede($event)" />
                  @if (!form.direccion) {
                    <p class="field__hint">
                      Escribe la dirección y elige una de las opciones que aparecen.
                    </p>
                  }
                </div>

                <div class="field field--required">
                  <label class="field__label" for="estrato">
                    2.5 Estrato socioeconómico de la sede
                  </label>
                  <select id="estrato" class="field__select" [(ngModel)]="form.estrato">
                    <option value="">Selecciona…</option>
                    @for (e of catalogos()!.estratos; track e) {
                      <option [value]="e">Estrato {{ e }}</option>
                    }
                  </select>
                </div>
              </div>
            }

            <h3 class="wiz-section-title">
              <span aria-hidden="true">🔗</span> Presencia digital
              <span class="field__optional">opcional</span>
            </h3>
            <div class="field-row field-row--3">
              <div class="field">
                <label class="field__label" for="redes_web">2.6 Página web o plataforma virtual</label>
                <input id="redes_web" type="url" class="field__input" [(ngModel)]="form.redes_web"
                       inputmode="url" placeholder="https://…">
              </div>
              <div class="field">
                <label class="field__label" for="redes_facebook">2.7 Perfil oficial de Facebook</label>
                <input id="redes_facebook" type="url" class="field__input"
                       [(ngModel)]="form.redes_facebook" inputmode="url"
                       placeholder="https://facebook.com/…">
              </div>
              <div class="field">
                <label class="field__label" for="redes_instagram">2.8 Perfil oficial de Instagram</label>
                <input id="redes_instagram" type="url" class="field__input"
                       [(ngModel)]="form.redes_instagram" inputmode="url"
                       placeholder="https://instagram.com/…">
              </div>
            </div>
          </section>
        }

        <!-- ═══════════ SECCIÓN 3 · CAPACIDAD DE LA ORGANIZACIÓN ═══════════ -->
        @if (seccionActual() === 3) {
          <section class="wiz-step" aria-labelledby="s3">
            <h2 id="s3" class="wiz-step__title">Sección 3 · Capacidad de la organización</h2>
            <p class="wiz-step__hint">
              Solidez operativa, antigüedad del colectivo y estructuras de
              permanencia en el territorio de base.
            </p>

            <div class="field field--required">
              <label class="field__label" for="tamano_staff_num">
                3.1 Tamaño de la organización (capacidad operativa interna)
              </label>
              <p class="field__hint">
                Ingrese el número exacto de personas activas que integran el staff,
                comité o equipo de trabajo de la organización.
              </p>
              <input id="tamano_staff_num" type="number" class="field__input"
                     [(ngModel)]="form.tamano_staff_num"
                     min="1" max="9999" step="1" inputmode="numeric" placeholder="Ej. 25">
            </div>

            <div class="field field--required">
              <label class="field__label" for="anios_experiencia">
                3.2 Años de trayectoria comunitaria demostrable del colectivo
              </label>
              <select id="anios_experiencia" class="field__select" [(ngModel)]="form.anios_experiencia">
                <option value="">Selecciona…</option>
                @for (r of catalogos()!.rangos_experiencia; track r.codigo) {
                  <option [value]="r.codigo">{{ r.nombre }}</option>
                }
              </select>
            </div>

            <div class="field field--required">
              <label class="field__label" for="composicion_organizacion">
                3.3 Composición y liderazgo de género
              </label>
              <select id="composicion_organizacion" class="field__select"
                      [(ngModel)]="form.composicion_organizacion">
                <option value="">Selecciona…</option>
                @for (c of composicionOpciones; track c.valor) {
                  <option [value]="c.valor">{{ c.etiqueta }}</option>
                }
              </select>
            </div>

            <div class="field field--required">
              <label class="field__label" for="rango_poblacion">
                3.4 Cantidad actual de personas que beneficia o atiende su organización
              </label>
              <p class="field__hint">
                Seleccione el rango de usuarios atendidos recurrentemente en los
                procesos comunitarios ejecutados en la localidad.
              </p>
              <select id="rango_poblacion" class="field__select" [(ngModel)]="form.rango_poblacion">
                <option value="">Selecciona…</option>
                @for (r of catalogos()!.rangos_poblacion; track r.codigo) {
                  <option [value]="r.codigo">{{ r.nombre }}</option>
                }
              </select>
            </div>

            <!-- Soportes de la sección 3 (Documento Guía) -->
            <div class="soportes">
              <h3 class="soportes__title">Soportes de esta sección</h3>
              <p class="soportes__hint">Estos documentos respaldan el puntaje de esta sección. Si una respuesta puntúa y no trae su soporte, ese criterio no se califica.</p>
              <div class="field">
                <label class="field__label" for="a_staff_listado">§3.1 · Listado del staff</label>
                <p class="field__hint">Nombres, identificación, funciones y firma de cada integrante.</p>
                <label class="anexo" for="a_staff_listado" [class.anexo--ok]="!!anexos.staff_listado">
                  <span class="anexo__icon" aria-hidden="true">📎</span>
                  <span class="anexo__txt">{{ nombreAnexo('staff_listado') || 'Seleccionar archivo (PDF)' }}</span>
                </label>
                <input id="a_staff_listado" type="file" class="anexo__input"
                       accept="application/pdf" (change)="onAnexo('staff_listado', $event)">
              </div>
              <div class="field">
                <label class="field__label" for="a_trayectoria">§3.2 · Certificaciones de trayectoria</label>
                <p class="field__hint">Emitidas por JAC, organizaciones legalmente constituidas o actas de eventos anteriores.</p>
                <label class="anexo" for="a_trayectoria" [class.anexo--ok]="!!anexos.trayectoria">
                  <span class="anexo__icon" aria-hidden="true">📎</span>
                  <span class="anexo__txt">{{ nombreAnexo('trayectoria') || 'Seleccionar archivo (PDF)' }}</span>
                </label>
                <input id="a_trayectoria" type="file" class="anexo__input"
                       accept="application/pdf" (change)="onAnexo('trayectoria', $event)">
              </div>
              <div class="field">
                <label class="field__label" for="a_composicion_genero">§3.3 · Conformación de género</label>
                <p class="field__hint">Acta de elección de dignatarios, estatutos o declaración juramentada.</p>
                <label class="anexo" for="a_composicion_genero" [class.anexo--ok]="!!anexos.composicion_genero">
                  <span class="anexo__icon" aria-hidden="true">📎</span>
                  <span class="anexo__txt">{{ nombreAnexo('composicion_genero') || 'Seleccionar archivo (PDF)' }}</span>
                </label>
                <input id="a_composicion_genero" type="file" class="anexo__input"
                       accept="application/pdf" (change)="onAnexo('composicion_genero', $event)">
              </div>
              <div class="field">
                <label class="field__label" for="a_beneficiarios_listado">§3.4 · Listado de beneficiarios</label>
                <p class="field__hint">Planillas de asistencia con firmas o registro fotográfico fechado.</p>
                <label class="anexo" for="a_beneficiarios_listado" [class.anexo--ok]="!!anexos.beneficiarios_listado">
                  <span class="anexo__icon" aria-hidden="true">📎</span>
                  <span class="anexo__txt">{{ nombreAnexo('beneficiarios_listado') || 'Seleccionar archivo (PDF)' }}</span>
                </label>
                <input id="a_beneficiarios_listado" type="file" class="anexo__input"
                       accept="application/pdf" (change)="onAnexo('beneficiarios_listado', $event)">
              </div>
            </div>

          </section>
        }

        <!-- ═══════════ SECCIÓN 4 · ARRAIGO TERRITORIAL ═══════════ -->
        @if (seccionActual() === 4) {
          <section class="wiz-step" aria-labelledby="s4">
            <h2 id="s4" class="wiz-step__title">Sección 4 · Arraigo territorial</h2>
            <p class="wiz-step__hint">
              Caracterización técnica y espacial de las actividades misionales de
              la organización, mapeando los entornos públicos donde consolida su
              arraigo territorial.
            </p>

            <div class="field field--required">
              <label class="field__label" for="modalidad_actividad">
                4.1 Actividad principal que desarrolla la organización
              </label>
              <select id="modalidad_actividad" class="field__select"
                      [(ngModel)]="form.modalidad_actividad">
                <option value="">Selecciona…</option>
                @for (m of catalogos()!.modalidades; track m.codigo) {
                  <option [value]="m.codigo">{{ m.nombre }}</option>
                }
              </select>
            </div>

            @if (form.modalidad_actividad) {
              <div class="conditional-block">
                <div class="field-row">
                  <div class="field">
                    <label class="field__label" for="disciplina_actividad">
                      Disciplina deportiva
                    </label>
                    <select id="disciplina_actividad" class="field__select"
                            [(ngModel)]="form.disciplina_actividad">
                      <option value="">Selecciona…</option>
                      @for (d of catalogos()!.disciplinas_deportivas; track d.codigo) {
                        <option [value]="d.codigo">{{ d.nombre }}</option>
                      }
                    </select>
                  </div>
                  <div class="field">
                    <label class="field__label" for="disciplina_actividad_otro">
                      Otros — si no está en la lista
                    </label>
                    <input id="disciplina_actividad_otro" type="text" class="field__input"
                           [(ngModel)]="form.disciplina_actividad_otro" maxlength="150"
                           placeholder="Otra disciplina o actividad">
                  </div>
                </div>
              </div>
            }

            <h3 class="wiz-section-title">
              <span aria-hidden="true">🗺️</span>
              4.2 Clasificación de entornos de práctica territorial
              <span class="required-mark">*</span>
            </h3>
            <p class="field__hint" style="margin-bottom: 0.75rem;">
              Elija el nivel de espacio que corresponde a su práctica; al hacerlo
              se habilitan los botones de ese nivel.
            </p>

            <app-nivel-espacio
              [redes]="catalogos()!.redes"
              [escenarios]="catalogos()!.escenarios"
              [redSeleccionada]="form.arraigo_red"
              (redSeleccionadaChange)="form.arraigo_red = $event"
              [seleccion]="form.arraigo_escenarios"
              [otro]="form.arraigo_escenario_otro"
              (otroChange)="form.arraigo_escenario_otro = $event"
              idOtro="arraigo_otro"
              (cambio)="marcarSucio()" />

            @if (form.arraigo_red) {
              <h3 class="wiz-section-title">
                <span aria-hidden="true">📍</span> Localización del espacio
                <span class="required-mark">*</span>
              </h3>

              <div class="field field--required">
                <label class="field__label" for="arraigo_espacio_nombre">Parque o espacio</label>
                <input id="arraigo_espacio_nombre" type="text" class="field__input"
                       [(ngModel)]="form.arraigo_espacio_nombre" maxlength="150"
                       placeholder="Ej. Parque Cayetano Cañizares">
              </div>

              <div class="field field--required">
                <app-direccion-picker
                  label="Dirección exacta"
                  placeholder="Escribe y elige de la lista: Cra 86 # 6-30"
                  [valor]="form.arraigo_direccion"
                  (direccionElegida)="onDireccionArraigo($event)" />
              </div>

              <div class="field field--required">
                <label class="field__label" for="arraigo_estrato">Estrato</label>
                <select id="arraigo_estrato" class="field__select" [(ngModel)]="form.arraigo_estrato">
                  <option value="">Selecciona…</option>
                  @for (e of catalogos()!.estratos; track e) {
                    <option [value]="e">Estrato {{ e }}</option>
                  }
                </select>
              </div>

              <div class="field field--required">
                <label class="field__label" for="arraigo_actividad">
                  Actividad específica que desarrolla allí
                </label>
                <textarea id="arraigo_actividad" class="field__textarea" rows="3"
                          [(ngModel)]="form.arraigo_actividad"
                          placeholder="Describe qué hace la organización en ese espacio"></textarea>
              </div>
            }

            <!-- Soportes de la sección 4 (Documento Guía) -->
            <div class="soportes">
              <h3 class="soportes__title">Soportes de esta sección</h3>
              <p class="soportes__hint">Estos documentos respaldan el puntaje de esta sección. Si una respuesta puntúa y no trae su soporte, ese criterio no se califica.</p>
              <div class="field">
                <label class="field__label" for="a_arraigo_uso_espacio">§4.2 · Uso del escenario y estrato</label>
                <p class="field__hint">Autorización de uso (JAC o IDRD) con registro fotográfico, y recibo de servicio público que acredite el estrato.</p>
                <label class="anexo" for="a_arraigo_uso_espacio" [class.anexo--ok]="!!anexos.arraigo_uso_espacio">
                  <span class="anexo__icon" aria-hidden="true">📎</span>
                  <span class="anexo__txt">{{ nombreAnexo('arraigo_uso_espacio') || 'Seleccionar archivo (PDF)' }}</span>
                </label>
                <input id="a_arraigo_uso_espacio" type="file" class="anexo__input"
                       accept="application/pdf" (change)="onAnexo('arraigo_uso_espacio', $event)">
              </div>
            </div>

          </section>
        }

        <!-- ═══════════ SECCIÓN 5 · DIVERSIDAD E INCLUSIÓN ═══════════ -->
        @if (seccionActual() === 5) {
          <section class="wiz-step" aria-labelledby="s5">
            <h2 id="s5" class="wiz-step__title">Sección 5 · Diversidad e inclusión comunitaria</h2>
            <p class="wiz-step__hint">
              Censo demográfico y mapa de inclusión de las comunidades atendidas
              de manera directa por la agrupación.
            </p>

            <div class="field field--required">
              <label class="field__label">
                5.1 Rangos etarios de la población atendida de manera directa
              </label>
              <p class="field__hint" style="margin-bottom: 0.5rem;">
                Indique el rango etario principal beneficiado; se priorizan
                poblaciones de mayor vulnerabilidad.
              </p>
              <div class="chips-grid">
                @for (r of catalogos()!.rangos_etarios; track r.codigo) {
                  <button type="button" class="chip chip--etario"
                          [class.chip--active]="form.rango_etarios.has(cod(r.codigo))"
                          [attr.aria-pressed]="form.rango_etarios.has(cod(r.codigo))"
                          (click)="alternar(form.rango_etarios, cod(r.codigo))">
                    {{ r.nombre }}
                    @if (r.edad_min != null && r.edad_max != null) {
                      <small>({{ r.edad_min }}–{{ r.edad_max }} años)</small>
                    }
                  </button>
                }
              </div>
            </div>

            <div class="field field--required">
              <label class="field__label">
                5.2 Enfoques poblacionales diferenciales de inclusión que atiende
                su organización
              </label>
              <p class="field__hint" style="margin-bottom: 0.75rem;">
                Seleccione el o los enfoques poblacionales centrales de su
                organización. El enfoque «Mujer y Género» se registra aparte;
                además puede marcar hasta {{ maxAdicionales52() }} enfoques más.
                Al marcar uno, precise las opciones de su submenú.
              </p>
              <app-enfoques-cascada
                [familias]="catalogos()!.enfoques_familias_52"
                [seleccion]="form.enfoques_52"
                [maxAdicionales]="maxAdicionales52()"
                [familiaBase]="familiaMujerGenero"
                (cambio)="marcarSucio()" />
            </div>

            <!-- Soportes de la sección 5 (Documento Guía) -->
            <div class="soportes">
              <h3 class="soportes__title">Soportes de esta sección</h3>
              <p class="soportes__hint">Estos documentos respaldan el puntaje de esta sección. Si una respuesta puntúa y no trae su soporte, ese criterio no se califica.</p>
              <div class="field">
                <label class="field__label" for="a_caracterizacion_demografica">§5.1 · Caracterización demográfica</label>
                <p class="field__hint">Distribución numérica de la población atendida por ciclos vitales.</p>
                <label class="anexo" for="a_caracterizacion_demografica" [class.anexo--ok]="!!anexos.caracterizacion_demografica">
                  <span class="anexo__icon" aria-hidden="true">📎</span>
                  <span class="anexo__txt">{{ nombreAnexo('caracterizacion_demografica') || 'Seleccionar archivo (PDF)' }}</span>
                </label>
                <input id="a_caracterizacion_demografica" type="file" class="anexo__input"
                       accept="application/pdf" (change)="onAnexo('caracterizacion_demografica', $event)">
              </div>
            </div>

          </section>
        }

        <!-- ═══════════ SECCIÓN 6 · PARTICIPACIÓN ═══════════ -->
        @if (seccionActual() === 6) {
          <section class="wiz-step" aria-labelledby="s6">
            <h2 id="s6" class="wiz-step__title">Sección 6 · Participación</h2>
            <p class="wiz-step__hint">
              Incidencia de la organización en espacios de participación y
              gobernanza territorial.
            </p>

            <div class="field field--required">
              <label class="field__label">
                ¿Tu organización está vinculada a algún espacio de participación local?
              </label>
              <div class="radio-row">
                <label class="radio-label">
                  <input type="radio" name="participa" [value]="true"
                         [(ngModel)]="form.participa_espacio">
                  <span>Sí</span>
                </label>
                <label class="radio-label">
                  <input type="radio" name="participa" [value]="false"
                         [(ngModel)]="form.participa_espacio">
                  <span>No</span>
                </label>
              </div>
            </div>

            @if (form.participa_espacio === true) {
              <div class="conditional-block">
                <div class="field field--required">
                  <label class="field__label">
                    6.1 Instancias o procesos de concertación ciudadana en donde
                    interviene activamente el colectivo
                  </label>
                  <p class="field__hint" style="margin-bottom: 0.5rem;">
                    Puede marcar varias.
                  </p>
                  <!-- El atributo open es estático, NO un binding: si Angular
                       reevaluara el estado abierto en cada ciclo, marcar la
                       primera instancia cerraría el menú en la cara del usuario
                       justo cuando va a marcar la segunda. -->
                  <details class="multiselect" open>
                    <summary class="multiselect__summary">
                      @if (form.instancias.size === 0) {
                        Instancias de concertación
                      } @else {
                        {{ form.instancias.size }} instancia(s) seleccionada(s)
                      }
                    </summary>
                    <div class="multiselect__body">
                      @for (i of catalogos()!.instancias_concertacion; track i.codigo) {
                        <label class="checkbox-label">
                          <input type="checkbox" class="checkbox-input"
                                 [checked]="form.instancias.has(cod(i.codigo))"
                                 (change)="alternar(form.instancias, cod(i.codigo))">
                          <span class="checkbox-text">{{ i.nombre }}</span>
                        </label>
                      }
                    </div>
                  </details>
                </div>
              </div>
            }

            <div class="field field--required">
              <label class="field__label">
                6.2 Experiencia previa en ejecución de proyectos o cofinanciaciones
                con la Alcaldía Local de Kennedy
              </label>
              <p class="field__hint" style="margin-bottom: 0.5rem;">
                Elija una sola opción, la que mejor describa el apoyo recibido.
              </p>
              <div class="radio-col">
                @for (b of catalogos()!.tipos_beneficio_alk; track b.codigo) {
                  <label class="radio-label radio-label--block">
                    <input type="radio" name="beneficio_alk" [value]="cod(b.codigo)"
                           [(ngModel)]="form.beneficio_alk">
                    <span>{{ b.nombre }}</span>
                  </label>
                }
              </div>
            </div>

            <!-- Soportes de la sección 6 (Documento Guía) -->
            <div class="soportes">
              <h3 class="soportes__title">Soportes de esta sección</h3>
              <p class="soportes__hint">Estos documentos respaldan el puntaje de esta sección. Si una respuesta puntúa y no trae su soporte, ese criterio no se califica.</p>
              <div class="field">
                <label class="field__label" for="a_instancias_actas">§6.1 · Participación en instancias</label>
                <p class="field__hint">Actas de asistencia o certificación de delegación vigente.</p>
                <label class="anexo" for="a_instancias_actas" [class.anexo--ok]="!!anexos.instancias_actas">
                  <span class="anexo__icon" aria-hidden="true">📎</span>
                  <span class="anexo__txt">{{ nombreAnexo('instancias_actas') || 'Seleccionar archivo (PDF)' }}</span>
                </label>
                <input id="a_instancias_actas" type="file" class="anexo__input"
                       accept="application/pdf" (change)="onAnexo('instancias_actas', $event)">
              </div>
              <div class="field">
                <label class="field__label" for="a_declaracion_antecedentes">§6.2 · Antecedentes con la ALK</label>
                <p class="field__hint">Declaración juramentada firmada por el representante legal.</p>
                <label class="anexo" for="a_declaracion_antecedentes" [class.anexo--ok]="!!anexos.declaracion_antecedentes">
                  <span class="anexo__icon" aria-hidden="true">📎</span>
                  <span class="anexo__txt">{{ nombreAnexo('declaracion_antecedentes') || 'Seleccionar archivo (PDF)' }}</span>
                </label>
                <input id="a_declaracion_antecedentes" type="file" class="anexo__input"
                       accept="application/pdf" (change)="onAnexo('declaracion_antecedentes', $event)">
              </div>
            </div>

          </section>
        }

        <!-- ═══════════ SECCIÓN 7 · FORMULACIÓN DE LA INICIATIVA ═══════════ -->
        @if (seccionActual() === 7) {
          <section class="wiz-step" aria-labelledby="s7">
            <h2 id="s7" class="wiz-step__title">Sección 7 · Formulación de la iniciativa y enfoques</h2>
            <p class="wiz-step__hint">
              Estructuración técnica y metodológica de la iniciativa
              recreodeportiva que presenta a la convocatoria.
            </p>

            <div class="field field--required">
              <label class="field__label" for="problematica">
                7.1 Situación o problemática a solucionar
              </label>
              <p class="field__hint" style="margin-bottom: 0.5rem;">
                Exponga la situación o problemática principal que su iniciativa
                aborda en su territorio.
              </p>
              <textarea id="problematica" class="field__textarea" rows="6"
                        [(ngModel)]="form.problematica"
                        placeholder="Describe la problemática concreta de tu territorio"></textarea>
              <app-contador-texto [texto]="form.problematica"
                                  [minCaracteres]="minNarrativa()" />
            </div>

            <div class="field field--required">
              <label class="field__label" for="justificacion">
                7.2 Justificación de la iniciativa
              </label>
              <p class="field__hint" style="margin-bottom: 0.5rem;">
                Argumente la pertinencia de la propuesta y su impacto esperado en
                el territorio.
              </p>
              <textarea id="justificacion" class="field__textarea" rows="6"
                        [(ngModel)]="form.justificacion"
                        placeholder="Explica por qué esta propuesta es pertinente"></textarea>
              <app-contador-texto [texto]="form.justificacion"
                                  [minCaracteres]="minNarrativa()" />
            </div>

            <div class="field field--required">
              <label class="field__label" for="modalidad_propuesta">
                7.3 Actividad técnica a desarrollar
              </label>
              <p class="field__hint" style="margin-bottom: 0.5rem;">
                Seleccione la modalidad recreodeportiva base y la disciplina que
                enmarcan la ejecución del proyecto.
              </p>
              <select id="modalidad_propuesta" class="field__select"
                      [(ngModel)]="form.modalidad_propuesta">
                <option value="">Selecciona…</option>
                @for (m of catalogos()!.modalidades; track m.codigo) {
                  <option [value]="m.codigo">{{ m.nombre }}</option>
                }
              </select>
            </div>

            @if (form.modalidad_propuesta) {
              <div class="conditional-block">
                <div class="field-row">
                  <div class="field">
                    <label class="field__label" for="disciplina_principal">
                      Disciplina
                    </label>
                    <select id="disciplina_principal" class="field__select"
                            [(ngModel)]="form.disciplina_principal">
                      <option value="">Selecciona…</option>
                      @for (d of catalogos()!.disciplinas_deportivas; track d.codigo) {
                        <option [value]="d.codigo">{{ d.nombre }}</option>
                      }
                    </select>
                  </div>
                  <div class="field">
                    <label class="field__label" for="otros_deportes">
                      Otros — si no está en la lista
                    </label>
                    <input id="otros_deportes" type="text" class="field__input"
                           [(ngModel)]="form.otros_deportes"
                           placeholder="Otras disciplinas o actividades">
                  </div>
                </div>
              </div>
            }

            <h3 class="wiz-section-title">
              <span aria-hidden="true">🎯</span> 7.4 Objetivos de la iniciativa
            </h3>
            <p class="field__hint" style="margin-bottom: 0.75rem;">
              Estructure las metas del proyecto dividiendo el propósito central de
              los logros específicos necesarios.
            </p>

            <div class="field field--required">
              <label class="field__label" for="objetivo_general">7.4.1 Objetivo general</label>
              <input id="objetivo_general" type="text" class="field__input"
                     [(ngModel)]="form.objetivo_general" maxlength="300"
                     placeholder="El propósito central del proyecto, en una frase">
            </div>

            <div class="field field--required">
              <label class="field__label">7.4.2 Objetivos específicos</label>
              @for (o of form.objetivos_especificos; track $index; let i = $index) {
                <div class="objetivo">
                  <label class="objetivo__lbl" [attr.for]="'objesp' + i">
                    Objetivo específico {{ i + 1 }}
                  </label>
                  <textarea [id]="'objesp' + i" class="field__textarea" rows="2"
                            [ngModel]="form.objetivos_especificos[i]"
                            (ngModelChange)="form.objetivos_especificos[i] = $event"
                            placeholder="Logro concreto necesario para cumplir el objetivo general"></textarea>
                </div>
              }
            </div>

            <h3 class="wiz-section-title">
              <span aria-hidden="true">👥</span> 7.5 Cobertura de ciudadanos beneficiados
              <span class="required-mark">*</span>
            </h3>
            <p class="field__hint" style="margin-bottom: 0.75rem;">
              Determine el volumen de impacto cuantitativo del proyecto tasando el
              staff, los usuarios directos y el entorno.
            </p>

            <div class="field field--required">
              <label class="field__label" for="cobertura_staff">
                7.5.1 Beneficiarios directos — staff
              </label>
              <select id="cobertura_staff" class="field__select" [(ngModel)]="form.cobertura_staff">
                <option value="">Selecciona…</option>
                @for (c of catalogos()!.cobertura_staff_choices; track c.valor) {
                  <option [value]="c.valor">{{ c.etiqueta }}</option>
                }
              </select>
            </div>
            <div class="field field--required">
              <label class="field__label" for="cobertura_comunidad">
                7.5.2 Beneficiarios directos — comunidad
              </label>
              <select id="cobertura_comunidad" class="field__select"
                      [(ngModel)]="form.cobertura_comunidad">
                <option value="">Selecciona…</option>
                @for (c of catalogos()!.cobertura_comunidad_choices; track c.valor) {
                  <option [value]="c.valor">{{ c.etiqueta }}</option>
                }
              </select>
            </div>
            <div class="field field--required">
              <label class="field__label" for="cobertura_indirectos">
                7.5.3 Beneficiarios indirectos
              </label>
              <select id="cobertura_indirectos" class="field__select"
                      [(ngModel)]="form.cobertura_indirectos">
                <option value="">Selecciona…</option>
                @for (c of catalogos()!.cobertura_indirectos_choices; track c.valor) {
                  <option [value]="c.valor">{{ c.etiqueta }}</option>
                }
              </select>
            </div>

            <div class="field field--required">
              <label class="field__label">7.6 Enfoque por ciclo vital</label>
              <p class="field__hint" style="margin-bottom: 0.5rem;">
                Marque los grupos de edad a los que se dirige el proyecto; se otorga
                prioridad a las poblaciones de cuidado.
              </p>
              <div class="chips-grid">
                @for (r of catalogos()!.rangos_etarios; track r.codigo) {
                  <button type="button" class="chip chip--etario"
                          [class.chip--active]="form.ciclo_vital.has(cod(r.codigo))"
                          [attr.aria-pressed]="form.ciclo_vital.has(cod(r.codigo))"
                          (click)="alternar(form.ciclo_vital, cod(r.codigo))">
                    {{ r.nombre }}
                    @if (r.edad_min != null && r.edad_max != null) {
                      <small>({{ r.edad_min }}–{{ r.edad_max }} años)</small>
                    }
                  </button>
                }
              </div>
            </div>

            <div class="field field--required">
              <label class="field__label" for="diversidad_genero_propuesta">
                7.7 Impacto en la diversidad de género
              </label>
              <p class="field__hint" style="margin-bottom: 0.5rem;">
                Seleccione la población según identidad y género priorizada por la
                propuesta. Su propuesta beneficia principalmente a:
              </p>
              <select id="diversidad_genero_propuesta" class="field__select"
                      [(ngModel)]="form.diversidad_genero_propuesta">
                <option value="">Selecciona…</option>
                @for (c of catalogos()!.diversidad_genero_choices; track c.valor) {
                  <option [value]="c.valor">{{ c.etiqueta }}</option>
                }
              </select>
            </div>

            <h3 class="wiz-section-title">
              <span aria-hidden="true">🏷️</span> 7.8 Enfoques poblacionales de inclusión
            </h3>
            <p class="field__hint" style="margin-bottom: 0.75rem;">
              Active las casillas de los sectores poblacionales especiales
              atendidos de forma central por la iniciativa.
              <strong>El orden en que las active queda registrado</strong>: marque
              primero el enfoque más central de su propuesta. Si ninguno aplica,
              marque «Ninguno».
            </p>
            <app-enfoques-cascada
              [familias]="catalogos()!.enfoques_familias_78"
              [seleccion]="form.enfoques_78"
              [mostrarOrden]="true"
              (cambio)="marcarSucio()" />

            <h3 class="wiz-section-title">
              <span aria-hidden="true">📌</span> 7.9 Focalización territorial del proyecto
              <span class="required-mark">*</span>
            </h3>
            <p class="field__hint" style="margin-bottom: 0.75rem;">
              Ubique geográficamente el proyecto; el sistema cruzará los datos con
              las capas cartográficas de la localidad.
            </p>

            <p class="field__label">
              7.9.1 Espacio o parque principal donde realizará la iniciativa
            </p>
            <app-nivel-espacio
              [redes]="catalogos()!.redes"
              [escenarios]="catalogos()!.escenarios"
              [redSeleccionada]="form.ejecucion_red"
              (redSeleccionadaChange)="form.ejecucion_red = $event"
              [seleccion]="form.ejecucion_escenarios"
              [otro]="form.ejecucion_escenario_otro"
              (otroChange)="form.ejecucion_escenario_otro = $event"
              idOtro="ejecucion_otro"
              (cambio)="marcarSucio()" />

            @if (form.ejecucion_red) {
              <p class="field__label" style="margin-top: 1rem;">7.9.2 Datos de ubicación</p>

              <div class="field field--required">
                <label class="field__label" for="nombre_espacio_ejecucion">Nombre del parque o espacio</label>
                <input id="nombre_espacio_ejecucion" type="text" class="field__input"
                       [(ngModel)]="form.nombre_espacio_ejecucion" maxlength="150"
                       placeholder="Ej. Parque El Tintal">
              </div>

              <div class="field field--required">
                <app-direccion-picker
                  label="Dirección"
                  placeholder="Escribe y elige de la lista: Cra 86 # 6-30"
                  [valor]="form.direccion_espacio_ejecucion"
                  (direccionElegida)="onDireccionEjecucion($event)" />
              </div>

              <div class="field field--required">
                <label class="field__label" for="ejecucion_estrato">Estrato</label>
                <select id="ejecucion_estrato" class="field__select"
                        [(ngModel)]="form.ejecucion_estrato">
                  <option value="">Selecciona…</option>
                  @for (e of catalogos()!.estratos; track e) {
                    <option [value]="e">Estrato {{ e }}</option>
                  }
                </select>
                <p class="field__hint">
                  La Alcaldía verifica este dato con la plataforma cartográfica
                  oficial IDECA a partir de la dirección que eligió.
                </p>
              </div>
            }

            <h3 class="wiz-section-title">
              <span aria-hidden="true">🌱</span> 7.10 Enfoque de sostenibilidad medioambiental
              <span class="required-mark">*</span>
            </h3>
            <p class="field__hint" style="margin-bottom: 0.75rem;">
              Declare si su proyecto implementa acciones de mitigación ecológica o
              manejo de residuos en los escenarios.
            </p>
            <div class="field field--required">
              <div class="radio-row">
                <label class="radio-label">
                  <input type="radio" name="ambiental" [value]="true"
                         [(ngModel)]="form.sostenibilidad_ambiental">
                  <span>Sí</span>
                </label>
                <label class="radio-label">
                  <input type="radio" name="ambiental" [value]="false"
                         [(ngModel)]="form.sostenibilidad_ambiental">
                  <span>No</span>
                </label>
              </div>
            </div>

            @if (form.sostenibilidad_ambiental === true) {
              <div class="conditional-block">
                <div class="field field--required">
                  <label class="field__label" for="sostenibilidad_sustento">
                    Sustento de las acciones ambientales
                  </label>
                  <textarea id="sostenibilidad_sustento" class="field__textarea" rows="7"
                            [(ngModel)]="form.sostenibilidad_sustento"
                            placeholder="Describe las acciones concretas de mitigación ecológica o manejo de residuos que aplicará en los escenarios"></textarea>
                  <app-contador-texto [texto]="form.sostenibilidad_sustento"
                                      [minPalabras]="minPalabrasSustento()" />
                </div>
              </div>
            }
          </section>
        }

        <!-- ═══════════ SECCIÓN 8 · GESTIÓN OPERATIVA Y PRESUPUESTO ═══════════ -->
        @if (seccionActual() === 8) {
          <section class="wiz-step" aria-labelledby="s8">
            <h2 id="s8" class="wiz-step__title">
              Sección 8 · Gestión operativa, financiera y presupuesto
            </h2>
            <p class="wiz-step__hint">
              Componentes técnicos de planeación operativa y matriz financiera,
              en el formato integral del IDRD como ente rector del sector.
            </p>

            <div class="field field--required">
              <label class="field__label" for="metodologia">8.1 Metodología</label>
              <p class="field__hint" style="margin-bottom: 0.5rem;">
                Describa el enfoque pedagógico y técnico de la propuesta.
              </p>
              <textarea id="metodologia" class="field__textarea" rows="7"
                        [(ngModel)]="form.metodologia"
                        [attr.maxlength]="maxMetodologia()"
                        placeholder="Cómo se va a ejecutar: enfoque pedagógico, técnicas, materiales, forma de trabajo con la comunidad"></textarea>
              <app-contador-texto [texto]="form.metodologia"
                                  [maxCaracteres]="maxMetodologia()" />
            </div>

            <h3 class="wiz-section-title">
              <span aria-hidden="true">📋</span> 8.2 Actividades y descripción
              <span class="required-mark">*</span>
            </h3>
            <p class="field__hint" style="margin-bottom: 0.75rem;">
              Detalle las acciones tácticas del proyecto. El cronograma y el
              presupuesto se arman sobre estas actividades.
            </p>

            @for (act of form.actividades; track $index; let i = $index) {
              <div class="fila-card">
                <div class="fila-card__head">
                  <span class="fila-card__title">Actividad {{ i + 1 }}</span>
                  @if (form.actividades.length > 1) {
                    <button type="button" class="btn-outline-brand btn-sm"
                            (click)="quitarActividad(i)">✕ Quitar</button>
                  }
                </div>
                <div class="field">
                  <label class="field__label" [attr.for]="'act-nom-' + i">Nombre de la actividad</label>
                  <input [id]="'act-nom-' + i" type="text" class="field__input" maxlength="200"
                         [ngModel]="act.nombre" (ngModelChange)="act.nombre = $event"
                         placeholder="Ej. Escuela de iniciación deportiva">
                </div>
                <div class="field" style="margin-bottom: 0;">
                  <label class="field__label" [attr.for]="'act-desc-' + i">
                    Descripción <span class="field__optional">opcional</span>
                  </label>
                  <textarea [id]="'act-desc-' + i" class="field__textarea" rows="2"
                            [ngModel]="act.descripcion" (ngModelChange)="act.descripcion = $event"
                            placeholder="En qué consiste"></textarea>
                </div>
              </div>
            }
            <button type="button" class="btn-outline-brand btn-sm"
                    (click)="agregarActividad()">+ Agregar actividad</button>

            <h3 class="wiz-section-title">
              <span aria-hidden="true">🗓️</span> 8.3 Cronograma
              <span class="required-mark">*</span>
            </h3>
            <p class="field__hint" style="margin-bottom: 0.75rem;">
              Marque, para cada actividad, las semanas de ejecución dentro de los
              4 meses del proyecto.
            </p>
            <app-cronograma-matriz [actividades]="form.actividades" (cambio)="marcarSucio()" />

            <h3 class="wiz-section-title">
              <span aria-hidden="true">🧑‍🏫</span> 8.4 Equipo de trabajo
              <span class="required-mark">*</span>
            </h3>

            @for (m of form.equipo; track $index; let i = $index) {
              <div class="fila-card">
                <div class="fila-card__head">
                  <span class="fila-card__title">Integrante {{ i + 1 }}</span>
                  @if (form.equipo.length > 1) {
                    <button type="button" class="btn-outline-brand btn-sm"
                            (click)="quitarIntegrante(i)">✕ Quitar</button>
                  }
                </div>
                <div class="field">
                  <label class="field__label" [attr.for]="'eq-nom-' + i">Nombre</label>
                  <input [id]="'eq-nom-' + i" type="text" class="field__input" maxlength="200"
                         [ngModel]="m.nombre" (ngModelChange)="m.nombre = $event"
                         placeholder="Nombre y apellido">
                </div>
                <div class="field-row" style="margin-bottom: 0;">
                  <div class="field" style="margin-bottom: 0;">
                    <label class="field__label" [attr.for]="'eq-niv-' + i">Nivel de formación</label>
                    <select [id]="'eq-niv-' + i" class="field__select"
                            [ngModel]="m.nivel_formacion_codigo"
                            (ngModelChange)="m.nivel_formacion_codigo = $event">
                      <option value="">Selecciona…</option>
                      @for (n of catalogos()!.niveles_educativos; track n.codigo) {
                        <option [value]="n.codigo">{{ n.nombre }}</option>
                      }
                    </select>
                  </div>
                  <div class="field" style="margin-bottom: 0;">
                    <label class="field__label" [attr.for]="'eq-rol-' + i">Rol en la iniciativa</label>
                    <input [id]="'eq-rol-' + i" type="text" class="field__input" maxlength="200"
                           [ngModel]="m.rol" (ngModelChange)="m.rol = $event"
                           placeholder="Ej. Entrenador, logística, monitor">
                  </div>
                </div>
              </div>
            }
            <button type="button" class="btn-outline-brand btn-sm"
                    (click)="agregarIntegrante()">+ Agregar integrante</button>

            <h3 class="wiz-section-title">
              <span aria-hidden="true">💰</span> 8.5 Presupuesto
              <span class="required-mark">*</span>
            </h3>
            <p class="field__hint" style="margin-bottom: 0.75rem;">
              Registre los rubros de gasto. El valor total de cada rubro y la
              sumatoria se calculan automáticamente y no se pueden editar.
            </p>

            @for (r of form.presupuesto; track $index; let i = $index) {
              <div class="fila-card">
                <div class="fila-card__head">
                  <span class="fila-card__title">Rubro {{ i + 1 }}</span>
                  @if (form.presupuesto.length > 1) {
                    <button type="button" class="btn-outline-brand btn-sm"
                            (click)="quitarRubro(i)">✕ Quitar</button>
                  }
                </div>

                <div class="field">
                  <label class="field__label" [attr.for]="'pr-act-' + i">Actividad asociada</label>
                  <select [id]="'pr-act-' + i" class="field__select"
                          [ngModel]="r.actividad_idx" (ngModelChange)="r.actividad_idx = $event">
                    <option [ngValue]="null">Sin actividad asociada</option>
                    @for (act of form.actividades; track $index; let j = $index) {
                      <option [ngValue]="j">
                        {{ j + 1 }}. {{ act.nombre || 'Actividad sin nombre' }}
                      </option>
                    }
                  </select>
                </div>

                <div class="field">
                  <label class="field__label" [attr.for]="'pr-desc-' + i">Descripción del rubro</label>
                  <input [id]="'pr-desc-' + i" type="text" class="field__input" maxlength="300"
                         [ngModel]="r.descripcion_rubro" (ngModelChange)="r.descripcion_rubro = $event"
                         placeholder="Ej. Balones de fútbol No. 5">
                </div>

                <div class="field-row field-row--3" style="margin-bottom: 0;">
                  <div class="field" style="margin-bottom: 0;">
                    <label class="field__label" [attr.for]="'pr-cant-' + i">Cantidad</label>
                    <input [id]="'pr-cant-' + i" type="number" class="field__input"
                           min="0" step="1" inputmode="numeric"
                           [ngModel]="r.cantidad" (ngModelChange)="r.cantidad = $event">
                  </div>
                  <div class="field" style="margin-bottom: 0;">
                    <label class="field__label" [attr.for]="'pr-vu-' + i">Valor unitario</label>
                    <input [id]="'pr-vu-' + i" type="number" class="field__input"
                           min="0" step="1000" inputmode="numeric"
                           [ngModel]="r.valor_unitario" (ngModelChange)="r.valor_unitario = $event">
                  </div>
                  <div class="field" style="margin-bottom: 0;">
                    <label class="field__label" [attr.for]="'pr-vt-' + i">Valor total</label>
                    <input [id]="'pr-vt-' + i" type="text" class="field__input field__input--ro"
                           [value]="moneda(total(r))" readonly tabindex="-1"
                           aria-readonly="true">
                  </div>
                </div>
              </div>
            }
            <button type="button" class="btn-outline-brand btn-sm"
                    (click)="agregarRubro()">+ Agregar rubro</button>

            <div class="total-card" [class.total-card--alerta]="excedeTope()">
              <span class="total-card__lbl">Total solicitado</span>
              <span class="total-card__val">{{ moneda(totalGeneral()) }}</span>
            </div>
            @if (excedeTope()) {
              <p class="field__error" role="alert">
                Ajuste de presupuesto requerido: el monto solicitado supera el
                máximo financiable de la convocatoria ({{ moneda(topeMaximo()) }}).
              </p>
            } @else {
              <p class="field__hint">
                El monto máximo financiable depende del rango que obtenga su
                iniciativa en la convocatoria. Si requiere ajuste, la Alcaldía
                Local se lo informará.
              </p>
            }
          </section>
        }

        <!-- ═══════════ SECCIÓN 9 · PRESENTACIÓN DE LA INICIATIVA ═══════════ -->
        @if (seccionActual() === 9) {
          <section class="wiz-step" aria-labelledby="s9">
            <h2 id="s9" class="wiz-step__title">Sección 9 · Presentación de la iniciativa</h2>
            <p class="wiz-step__hint">
              Formalización legal, declaración de transparencia bajo el principio
              de buena fe y cierre del proceso digital.
            </p>

            <h3 class="wiz-section-title">
              <span aria-hidden="true">🤝</span> Compromisos de ley
              <span class="required-mark">*</span>
            </h3>
            <div class="compromiso-list">
              <label class="checkbox-label checkbox-label--lg">
                <input type="checkbox" class="checkbox-input" [(ngModel)]="form.compromiso_redes">
                <span class="checkbox-text">
                  Me comprometo a difundir las actividades financiadas a través de
                  las redes sociales de la organización.
                </span>
              </label>
              <label class="checkbox-label checkbox-label--lg">
                <input type="checkbox" class="checkbox-input" [(ngModel)]="form.compromiso_carta_1ano">
                <span class="checkbox-text">
                  Me comprometo a suscribir la carta de intención de continuidad
                  por mínimo 1 año.
                </span>
              </label>
              <label class="checkbox-label checkbox-label--lg">
                <input type="checkbox" class="checkbox-input" [(ngModel)]="form.compromiso_actualizacion">
                <span class="checkbox-text">
                  Me comprometo a mantener actualizada la información de la
                  organización durante la ejecución.
                </span>
              </label>
            </div>

            <h3 class="wiz-section-title">
              <span aria-hidden="true">🪪</span> Registro de identidad del firmante
            </h3>
            <div class="field-row">
              <div class="field field--required">
                <label class="field__label" for="firma_cedula">Cédula del firmante</label>
                <input id="firma_cedula" type="text" class="field__input"
                       [(ngModel)]="form.firma_cedula"
                       inputmode="numeric" minlength="5" maxlength="15"
                       placeholder="Ej. 52123456">
                @if (cedulaNoCoincide()) {
                  <p class="field__error" role="alert">
                    La cédula del firmante debe ser la misma que registró en la
                    Sección 1 ({{ form.rep_numero_doc }}).
                  </p>
                }
              </div>
              <div class="field field--required">
                <label class="field__label" for="firma_fecha">Fecha de firma</label>
                <input id="firma_fecha" type="date" class="field__input"
                       [attr.max]="hoyISO()" [(ngModel)]="form.firma_fecha">
              </div>
            </div>

            <h3 class="wiz-section-title">
              <span aria-hidden="true">✍️</span> Firma
              <span class="required-mark">*</span>
            </h3>
            <app-firma-lienzo (firmaCambio)="onFirma($event)" />

            <h3 class="wiz-section-title">
              <span aria-hidden="true">⚖️</span> Aceptación jurídica de buena fe
              <span class="required-mark">*</span>
            </h3>
            <label class="checkbox-label checkbox-label--lg">
              <input type="checkbox" class="checkbox-input" [(ngModel)]="form.declaracion_buena_fe">
              <span class="checkbox-text">
                <strong>Declaración bajo juramento y aceptación de buena fe.</strong>
                Como representante legal o líder autorizado del colectivo u
                organización, declaro bajo la gravedad del juramento que toda la
                información cuantitativa, territorial, poblacional y técnica
                registrada en este formulario es verídica, exacta y corresponde a
                la realidad operativa de nuestra agrupación. Manifiesto que
                conozco y acepto los términos de esta postulación ciega y
                automatizada, entendiendo que el aplicativo se rige de manera
                estricta por el Principio de Buena Fe, consagrado en el Artículo 83
                de la Constitución Política de Colombia. En virtud de este mandato
                constitucional, las actuaciones de los particulares y de las
                autoridades públicas deben ceñirse a los postulados de la honestidad
                y la lealtad. Por lo tanto, asumo la responsabilidad legal de los
                datos suministrados y acepto que cualquier inconsistencia grave,
                falsedad o alteración en los soportes documentales cargados o en las
                declaraciones del formulario, facultará a la administración local
                para proceder con la inadmisión inmediata de la propuesta, la
                pérdida automática de la posición en el listado del sistema, o la
                revocatoria del fomento asignado, sin perjuicio de las acciones
                legales y penales que correspondan ante las autoridades competentes.
              </span>
            </label>

            <div class="wiz-aviso">
              <strong>Antes de radicar:</strong> revise cada sección con el botón
              «Sección anterior». Una vez enviada, la postulación queda registrada
              con fecha y hora, y no se puede modificar.
            </div>
          </section>
        }

        <!-- Botonera fija -->
        <div class="wiz-actions">
          <button type="button" class="btn-outline-brand btn-wiz-prev"
                  (click)="irAnterior()"
                  [disabled]="seccionActual() === 1"
                  [class.btn--hidden]="seccionActual() === 1">
            ← Sección anterior
          </button>

          @if (seccionActual() < totalSecciones) {
            <button type="button" class="btn-brand btn-wiz-next" (click)="irSiguiente()">
              Siguiente →
            </button>
          } @else {
            <button type="button" class="btn-brand btn-wiz-submit"
                    (click)="enviar()" [disabled]="enviando()">
              @if (enviando()) {
                <span class="spinner-inline" aria-hidden="true"></span> Radicando…
              } @else {
                ✉ Enviar postulación y radicar proyecto
              }
            </button>
          }
        </div>

        <p class="guardado" aria-live="polite">
          @if (guardadoEn()) {
            @if (borradorEnServidor()) {
              💾 Borrador guardado a las {{ guardadoEn() }}
              <strong>en este dispositivo y en el servidor</strong> — puede
              continuar desde otro equipo.
            } @else {
              💾 Borrador guardado a las {{ guardadoEn() }}
              <strong>en este dispositivo</strong>. Sin conexión no se pudo
              copiar al servidor: no cierre este navegador hasta radicar.
            }
          } @else {
            💾 El formulario se guarda automáticamente mientras lo diligencia.
          }
          <button type="button" class="guardado__btn" (click)="guardarAhora()">Guardar ahora</button>
        </p>
      </main>
    }
  `,
  styles: [`
    @use '../../../styles/tokens' as *;

    $brand-dark: #1d3557;
    $brand-gradient: linear-gradient(135deg, #{$brand-dark}, #{$color-primary});
    $conditional-bg: #fffbe6;
    $conditional-border: $color-secondary;

    :host {
      display: block;
      background: $color-bg-subtle;
      min-height: 100vh;
      font-family: $font-family-base;
    }

    // ── Estados de carga, error, cierre y éxito ───────────────────────
    .loading-wrap, .error-wrap, .cerrado-wrap, .exito-wrap {
      display: flex;
      align-items: center;
      justify-content: center;
      min-height: 100vh;
      padding: $space-6;
    }

    .loading-spinner {
      width: 40px; height: 40px;
      border: 4px solid $color-border;
      border-top-color: $color-primary;
      border-radius: 50%;
      animation: spin 0.8s linear infinite;
      margin: 0 auto $space-4;

      @media (prefers-reduced-motion: reduce) { animation: none; }
    }

    .loading-wrap { flex-direction: column; gap: $space-3; color: $color-text-muted; }

    .error-card, .cerrado-card, .exito-card {
      background: $color-bg;
      border-radius: $radius-2xl;
      padding: $space-10 $space-8;
      text-align: center;
      max-width: 520px;
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
    .cerrado-sub { color: $color-text-muted; font-size: $font-size-sm; }

    .exito-icono {
      width: 80px; height: 80px; margin: 0 auto $space-5;
      svg { width: 100%; height: 100%; }
    }
    .exito-title {
      font-size: $font-size-2xl;
      font-weight: $font-weight-bold;
      color: $color-success;
      margin: 0 0 $space-3;
    }
    .exito-desc { color: $color-text; font-size: $font-size-md; margin-bottom: $space-5; }
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
      color: $color-text-muted;
      font-weight: $font-weight-semibold;
    }
    .exito-num__val {
      font-size: $font-size-2xl;
      font-weight: $font-weight-bold;
      color: $color-primary;
    }
    .exito-footer { color: $color-text-muted; font-size: $font-size-sm; margin: 0; }

    // ── Header ────────────────────────────────────────────────────────
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
    .wiz-banner__icon { font-size: 1.8rem; flex-shrink: 0; }
    .wiz-banner__title {
      font-size: $font-size-base;
      font-weight: $font-weight-bold;
      margin: 0;
      line-height: $line-height-tight;

      @media (min-width: #{$bp-md}) { font-size: $font-size-md; }
    }
    .wiz-banner__sub { margin: $space-1 0 0; font-size: $font-size-xs; opacity: 0.9; }

    // ── Bienvenida ────────────────────────────────────────────────────
    .intro { max-width: 760px; margin: 0 auto; }
    .intro__card {
      background: $color-bg;
      border: 1px solid $color-border;
      border-radius: $radius-lg;
      padding: $space-4 $space-5;
      margin: $space-4 $space-3;
    }
    .intro__lead { color: $color-text; line-height: $line-height-relaxed; margin: 0 0 $space-3; }
    .intro__list { margin: 0 0 $space-3; padding-left: $space-5; color: $color-text; }
    .intro__list li { margin-bottom: $space-1; line-height: $line-height-normal; }
    .intro__docs-title { font-weight: $font-weight-semibold; margin: $space-3 0 $space-1; }
    .intro__btn { margin-top: $space-3; width: 100%; }

    .borrador-aviso {
      border: 1.5px solid $color-info;
      background: $color-info-bg;
      border-radius: $radius-lg;
      padding: $space-4;
      margin-bottom: $space-4;
    }
    .borrador-aviso__txt { margin: 0 0 $space-2; color: $color-text; }
    .borrador-aviso__nota { margin: 0 0 $space-3; font-size: $font-size-xs; color: $color-text-muted; }
    .borrador-aviso__btns { display: flex; gap: $space-2; flex-wrap: wrap; }

    // ── Progreso ──────────────────────────────────────────────────────
    .wiz-progress { padding: $space-3 $space-5; }
    .wiz-progress__meta {
      display: flex;
      justify-content: space-between;
      align-items: center;
      font-size: $font-size-xs;
      color: $color-text-muted;
      margin-bottom: $space-2;
      gap: $space-2;

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

      &[disabled] { opacity: 0.6; }
      &:not([disabled]) { cursor: pointer; }

      &--active {
        background: $color-primary-bg;
        color: $color-primary;
        border-color: rgba($color-primary, 0.3);
      }
      &--done { background: $color-success-bg; color: $color-success; cursor: pointer; }
    }
    .wiz-pill__num {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      width: 18px; height: 18px;
      border-radius: 50%;
      background: rgba(0, 0, 0, 0.1);
      font-size: 0.65rem;

      .wiz-pill--active & { background: $color-primary; color: $color-text-inverse; }
      .wiz-pill--done & { background: $color-success; color: $color-text-inverse; }
    }

    .wiz-fases { display: flex; gap: $space-2; padding: $space-3 $space-5 0; }
    .wiz-fase {
      flex: 1;
      display: flex;
      flex-direction: column;
      gap: 1px;
      padding: $space-2 $space-3;
      border-radius: $radius-lg;
      background: $color-bg-muted;
      border: 1px solid $color-border;
      color: $color-text-muted;

      &--active {
        background: $color-primary-bg;
        border-color: rgba($color-primary, 0.35);
        color: $color-primary;
      }
    }
    .wiz-fase__num {
      font-size: $font-size-xs;
      font-weight: $font-weight-bold;
      text-transform: uppercase;
    }
    .wiz-fase__lbl { font-size: $font-size-sm; font-weight: $font-weight-semibold; }
    .wiz-fase__rng { font-size: 0.65rem; opacity: 0.85; }

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

    // ── Contenido ─────────────────────────────────────────────────────
    .wiz-main {
      max-width: 100%;
      margin: 0 auto;
      padding: $space-4;

      @media (min-width: #{$bp-md}) { max-width: 780px; padding: $space-6 $space-4; }
      @media (min-width: #{$bp-xl}) { max-width: 920px; }
    }

    .wiz-step {
      background: $color-bg;
      border-radius: $radius-xl;
      padding: $space-5 $space-4;
      box-shadow: $shadow-sm;
      margin-bottom: 5rem;

      @media (min-width: #{$bp-md}) { padding: $space-8 $space-10; }
      @media (prefers-reduced-motion: no-preference) { animation: step-in 0.22s ease-out both; }
    }

    @keyframes step-in {
      from { opacity: 0; transform: translateY(10px); }
      to   { opacity: 1; transform: translateY(0); }
    }
    @keyframes spin { to { transform: rotate(360deg); } }

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
      margin: $space-6 0 $space-3;
      display: flex;
      align-items: center;
      gap: $space-2;
      flex-wrap: wrap;
    }

    // ── Campos ────────────────────────────────────────────────────────
    .field {
      margin-bottom: $space-5;

      &--required > .field__label::after,
      &--required > label.field__label::after {
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
    .field__input, .field__select, .field__textarea {
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
    }
    .field__input--ro {
      background: $color-bg-muted;
      color: $color-text;
      font-weight: $font-weight-semibold;
      border-style: dashed;
    }
    .field__textarea { min-height: 90px; resize: vertical; }
    .field__error {
      color: $color-danger;
      font-size: $font-size-xs;
      margin: $space-1 0 0;
      font-weight: $font-weight-medium;
    }
    .field__hint { color: $color-text-muted; font-size: $font-size-xs; margin: $space-1 0 0; }
    .field__status {
      font-size: $font-size-xs;
      margin: $space-1 0 0;
      color: $color-info;

      &--ok { color: $color-success; }
    }
    .required-mark { color: $color-primary; font-weight: $font-weight-bold; }

    .field-row {
      display: grid;
      grid-template-columns: 1fr;
      gap: $space-3;

      @media (min-width: #{$bp-sm}) { grid-template-columns: 1fr 1fr; }
      &--3 { @media (min-width: #{$bp-md}) { grid-template-columns: 1fr 1fr 1fr; } }
    }

    .objetivo { margin-bottom: $space-3; }
    .objetivo__lbl { display: block; font-size: $font-size-xs; color: $color-text-muted; margin-bottom: $space-1; }

    // ── Anexos ────────────────────────────────────────────────────────
    .anexo {
      display: flex;
      align-items: center;
      gap: $space-3;
      width: 100%;
      min-height: 56px;
      padding: $space-3 $space-4;
      border: 2px dashed $color-border-strong;
      border-radius: $radius-lg;
      background: $color-bg-subtle;
      cursor: pointer;

      &--ok { border-style: solid; border-color: $color-success; background: $color-success-bg; }
      &:focus-within { outline: $focus-ring; outline-offset: $focus-ring-offset; }
    }
    .anexo__icon { font-size: 1.4rem; }
    .anexo__txt { font-size: $font-size-sm; color: $color-text; word-break: break-word; }
    .anexo__input {
      position: absolute;
      left: -9999px;
      width: 1px; height: 1px;
      opacity: 0;
    }

    // ── Checkboxes y radios ───────────────────────────────────────────
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

        &:has(.checkbox-input:checked) {
          border-color: $color-success;
          background: $color-success-bg;
        }
      }
    }
    .checkbox-input {
      width: 22px; height: 22px; min-width: 22px;
      accent-color: $color-primary;
      cursor: pointer;
      margin-top: 2px;
    }
    .checkbox-text { font-size: $font-size-sm; line-height: $line-height-normal; color: $color-text; }
    .compromiso-list { display: flex; flex-direction: column; gap: $space-3; }

    .radio-row { display: flex; gap: $space-3; flex-wrap: wrap; }
    .radio-col { display: flex; flex-direction: column; gap: $space-2; }
    .radio-label {
      display: inline-flex;
      align-items: center;
      gap: $space-2;
      padding: $space-3 $space-5;
      min-height: $touch-target-min;
      border: 1.5px solid $color-border-strong;
      border-radius: $radius-lg;
      cursor: pointer;
      font-size: $font-size-base;
      color: $color-text;
      background: $color-bg;

      &:has(input:checked) {
        border-color: $color-primary;
        background: $color-primary-bg;
        color: $color-primary;
        font-weight: $font-weight-semibold;
      }
      &--block { width: 100%; justify-content: flex-start; font-size: $font-size-sm; }

      input { width: 20px; height: 20px; accent-color: $color-primary; cursor: pointer; }
    }

    // ── Multiselección desplegable (§6.1) ─────────────────────────────
    .multiselect {
      border: 1.5px solid $color-border-strong;
      border-radius: $radius-lg;
      background: $color-bg;
    }
    .multiselect__summary {
      padding: $space-3 $space-4;
      min-height: $touch-target-min;
      display: flex;
      align-items: center;
      cursor: pointer;
      font-size: $font-size-sm;
      font-weight: $font-weight-semibold;
      color: $color-primary;
    }
    .multiselect__body {
      padding: $space-3 $space-4;
      border-top: 1px solid $color-border;

      .checkbox-label:last-child { margin-bottom: 0; }
    }

    // ── Chips ─────────────────────────────────────────────────────────
    .chips-grid { display: flex; flex-wrap: wrap; gap: $space-2; }
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
      min-height: $touch-target-min;
      user-select: none;

      &:hover { border-color: $color-primary; color: $color-primary; background: $color-primary-bg; }

      &--active {
        background: $color-primary;
        color: $color-text-inverse;
        border-color: $color-primary-dark;

        &:hover { background: $color-primary-dark; color: $color-text-inverse; }
      }
      &--etario {
        flex-direction: column;
        gap: 0;
        min-width: 104px;
        text-align: center;
        padding: $space-2 $space-3;

        small { font-size: 0.65rem; opacity: 0.8; }
      }
    }

    .conditional-block {
      border-left: 3px solid $conditional-border;
      background: $conditional-bg;
      padding: $space-4;
      border-radius: 0 $radius-md $radius-md 0;
      margin: $space-3 0 $space-4;
    }

    // ── Filas dinámicas (§8) ──────────────────────────────────────────
    .fila-card {
      border: 1.5px solid $color-border;
      border-radius: $radius-lg;
      background: $color-bg-subtle;
      padding: $space-4;
      margin-bottom: $space-3;
    }
    .fila-card__head {
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: $space-3;
      margin-bottom: $space-3;
    }
    .fila-card__title {
      font-size: $font-size-sm;
      font-weight: $font-weight-semibold;
      color: $brand-dark;
    }

    .total-card {
      display: flex;
      justify-content: space-between;
      align-items: baseline;
      gap: $space-3;
      margin-top: $space-4;
      padding: $space-4;
      border-radius: $radius-lg;
      background: $color-primary-bg;
      border: 1.5px solid $color-primary;

      &--alerta { background: $color-danger-bg; border-color: $color-danger; }
    }
    .total-card__lbl { font-size: $font-size-sm; font-weight: $font-weight-semibold; color: $color-text; }
    .total-card__val { font-size: $font-size-xl; font-weight: $font-weight-bold; color: $color-primary; }
    .total-card--alerta .total-card__val { color: $color-danger; }

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

    // ── Botonera ──────────────────────────────────────────────────────
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
      margin: 0 auto;
      border-radius: $radius-xl $radius-xl 0 0;
      box-shadow: 0 -4px 12px rgba(0, 0, 0, 0.08);
    }
    .btn--hidden { visibility: hidden; }

    .guardado {
      display: flex;
      align-items: center;
      justify-content: center;
      gap: $space-2;
      flex-wrap: wrap;
      margin: $space-3 0 0;
      font-size: $font-size-xs;
      color: $color-text-muted;
    }
    .guardado__btn {
      background: none;
      border: 0;
      padding: 0;
      font: inherit;
      color: $color-primary;
      text-decoration: underline;
      cursor: pointer;
    }

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

      &:hover { background: $color-primary-dark; }
      &[disabled] { opacity: 0.65; cursor: not-allowed; }
      &-lg { font-size: $font-size-md; padding: $space-4 $space-8; }
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

      &:hover { background: $color-primary-bg; }
      &[disabled] { opacity: 0.65; cursor: not-allowed; }
    }
    .btn-sm { min-height: 40px; padding: $space-1 $space-3; font-size: $font-size-sm; }
    .btn-wiz-prev { min-width: 96px; }
    .btn-wiz-next, .btn-wiz-submit { flex: 1; }

    .spinner-inline {
      display: inline-block;
      width: 16px; height: 16px;
      border: 2px solid rgba(255, 255, 255, 0.4);
      border-top-color: $color-text-inverse;
      border-radius: 50%;
      animation: spin 0.7s linear infinite;

      @media (prefers-reduced-motion: reduce) { animation: none; }
    }
  `],
})
export class BancoPublicoComponent implements OnInit, OnDestroy {
  private route = inject(ActivatedRoute);
  private http = inject(HttpClient);
  private cfg = inject(ConfigService);
  private borradores = inject(BancoBorradorService);

  // ── Estado de pantalla ────────────────────────────────────────────
  cargandoCatalogos = signal(true);
  errorCarga = signal('');
  cerrado = signal(false);
  cerradoMsg = signal('');
  exito = signal(false);
  exitoId = signal<number | null>(null);
  enviando = signal(false);
  intro = signal(true);

  catalogos = signal<BancoCatalogos | null>(null);
  seccionActual = signal(1);

  erroresServidor = signal<string[]>([]);
  erroresSeccion = signal<string[]>([]);
  private erroresCampo = signal<Record<string, string[]>>({});

  autollenado = signal<'ok' | 'nuevo' | null>(null);
  guardadoEn = signal('');
  /** ¿El último autoguardado llegó al servidor, o solo a este dispositivo? */
  borradorEnServidor = signal(false);
  hayBorrador = signal(false);
  borradorFecha = signal('');

  // ── Modelo ────────────────────────────────────────────────────────
  form: BancoForm = formInicial();
  anexos: BancoAnexos = anexosVacios();

  // ── Constantes expuestas al template ──────────────────────────────
  readonly secciones = SECCIONES;
  readonly totalSecciones = TOTAL_SECCIONES;
  readonly composicionOpciones = COMPOSICION_GENERO_OPCIONES;
  readonly familiaMujerGenero = FAMILIA_MUJER_GENERO_52;
  readonly cod = codigoStr;
  readonly total = totalRubro;

  /**
   * Umbrales de validación. Se leen del bloque `reglas` que publica el endpoint
   * de catálogos, no de una constante compilada en el bundle: si el servidor
   * sube el mínimo de la narrativa a 250, el contador de la pantalla lo sube
   * con él. Las constantes locales quedan como red por si un backend viejo no
   * manda `reglas` — un formulario sin mínimos es mejor que uno con mínimos que
   * ya no son los del validador.
   */
  private reglas = computed(() => this.catalogos()?.reglas);

  minNarrativa = computed(
    () => this.reglas()?.narrativa_min_caracteres ?? MIN_CARACTERES_NARRATIVA,
  );
  minPalabrasSustento = computed(
    () => this.reglas()?.ambiental_min_palabras ?? MIN_PALABRAS_SUSTENTO,
  );
  maxMetodologia = computed(
    () => this.reglas()?.metodologia_max_caracteres ?? MAX_CARACTERES_METODOLOGIA,
  );
  maxAdicionales52 = computed(
    () => this.reglas()?.enfoques_52?.max_adicionales ?? MAX_ENFOQUES_ADICIONALES_52,
  );
  topeMaximo = computed(
    () => this.reglas()?.presupuesto?.tope_maximo_cop ?? TOPE_PRESUPUESTO_MAXIMO,
  );
  mensajeTope = computed(
    () => this.reglas()?.presupuesto?.mensaje_bloqueo ?? 'Ajuste de presupuesto requerido',
  );

  private sucio = false;
  private temporizador?: ReturnType<typeof setInterval>;

  // ── Computados ────────────────────────────────────────────────────
  listo = computed(
    () =>
      !this.cerrado() &&
      !this.cargandoCatalogos() &&
      !this.errorCarga() &&
      !this.exito() &&
      !!this.catalogos(),
  );

  progresoPct = computed(() =>
    Math.round((this.seccionActual() / this.totalSecciones) * 100),
  );

  /** Fase 1 = caracterización (§1-6). Fase 2 = propuesta (§7-9). */
  fase1Activa = computed(() => this.seccionActual() <= 6);

  tituloSeccion = computed(
    () => SECCIONES[this.seccionActual() - 1]?.titulo ?? '',
  );

  // ── Ciclo de vida ─────────────────────────────────────────────────
  ngOnInit(): void {
    this.cargarCatalogos();
    this.ofrecer(this.borradores.cargar(this.eventoId()));
    // El del servidor cubre lo que el dispositivo no puede: cambiar de
    // teléfono, limpiar el navegador, modo privado. Llega después porque va
    // por red; si resulta más reciente que el local, reemplaza la oferta.
    this.borradores.cargarDelServidor(this.eventoId()).subscribe((remoto) => {
      if (!remoto) return;
      this.ofrecer(
        this.borradores.masReciente(this.borradores.cargar(this.eventoId()), remoto),
      );
    });
    // Cada 15 s se persiste lo que haya cambiado. No en cada tecla: escribir en
    // localStorage es síncrono y bloquea el hilo de la interfaz.
    this.temporizador = setInterval(() => this.guardarSiSucio(), 15_000);
  }

  ngOnDestroy(): void {
    if (this.temporizador) clearInterval(this.temporizador);
    this.guardarSiSucio();
  }

  /** Cerrar la pestaña o mandar la app al fondo también guarda. */
  @HostListener('window:beforeunload')
  @HostListener('document:visibilitychange')
  alSalir(): void {
    this.guardarSiSucio();
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

    this.http.get<BancoCatalogos>(url).subscribe({
      next: (data) => {
        this.catalogos.set(data);
        this.cargandoCatalogos.set(false);
      },
      error: (err) => {
        this.cargandoCatalogos.set(false);
        if (err.status === 410) {
          this.cerrado.set(true);
          this.cerradoMsg.set(err.error?.detail || 'Esta convocatoria ya cerró.');
        } else {
          this.errorCarga.set(
            err.error?.detail ||
              'No se pudo cargar el formulario. Revisa tu conexión.',
          );
        }
      },
    });
  }

  // ── Guardado progresivo ───────────────────────────────────────────
  marcarSucio(): void {
    this.sucio = true;
  }

  private guardarSiSucio(): void {
    if (!this.sucio) return;
    this.guardarAhora();
  }

  guardarAhora(): void {
    const ok = this.borradores.guardar(
      this.eventoId(),
      this.form,
      this.seccionActual(),
    );
    this.sucio = false;
    if (ok) {
      this.guardadoEn.set(
        new Date().toLocaleTimeString('es-CO', {
          hour: '2-digit',
          minute: '2-digit',
        }),
      );
    }
    // Y al servidor, para que el respaldo no dependa de este aparato. Va
    // aparte y sin bloquear: si no hay señal, lo local ya salvó el trabajo.
    this.borradores
      .sincronizar(this.eventoId(), this.form, this.seccionActual())
      .subscribe((subido) => this.borradorEnServidor.set(subido));
  }

  /** Deja lista la oferta de «retomar» con el borrador que corresponda. */
  private ofrecer(guardado: { guardadoEn: Date } | null): void {
    if (!guardado) return;
    this.hayBorrador.set(true);
    this.borradorFecha.set(
      guardado.guardadoEn.toLocaleString('es-CO', {
        dateStyle: 'medium',
        timeStyle: 'short',
      }),
    );
  }

  retomarBorrador(): void {
    this.borradores.cargarDelServidor(this.eventoId()).subscribe((remoto) => {
      const guardado = this.borradores.masReciente(
        this.borradores.cargar(this.eventoId()), remoto);
      if (guardado) this.aplicarBorrador(guardado);
    });
  }

  private aplicarBorrador(guardado: BorradorRecuperado): void {
    this.form = guardado.form;
    // Los archivos no se pueden restaurar: se vuelven a pedir, y quedan en
    // blanco para que el usuario los vea vacíos en lugar de creerlos cargados.
    this.anexos = anexosVacios();
    this.seccionActual.set(guardado.seccion);
    this.hayBorrador.set(false);
    this.intro.set(false);
    this.scrollArriba();
  }

  descartarBorrador(): void {
    this.borradores.descartar(this.eventoId());
    this.form = formInicial();
    this.anexos = anexosVacios();
    this.hayBorrador.set(false);
    this.guardadoEn.set('');
  }

  comenzar(): void {
    this.intro.set(false);
    this.scrollArriba();
  }

  // ── Navegación ────────────────────────────────────────────────────
  irSiguiente(): void {
    const faltantes = this.faltantesDe(this.seccionActual());
    if (faltantes.length > 0) {
      this.erroresSeccion.set(faltantes);
      this.scrollArriba();
      return;
    }
    this.erroresSeccion.set([]);
    this.guardarAhora();
    if (this.seccionActual() < this.totalSecciones) {
      this.seccionActual.update((s) => s + 1);
      this.scrollArriba();
    }
  }

  irAnterior(): void {
    if (this.seccionActual() > 1) {
      this.erroresSeccion.set([]);
      this.guardarAhora();
      this.seccionActual.update((s) => s - 1);
      this.scrollArriba();
    }
  }

  irASeccion(n: number): void {
    if (n <= this.seccionActual()) {
      this.erroresSeccion.set([]);
      this.seccionActual.set(n);
      this.scrollArriba();
    }
  }

  private scrollArriba(): void {
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }

  // ── Validación ────────────────────────────────────────────────────
  /**
   * Devuelve la lista de lo que falta en una sección, en lenguaje del
   * ciudadano. Una sola función y no un par validar/mensajes: si la condición
   * y el mensaje viven separados, tarde o temprano dicen cosas distintas.
   */
  private faltantesDe(seccion: number): string[] {
    const f = this.form;
    const e: string[] = [];
    const pide = (falta: boolean, msg: string) => {
      if (falta) e.push(msg);
    };
    const vacio = (s: string) => !s?.trim();
    const docValido = (s: string) => /^\d{5,15}$/.test((s ?? '').trim());

    switch (seccion) {
      case 1:
        pide(vacio(f.nombre_organizacion), '1.1 Nombre de la organización');
        pide(!f.tipo_organizacion, '1.2 Tipo de organización');
        pide(!this.anexos.soporte_legal, '1.4 Soporte legal de la organización (archivo)');
        pide(vacio(f.rep_nombre1), '1.5 Primer nombre del representante');
        pide(vacio(f.rep_apellido1), '1.5 Primer apellido del representante');
        pide(!f.rep_tipo_doc, '1.6 Tipo de documento del representante');
        pide(!docValido(f.rep_numero_doc), '1.7 Número de documento (5 a 15 dígitos)');
        pide(!this.anexos.cedula_representante, '1.8 Documento de identidad del representante (archivo)');
        break;

      case 2:
        pide(vacio(f.telefono), '2.1 Teléfono');
        pide(vacio(f.correo) || !f.correo.includes('@'), '2.2 Correo electrónico válido');
        pide(f.tiene_sede_fisica === null, 'Indica si la organización tiene sede física');
        if (f.tiene_sede_fisica === true) {
          pide(!f.barrio, '2.3 Barrio de la sede');
          pide(vacio(f.direccion), '2.4 Dirección de la sede (elígela de la lista)');
          pide(!f.estrato, '2.5 Estrato de la sede');
        }
        break;

      case 3:
        pide(
          f.tamano_staff_num === null || Number(f.tamano_staff_num) < 1,
          '3.1 Número de personas del staff',
        );
        pide(!f.anios_experiencia, '3.2 Años de trayectoria');
        pide(!f.composicion_organizacion, '3.3 Composición y liderazgo de género');
        pide(!f.rango_poblacion, '3.4 Personas que atiende la organización');
        break;

      case 4:
        pide(!f.modalidad_actividad, '4.1 Actividad principal de la organización');
        if (f.modalidad_actividad) {
          pide(
            !f.disciplina_actividad && vacio(f.disciplina_actividad_otro),
            '4.1 La disciplina deportiva, o descríbela en «Otros»',
          );
        }
        pide(!f.arraigo_red, '4.2 Nivel de espacio de práctica');
        if (f.arraigo_red) {
          // El servidor exige al menos un botón del nivel elegido, o el texto
          // "Otro": un nivel sin espacios no describe ningún entorno real.
          pide(
            f.arraigo_escenarios.size === 0 && vacio(f.arraigo_escenario_otro),
            '4.2 Al menos un espacio del nivel elegido (o descríbelo en «Otro»)',
          );
          pide(vacio(f.arraigo_espacio_nombre), '4.2 Parque o espacio');
          pide(vacio(f.arraigo_direccion), '4.2 Dirección exacta (elígela de la lista)');
          pide(!f.arraigo_estrato, '4.2 Estrato del espacio');
          pide(vacio(f.arraigo_actividad), '4.2 Actividad específica que desarrolla');
        }
        break;

      case 5:
        pide(f.rango_etarios.size === 0, '5.1 Al menos un rango etario atendido');
        pide(f.enfoques_52.length === 0, '5.2 Al menos un enfoque poblacional (o «Ninguno»)');
        break;

      case 6:
        pide(f.participa_espacio === null, 'Indica si participas en un espacio local');
        if (f.participa_espacio === true) {
          pide(f.instancias.size === 0, '6.1 Al menos una instancia de concertación');
        }
        pide(!f.beneficio_alk, '6.2 Experiencia previa con la Alcaldía Local');
        break;

      case 7:
        pide(
          f.problematica.trim().length < this.minNarrativa(),
          `7.1 Problemática con al menos ${this.minNarrativa()} caracteres`,
        );
        pide(
          f.justificacion.trim().length < this.minNarrativa(),
          `7.2 Justificación con al menos ${this.minNarrativa()} caracteres`,
        );
        pide(!f.modalidad_propuesta, '7.3 Actividad técnica a desarrollar');
        if (f.modalidad_propuesta) {
          pide(
            !f.disciplina_principal && vacio(f.otros_deportes),
            '7.3 La disciplina, o descríbela en «Otros»',
          );
        }
        pide(vacio(f.objetivo_general), '7.4.1 Objetivo general');
        pide(
          f.objetivos_especificos.some((o) => vacio(o)),
          '7.4.2 Los tres objetivos específicos',
        );
        pide(!f.cobertura_staff, '7.5.1 Beneficiarios directos — staff');
        pide(!f.cobertura_comunidad, '7.5.2 Beneficiarios directos — comunidad');
        pide(!f.cobertura_indirectos, '7.5.3 Beneficiarios indirectos');
        pide(f.ciclo_vital.size === 0, '7.6 Al menos un grupo de edad del proyecto');
        pide(!f.diversidad_genero_propuesta, '7.7 Impacto en la diversidad de género');
        pide(!f.ejecucion_red, '7.9.1 Nivel del espacio donde se ejecutará');
        if (f.ejecucion_red) {
          pide(
            f.ejecucion_escenarios.size === 0 && vacio(f.ejecucion_escenario_otro),
            '7.9.1 Al menos un espacio del nivel elegido (o descríbelo en «Otro»)',
          );
          pide(vacio(f.nombre_espacio_ejecucion), '7.9.2 Nombre del parque o espacio');
          pide(
            vacio(f.direccion_espacio_ejecucion),
            '7.9.2 Dirección del espacio (elígela de la lista)',
          );
          pide(!f.ejecucion_estrato, '7.9.2 Estrato del espacio');
        }
        pide(f.sostenibilidad_ambiental === null, '7.10 Declaración de sostenibilidad ambiental');
        if (f.sostenibilidad_ambiental === true) {
          pide(
            contarPalabras(f.sostenibilidad_sustento) < this.minPalabrasSustento(),
            `7.10 Sustento ambiental con al menos ${this.minPalabrasSustento()} palabras`,
          );
        }
        break;

      case 8:
        pide(vacio(f.metodologia), '8.1 Metodología');
        pide(
          this.actividadesValidas().length === 0,
          '8.2 Al menos una actividad con nombre',
        );
        pide(
          this.actividadesValidas().some((a) => a.celdas.size === 0),
          '8.3 Cada actividad necesita al menos una semana marcada en el cronograma',
        );
        pide(this.equipoValido().length === 0, '8.4 Al menos un integrante con nombre y rol');
        pide(
          this.presupuestoValido().length === 0,
          '8.5 Al menos un rubro con descripción, cantidad y valor unitario',
        );
        pide(
          this.excedeTope(),
          `8.5 ${this.mensajeTope()}: el total supera ${this.moneda(this.topeMaximo())}`,
        );
        break;

      case 9:
        pide(
          !f.compromiso_redes || !f.compromiso_carta_1ano || !f.compromiso_actualizacion,
          'Los tres compromisos de ley',
        );
        pide(!docValido(f.firma_cedula), 'Cédula del firmante (5 a 15 dígitos)');
        pide(this.cedulaNoCoincide(), 'La cédula del firmante debe coincidir con la de la Sección 1');
        pide(!f.firma_fecha, 'Fecha de firma');
        pide(
          !!f.firma_fecha && f.firma_fecha > this.hoyISO(),
          'La fecha de firma no puede ser futura',
        );
        pide(!this.anexos.firma, 'Firma en el lienzo o PDF firmado');
        pide(!f.declaracion_buena_fe, 'La declaración de buena fe (Art. 83 C.P.)');
        break;
    }
    return e;
  }

  cedulaNoCoincide(): boolean {
    const firmante = this.form.firma_cedula.trim();
    const rep = this.form.rep_numero_doc.trim();
    return !!firmante && !!rep && firmante !== rep;
  }

  // ── Helpers de UI ─────────────────────────────────────────────────
  alternar(set: Set<string>, valor: string): void {
    if (set.has(valor)) set.delete(valor);
    else set.add(valor);
    this.marcarSucio();
  }

  err(campo: string): string {
    const errs = this.erroresCampo()[campo];
    return errs?.length ? errs[0] : '';
  }

  nombreAnexo(tipo: keyof BancoAnexos): string {
    const file = this.anexos[tipo];
    return file ? `${file.name} (${Math.round(file.size / 1024)} KB)` : '';
  }

  onAnexo(tipo: keyof BancoAnexos, ev: Event): void {
    const input = ev.target as HTMLInputElement;
    const file = input.files?.[0] ?? null;
    // El mismo tope que aplica el servidor (DOCUMENTOS_MAX_UPLOAD_BYTES).
    // Rechazarlo acá le ahorra al ciudadano subir 8 MB por la red del celular
    // para que el POST se caiga al final.
    if (file && file.size > 2 * 1024 * 1024) {
      this.erroresSeccion.set([
        `El archivo "${file.name}" pesa ${Math.round(file.size / 1024 / 1024)} MB y el máximo es 2 MB. Sube una versión más liviana.`,
      ]);
      input.value = '';
      return;
    }
    this.anexos[tipo] = file;
  }

  onFirma(file: File | null): void {
    this.anexos.firma = file;
  }

  onDireccionSede(d: DireccionElegida | null): void {
    this.form.direccion = d?.direccion ?? '';
    this.form.direccion_lon = d?.lon ?? null;
    this.form.direccion_lat = d?.lat ?? null;
    this.marcarSucio();
  }

  onDireccionArraigo(d: DireccionElegida | null): void {
    this.form.arraigo_direccion = d?.direccion ?? '';
    this.form.arraigo_lon = d?.lon ?? null;
    this.form.arraigo_lat = d?.lat ?? null;
    this.marcarSucio();
  }

  onDireccionEjecucion(d: DireccionElegida | null): void {
    this.form.direccion_espacio_ejecucion = d?.direccion ?? '';
    this.form.ejecucion_lon = d?.lon ?? null;
    this.form.ejecucion_lat = d?.lat ?? null;
    this.marcarSucio();
  }

  // ── §8 · filas dinámicas ──────────────────────────────────────────
  agregarActividad(): void {
    this.form.actividades.push(filaActividadVacia());
    this.marcarSucio();
  }

  quitarActividad(i: number): void {
    this.form.actividades.splice(i, 1);
    // Los rubros apuntan a la actividad por índice: al borrar una, los índices
    // de atrás se corren. Si no se reindexa acá, el rubro 3 termina cobrándole
    // a la actividad equivocada sin que nada avise.
    for (const r of this.form.presupuesto) {
      if (r.actividad_idx === null) continue;
      if (r.actividad_idx === i) r.actividad_idx = null;
      else if (r.actividad_idx > i) r.actividad_idx -= 1;
    }
    this.marcarSucio();
  }

  agregarIntegrante(): void {
    this.form.equipo.push(filaEquipoVacia());
    this.marcarSucio();
  }

  quitarIntegrante(i: number): void {
    this.form.equipo.splice(i, 1);
    this.marcarSucio();
  }

  agregarRubro(): void {
    this.form.presupuesto.push(filaPresupuestoVacia());
    this.marcarSucio();
  }

  quitarRubro(i: number): void {
    this.form.presupuesto.splice(i, 1);
    this.marcarSucio();
  }

  totalGeneral(): number {
    return totalPresupuesto(this.form.presupuesto);
  }

  excedeTope(): boolean {
    return this.totalGeneral() > this.topeMaximo();
  }

  moneda(valor: number): string {
    return new Intl.NumberFormat('es-CO', {
      style: 'currency',
      currency: 'COP',
      maximumFractionDigits: 0,
    }).format(valor || 0);
  }

  private actividadesValidas() {
    return this.form.actividades.filter((a) => a.nombre.trim());
  }

  private equipoValido() {
    return this.form.equipo.filter((m) => m.nombre.trim() && m.rol.trim());
  }

  private presupuestoValido(): FilaPresupuesto[] {
    return this.form.presupuesto.filter(
      (r) =>
        r.descripcion_rubro.trim() &&
        r.cantidad !== null &&
        Number(r.cantidad) > 0 &&
        r.valor_unitario !== null &&
        Number(r.valor_unitario) >= 0,
    );
  }

  // ── Autollenado del representante ─────────────────────────────────
  autollenarRepresentante(): void {
    const doc = this.form.rep_numero_doc.trim();
    if (doc.length < 4) {
      this.autollenado.set(null);
      return;
    }
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
            this.autollenado.set('nuevo');
            return;
          }
          if (!this.form.rep_nombre1 && data.nombre1) this.form.rep_nombre1 = data.nombre1;
          if (!this.form.rep_nombre2 && data.nombre2) this.form.rep_nombre2 = data.nombre2;
          if (!this.form.rep_apellido1 && data.apellido1) this.form.rep_apellido1 = data.apellido1;
          if (!this.form.rep_apellido2 && data.apellido2) this.form.rep_apellido2 = data.apellido2;
          this.autollenado.set('ok');
        },
        error: () => this.autollenado.set(null),
      });
  }

  // ── Envío ─────────────────────────────────────────────────────────
  enviar(): void {
    for (let s = 1; s <= this.totalSecciones; s++) {
      const faltantes = this.faltantesDe(s);
      if (faltantes.length > 0) {
        this.seccionActual.set(s);
        this.erroresSeccion.set(faltantes);
        this.scrollArriba();
        return;
      }
    }

    this.enviando.set(true);
    this.erroresCampo.set({});
    this.erroresServidor.set([]);
    this.erroresSeccion.set([]);

    const url = this.cfg.url(
      `/banco-iniciativas/api/publico/${this.eventoId()}/inscribir/`,
    );

    this.http
      .post<{ id: number; detail: string }>(url, this.construirPayload())
      .subscribe({
        next: (resp) => {
          this.enviando.set(false);
          // Radicado: el borrador ya no tiene razón de existir, y dejarlo
          // invitaría a radicar dos veces la misma iniciativa.
          this.borradores.descartar(this.eventoId());
          this.exitoId.set(resp.id);
          this.exito.set(true);
          this.scrollArriba();
        },
        error: (err) => {
          this.enviando.set(false);
          const body = err.error as ApiError | null;
          if (err.status === 400 && body?.errors) {
            this.erroresCampo.set(body.errors);
            const msgs: string[] = [];
            for (const [campo, errs] of Object.entries(body.errors)) {
              for (const msg of errs) msgs.push(`${campo}: ${msg}`);
            }
            this.erroresServidor.set(msgs);
          } else {
            this.erroresServidor.set([
              body?.detail || 'Error al radicar. Intenta nuevamente.',
            ]);
          }
          this.scrollArriba();
        },
      });
  }

  /**
   * Arma el multipart del POST.
   *
   * Convenciones (contrato del formulario, 2026-07-29):
   *   · Cabecera → una clave por campo del modelo, con su nombre exacto.
   *   · Listas de códigos (`instancias`, `escenarios`, `rango_etarios`,
   *     `ciclo_vital`, `objetivos_especificos`) → clave repetida, que es lo que
   *     lee `request.POST.getlist()` / un `ModelMultipleChoiceField`.
   *   · Colecciones con estructura (`enfoques`, `actividades`, `cronograma`,
   *     `equipo`, `presupuesto`) → una sola clave con JSON, porque un multipart
   *     plano no puede representar objetos anidados sin inventar convenciones
   *     de nombres tipo `equipo[0][rol]`.
   *   · Archivos → `soporte_legal`, `cedula_representante`, `rut`,
   *     `reconocimiento_deportivo`, `firma`.
   *   · `valor_total` NO se manda: es columna generada en la BD. Mandarlo
   *     permitiría radicar un total que no corresponde a cantidad × unitario y
   *     saltarse el tope presupuestal.
   */
  private construirPayload(): FormData {
    const fd = new FormData();
    const f = this.form;

    // Para que el backend borre el borrador del servidor en la misma
    // operación en que radica: si se dejara vivo, quedarían cédulas guardadas
    // de una postulación que ya está en firme.
    const tokenBorrador = this.borradores.token(this.eventoId());
    if (tokenBorrador) fd.append('borrador_token', tokenBorrador);

    const txt = (clave: string, valor: string | number | null | undefined) => {
      if (valor === null || valor === undefined) return;
      const s = String(valor).trim();
      if (s !== '') fd.append(clave, s);
    };
    // Las tres compuertas Sí/No del documento (§2 sede, §6 participación,
    // §7.10 ambiental) son ChoiceField('si'|'no') en el servidor, no booleanos:
    // mandar 'true' devolvería «Escoja una opción válida» sobre un campo que el
    // ciudadano sí respondió.
    const siNo = (clave: string, valor: boolean | null) => {
      if (valor !== null) fd.append(clave, valor ? 'si' : 'no');
    };
    const lista = (clave: string, valores: Iterable<string>) => {
      for (const v of valores) if (v) fd.append(clave, v);
    };

    // ── §1 ──────────────────────────────────────────────────────────
    txt('nombre_organizacion', f.nombre_organizacion);
    txt('tipo_organizacion', f.tipo_organizacion);
    txt('numero_soporte_legal', f.numero_soporte_legal);
    txt('rep_tipo_doc', f.rep_tipo_doc);
    txt('rep_numero_doc', f.rep_numero_doc);
    txt('rep_nombre1', f.rep_nombre1);
    txt('rep_nombre2', f.rep_nombre2);
    txt('rep_apellido1', f.rep_apellido1);
    txt('rep_apellido2', f.rep_apellido2);
    txt('nivel_educativo', f.nivel_educativo);
    txt('titulos_obtenidos', f.titulos_obtenidos);

    // ── §2 ──────────────────────────────────────────────────────────
    txt('telefono', f.telefono);
    txt('correo', f.correo);
    siNo('tiene_sede_fisica', f.tiene_sede_fisica);
    if (f.tiene_sede_fisica === true) {
      txt('upz', f.upz);
      txt('barrio', f.barrio);
      // Espejo en texto del barrio elegido: la columna existe desde M-02 y los
      // reportes la leen. Se deriva del código, no se vuelve a preguntar.
      txt('barrio_texto', this.nombreBarrio());
      txt('direccion', f.direccion);
      txt('estrato', f.estrato);
      // Las dos coordenadas van juntas o no van: media coordenada no ubica nada.
      if (f.direccion_lon !== null && f.direccion_lat !== null) {
        txt('direccion_lon', f.direccion_lon);
        txt('direccion_lat', f.direccion_lat);
      }
    }
    txt('redes_web', f.redes_web);
    txt('redes_facebook', f.redes_facebook);
    txt('redes_instagram', f.redes_instagram);

    // ── §3 ──────────────────────────────────────────────────────────
    txt('tamano_staff_num', f.tamano_staff_num);
    txt('anios_experiencia', f.anios_experiencia);
    txt('composicion_organizacion', f.composicion_organizacion);
    txt('rango_poblacion', f.rango_poblacion);

    // ── §4 ──────────────────────────────────────────────────────────
    txt('modalidad_actividad', f.modalidad_actividad);
    txt('disciplina_actividad', f.disciplina_actividad);
    txt('disciplina_actividad_otro', f.disciplina_actividad_otro);
    txt('arraigo_red', f.arraigo_red);
    txt('arraigo_escenario_otro', f.arraigo_escenario_otro);
    txt('arraigo_espacio_nombre', f.arraigo_espacio_nombre);
    txt('arraigo_direccion', f.arraigo_direccion);
    txt('arraigo_estrato', f.arraigo_estrato);
    txt('arraigo_actividad', f.arraigo_actividad);
    if (f.arraigo_lon !== null && f.arraigo_lat !== null) {
      txt('arraigo_lon', f.arraigo_lon);
      txt('arraigo_lat', f.arraigo_lat);
    }
    // Botones del nivel §4.2 → escenarios donde la organización opera hoy.
    lista('escenarios_actuales', f.arraigo_escenarios);

    // ── §5 ──────────────────────────────────────────────────────────
    lista('rango_etarios', f.rango_etarios);

    // ── §6 ──────────────────────────────────────────────────────────
    siNo('participa_espacio', f.participa_espacio);
    if (f.participa_espacio === true) lista('instancias', f.instancias);
    txt('beneficio_alk', f.beneficio_alk);

    // ── §7 ──────────────────────────────────────────────────────────
    txt('problematica', f.problematica);
    txt('justificacion', f.justificacion);
    txt('modalidad_propuesta', f.modalidad_propuesta);
    txt('disciplina_principal', f.disciplina_principal);
    txt('otros_deportes', f.otros_deportes);
    txt('objetivo_general', f.objetivo_general);
    // Colección, no lista de códigos: en el servidor es un ListaJsonField que
    // exige exactamente 3 textos. Con claves repetidas Django solo leería el
    // último y el json.loads reventaría sobre el texto del tercer objetivo.
    fd.append(
      'objetivos_especificos',
      JSON.stringify(f.objetivos_especificos.map((o) => o.trim()).filter((o) => o)),
    );
    txt('cobertura_staff', f.cobertura_staff);
    txt('cobertura_comunidad', f.cobertura_comunidad);
    txt('cobertura_indirectos', f.cobertura_indirectos);
    lista('ciclo_vital', f.ciclo_vital);
    txt('diversidad_genero_propuesta', f.diversidad_genero_propuesta);
    txt('ejecucion_red', f.ejecucion_red);
    txt('ejecucion_escenario_otro', f.ejecucion_escenario_otro);
    txt('nombre_espacio_ejecucion', f.nombre_espacio_ejecucion);
    txt('direccion_espacio_ejecucion', f.direccion_espacio_ejecucion);
    // Estrato DECLARADO por el proponente. El que puntúa lo certifica IDECA en
    // el servidor (`ejecucion_estrato_ideca`) y NO se manda desde acá.
    txt('ejecucion_estrato', f.ejecucion_estrato);
    if (f.ejecucion_lon !== null && f.ejecucion_lat !== null) {
      txt('ejecucion_lon', f.ejecucion_lon);
      txt('ejecucion_lat', f.ejecucion_lat);
    }
    // Botones del nivel §7.9.1 → escenarios requeridos por la propuesta.
    lista('escenarios', f.ejecucion_escenarios);
    siNo('sostenibilidad_ambiental', f.sostenibilidad_ambiental);
    if (f.sostenibilidad_ambiental === true) {
      txt('sostenibilidad_sustento', f.sostenibilidad_sustento);
    }

    // §5.2 + §7.8 · enfoques con su ORDEN DE ACTIVACIÓN explícito.
    const enfoques = [
      ...f.enfoques_52.map((s, i) => ({
        seccion: '5.2',
        familia: s.familia,
        orden: i + 1,
        opciones: [...s.opciones],
      })),
      ...f.enfoques_78.map((s, i) => ({
        seccion: '7.8',
        familia: s.familia,
        orden: i + 1,
        opciones: [...s.opciones],
      })),
    ];
    if (enfoques.length) fd.append('enfoques', JSON.stringify(enfoques));

    // ── §8 ──────────────────────────────────────────────────────────
    txt('metodologia', f.metodologia);

    // Solo viajan las actividades con nombre; los índices del cronograma y del
    // presupuesto se remapean a ESA lista, no a la del formulario, para que
    // `actividad_idx` signifique lo mismo en los dos lados.
    const indicesValidos: number[] = [];
    f.actividades.forEach((a, i) => {
      if (a.nombre.trim()) indicesValidos.push(i);
    });
    const nuevoIndice = new Map<number, number>();
    indicesValidos.forEach((original, nuevo) => nuevoIndice.set(original, nuevo));

    const actividades = indicesValidos.map((i) => ({
      nombre: f.actividades[i].nombre.trim(),
      descripcion: f.actividades[i].descripcion.trim(),
    }));
    fd.append('actividades', JSON.stringify(actividades));

    const cronograma: Array<{ actividad_idx: number; mes: number; semana: number }> = [];
    indicesValidos.forEach((original, nuevo) => {
      for (const celda of f.actividades[original].celdas) {
        const [mes, semana] = celda.split('-').map(Number);
        if (mes >= 1 && mes <= 4 && semana >= 1 && semana <= 4) {
          cronograma.push({ actividad_idx: nuevo, mes, semana });
        }
      }
    });
    cronograma.sort(
      (a, b) =>
        a.actividad_idx - b.actividad_idx || a.mes - b.mes || a.semana - b.semana,
    );
    fd.append('cronograma', JSON.stringify(cronograma));

    const equipo = this.equipoValido().map((m) => ({
      nombre: m.nombre.trim(),
      nivel_formacion_codigo: m.nivel_formacion_codigo || null,
      rol: m.rol.trim(),
    }));
    fd.append('equipo', JSON.stringify(equipo));

    const presupuesto = this.presupuestoValido().map((r) => ({
      actividad_idx:
        r.actividad_idx !== null && nuevoIndice.has(r.actividad_idx)
          ? nuevoIndice.get(r.actividad_idx)
          : null,
      descripcion_rubro: r.descripcion_rubro.trim(),
      cantidad: Number(r.cantidad),
      valor_unitario: Number(r.valor_unitario),
    }));
    fd.append('presupuesto', JSON.stringify(presupuesto));

    // ── §9 ──────────────────────────────────────────────────────────
    fd.append('compromiso_redes', 'true');
    fd.append('compromiso_carta_1ano', 'true');
    fd.append('compromiso_actualizacion', 'true');
    fd.append('declaracion_buena_fe', 'true');
    txt('firma_cedula', f.firma_cedula);
    txt('firma_fecha', f.firma_fecha);

    // ── Anexos ──────────────────────────────────────────────────────
    for (const tipo of Object.keys(this.anexos) as Array<keyof BancoAnexos>) {
      const file = this.anexos[tipo];
      if (file) fd.append(tipo, file, file.name);
    }

    return fd;
  }

  /** Hoy en ISO. Tope del calendario de firma: el servidor rechaza el futuro. */
  hoyISO(): string {
    return new Date().toISOString().slice(0, 10);
  }

  /** Nombre del barrio elegido, para el espejo en texto de la columna legacy. */
  private nombreBarrio(): string {
    const cat = this.catalogos();
    if (!cat || !this.form.barrio) return '';
    return (
      cat.barrios.find((b) => codigoStr(b.codigo) === this.form.barrio)?.nombre ?? ''
    );
  }
}
