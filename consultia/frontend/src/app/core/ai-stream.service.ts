import { Injectable, Inject, PLATFORM_ID } from '@angular/core';
import { isPlatformBrowser } from '@angular/common';
import { BehaviorSubject } from 'rxjs';

/** Alineado con el schema de Historia Clínica del backend */
export interface HistoriaClinica {
  afiliacion?: {
    nombreCompleto?: string;
    edad?: { anios: number; meses?: number };
    sexo?: 'Masculino'|'Femenino'|'M'|'F'|string;
    dni?: string;
    grupoSangre?: string;
    fechaHora?: string;
    seguro?: string;
    tipoConsulta?: string;
    numeroSeguro?: string;
    motivoConsulta?: string;
  };
  anamnesis?: {
    tiempoEnfermedad?: string;
    sintomasPrincipales?: string[];
    relato?: string;
    funcionesBiologicas?: {
      apetito?: string; sed?: string; orina?: string; deposiciones?: string; sueno?: string;
    };
    antecedentes?: { personales?: string[]; padre?: string[]; madre?: string[] };
    alergias?: string[];
    medicamentos?: string[];
  };
  examenClinico?: {
    signosVitales?: { PA?: string; FC?: number; FR?: number; peso?: number; talla?: number; SpO2?: number; temperatura?: number; IMC?: number; glasgow?: number; };
    estadoGeneral?: string;
    descripcionGeneral?: string;
    sistemas?: {
      piel?: string; tcs?: string; cabeza?: string; cuello?: string; torax?: string; pulmones?: string;
      corazon?: string; mamasAxilas?: string; abdomen?: string; genitoUrinario?: string; rectalPerianal?: string;
      extremidades?: string; vascularPeriferico?: string; neurologico?: string;
    };
  };
  diagnosticos?: { nombre:string; tipo?:'presuntivo'|'definitivo'|string; cie10?:string }[];
  tratamientos?: { medicamento:string; dosisIndicacion?:string; gtin?:string }[];
  firma?: { medico?:string; colegiatura?:string; fecha?:string };
}

/** Estados de conexión para la UI */
export type AiWsStatus = 'idle' | 'connecting' | 'open' | 'closing' | 'closed' | 'error' | 'reconnecting';
export type FormDelta = { path: string; value: any; reason?: string; evidence?: string };
export type InsightMsg = { label: string; text: string };



@Injectable({ providedIn: 'root' })
export class AiStreamService {
  private ws?: WebSocket;
  private isBrowser: boolean;

  // URL del WS: usa primero variable global (p. ej. inyectada vía environment), sino fallback
  private WS_URL: string =
    (globalThis as any).__AI_WS_URL__ ||
    (typeof import.meta !== 'undefined' && (import.meta as any).env?.NG_APP_WS_URL) ||
    'ws://localhost:8001/ws';

  // Observables públicos
  readonly aiText$ = new BehaviorSubject<string>('');
  readonly form$ = new BehaviorSubject<HistoriaClinica|null>(null);
  readonly missing$ = new BehaviorSubject<string[]>([]);
  readonly suggestions$ = new BehaviorSubject<string[]>([]);
  readonly status$ = new BehaviorSubject<AiWsStatus>('idle');
  readonly deltas$    = new BehaviorSubject<FormDelta[]>([]);
  readonly insights$  = new BehaviorSubject<InsightMsg | null>(null);
  // Reconexión
  private reconnectAttempts = 0;
  private maxBackoffMs = 5000;
  private sessionId = '';

  constructor(@Inject(PLATFORM_ID) platformId: Object) {
    this.isBrowser = isPlatformBrowser(platformId);
  }

  /** Abre la conexión WebSocket (solo en navegador) */
  connect(sessionId: string, wsUrl?: string) {
    if (!this.isBrowser) return;
    if (this.ws && (this.ws.readyState === WebSocket.OPEN || this.ws.readyState === WebSocket.CONNECTING)) {
      // Ya hay una conexión activa/conectando
      return;
    }

    this.sessionId = sessionId;
    const url = (wsUrl || this.WS_URL) + `?session=${encodeURIComponent(sessionId)}`;

    try {
      this.status$.next(this.reconnectAttempts > 0 ? 'reconnecting' : 'connecting');
      this.ws = new WebSocket(url);

            // 👇 añade estos logs y helpers
      (this as any)._dbg = { ws: this.ws, sendFinal: (t: string)=> this.sendFinal(t), sendPartial: (t:string)=> this.sendPartial(t) };
      (window as any).__ai = (this as any)._dbg;
      this.ws.onopen = () => {
        this.status$.next('open');
        this.reconnectAttempts = 0;
        console.log('[AI WS] conectado');
      };

      this.ws.onclose = (ev) => {
        console.log('[AI WS] cerrado', ev.code, ev.reason);
        this.status$.next(ev.wasClean ? 'closed' : 'error');
        this.scheduleReconnect(); // intenta reconectar
      };

      this.ws.onerror = (err) => {
        console.error('[AI WS] error', err);
        this.status$.next('error');
      };

      this.ws.onmessage = (ev) => {
        try {
          const msg = JSON.parse(ev.data);
          console.log('[AI WS <<]', ev.data);   // 👈 log de todo lo recibido
 
          if (msg.type === 'form_delta') {
            this.deltas$.next(msg.changes ?? []);
          } else if (msg.type === 'insight') {
            this.insights$.next({ label: msg.label, text: msg.text });
          }
          switch (msg.type) {
            case 'assistant_reset':
              this.aiText$.next('');
              break;
            case 'assistant_token':
              this.aiText$.next(this.aiText$.value + (msg.delta || ''));
              break;
            case 'form_update':
              this.form$.next(msg.form || null);
              this.missing$.next(msg.missing || []);
              this.suggestions$.next(msg.suggestions || []);
              break;
            case 'error':
              console.error('[AI WS error]', msg.message);
              this.status$.next('error');
              break;
            default:
              // Ignorar mensajes no reconocidos para forward‑compat
              break;
          }
        } catch (e) {
          console.error('[AI WS] parse error', e);
        }
      };
    } catch (e) {
      console.error('[AI WS] connect exception', e);
      this.status$.next('error');
      this.scheduleReconnect();
    }
  }

  /** Envía texto parcial (si la conexión está abierta) */
  sendPartial(text: string) {
    if (!this.canSend()) return;
    this.ws!.send(JSON.stringify({ type: 'partial', text }));
  }

  /** Envía texto final (si la conexión está abierta) */
  sendFinal(text: string) {
    if (!this.canSend()) return;
    this.ws!.send(JSON.stringify({ type: 'final', text }));
  }

  /** Cierra manualmente la conexión */
  close() {
    if (!this.ws) return;
    this.status$.next('closing');
    try { this.ws.close(); } catch {}
    this.ws = undefined;
  }

  // ----------------- Privados -----------------

  private canSend(): boolean {
    return !!(this.ws && this.ws.readyState === WebSocket.OPEN);
  }

  /** Programa reconexión con backoff exponencial (cap a 5s) */
  private scheduleReconnect() {
    if (!this.isBrowser) return;

    // Si el usuario cerró manualmente (no hay ws), no reconectar
    if (!this.ws) return;

    const backoff = Math.min(200 * Math.pow(2, this.reconnectAttempts++), this.maxBackoffMs);
    this.status$.next('reconnecting');
    console.log(`[AI WS] reconectando en ${backoff}ms (intento ${this.reconnectAttempts})`);
    setTimeout(() => {
      // Evita reconectar si ya se reabrió o se cerró manualmente
      if (this.ws && this.ws.readyState !== WebSocket.OPEN && this.ws.readyState !== WebSocket.CONNECTING) {
        this.connect(this.sessionId);
      }
    }, backoff);
  }
}

