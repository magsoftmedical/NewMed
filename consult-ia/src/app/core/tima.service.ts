import { Injectable, inject } from '@angular/core';
import { HttpClient, HttpHeaders } from '@angular/common/http';
import { environment } from '../../environments/environment';
import { map, Observable } from 'rxjs';

export interface ClinicalNote {
  anamnesis?: { sintomas?: string; tiempo_sintomas?: { valor?: number; unidad?: string }; relato?: string; };
  examen_fisico?: { glasgow?: { ocular?: number; verbal?: number; motora?: number }; descripcion?: string; };
  signos_vitales?: { tas?: number; tad?: number; temp?: number; fc?: number; fr?: number; spo2?: number; peso?: number; talla?: number; imc?: number; };
  diagnosticos?: { cie10?: string; nombre: string; tipo?: 'presuntivo'|'definitivo' }[];
  medicamentos?: { nombre: string; dosis?: string; frecuencia?: string; duracion?: string }[];
  indicaciones?: string;
}

@Injectable({ providedIn: 'root' })
export class TimaService {
  private http = inject(HttpClient);
  private base = environment.timaBase;

  private headers() { return new HttpHeaders({ 'x-api-key': 'apikey_tima_2025' }); }

  // ⬇️ la API devuelve { formatted: ClinicalNote }, lo mapeamos
formatClinicalNote(transcript: string, locale='es-PE'): Observable<ClinicalNote> {
  return this.http
    .post<{ formatted: ClinicalNote }>(`${this.base}/format/clinical-note`,
      { transcript, locale },
      { headers: new HttpHeaders({ 'x-api-key': 'apikey_tima_2025' }) }
    )
    .pipe(map(r => r.formatted));
}
}
