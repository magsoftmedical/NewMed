import { Injectable } from '@angular/core';
import { Subject } from 'rxjs';
import { environment } from '../../environments/environment';

export interface PartialResult { text: string; is_final: boolean; }

@Injectable({ providedIn: 'root' })
export class SttService {
  private ws?: WebSocket;
  private openPromise?: Promise<void>;
  private openResolve?: () => void;
  public onResult$ = new Subject<PartialResult>();

  start() {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) return Promise.resolve();
    const url = `${environment.wsBase}/ws/transcribe`.replace(/^http/,'ws');
    this.ws = new WebSocket(url);
    this.ws.binaryType = 'arraybuffer';

    this.openPromise = new Promise<void>((resolve) => (this.openResolve = resolve));

    this.ws.onopen = () => {
      this.openResolve?.();
    };

    this.ws.onmessage = (ev) => {
      try {
        const msg = JSON.parse(ev.data);
        if (msg.text !== undefined) this.onResult$.next(msg);
      } catch {}
    };

    this.ws.onclose = () => {
      this.ws = undefined;
    };

    this.ws.onerror = () => {
      // deja que onclose limpie; el componente verá que no hay OPEN
    };

    return this.openPromise;
  }

  async sendPcmInt16(pcm: Int16Array) {
    // espera a que esté OPEN
    if (!this.ws || this.ws.readyState === WebSocket.CLOSED) return;
    if (this.ws.readyState === WebSocket.CONNECTING) {
      await this.openPromise; // espera handshake
    }
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(pcm.buffer);
    }
  }

  stop() {
    if (this.ws && this.ws.readyState <= WebSocket.CLOSING) {
      try { this.ws.send('__END__'); } catch {}
      try { this.ws.close(); } catch {}
    }
    this.ws = undefined;
    this.openPromise = undefined;
    this.openResolve = undefined;
  }
}
