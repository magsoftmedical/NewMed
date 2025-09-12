import { Injectable } from '@angular/core';
import { SttGcpService } from './stt-gcp.service';

@Injectable({ providedIn: 'root' })
export class RecorderGcpService {
  private ctx?: AudioContext;
  private source?: MediaStreamAudioSourceNode;
  private worklet?: AudioWorkletNode;
  private running = false;

  constructor(private stt: SttGcpService) {}

  async start() {
    if (this.running) return;
    await this.stt.start();

    this.ctx = new AudioContext({ sampleRate: 48000 });
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });

    // Cargar el módulo del worklet (ruta pública)
    await this.ctx.audioWorklet.addModule('/assets/worklets/recorder-processor.js');

    this.source = this.ctx.createMediaStreamSource(stream);
    this.worklet = new AudioWorkletNode(this.ctx, 'recorder-processor');

    // Recibir buffers PCM16 16k desde el worklet y mandarlos por WS
    this.worklet.port.onmessage = (ev) => {
      const ab: ArrayBuffer = ev.data;
      this.stt.sendPcmInt16(ab);
    };

    // No reproducir (evita eco). Conecta a un Gain con 0 de ganancia si quieres.
    this.source.connect(this.worklet);
    this.running = true;
  }

  async stop() {
    this.running = false;
    try { this.source?.disconnect(); } catch {}
    try { this.worklet?.disconnect(); } catch {}
    try { await this.ctx?.close(); } catch {}
    this.stt.stop();
  }
}
