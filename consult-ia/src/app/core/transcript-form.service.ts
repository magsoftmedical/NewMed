import { Injectable } from '@angular/core';
import { BehaviorSubject } from 'rxjs';

export interface ClinicalForm {
  paciente?: string;         // Nombre completo
  edad?: number;             // años
  sexo?: 'M' | 'F';
  motivoConsulta?: string;
  antecedentes?: string;     // médicos/quirúrgicos relevantes
  alergias?: string;
  medicacion?: string;
  examenFisico?: string;     // texto libre
  signosVitales?: {
    PA?: string; FC?: number; FR?: number; T?: number; SpO2?: number;
  };
  impresionDiagnostica?: string;
  plan?: string;             // indicaciones/tratamiento
}

@Injectable({ providedIn: 'root' })
export class TranscriptFormService {
  // Estado observable
  readonly form$ = new BehaviorSubject<ClinicalForm>({});
  readonly missing$ = new BehaviorSubject<string[]>([]);
  readonly cleanText$ = new BehaviorSubject<string>('');

  // Campos “mínimos” de una HC corta (ajusta a tu realidad)
  private required = [
    'paciente', 'edad', 'sexo', 'motivoConsulta',
    'impresionDiagnostica', 'plan'
  ];

  // --------- API pública ---------
  /** Llama esto cada vez que cambie el transcript (parcial + final). */
  updateFromTranscript(fullTranscript: string) {
    const clean = this.cleanTranscript(fullTranscript);
    const current = { ...this.form$.value };
    const updated = this.extractFields(clean, current);

    this.form$.next(updated);
    this.cleanText$.next(clean);
    this.missing$.next(this.computeMissing(updated));
  }

  /** Permite sobreescribir manualmente desde la UI */
  patchForm(patch: Partial<ClinicalForm>) {
    const updated = { ...this.form$.value, ...patch };
    this.form$.next(updated);
    this.missing$.next(this.computeMissing(updated));
  }

  // --------- Limpieza de texto ---------
  private cleanTranscript(t: string): string {
    // Une espacios, agrega punto si falta, normaliza mayúsculas detrás de punto
    let out = (t || '')
      .replace(/\s+/g, ' ')
      .replace(/\s*([,.!?;:])\s*/g, '$1 ')
      .replace(/\s+\./g, '.')
      .trim();

    if (out && !/[.!?]$/.test(out)) out += '.';

    // Capitalizar inicio de oraciones simple
    out = out.replace(/(^|[.!?]\s+)([a-záéíóúñ])/g, (m, p1, p2) => p1 + p2.toUpperCase());
    return out;
  }

  // --------- Extracción con reglas sencillas ---------
  private extractFields(text: string, base: ClinicalForm): ClinicalForm {
    const f: ClinicalForm = { ...base };
    const t = text;

    // Paciente (heurística: “paciente/ señor(a) NOMBRES APELLIDOS”)
    const mPac = t.match(/\b(?:paciente|señor(?:a)?|sr\.?|sra\.?)\s+([A-ZÁÉÍÓÚÑ][\wÁÉÍÓÚÑ]+(?:\s+[A-ZÁÉÍÓÚÑ][\wÁÉÍÓÚÑ]+){1,3})\b/iu);
    if (mPac && !f.paciente) f.paciente = this.titleCase(mPac[1]);

    // Edad
    const mEdad = t.match(/\b(\d{1,2})\s*(?:años?|a\.)\b/iu);
    if (mEdad && !f.edad) f.edad = Number(mEdad[1]);

    // Sexo
    const mSexo = t.match(/\b(sexo|género)\s*[:\-]?\s*(masculino|femenino|m|f)\b/iu)
                || t.match(/\b(varón|hombre)\b/iu) || t.match(/\b(mujer|femenina)\b/iu);
    if (mSexo && !f.sexo) {
      const v = (mSexo[2] || mSexo[0]).toLowerCase();
      f.sexo = /m|masculino|varón|hombre/.test(v) ? 'M' : 'F';
    }

    // Motivo de consulta
    const mMot = t.match(/\b(motivo (?:de )?consulta|consulta por|viene por|acude por)\s*[:\-]?\s*(.+?)(?=[.;]|$)/iu);
    if (mMot && !f.motivoConsulta) f.motivoConsulta = this.cut(mMot[2]);

    // Antecedentes
    const mAnt = t.match(/\b(antecedentes(?: personales| patológicos| quirúrgicos)?)\s*[:\-]?\s*(.+?)(?=[.;]|$)/iu);
    if (mAnt) f.antecedentes = this.preferLonger(f.antecedentes, this.cut(mAnt[2]));

    // Alergias
    const mAler = t.match(/\b(alergias?)\s*[:\-]?\s*(.+?)(?=[.;]|$)/iu)
                || t.match(/\b(alérgic[oa]\s+a\s+.+?)(?=[.;]|$)/iu);
    if (mAler) f.alergias = this.preferLonger(f.alergias, this.cut(mAler[2] || mAler[1]));

    // Medicación
    const mMed = t.match(/\b(medicación|tratamiento actual|fármacos?)\s*[:\-]?\s*(.+?)(?=[.;]|$)/iu);
    if (mMed) f.medicacion = this.preferLonger(f.medicacion, this.cut(mMed[2]));

    // Signos vitales (PA 120/80, FC 80, FR 18, T 36.5, SpO2 98)
    const sv: ClinicalForm['signosVitales'] = { ...(f.signosVitales || {}) };
    const mPA = t.match(/\b(?:PA|TA)\s*[:\-]?\s*(\d{2,3}\/\d{2,3})\b/iu);
    const mFC = t.match(/\b(?:FC|pulso)\s*[:\-]?\s*(\d{2,3})\b/iu);
    const mFR = t.match(/\b(?:FR|respiraciones?)\s*[:\-]?\s*(\d{1,2})\b/iu);
    const mT  = t.match(/\b(?:T|temp(?:eratura)?)\s*[:\-]?\s*(\d{2}(?:\.\d)?)\b/iu);
    const mSp = t.match(/\b(?:SpO2|Sat(?:uración)?)\s*[:\-]?\s*(\d{2,3})\s*%?\b/iu);
    if (mPA) sv.PA = mPA[1];
    if (mFC) sv.FC = Number(mFC[1]);
    if (mFR) sv.FR = Number(mFR[1]);
    if (mT)  sv.T  = Number(mT[1]);
    if (mSp) sv.SpO2 = Number(mSp[1]);
    if (Object.keys(sv).length) f.signosVitales = sv;

    // Examen físico (si alguien dicta así)
    const mEF = t.match(/\b(examen físico|EF)\s*[:\-]?\s*(.+?)(?=(?:impresión|diagnóstico|plan|$))/iu);
    if (mEF) f.examenFisico = this.preferLonger(f.examenFisico, this.cut(mEF[2]));

    // Impresión diagnóstica
    const mDx = t.match(/\b(impresión diagnóstica|diagnóstico(?: presuntivo| final)?)\s*[:\-]?\s*(.+?)(?=[.;]|$)/iu);
    if (mDx && !f.impresionDiagnostica) f.impresionDiagnostica = this.cut(mDx[2]);

    // Plan
    const mPlan = t.match(/\b(plan|indicación(?:es)?|tratamiento)\s*[:\-]?\s*(.+?)(?=[.;]|$)/iu);
    if (mPlan && !f.plan) f.plan = this.cut(mPlan[2]);

    return f;
  }

  private computeMissing(f: ClinicalForm): string[] {
    const miss = [];
    for (const k of this.required) {
      const v: any = (f as any)[k];
      if (v === undefined || v === null || v === '') miss.push(k);
    }
    return miss;
  }

  private titleCase(s: string) {
    return s.replace(/\w\S*/g, w => w[0].toUpperCase() + w.slice(1).toLowerCase());
  }
  private cut(s: string) { return (s || '').trim(); }
  private preferLonger(prev: string | undefined, next: string) {
    if (!prev) return next;
    return next.length > prev.length ? next : prev;
  }
}
