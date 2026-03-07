/**
 * Modelos TypeScript para integración con Medberos AI
 */

export interface DiagnosisPrediction {
  Name?: string;
  Description?: string;
  CieCode?: string;
  ICD10Code?: string;
  Type?: string;
  Confidence?: number;
  Score?: number;
}

export interface ExamPrediction {
  Name?: string;
  Description?: string;
  Confidence?: number;
  Score?: number;
}

export interface TreatmentPrediction {
  Name?: string;
  MedicineName?: string;
  Dosage?: string;
  Dose?: string;
  Indication?: string;
  Code?: string;
  GTIN?: string;
  Confidence?: number;
  Score?: number;
}

export interface MedberosResponse {
  success: boolean;
  diagnosticos?: Array<{
    nombre: string;
    cie10: string;
    tipo: string;
    confianza?: number;
  }>;
  examenes?: string[];
  tratamientos?: Array<{
    medicamento: string;
    dosisIndicacion: string;
    gtin?: string;
    confianza?: number;
  }>;
  error?: string;
  raw?: any;
}

export interface AIPredictionsMessage {
  diagnoses?: {
    predictions: DiagnosisPrediction[];
  };
  exams?: {
    predictions: ExamPrediction[];
  };
  treatments?: {
    predictions: TreatmentPrediction[];
  };
  diagnosticos_consultia?: Array<{
    nombre: string;
    cie10: string;
    tipo: string;
    confianza?: number;
  }>;
}
