import { Component, OnDestroy, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Observable, Subscription } from 'rxjs';
import { AiStreamState, FilledField } from '../../core/ai-stream.state';
import { AiStreamService } from '../../core/ai-stream.service';

@Component({
  selector: 'ai-stream-panel',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './ai-stream-panel.component.html',
  styleUrls: ['./ai-stream-panel.component.scss']
})
export class AiStreamPanelComponent implements OnInit, OnDestroy {
  private sub?: Subscription;

  /** Lista de campos llenados por IA */
  fields: FilledField[] = [];

  /** Secciones únicas derivadas de fields */
  sections: string[] = [];

  /** Sección actualmente abierta */
  open: string | null = null;

  /** Contadores globales */
  private doneCount = 0;
  private totalCount = 0;

  /** Texto del asistente IA (streaming) */
  aiText$: Observable<string>;

  /** Campos faltantes */
  missing$: Observable<string[]>;

  /** Sugerencias */
  suggestions$: Observable<string[]>;

  constructor(
    public state: AiStreamState,
    private aiStream: AiStreamService
  ) {
    this.aiText$ = this.aiStream.aiText$;
    this.missing$ = this.aiStream.missing$;
    this.suggestions$ = this.aiStream.suggestions$;
  }

  ngOnInit(): void {
    this.sub = this.state.list$.subscribe((list: FilledField[]) => {
      this.fields = list ?? [];

      // Extraer secciones únicas
      this.sections = [...new Set(this.fields.map(x => x.section))];

      // abrir la primera sección si no hay una abierta
      if (!this.open && this.sections.length) this.open = this.sections[0];

      // actualizar contadores
      this.totalCount = this.fields.length;
      this.doneCount = this.fields.filter(f => f.value !== undefined && f.value !== '').length;
    });
  }

  ngOnDestroy(): void {
    this.sub?.unsubscribe();
  }

  // --------- API para el template ----------

  /** Campos por sección */
  bySection(s: string): FilledField[] {
    return this.fields.filter(f => f.section === s);
  }

  /** Completados globales */
  completed(): number {
    return this.doneCount;
  }

  /** Total global */
  total(): number {
    return this.totalCount;
  }

  /** Completados por sección */
  completedIn(s: string): number {
    return this.bySection(s).filter(f => f.value !== undefined && f.value !== '').length;
  }

  /** Porcentaje global 0..100 para la barra */
  progress(): number {
    const t = this.totalCount || 0;
    return t ? Math.round((this.doneCount / t) * 100) : 0;
  }

  /** trackBy */
  trackByPath(_: number, f: FilledField) {
    return f.path;
  }

  /** abrir/cerrar acordeón */
  toggle(s: string) {
    this.open = this.open === s ? null : s;
  }

  /** Total de campos en una sección */
  totalIn(s: string): number {
    return this.bySection(s).length;
  }

  /** Verificar si una sección está completa */
  isSectionComplete(s: string): boolean {
    const fields = this.bySection(s);
    if (fields.length === 0) return false;
    return fields.every(f => f.value !== undefined && f.value !== '');
  }

  /** Total de secciones */
  totalSections(): number {
    return this.sections.length;
  }

  /** Secciones completadas */
  completedSections(): number {
    return this.sections.filter(s => this.isSectionComplete(s)).length;
  }

  /** Verifica si hay alguna actividad (texto de IA, sugerencias, o campos) */
  hasActivity(): boolean {
    // Mostrar contadores si hay secciones O si ya se está recibiendo datos de IA
    return this.sections.length > 0 || this.fields.length > 0;
  }

  // --------- Acciones ----------
  clearField(f: FilledField) {
    this.state.applyDelta({ path: f.path, value: '' });
  }

  clearAll() {
    this.state.clearAll();
  }
}
