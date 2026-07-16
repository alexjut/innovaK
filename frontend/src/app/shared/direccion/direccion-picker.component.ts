import {
  AfterViewInit, Component, ElementRef, EventEmitter, Input, OnDestroy,
  Output, ViewChild, signal,
} from '@angular/core';
import { CommonModule } from '@angular/common';
import { HttpClient } from '@angular/common/http';
import { FormsModule } from '@angular/forms';
import { Subject, debounceTime, distinctUntilChanged, switchMap } from 'rxjs';
import * as L from 'leaflet';

export interface DireccionElegida {
  direccion: string;
  lon: number;
  lat: number;
  en_kennedy: boolean;
}

interface Sugerencia {
  direccion: string;
  via: string;
  placa: string | null;
  lon: number | null;
  lat: number | null;
  completa: boolean;
  en_kennedy: boolean;
}

/**
 * Selector de dirección: se escribe, se ELIGE de la lista, y queda el punto.
 *
 * Por qué existe: una dirección escrita a mano es una dirección que puede no
 * existir. En el piloto del Banco, 11 de 24 inscripciones quedaron sin ubicar
 * por eso (4 direcciones inexistentes, 4 de otra localidad, 3 vacías). Y la
 * dirección alimenta el estrato, que alimenta el puntaje, que reparte recursos.
 *
 * El contrato es estricto a propósito: `direccionElegida` SOLO emite cuando el
 * usuario eligió una dirección real de Catastro (o movió el pin a mano, que es
 * una decisión explícita). Escribir texto no emite nada — si el formulario no
 * recibió nada, es que no hay dirección válida, y así debe guardarse.
 *
 * **Sin `maxlength` a propósito.** Esto ya no es un campo de texto libre: lo que
 * sale de acá es una dirección normalizada de Catastro. Medido sobre las
 * 1.771.088 placas de Bogotá (2026-07-16): la más larga tiene **25 caracteres**,
 * el promedio 16, y **ninguna** pasa de 50 — el límite de los modelos que la
 * reciben. Acotar el largo acá solo podría cortar una dirección válida.
 *
 * Uso:
 *   <app-direccion-picker
 *      [valor]="direccion"
 *      [soloKennedy]="true"
 *      (direccionElegida)="onDireccion($event)" />
 */
@Component({
  selector: 'app-direccion-picker',
  standalone: true,
  imports: [CommonModule, FormsModule],
  template: `
    <div class="dp">
      <label class="dp__label" *ngIf="label">{{ label }}</label>

      <div class="dp__campo">
        <input
          type="text"
          class="dp__input"
          [class.dp__input--ok]="elegida()"
          [(ngModel)]="texto"
          (ngModelChange)="onTexto($event)"
          (focus)="abierto.set(true)"
          [placeholder]="placeholder"
          autocomplete="off"
          spellcheck="false" />
        <span class="dp__estado" *ngIf="buscando()">buscando…</span>
        <span class="dp__estado dp__estado--ok" *ngIf="elegida() && !buscando()">✓</span>
      </div>

      <ul class="dp__lista" *ngIf="abierto() && sugerencias().length">
        <li *ngFor="let s of sugerencias()"
            class="dp__item"
            [class.dp__item--fuera]="!s.en_kennedy"
            (mousedown)="elegir(s)">
          <span class="dp__item-dir">{{ s.direccion }}</span>
          <span class="dp__item-nota" *ngIf="!s.completa">seguí escribiendo el número…</span>
          <span class="dp__item-nota dp__item-nota--fuera" *ngIf="s.completa && !s.en_kennedy">
            fuera de Kennedy
          </span>
        </li>
      </ul>

      <p class="dp__msg dp__msg--vacio"
         *ngIf="abierto() && !buscando() && !sugerencias().length && texto.length >= 3">
        Esa dirección no existe en el catastro de Bogotá. Revisá el número.
      </p>

      <p class="dp__msg dp__msg--alerta" *ngIf="elegida() && !elegida()!.en_kennedy">
        Esta dirección existe, pero <strong>no está en la localidad de Kennedy</strong>.
      </p>

      <ng-container *ngIf="conMapa">
        <div class="dp__mapa" #mapaEl [class.dp__mapa--visible]="elegida()"></div>
        <p class="dp__ayuda" *ngIf="elegida()">
          ¿El punto no queda exacto? Arrastralo hasta la puerta.
        </p>
      </ng-container>
    </div>
  `,
  styles: [`
    .dp { position: relative; display: block; }
    .dp__label { display: block; font-size: .82rem; font-weight: 600; margin-bottom: .3rem; }
    .dp__campo { position: relative; display: flex; align-items: center; }
    .dp__input {
      width: 100%; padding: .6rem .75rem; border: 1px solid #cbd5e1;
      border-radius: 8px; font-size: .95rem;
    }
    .dp__input--ok { border-color: #0D9488; }
    .dp__estado {
      position: absolute; right: .6rem; font-size: .75rem; color: #64748b;
    }
    .dp__estado--ok { color: #0D9488; font-weight: 700; }
    .dp__lista {
      position: absolute; z-index: 1000; left: 0; right: 0; margin: .2rem 0 0;
      padding: 0; list-style: none; background: #fff; border: 1px solid #cbd5e1;
      border-radius: 8px; box-shadow: 0 8px 20px rgba(0,0,0,.12);
      max-height: 260px; overflow-y: auto;
    }
    .dp__item {
      padding: .55rem .75rem; cursor: pointer; display: flex;
      justify-content: space-between; gap: .5rem; align-items: baseline;
    }
    .dp__item:hover { background: #f1f5f9; }
    .dp__item--fuera { background: #fffbeb; }
    .dp__item-dir { font-size: .9rem; }
    .dp__item-nota { font-size: .72rem; color: #94a3b8; white-space: nowrap; }
    .dp__item-nota--fuera { color: #b45309; font-weight: 600; }
    .dp__msg { margin: .4rem 0 0; font-size: .8rem; }
    .dp__msg--vacio { color: #64748b; }
    .dp__msg--alerta {
      color: #b45309; background: #fffbeb; border: 1px solid #fde68a;
      border-radius: 6px; padding: .5rem .6rem;
    }
    .dp__mapa {
      height: 0; margin-top: .5rem; border-radius: 8px; overflow: hidden;
      transition: height .18s ease;
    }
    .dp__mapa--visible { height: 190px; border: 1px solid #cbd5e1; }
    .dp__ayuda { margin: .3rem 0 0; font-size: .75rem; color: #64748b; }
  `],
})
export class DireccionPickerComponent implements AfterViewInit, OnDestroy {
  @Input() label = 'Dirección';
  @Input() placeholder = 'Ej: Calle 42F Sur # 72K-10';
  @Input() soloKennedy = true;
  /** `false` cuando el formulario que lo hospeda ya tiene su propio mapa: dos
   *  mapas en la misma pantalla confunden más de lo que ayudan. El punto sigue
   *  saliendo por `direccionElegida`; lo dibuja el anfitrión. */
  @Input() conMapa = true;
  @Input() set valor(v: string | null | undefined) {
    if (v && !this.texto) { this.texto = v; }
  }
  @Output() direccionElegida = new EventEmitter<DireccionElegida | null>();

  @ViewChild('mapaEl') mapaEl?: ElementRef<HTMLDivElement>;

  texto = '';
  readonly sugerencias = signal<Sugerencia[]>([]);
  readonly buscando = signal(false);
  readonly abierto = signal(false);
  readonly elegida = signal<DireccionElegida | null>(null);

  private readonly teclas$ = new Subject<string>();
  private map?: L.Map;
  private marker?: L.Marker;

  constructor(private http: HttpClient) {
    // 250 ms: por debajo se dispara una consulta por tecla sin que el usuario
    // termine de pensar; por encima se siente lento.
    this.teclas$.pipe(
      debounceTime(250),
      distinctUntilChanged(),
      switchMap(q => {
        this.buscando.set(true);
        return this.http.get<{ sugerencias: Sugerencia[] }>(
          '/geo/api/direcciones/sugerir/', { params: { q, limite: 8 } });
      }),
    ).subscribe({
      next: r => { this.sugerencias.set(r.sugerencias ?? []); this.buscando.set(false); },
      error: () => { this.sugerencias.set([]); this.buscando.set(false); },
    });
  }

  ngAfterViewInit(): void { /* el mapa se crea al elegir, no antes */ }

  ngOnDestroy(): void { this.map?.remove(); }

  onTexto(v: string): void {
    // Escribir invalida lo elegido: si el texto ya no es la dirección que se
    // eligió, el formulario NO puede seguir creyendo que tiene un punto válido.
    if (this.elegida() && v !== this.elegida()!.direccion) {
      this.elegida.set(null);
      this.direccionElegida.emit(null);
    }
    this.abierto.set(true);
    if ((v ?? '').trim().length < 3) {
      this.sugerencias.set([]);
      return;
    }
    this.teclas$.next(v);
  }

  elegir(s: Sugerencia): void {
    // Una vía sin placa no es una dirección: se completa el texto y se sigue.
    if (!s.completa) {
      this.texto = s.direccion + ' # ';
      this.teclas$.next(this.texto);
      return;
    }
    this.texto = s.direccion;
    this.abierto.set(false);
    this.sugerencias.set([]);
    const elegida: DireccionElegida = {
      direccion: s.direccion, lon: s.lon!, lat: s.lat!, en_kennedy: s.en_kennedy,
    };
    this.elegida.set(elegida);
    this.direccionElegida.emit(elegida);
    setTimeout(() => this.mostrarEnMapa(elegida), 0);
  }

  private mostrarEnMapa(d: DireccionElegida): void {
    const el = this.mapaEl?.nativeElement;
    if (!this.conMapa || !el) { return; }
    if (!this.map) {
      this.map = L.map(el, { center: [d.lat, d.lon], zoom: 17, attributionControl: false });
      L.tileLayer('https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png', {
        subdomains: 'abcd', maxZoom: 19,
      }).addTo(this.map);
    }
    this.map.invalidateSize();
    this.map.setView([d.lat, d.lon], 17);

    if (this.marker) {
      this.marker.setLatLng([d.lat, d.lon]);
    } else {
      this.marker = L.marker([d.lat, d.lon], { draggable: true }).addTo(this.map);
      // Arrastrar es una corrección deliberada del usuario (la puerta real vs.
      // el centroide de la placa): se respeta y se emite el punto movido.
      this.marker.on('dragend', () => {
        const p = this.marker!.getLatLng();
        const actual = this.elegida();
        if (!actual) { return; }
        const movida: DireccionElegida = {
          ...actual,
          lat: Math.round(p.lat * 1e6) / 1e6,
          lon: Math.round(p.lng * 1e6) / 1e6,
        };
        this.elegida.set(movida);
        this.direccionElegida.emit(movida);
      });
    }
  }
}
