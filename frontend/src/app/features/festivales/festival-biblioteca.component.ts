import { CommonModule } from '@angular/common';
import {
  Component, Input, OnDestroy, OnInit, inject, signal, computed,
} from '@angular/core';
import { FormsModule } from '@angular/forms';
import { DescargasService } from '../../core/descargas.service';
import { FestivalesApi } from './festivales.api';
import { FestivalArchivo, FestivalDia, TipoArchivo } from './festivales.types';

/**
 * Biblioteca de evidencias del festival (PR-B): fotos, videos, actas,
 * listados y soportes. El binario va CIFRADO a Mongo; aquí se sube,
 * lista (con miniatura para imágenes vía blob autenticado), descarga y
 * borra. Tope de fotos configurado en el backend (por ahora 3).
 */
@Component({
  standalone: true,
  selector: 'app-festival-biblioteca',
  imports: [CommonModule, FormsModule],
  template: `
    <section class="biblio">
      <div class="biblio__head">
        <h2><i class="fa fa-photo-film"></i> Biblioteca / evidencias</h2>
        <span class="cuenta">{{ fotos().length }}/{{ maxFotos }} fotos</span>
      </div>

      @if (flash()) { <div class="ui-info-bar ui-info-bar--success">{{ flash() }}</div> }
      @if (error()) { <div class="ui-info-bar ui-info-bar--danger">{{ error() }}</div> }

      <!-- Subida -->
      <form class="subir" (ngSubmit)="subir()">
        <div class="grid">
          <label>Tipo
            <select [(ngModel)]="tipo" name="tipo">
              <option value="foto">Foto</option>
              <option value="video">Video</option>
              <option value="acta">Acta</option>
              <option value="listado">Listado de asistencia</option>
              <option value="soporte">Soporte</option>
            </select>
          </label>
          <label>Día (opcional)
            <select [(ngModel)]="diaId" name="dia">
              <option [ngValue]="null">— General del festival —</option>
              @for (d of dias; track d.id) {
                <option [ngValue]="d.id">{{ d.fecha }}{{ d.nombre ? ' · ' + d.nombre : '' }}</option>
              }
            </select>
          </label>
          <label>Archivo
            <input type="file" (change)="onFile($event)"
                   [accept]="tipo === 'foto' ? 'image/*' : '*/*'">
          </label>
          <label>Descripción (opcional)
            <input type="text" [(ngModel)]="descripcion" name="desc" placeholder="Ej. Tarima principal, día 1">
          </label>
        </div>
        @if (tipo === 'foto' && fotos().length >= maxFotos) {
          <p class="tope">Ya llegaste al tope de {{ maxFotos }} fotos. Borra una para subir otra.</p>
        }
        <button type="submit" class="ui-btn ui-btn--primary ui-btn--sm"
                [disabled]="uploading() || !file() || (tipo === 'foto' && fotos().length >= maxFotos)">
          <i class="fa fa-upload"></i> {{ uploading() ? 'Subiendo…' : 'Subir evidencia' }}
        </button>
        <p class="hint">Las fotos se optimizan automáticamente y se guardan cifradas. Máx 50 MB.</p>
      </form>

      @if (loading()) { <div class="ui-info-bar ui-info-bar--info">Cargando biblioteca…</div> }

      @if (!loading() && archivos().length === 0) {
        <div class="ui-empty-state ui-empty-state--sm">
          <i class="fa fa-folder-open"></i>
          <p>Sin evidencias todavía. Sube fotos, actas o listados del festival.</p>
        </div>
      }

      <!-- Galería de imágenes -->
      @if (fotos().length > 0) {
        <h3>Fotos</h3>
        <div class="galeria">
          @for (a of fotos(); track a.id) {
            <figure class="foto">
              @if (thumbs()[a.id]) {
                <img [src]="thumbs()[a.id]" [alt]="a.descripcion || a.nombre_archivo || 'Foto'"
                     (click)="abrir(thumbs()[a.id])">
              } @else {
                <div class="foto__ph"><i class="fa fa-image"></i></div>
              }
              <figcaption>
                <span>{{ a.descripcion || a.nombre_archivo }}</span>
                @if (a.dia_fecha) { <small>{{ a.dia_fecha }}</small> }
              </figcaption>
              <button class="foto__del" (click)="eliminar(a)" title="Eliminar"><i class="fa fa-trash"></i></button>
            </figure>
          }
        </div>
      }

      <!-- Documentos / videos -->
      @if (docs().length > 0) {
        <h3>Documentos y videos</h3>
        <ul class="docs">
          @for (a of docs(); track a.id) {
            <li class="doc">
              <i class="fa" [class.fa-file-video]="a.tipo === 'video'"
                 [class.fa-file-lines]="a.tipo !== 'video'"></i>
              <div class="doc__info">
                <span class="doc__name">{{ a.nombre_archivo || a.tipo_display }}</span>
                <small>{{ a.tipo_display }}{{ a.dia_fecha ? ' · ' + a.dia_fecha : '' }}{{ a.tamano_bytes ? ' · ' + tam(a.tamano_bytes) : '' }}</small>
                @if (a.descripcion) { <small class="doc__desc">{{ a.descripcion }}</small> }
              </div>
              <button class="link" (click)="descargar(a)" title="Descargar"><i class="fa fa-download"></i></button>
              <button class="link link--danger" (click)="eliminar(a)" title="Eliminar"><i class="fa fa-trash"></i></button>
            </li>
          }
        </ul>
      }
    </section>
  `,
  styles: [`
    @use '../../../styles/tokens' as *;
    :host { display: block; }
    .biblio { background: #fff; border: 1px solid $color-border; border-radius: $radius-lg; padding: $space-4; margin-top: $space-3; }
    .biblio__head { display: flex; justify-content: space-between; align-items: center; }
    .biblio__head h2 { margin: 0; color: $color-primary; font-size: 1.1rem; }
    .cuenta { font-size: $font-size-sm; color: $color-text-muted; font-weight: 600; }
    h3 { margin: $space-3 0 $space-2; font-size: .95rem; color: $color-text; }

    .subir { border: 1px dashed $color-border; border-radius: $radius-md; padding: $space-3; margin: $space-3 0; background: #FAFAFA; }
    .subir .grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: $space-2 $space-3; }
    @media (max-width: 700px) { .subir .grid { grid-template-columns: 1fr; } }
    .subir label { display: flex; flex-direction: column; gap: 4px; font-size: $font-size-sm; color: $color-text-muted; font-weight: 600; }
    .subir input, .subir select { font-size: $font-size-sm; padding: 6px 8px; border: 1px solid $color-border; border-radius: $radius-sm; font-family: inherit; }
    .subir button { margin-top: $space-2; }
    .hint { font-size: .72rem; color: $color-text-muted; margin: $space-1 0 0; }
    .tope { font-size: $font-size-sm; color: #B45309; margin: $space-2 0 0; }

    .galeria { display: grid; grid-template-columns: repeat(auto-fill, minmax(160px, 1fr)); gap: $space-3; }
    .foto { position: relative; margin: 0; border: 1px solid $color-border; border-radius: $radius-md; overflow: hidden; background: #F9FAFB; }
    .foto img { width: 100%; height: 130px; object-fit: cover; display: block; cursor: zoom-in; }
    .foto__ph { height: 130px; display: flex; align-items: center; justify-content: center; color: $color-text-muted; font-size: 1.5rem; }
    .foto figcaption { padding: 6px 8px; font-size: .72rem; color: $color-text; display: flex; flex-direction: column; gap: 2px; }
    .foto figcaption small { color: $color-text-muted; }
    .foto__del { position: absolute; top: 6px; right: 6px; background: rgba(255,255,255,.9); border: none; border-radius: 6px; padding: 4px 6px; cursor: pointer; color: #DC2626; }
    .foto__del:hover { background: #fff; }

    .docs { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: $space-2; }
    .doc { display: flex; align-items: center; gap: $space-2; border: 1px solid $color-border; border-radius: $radius-sm; padding: $space-2 $space-3; }
    .doc > i { font-size: 1.2rem; color: $color-primary; }
    .doc__info { flex: 1; display: flex; flex-direction: column; }
    .doc__name { font-weight: 600; font-size: $font-size-sm; }
    .doc__info small { color: $color-text-muted; font-size: .72rem; }
    .doc__desc { font-style: italic; }
    .link { background: none; border: none; cursor: pointer; color: $color-text-muted; padding: 4px 6px; }
    .link:hover { color: $color-primary; }
    .link--danger:hover { color: #DC2626; }
  `],
})
export class FestivalBibliotecaComponent implements OnInit, OnDestroy {
  @Input({ required: true }) festivalId!: number;
  @Input() dias: FestivalDia[] = [];
  @Input() maxFotos = 3;

  private api = inject(FestivalesApi);
  private descargas = inject(DescargasService);

  archivos = signal<FestivalArchivo[]>([]);
  thumbs = signal<Record<number, string>>({});
  loading = signal(true);
  uploading = signal(false);
  error = signal('');
  flash = signal('');

  tipo: TipoArchivo = 'foto';
  diaId: number | null = null;
  descripcion = '';
  file = signal<File | null>(null);

  fotos = computed(() => this.archivos().filter((a) => a.tipo === 'foto'));
  docs = computed(() => this.archivos().filter((a) => a.tipo !== 'foto'));

  ngOnInit(): void { this.cargar(); }

  ngOnDestroy(): void {
    // Libera los object URLs de las miniaturas.
    Object.values(this.thumbs()).forEach((u) => URL.revokeObjectURL(u));
  }

  private cargar(): void {
    this.loading.set(true);
    this.api.biblioteca(this.festivalId).subscribe({
      next: (list) => {
        this.archivos.set(list);
        this.loading.set(false);
        this.cargarThumbs(list);
      },
      error: (e) => { this.loading.set(false); this.error.set(this.msg(e)); },
    });
  }

  private cargarThumbs(list: FestivalArchivo[]): void {
    // Solo imágenes; cada blob se pide autenticado (Bearer vía interceptor).
    for (const a of list.filter((x) => x.es_imagen)) {
      if (this.thumbs()[a.id]) continue;
      this.api.blob(a.archivo_url).subscribe({
        next: (b) => this.thumbs.update((m) => ({ ...m, [a.id]: URL.createObjectURL(b) })),
        error: () => {},
      });
    }
  }

  onFile(ev: Event): void {
    const input = ev.target as HTMLInputElement;
    this.file.set(input.files && input.files.length ? input.files[0] : null);
  }

  subir(): void {
    const f = this.file();
    if (!f) { this.error.set('Selecciona un archivo.'); return; }
    this.uploading.set(true);
    this.error.set('');
    const fd = new FormData();
    fd.append('file', f);
    fd.append('tipo', this.tipo);
    if (this.diaId) fd.append('festival_dia_id', String(this.diaId));
    if (this.descripcion) fd.append('descripcion', this.descripcion);
    this.api.subirArchivo(this.festivalId, fd).subscribe({
      next: () => {
        this.uploading.set(false);
        this.file.set(null);
        this.descripcion = '';
        this.notify('Evidencia subida.');
        this.cargar();
      },
      error: (e) => { this.uploading.set(false); this.error.set(this.msg(e)); },
    });
  }

  descargar(a: FestivalArchivo): void {
    this.descargas.descargar(a.archivo_url, a.nombre_archivo || `evidencia_${a.id}`);
  }

  eliminar(a: FestivalArchivo): void {
    if (!confirm(`¿Eliminar "${a.nombre_archivo || a.tipo_display}"?`)) return;
    this.api.eliminarArchivo(a.id).subscribe({
      next: () => {
        const u = this.thumbs()[a.id];
        if (u) { URL.revokeObjectURL(u); this.thumbs.update((m) => { const c = { ...m }; delete c[a.id]; return c; }); }
        this.notify('Evidencia eliminada.');
        this.cargar();
      },
      error: (e) => this.error.set(this.msg(e)),
    });
  }

  abrir(url: string): void { window.open(url, '_blank'); }

  tam(bytes: number): string {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  }

  private notify(m: string): void { this.flash.set(m); setTimeout(() => this.flash.set(''), 3000); }

  private msg(e: { error?: { detail?: string }; status?: number; message?: string }): string {
    if (e?.error?.detail) return e.error.detail;
    if (e?.status === 401 || e?.status === 403) return 'No tienes permiso.';
    return e?.message || 'Error inesperado.';
  }
}
