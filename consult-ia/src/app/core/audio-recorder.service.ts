// src/app/core/audio-recorder.service.ts
import { Injectable } from '@angular/core';
import { SttService } from './stt-service';

@Injectable({ providedIn: 'root' })
export class AudioRecorderService {
  private ctx?: AudioContext;
  private source?: MediaStreamAudioSourceNode;
  private processor?: ScriptProcessorNode;
  private sending = false;

  // buffers para juntar ~200 ms antes de enviar
  private acc: Float32Array[] = [];
  private accLen = 0;
  private readonly CHUNK_MS = 200; // ~0.2 s
  private inputRate = 48000;
  private targetRate = 16000;

  constructor(private stt: SttService) {}

  async start() {
    this.ctx = new AudioContext({ sampleRate: this.inputRate });
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    this.source = this.ctx.createMediaStreamSource(stream);
    this.processor = this.ctx.createScriptProcessor(4096, 1, 1);

    this.processor.onaudioprocess = (e) => {
      if (!this.sending) return;
      const f32 = e.inputBuffer.getChannelData(0);
      this.acc.push(new Float32Array(f32));
      this.accLen += f32.length;

      // Enviar cada ~200 ms (inputRate = 48000 -> 9600 samples)
      const samplesPerChunk = Math.round(this.inputRate * this.CHUNK_MS / 1000);
      if (this.accLen >= samplesPerChunk) {
        const merged = this.merge(this.acc, this.accLen);
        this.acc = []; this.accLen = 0;
        const down = this.downsample(merged, this.inputRate, this.targetRate);
        const pcm16 = this.floatTo16LE(down);
        this.stt.sendPcmInt16(pcm16);
      }
    };

    this.source.connect(this.processor);
    this.processor.connect(this.ctx.destination); // o ctx.createGain() si no quieres oírte

    await this.stt.start();  // <--- MUY IMPORTANTE: espera onopen antes de capturar/enviar
    this.sending = true;
  }

  stop() {
    this.sending = false;
    this.stt.stop();
    try { this.processor?.disconnect(); this.source?.disconnect(); } catch {}
    this.ctx?.close();
  }

  private merge(chunks: Float32Array[], totalLen: number): Float32Array {
    const out = new Float32Array(totalLen);
    let off = 0;
    for (const c of chunks) { out.set(c, off); off += c.length; }
    return out;
  }

  private downsample(input: Float32Array, inRate: number, outRate: number): Float32Array {
    if (outRate === inRate) return input;
    const ratio = inRate / outRate; // 48000/16000 = 3
    const newLen = Math.floor(input.length / ratio);
    const out = new Float32Array(newLen);
    let pos = 0;
    for (let i = 0; i < newLen; i++) {
      const start = Math.floor(i * ratio);
      const end = Math.floor((i + 1) * ratio);
      let sum = 0, cnt = 0;
      for (let j = start; j < end && j < input.length; j++) { sum += input[j]; cnt++; }
      out[i] = cnt ? (sum / cnt) : input[start];
      pos += ratio;
    }
    return out;
  }

  private floatTo16LE(f32: Float32Array): Int16Array {
    const out = new Int16Array(f32.length);
    for (let i = 0; i < f32.length; i++) {
      let s = Math.max(-1, Math.min(1, f32[i]));
      out[i] = s < 0 ? s * 0x8000 : s * 0x7FFF;
    }
    return out;
  }
}
