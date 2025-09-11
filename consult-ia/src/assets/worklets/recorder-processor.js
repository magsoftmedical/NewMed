class RecorderProcessor extends AudioWorkletProcessor {
  constructor() {
    super();
    // Parámetros
    this.inputRate = sampleRate;      // típico 48000
    this.targetRate = 16000;
    this.ratio = this.inputRate / this.targetRate; // 3 si 48k -> 16k
    this.chunkMs = 200;               // ~200 ms por envío
    this.samplesTarget = Math.round(this.targetRate * this.chunkMs / 1000); // 3200

    // Acumuladores
    this._acc = [];        // trozos Float32
    this._accLen = 0;      // muestras acumuladas a tasa de entrada
  }

  _mergeFloat32(chunks, totalLen) {
    const out = new Float32Array(totalLen);
    let off = 0;
    for (const c of chunks) { out.set(c, off); off += c.length; }
    return out;
  }

  _downsampleAverage(input, inRate, outRate) {
    if (inRate === outRate) return input;
    const ratio = inRate / outRate;
    const newLen = Math.floor(input.length / ratio);
    const out = new Float32Array(newLen);
    for (let i = 0; i < newLen; i++) {
      const start = Math.floor(i * ratio);
      const end = Math.floor((i + 1) * ratio);
      let sum = 0, cnt = 0;
      for (let j = start; j < end && j < input.length; j++) { sum += input[j]; cnt++; }
      out[i] = cnt ? (sum / cnt) : input[start];
    }
    return out;
  }

  _floatTo16LE(f32) {
    const out = new Int16Array(f32.length);
    for (let i = 0; i < f32.length; i++) {
      let s = Math.max(-1, Math.min(1, f32[i]));
      out[i] = s < 0 ? s * 0x8000 : s * 0x7FFF;
    }
    return out;
  }

  process(inputs /* [ [channel0, channel1...] ] */) {
    const input = inputs[0];
    if (!input || input.length === 0) return true;
    const ch0 = input[0]; // mono
    if (!ch0) return true;

    // Acumular a tasa de ENTRADA (48k). Cada callback trae 128 samples aprox.
    this._acc.push(new Float32Array(ch0));
    this._accLen += ch0.length;

    // ¿Ya tenemos ~chunkMs de audio a 48k? → remuestrear y emitir
    const samplesInputTarget = Math.round(this.inputRate * this.chunkMs / 1000); // 9600 si 48k
    if (this._accLen >= samplesInputTarget) {
      const merged = this._mergeFloat32(this._acc, this._accLen);
      this._acc = []; this._accLen = 0;

      // Remuestrear a 16k y recortar exactamente a samplesTarget
      const down = this._downsampleAverage(merged, this.inputRate, this.targetRate);
      const exact = down.length > this.samplesTarget ? down.subarray(0, this.samplesTarget) : down;
      const pcm16 = this._floatTo16LE(exact);

      // Enviar ArrayBuffer transferible al hilo principal
      this.port.postMessage(pcm16.buffer, [pcm16.buffer]);
    }

    return true; // seguir procesando
  }
}

registerProcessor('recorder-processor', RecorderProcessor);
