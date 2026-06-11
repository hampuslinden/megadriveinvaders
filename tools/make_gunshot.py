#!/usr/bin/env python3
"""Synthesize a short, punchy gunshot as a 32 kHz / 16-bit mono PCM WAV.

A gunshot is essentially a noise transient, not a pitched instrument, so we
build it from:
  * a hard initial click (1-2 ms of full-scale noise) for the sharp attack,
  * a lowpassed white-noise body with a fast exponential decay (the "crack"),
  * a low sine "thump" (~95 Hz) with its own decay for the punch/boom.
The pieces are summed and soft-limited. snesbrr (-e) then encodes it to BRR.

Output: res/gunshot.wav  (run `snesbrr -e res/gunshot.wav res/gunshot.brr`).
"""
import math
import os
import random
import struct
import wave

RATE = 32000
DUR = 0.16                      # seconds; short so rapid fire stays responsive
N = int(RATE * DUR)

random.seed(1234)               # deterministic output across rebuilds

samples = [0.0] * N
prev = 0.0                      # one-pole lowpass state for the noise body
for i in range(N):
    t = i / RATE

    # --- noise body: white noise -> one-pole lowpass -> fast decay ---
    white = random.uniform(-1.0, 1.0)
    prev = prev + 0.45 * (white - prev)        # lowpass: tames hiss, adds body
    body = prev * math.exp(-t / 0.028)         # ~28 ms decay -> the "crack"

    # --- sharp attack click: a couple ms of unfiltered full-scale noise ---
    click = 0.0
    if t < 0.0025:
        click = random.uniform(-1.0, 1.0) * (1.0 - t / 0.0025)

    # --- low thump for punch ---
    thump = math.sin(2.0 * math.pi * 95.0 * t) * math.exp(-t / 0.045)

    s = 0.85 * body + 0.45 * click + 0.55 * thump

    # soft limiter (tanh) keeps the transient hot without harsh digital clip
    samples[i] = math.tanh(s * 1.4)

# normalize to ~95% full scale
peak = max(1e-6, max(abs(s) for s in samples))
scale = 0.95 / peak
pcm = b"".join(struct.pack("<h", int(max(-32768, min(32767, s * scale * 32767))))
               for s in samples)

out = os.path.join(os.path.dirname(__file__), "..", "res", "gunshot.wav")
out = os.path.normpath(out)
with wave.open(out, "wb") as w:
    w.setnchannels(1)
    w.setsampwidth(2)
    w.setframerate(RATE)
    w.writeframes(pcm)
print(f"wrote {out}: {N} samples ({DUR*1000:.0f} ms)")
