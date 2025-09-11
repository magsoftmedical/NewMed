export type FieldStatus = 'empty' | 'new' | 'updated';

export interface FilledField {
  path: string;         // p.ej. "signos.talla"
  label: string;        // "Talla"
  value?: string | number | string[];
  section: string;      // "Signos vitales" | "Examen clínico" | ...
  status: FieldStatus;  // empty/new/updated
  updatedAt?: number;   // Date.now()
}
