import { Injectable, Inject, PLATFORM_ID } from '@angular/core';
import { isPlatformBrowser } from '@angular/common';
import { BehaviorSubject, Subject, Subscription } from 'rxjs';
import { throttleTime } from 'rxjs/operators';

export interface WSPartial {
  text: string;
  is_final: boolean;
}

// Constructor tipado para evitar errores TS
type RecognitionConstructor = new () => SpeechRecognition;

@Injectable({ providedIn: 'root' })
export class WebSpeechService {
  // Streams públicosD
  readonly result$    = new Subject<WSPartial>();
  readonly listening$ = new BehaviorSubject<boolean>(false);
  readonly error$     = new Subject<string>();
  readonly level$     = new BehaviorSubject<number>(0); // 0..1

  // Estado interno
  private recognition?: SpeechRecognition;
  private partialRelay$ = new Subject<string>();
  private partialSub?: Subscription;

  private _manualStop = false;
  private _autoRestart = true;
  private _retryCount = 0;

  // Audio/VAD
  private audioCtx?: AudioContext;
  private mediaStream?: MediaStream;
  private analyser?: AnalyserNode;
  private rafId?: number;

  constructor(@Inject(PLATFORM_ID) private platformId: Object) {
    // Throttle de parciales para suavizar la UI
    this.partialSub = this.partialRelay$
      .pipe(throttleTime(80, undefined, { leading: true, trailing: true }))
      .subscribe(txt => this.result$.next({ text: txt, is_final: false }));
  }

  get supported(): boolean {
    if (!isPlatformBrowser(this.platformId)) return false;
    const w = window as any;
    return !!(w.SpeechRecognition || w.webkitSpeechRecognition);
  }

  start(lang = 'es-PE', continuous = true, interim = true, autoRestart = true) {
    if (!this.supported) {
      this.error$.next('Web Speech API no soportada en este entorno/navegador.');
      return;
    }
    this._manualStop = false;
    this._autoRestart = autoRestart;

    // Crear instancia una vez
    if (!this.recognition) {
      const w = window as any;
      const Ctor = (w.SpeechRecognition || w.webkitSpeechRecognition) as RecognitionConstructor;
      this.recognition = new Ctor();

      this.recognition.onstart = () => {
        this.listening$.next(true);
        this._retryCount = 0; // reset backoff
      };

      this.recognition.onerror = (ev: any) => {
        const err = ev?.error || 'unknown';
        this.error$.next(`Speech error: ${err}`);
      };

      this.recognition.onend = () => {
        this.listening$.next(false);
        // Auto‑restart si no fue un stop manual
        if (!this._manualStop && this._autoRestart) {
          const delay = Math.min(200 * Math.pow(2, this._retryCount++), 3000);
          setTimeout(() => {
            try {
              this.recognition?.start();
            } catch {
              // si dispara InvalidStateError, reintenta un poco después
              setTimeout(() => { try { this.recognition?.start(); } catch {} }, 500);
            }
          }, delay);
        }
      };

      this.recognition.onresult = (ev: SpeechRecognitionEvent) => {
        for (let i = ev.resultIndex; i < ev.results.length; i++) {
          const res = ev.results[i];
          const txt = res[0].transcript;
          if (res.isFinal) {
            this.result$.next({ text: txt, is_final: true });
          } else {
            this.partialRelay$.next(txt);
          }
        }
      };
    }

    // Config por inicio
    this.recognition.lang = lang;
    this.recognition.continuous = continuous;
    (this.recognition as any).interimResults = interim;

    // Iniciar reconocimiento
    try { this.recognition.start(); } catch {}

    // Iniciar VAD simple
    this.startVAD().catch(err => this.error$.next(`VAD error: ${String(err)}`));
  }

  stop() {
    this._manualStop = true;
    this._autoRestart = false;
    try { this.recognition?.stop(); } catch {}
    this.stopVAD();
  }

  // --------- VAD: nivel de voz 0..1 usando RMS ----------
  private async startVAD() {
  if (!isPlatformBrowser(this.platformId)) return;
  // si ya está activo, no re-abrir
  if (this.audioCtx && this.mediaStream && this.analyser) return;

  if (!navigator.mediaDevices?.getUserMedia) return;
  const ms = await navigator.mediaDevices.getUserMedia({ audio: true });
  this.mediaStream = ms;

  const ACtor: any = (window as any).AudioContext || (window as any).webkitAudioContext;
  const ctx = new ACtor() as AudioContext;     // <- local no-opcional
  this.audioCtx = ctx;

  const src = ctx.createMediaStreamSource(ms);
  const analyser = ctx.createAnalyser();       // <- local no-opcional
  analyser.fftSize = 1024;
  src.connect(analyser);
  this.analyser = analyser;

  const buf = new Float32Array(analyser.fftSize);

  const tick = () => {
    // usa la referencia local 'analyser' ya definida:
    analyser.getFloatTimeDomainData(buf);
    let sum = 0;
    for (let i = 0; i < buf.length; i++) sum += buf[i] * buf[i];
    const rms = Math.sqrt(sum / buf.length);       // ~0..0.5
    const level = Math.min(rms * 3.0, 1.0);        // 0..1
    this.level$.next(level);
    this.rafId = requestAnimationFrame(tick);
  };

  this.rafId = requestAnimationFrame(tick);
}

  private stopVAD() {
    if (this.rafId) cancelAnimationFrame(this.rafId);
    this.rafId = undefined;

    if (this.analyser) {
      try { this.analyser.disconnect(); } catch {}
    }
    this.analyser = undefined;

    if (this.audioCtx) {
      try { this.audioCtx.close(); } catch {}
    }
    this.audioCtx = undefined;

    if (this.mediaStream) {
      this.mediaStream.getTracks().forEach(t => t.stop());
    }
    this.mediaStream = undefined;

    this.level$.next(0);
  }
}
