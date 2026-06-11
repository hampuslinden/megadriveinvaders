// Synthesize a short, punchy gunshot as a 32 kHz / 16-bit mono PCM WAV.
//
// A gunshot is a noise transient, not a pitched instrument, so we build it from:
//   * a hard initial click (~2 ms full-scale noise) for the sharp attack,
//   * a lowpassed white-noise body with a fast exponential decay (the "crack"),
//   * a low sine "thump" (~95 Hz) with its own decay for the punch/boom.
// The pieces are summed and soft-limited (tanh). snesbrr (-e) encodes to BRR.
//
// Output: res/gunshot.wav
const fs = require("fs");
const path = require("path");

const RATE = 32000;
const DUR = 0.16; // seconds; short so rapid fire stays responsive
const N = Math.floor(RATE * DUR);

// Small deterministic PRNG so rebuilds produce identical output.
let seed = 1234 >>> 0;
function rand() {
  // xorshift32 -> [-1, 1)
  seed ^= seed << 13; seed >>>= 0;
  seed ^= seed >> 17;
  seed ^= seed << 5;  seed >>>= 0;
  return (seed / 0xffffffff) * 2 - 1;
}

const samples = new Float64Array(N);
let prev = 0; // one-pole lowpass state for the noise body
for (let i = 0; i < N; i++) {
  const t = i / RATE;

  // noise body: white noise -> one-pole lowpass -> fast decay ("crack")
  const white = rand();
  prev = prev + 0.45 * (white - prev); // lowpass: tames hiss, adds body
  const body = prev * Math.exp(-t / 0.028); // ~28 ms decay

  // sharp attack click: a couple ms of unfiltered full-scale noise
  let click = 0;
  if (t < 0.0025) click = rand() * (1 - t / 0.0025);

  // low thump for punch
  const thump = Math.sin(2 * Math.PI * 95 * t) * Math.exp(-t / 0.045);

  const s = 0.85 * body + 0.45 * click + 0.55 * thump;
  samples[i] = Math.tanh(s * 1.4); // soft limiter keeps the transient hot
}

// normalize to ~95% full scale
let peak = 1e-6;
for (const s of samples) peak = Math.max(peak, Math.abs(s));
const scale = (0.95 / peak) * 32767;

const dataBytes = N * 2;
const buf = Buffer.alloc(44 + dataBytes);
// RIFF header
buf.write("RIFF", 0, "ascii");
buf.writeUInt32LE(36 + dataBytes, 4);
buf.write("WAVE", 8, "ascii");
// fmt chunk (PCM, mono, 16-bit)
buf.write("fmt ", 12, "ascii");
buf.writeUInt32LE(16, 16);
buf.writeUInt16LE(1, 20);            // PCM
buf.writeUInt16LE(1, 22);            // channels
buf.writeUInt32LE(RATE, 24);         // sample rate
buf.writeUInt32LE(RATE * 2, 28);     // byte rate
buf.writeUInt16LE(2, 32);            // block align
buf.writeUInt16LE(16, 34);           // bits/sample
// data chunk
buf.write("data", 36, "ascii");
buf.writeUInt32LE(dataBytes, 40);
for (let i = 0; i < N; i++) {
  let v = Math.round(samples[i] * scale);
  if (v > 32767) v = 32767;
  if (v < -32768) v = -32768;
  buf.writeInt16LE(v, 44 + i * 2);
}

const out = path.normpath
  ? path.normpath(path.join(__dirname, "..", "res", "gunshot.wav"))
  : path.join(__dirname, "..", "res", "gunshot.wav");
fs.writeFileSync(out, buf);
console.log(`wrote ${out}: ${N} samples (${(DUR * 1000).toFixed(0)} ms)`);
