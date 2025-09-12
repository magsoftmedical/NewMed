// src/assets/js/pcm-processor.js
class PcmProcessor extends AudioWorkletProcessor {
  constructor(options) {
    super();
    const opts = (options && options.processorOptions) || {};
    this.targetRate = opts.targetSampleRate || 16000;
    this.inRate = sampleRate; // del AudioContext
    this.frameSamples = Math.floor(this.targetRate * 0.02); // 20 ms
    this._buf = new Float32Array(0);

    // Señal de vida
    this.port.postMessage({ __boot: true, inRate: this.inRate, targetRate: this.targetRate });
  }

  _downsample(f32) {
    const ratio = this.inRate / this.targetRate;
    const outLen = Math.floor(f32.length / ratio);
    const out = new Float32Array(outLen);
    let j = 0;
    for (let i = 0; i < outLen; i++) {
      out[i] = f32[Math.floor(j)];
      j += ratio;
    }
    return out;
  }

  _toPCM16(f32) {
    const buf = new ArrayBuffer(f32.length * 2);
    const view = new DataView(buf);
    for (let i = 0; i < f32.length; i++) {
      let s = Math.max(-1, Math.min(1, f32[i]));
      view.setInt16(i * 2, s < 0 ? s * 0x8000 : s * 0x7FFF, true);
    }
    return buf;
  }

  process(inputs) {
    const input = inputs[0];
    if (!input || input.length === 0) return true;

    // mono: canal 0
    const ch0 = input[0] || new Float32Array(0);

    // concatenar a buffer y downsamplear
    const concat = new Float32Array(this._buf.length + ch0.length);
    concat.set(this._buf, 0);
    concat.set(ch0, this._buf.length);
    const ds = this._downsample(concat);

    // emitir frames de 20 ms
    let off = 0;
    while (off + this.frameSamples <= ds.length) {
      const slice = ds.subarray(off, off + this.frameSamples);
      off += this.frameSamples;
      const buf = this._toPCM16(slice);
      this.port.postMessage(buf, [buf]);
    }
    this._buf = ds.subarray(off);

    return true;
  }
}
registerProcessor('pcm-processor', PcmProcessor);
