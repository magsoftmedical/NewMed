import { Injectable } from '@angular/core';
import { BehaviorSubject, Observable, Subject } from 'rxjs';

export type WsState = 'idle' | 'connecting' | 'open' | 'closed' | 'error';

type InboundMsg =
  | { type: 'partial'; text: string }
  | { type: 'final'; text: string }
  | { type: 'status'; status: WsState }
  | { partial?: string; final?: string; status?: WsState }
  | string;

@Injectable({ providedIn: 'root' })
export class SttStreamService {
  private ws?: WebSocket;

  private _status$  = new BehaviorSubject<WsState>('idle');
  private _partial$ = new Subject<string>();
  private _final$   = new Subject<string>();
  private _error$   = new Subject<unknown>();

  readonly onStatus$:  Observable<WsState> = this._status$.asObservable();
  readonly onPartial$: Observable<string>  = this._partial$.asObservable();
  readonly onFinal$:   Observable<string>  = this._final$.asObservable();
  readonly onError$:   Observable<unknown> = this._error$.asObservable();

  get state(): WsState { return this._status$.value; }

  async open(url: string): Promise<void> {
    if (this.ws && (this.ws.readyState === WebSocket.OPEN || this.ws.readyState === WebSocket.CONNECTING)) return;

    this._status$.next('connecting');
    this.ws = new WebSocket(url);
    this.ws.binaryType = 'arraybuffer';

    await new Promise<void>((resolve, reject) => {
      if (!this.ws) return reject(new Error('WS no inicializado'));

      this.ws.onopen = () => { this._status$.next('open'); resolve(); };
      this.ws.onerror = (ev) => { this._status$.next('error'); this._error$.next(ev); reject(new Error('WS error')); };
      this.ws.onclose = () => { this._status$.next('closed'); };
      this.ws.onmessage = async (ev: MessageEvent) => {
        try {
          if (typeof ev.data === 'string') return this.routeMessage(ev.data);
          if (ev.data instanceof Blob) return this.routeMessage(await ev.data.text());
        } catch (e) { this._error$.next(e); }
      };
    });
  }

  send(ab: ArrayBuffer): void {
    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) return;
    try { this.ws.send(ab); } catch (e) { this._error$.next(e); }
  }

  async close(): Promise<void> {
    if (!this.ws) return;
    await new Promise<void>((resolve) => {
      const ws = this.ws!;
      ws.onclose = () => { this._status$.next('closed'); resolve(); };
      try { ws.close(); } catch { resolve(); }
    });
    this.ws = undefined;
  }

  private routeMessage(raw: string) {
    let msg: InboundMsg = raw;
    try { msg = JSON.parse(raw); } catch { this._final$.next(raw); return; }

    if (typeof msg === 'string') { this._final$.next(msg); return; }
    if ('type' in msg && msg.type === 'partial') { this._partial$.next(msg.text ?? ''); return; }
    if ('type' in msg && msg.type === 'final')   { this._final$.next(msg.text ?? '');   return; }
    if ('type' in msg && msg.type === 'status')  { this._status$.next(msg.status ?? 'open'); return; }

    if ('partial' in msg && msg.partial != null) this._partial$.next(msg.partial ?? '');
    if ('final'   in msg && msg.final   != null) this._final$.next(msg.final ?? '');
    if ('status'  in msg && msg.status  != null) this._status$.next(msg.status ?? 'open');
  }
}
