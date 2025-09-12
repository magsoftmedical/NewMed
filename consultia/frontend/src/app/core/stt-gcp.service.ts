import { Injectable } from '@angular/core';
import { Subject } from 'rxjs';
import { environment } from '../../environments/environment';

export interface GcpPartial { text: string; is_final: boolean; }

@Injectable({ providedIn: 'root' })
export class SttGcpService {
  private ws?: WebSocket;
  private openPromise?: Promise<void>;
  private resolveOpen?: () => void;

  public onResult$ = new Subject<GcpPartial>();
  public onError$ = new Subject<string>();

  start(): Promise<void> {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) return Promise.resolve();
    const url = `${environment.wsBase}/ws/transcribe`.replace(/^http/, 'ws');
    this.ws = new WebSocket(url);
    this.ws.binaryType = 'arraybuffer';

    this.openPromise = new Promise<void>((res) => this.resolveOpen = res);

    this.ws.onopen = () => this.resolveOpen?.();
    this.ws.onmessage = (ev) => {
      try {
        const msg = JSON.parse(ev.data);
        if (msg.text !== undefined) this.onResult$.next(msg);
      } catch (e) {
        // mensajes no JSON, ignorar
      }
    };
    this.ws.onerror = () => this.onError$.next('ws-error');
    this.ws.onclose = () => { this.ws = undefined; };

    return this.openPromise;
  }

  async sendPcmInt16(pcmBuffer: ArrayBuffer) {
    if (!this.ws) return;
    if (this.ws.readyState === WebSocket.CONNECTING) await this.openPromise;
    if (this.ws.readyState === WebSocket.OPEN) this.ws.send(pcmBuffer);
  }

  stop() {
    if (!this.ws) return;
    try { this.ws.send('__END__'); } catch {}
    try { this.ws.close(); } catch {}
    this.ws = undefined;
  }
}
