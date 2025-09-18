import { Component, OnDestroy, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Subscription } from 'rxjs';
import { AiStreamState, FilledField } from '../../core/ai-stream.state';

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

  constructor(public state: AiStreamState) {}

  ngOnInit(): void {
    this.sub = this.state.list$.subscribe((list: FilledField[]) => {
      this.fields = list ?? [];
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

  // --------- Acciones ----------
  clearField(f: FilledField) {
    this.state.applyDelta({ path: f.path, value: '' });
  }

  clearAll() {
    this.state.clearAll();
  }
}
