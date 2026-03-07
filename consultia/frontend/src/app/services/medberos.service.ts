import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable, of } from 'rxjs';
import { catchError, tap } from 'rxjs/operators';
import { MedberosResponse } from '../models/medberos.models';

@Injectable({
  providedIn: 'root'
})
export class MedberosService {
  private baseUrl = '/api'; // Usar proxy configurado

  constructor(private http: HttpClient) {}

  /**
   * Prueba la conexión con Medberos AI
   */
  testConnection(): Observable<any> {
    return this.http.get(`${this.baseUrl}/medberos/test`).pipe(
      tap(() => console.log('[MEDBEROS] Connection test successful')),
      catchError(error => {
        console.error('[MEDBEROS] Connection test failed:', error);
        return of({ ok: false, error: error.message });
      })
    );
  }

  /**
   * Predice diagnósticos usando Medberos AI
   */
  predictDiagnoses(form: any, doctorComments: string = ''): Observable<MedberosResponse> {
    const payload = {
      form,
      doctorComments
    };

    console.log('[MEDBEROS] Calling predictDiagnoses...', payload);

    return this.http.post<MedberosResponse>(
      `${this.baseUrl}/medberos/predict-diagnoses`,
      payload
    ).pipe(
      tap(response => console.log('[MEDBEROS] Diagnoses received:', response)),
      catchError(error => {
        console.error('[MEDBEROS] predictDiagnoses error:', error);
        return of({
          success: false,
          error: error.message || 'Error al predecir diagnósticos'
        });
      })
    );
  }

  /**
   * Predice exámenes médicos usando Medberos AI
   */
  predictExams(form: any, doctorComments: string = ''): Observable<MedberosResponse> {
    const payload = {
      form,
      doctorComments
    };

    console.log('[MEDBEROS] Calling predictExams...', payload);

    return this.http.post<MedberosResponse>(
      `${this.baseUrl}/medberos/predict-exams`,
      payload
    ).pipe(
      tap(response => console.log('[MEDBEROS] Exams received:', response)),
      catchError(error => {
        console.error('[MEDBEROS] predictExams error:', error);
        return of({
          success: false,
          error: error.message || 'Error al predecir exámenes'
        });
      })
    );
  }

  /**
   * Predice tratamientos usando Medberos AI
   */
  predictTreatments(form: any, doctorComments: string = ''): Observable<MedberosResponse> {
    const payload = {
      form,
      doctorComments
    };

    console.log('[MEDBEROS] Calling predictTreatments...', payload);

    return this.http.post<MedberosResponse>(
      `${this.baseUrl}/medberos/predict-treatments`,
      payload
    ).pipe(
      tap(response => console.log('[MEDBEROS] Treatments received:', response)),
      catchError(error => {
        console.error('[MEDBEROS] predictTreatments error:', error);
        return of({
          success: false,
          error: error.message || 'Error al predecir tratamientos'
        });
      })
    );
  }

  /**
   * Llama al endpoint unificado que devuelve todas las predicciones en una sola llamada
   * Por ahora solo diagnósticos funcionan, exámenes y tratamientos vienen vacíos
   */
  predictAll(form: any, doctorComments: string = ''): Observable<any> {
    const payload = {
      form,
      doctorComments
    };

    console.log('[MEDBEROS] Calling predictAll (unified endpoint)...', payload);

    return this.http.post<any>(
      `${this.baseUrl}/medberos/predict-all`,
      payload
    ).pipe(
      tap(response => console.log('[MEDBEROS] All predictions received:', response)),
      catchError(error => {
        console.error('[MEDBEROS] predictAll error:', error);
        return of({
          success: false,
          diagnosticos: [],
          examenes: [],
          tratamientos: [],
          error: error.message || 'Error al obtener predicciones'
        });
      })
    );
  }
}
