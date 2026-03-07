import { Component, Input, Output, EventEmitter } from '@angular/core';
import { CommonModule } from '@angular/common';
import { AIPredictionsMessage } from '../../models/medberos.models';

interface PredictionItem {
  nombre: string;
  codigo?: string;
  tipo?: string;
  confianza?: number;
  detalle?: string;
}

@Component({
  selector: 'nm-ai-predictions',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './ai-predictions.component.html',
  styleUrl: './ai-predictions.component.scss'
})
export class AiPredictionsComponent {
  @Input() predictions: AIPredictionsMessage | null = null;
  @Output() acceptDiagnosis = new EventEmitter<any>();
  @Output() acceptExam = new EventEmitter<string>();
  @Output() acceptTreatment = new EventEmitter<any>();

  // Estado
  activeTab: 'diagnoses' | 'exams' | 'treatments' = 'diagnoses';
  loading = false;

  get hasPredictions(): boolean {
    return !!(this.predictions?.diagnoses?.predictions?.length ||
              this.predictions?.exams?.predictions?.length ||
              this.predictions?.treatments?.predictions?.length);
  }

  get diagnosticos(): PredictionItem[] {
    if (!this.predictions?.diagnoses?.predictions) return [];

    return this.predictions.diagnoses.predictions.map(pred => ({
      nombre: pred.Name || pred.Description || 'Sin nombre',
      codigo: pred.CieCode || pred.ICD10Code || '',
      tipo: pred.Type || 'Presuntivo',
      confianza: pred.Confidence || pred.Score || 0
    }));
  }

  get examenes(): PredictionItem[] {
    if (!this.predictions?.exams?.predictions) return [];

    return this.predictions.exams.predictions.map(pred => ({
      nombre: pred.Name || pred.Description || 'Sin nombre',
      confianza: pred.Confidence || pred.Score || 0
    }));
  }

  get tratamientos(): PredictionItem[] {
    if (!this.predictions?.treatments?.predictions) return [];

    return this.predictions.treatments.predictions.map(pred => ({
      nombre: pred.Name || pred.MedicineName || 'Sin nombre',
      detalle: pred.Dosage || pred.Dose || pred.Indication || '',
      codigo: pred.Code || pred.GTIN || '',
      confianza: pred.Confidence || pred.Score || 0
    }));
  }

  setActiveTab(tab: 'diagnoses' | 'exams' | 'treatments'): void {
    this.activeTab = tab;
  }

  onAcceptDiagnosis(item: PredictionItem): void {
    console.log('[AI-PREDICTIONS] Accepting diagnosis:', item);
    this.acceptDiagnosis.emit({
      nombre: item.nombre,
      cie10: item.codigo,
      tipo: item.tipo || 'Presuntivo'
    });
  }

  onAcceptExam(item: PredictionItem): void {
    console.log('[AI-PREDICTIONS] Accepting exam:', item);
    this.acceptExam.emit(item.nombre);
  }

  onAcceptTreatment(item: PredictionItem): void {
    console.log('[AI-PREDICTIONS] Accepting treatment:', item);
    this.acceptTreatment.emit({
      medicamento: item.nombre,
      dosisIndicacion: item.detalle
    });
  }

  getConfidenceClass(confidence: number = 0): string {
    if (confidence >= 0.8) return 'high';
    if (confidence >= 0.5) return 'medium';
    return 'low';
  }

  getConfidenceColor(confidence: number = 0): string {
    if (confidence >= 0.8) return '#22c55e'; // Verde
    if (confidence >= 0.5) return '#eab308'; // Amarillo
    return '#94a3b8'; // Gris
  }
}
