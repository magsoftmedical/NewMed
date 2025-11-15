import { Injectable } from '@angular/core';
import { BehaviorSubject } from 'rxjs';

export type FieldStatus = 'empty' | 'new' | 'updated';
export interface FilledField {
  path: string; label: string; section: string;
  value?: any; status: FieldStatus; updatedAt?: number;
}

function pathToSection(p: string) {
  // IGNORAR paths que son metadata de IA (no son campos del formulario)
  if (p.includes('sugerencias') || p.includes('Sugerencias')) return '__IGNORE__';
  if (p.includes('faltantes') || p.includes('Campos faltantes')) return '__IGNORE__';
  if (p.includes('missing')) return '__IGNORE__';

  if (p.startsWith('examenClinico.signosVitales')) return 'Signos vitales';
  if (p.startsWith('examenClinico')) return 'Examen clínico';
  if (p.startsWith('anamnesis')) return 'Anamnesis';
  if (p.startsWith('diagnosticos')) return 'Diagnóstico';
  if (p.startsWith('tratamientos')) return 'Tratamiento';
  if (p.startsWith('firma')) return 'Firma';
  if (p.startsWith('afiliacion')) return 'Afiliación';
  return 'Otros';
}
const label = (p: string) =>
  (p.split('.').pop() || p)
    .replace(/([A-Z])/g, ' $1')
    .replace(/_/g, ' ')
    .replace(/\b\w/g, m => m.toUpperCase());

@Injectable({ providedIn: 'root' })
export class AiStreamState {
  private fields = new Map<string, FilledField>();
  private _list$ = new BehaviorSubject<FilledField[]>([]);
  list$ = this._list$.asObservable();

  applyDelta(delta: { path: string; value: any }) {
    const k = delta.path, now = Date.now();

    // IGNORAR campos que no son del formulario (metadata de IA)
    const section = pathToSection(k);
    if (section === '__IGNORE__') {
      return; // No agregar este campo
    }

    const ex = this.fields.get(k);
    if (!ex) {
      this.fields.set(k, { path: k, label: label(k), section, value: delta.value, status: 'new', updatedAt: now });
    } else {
      ex.value = delta.value;
      ex.status = ex.status === 'empty' ? 'new' : 'updated';
      ex.updatedAt = now;
      this.fields.set(k, ex);
    }
    this.emit();

    // quitar el "updated" después de 3s
    setTimeout(() => {
      const f = this.fields.get(k);
      if (f && f.status === 'updated') { f.status = 'new'; this.fields.set(k, f); this.emit(); }
    }, 3000);
  }

  clearAll() { this.fields.clear(); this.emit(); }

  private emit() {
    const arr = Array.from(this.fields.values())
      .sort((a, b) => a.section.localeCompare(b.section) || a.label.localeCompare(b.label));
    this._list$.next(arr);
  }
}
