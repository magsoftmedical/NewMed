import { Injectable, Inject, PLATFORM_ID } from '@angular/core';
import { isPlatformBrowser } from '@angular/common';
import { HttpClient } from '@angular/common/http';
import { BehaviorSubject, Subject } from 'rxjs';

export interface WhisperResult {
  text: string;
  is_final: true;
}

@Injectable({ providedIn: 'root' })
export class WhisperRecorderService {
  readonly recording$ = new BehaviorSubject<boolean>(false);
  readonly transcribing$ = new BehaviorSubject<boolean>(false);
  readonly result$ = new Subject<WhisperResult>();
  readonly error$ = new Subject<string>();
  readonly level$ = new BehaviorSubject<number>(0);

  private mediaRecorder?: MediaRecorder;
  private chunks: Blob[] = [];
  private mediaStream?: MediaStream;

  // VAD
  private audioCtx?: AudioContext;
  private analyser?: AnalyserNode;
  private rafId?: number;
  private peakLevel = 0; // track max audio level during recording

  // Known Whisper hallucinations on silent audio
  private static readonly HALLUCINATIONS = [
    'subtítulos realizados por la comunidad de amara.org',
    'gracias por ver el vídeo',
    'thanks for watching',
    'subtítulos por la comunidad de amara.org',
    'suscríbete al canal',
    'música',
    'aplausos',
  ];

  private isBrowser: boolean;

  constructor(
    private http: HttpClient,
    @Inject(PLATFORM_ID) platformId: Object,
  ) {
    this.isBrowser = isPlatformBrowser(platformId);
  }

  async start(): Promise<void> {
    if (!this.isBrowser) return;

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      this.mediaStream = stream;

      this.chunks = [];
      this.peakLevel = 0;
      this.mediaRecorder = new MediaRecorder(stream, { mimeType: this.pickMimeType() });

      this.mediaRecorder.ondataavailable = (e) => {
        if (e.data.size > 0) this.chunks.push(e.data);
      };

      this.mediaRecorder.onerror = () => {
        this.error$.next('Error en la grabación de audio');
        this.cleanup();
      };

      this.mediaRecorder.start(250); // collect chunks every 250ms
      this.recording$.next(true);

      this.startVAD(stream);
    } catch (err: any) {
      this.error$.next(`No se pudo acceder al micrófono: ${err.message || err}`);
    }
  }

  stopAndTranscribe(): void {
    if (!this.mediaRecorder || this.mediaRecorder.state === 'inactive') return;

    this.mediaRecorder.onstop = () => {
      this.recording$.next(false);
      this.stopVAD();

      const blob = new Blob(this.chunks, { type: this.mediaRecorder!.mimeType || 'audio/webm' });
      this.chunks = [];

      if (blob.size === 0 || this.peakLevel < 0.02) {
        this.error$.next(blob.size === 0 ? 'La grabación está vacía' : 'No se detectó voz en la grabación');
        this.releaseStream();
        return;
      }

      this.transcribing$.next(true);

      const ext = this.mimeToExt(this.mediaRecorder!.mimeType);
      const formData = new FormData();
      formData.append('file', blob, `audio.${ext}`);

      this.http.post<{ text?: string; error?: string }>('/api/transcribe', formData).subscribe({
        next: (res) => {
          this.transcribing$.next(false);
          if (res.text && !this.isHallucination(res.text)) {
            this.result$.next({ text: res.text, is_final: true });
          } else if (res.text) {
            // Whisper hallucinated on near-silent audio — discard silently
            console.warn('[Whisper] Hallucination filtered:', res.text);
          } else {
            this.error$.next(res.error || 'Respuesta vacía del servidor');
          }
          this.releaseStream();
        },
        error: (err) => {
          this.transcribing$.next(false);
          this.error$.next(`Error al transcribir: ${err.message || err.statusText || 'Error de red'}`);
          this.releaseStream();
        },
      });
    };

    this.mediaRecorder.stop();
  }

  cancel(): void {
    if (this.mediaRecorder && this.mediaRecorder.state !== 'inactive') {
      this.mediaRecorder.onstop = null;
      this.mediaRecorder.stop();
    }
    this.chunks = [];
    this.recording$.next(false);
    this.transcribing$.next(false);
    this.stopVAD();
    this.releaseStream();
  }

  // --- VAD (reuses pattern from WebSpeechService) ---
  private startVAD(stream: MediaStream): void {
    const ACtor: any = (window as any).AudioContext || (window as any).webkitAudioContext;
    if (!ACtor) return;

    const ctx = new ACtor() as AudioContext;
    this.audioCtx = ctx;

    const src = ctx.createMediaStreamSource(stream);
    const analyser = ctx.createAnalyser();
    analyser.fftSize = 1024;
    src.connect(analyser);
    this.analyser = analyser;

    const buf = new Float32Array(analyser.fftSize);

    const tick = () => {
      analyser.getFloatTimeDomainData(buf);
      let sum = 0;
      for (let i = 0; i < buf.length; i++) sum += buf[i] * buf[i];
      const rms = Math.sqrt(sum / buf.length);
      const level = Math.min(rms * 3.0, 1.0);
      if (level > this.peakLevel) this.peakLevel = level;
      this.level$.next(level);
      this.rafId = requestAnimationFrame(tick);
    };

    this.rafId = requestAnimationFrame(tick);
  }

  private stopVAD(): void {
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

    this.level$.next(0);
  }

  private releaseStream(): void {
    if (this.mediaStream) {
      this.mediaStream.getTracks().forEach(t => t.stop());
    }
    this.mediaStream = undefined;
  }

  private cleanup(): void {
    this.recording$.next(false);
    this.transcribing$.next(false);
    this.stopVAD();
    this.releaseStream();
    this.chunks = [];
  }

  private pickMimeType(): string {
    const preferred = ['audio/webm;codecs=opus', 'audio/webm', 'audio/ogg;codecs=opus', 'audio/mp4'];
    for (const mt of preferred) {
      if (MediaRecorder.isTypeSupported(mt)) return mt;
    }
    return '';
  }

  private mimeToExt(mime: string): string {
    if (mime.includes('webm')) return 'webm';
    if (mime.includes('ogg')) return 'ogg';
    if (mime.includes('mp4')) return 'mp4';
    return 'webm';
  }

  private isHallucination(text: string): boolean {
    const lower = text.toLowerCase().replace(/[¡!¿?.,:;]/g, '').trim();
    return WhisperRecorderService.HALLUCINATIONS.some(h => lower.includes(h));
  }
}
