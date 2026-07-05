#!/usr/bin/env python3
"""Convert music/summergames.mid into res/summergames.it for smconv.

PVSnesLib's audio converter (smconv) only accepts Impulse Tracker (.it)
modules, not raw MIDI. This script hand-parses the MIDI (no external
dependencies -- none are installed in this environment) and hand-writes a
minimal, valid .it: no instrument structures (sample-direct/"old style"
mode), two synthesized single-cycle waveforms (one per MIDI track), and
uncompressed signed 8-bit PCM samples. The binary layout follows the
ITFileHeader (192 bytes) / ITSample (80 bytes) structs and the pattern
row-compression scheme exactly as documented in OpenMPT's own IT loader
(soundlib/ITTools.h, soundlib/Load_it.cpp).

Looping is intentionally NOT baked into the module (no Bxx pattern-jump
effect) -- the game code restarts playback with spcPlay(0) once the known
song duration elapses, which avoids needing to get IT's effect-column byte
encoding exactly right.
"""
import struct
import math

MIDI_PATH = "music/summergames.mid"
OUT_PATH = "res/summergames.it"

TICKS_PER_ROW = 256      # 1 row = 1 sixteenth note at division=1024
ROWS_PER_PATTERN = 64
IT_TEMPO = 160           # BPM
IT_SPEED = 3             # ticks/row -> seconds/row = 2.5*speed/tempo = 0.046875s
                         # (half of the original 6 -- doubles playback rate with
                         # no pitch shift, since it's sequenced tempo, not audio)
MIDDLE_C_HZ = 261.6256   # MIDI note 60


# --- MIDI parsing (pure Python, no deps) ------------------------------------

def read_varlen(data, i):
    val = 0
    while True:
        b = data[i]; i += 1
        val = (val << 7) | (b & 0x7F)
        if not (b & 0x80):
            break
    return val, i


def read_chunks(data):
    i = 0
    chunks = []
    while i < len(data):
        cid = data[i:i + 4]
        clen = struct.unpack(">I", data[i + 4:i + 8])[0]
        chunks.append((cid, data[i + 8:i + 8 + clen]))
        i += 8 + clen
    return chunks


def parse_midi(path):
    with open(path, "rb") as f:
        data = f.read()
    chunks = read_chunks(data)
    fmt, ntrks, division = struct.unpack(">HHH", chunks[0][1][:6])

    tracks = []  # list of (name, [(start_tick, end_tick, note, vel), ...])
    for cid, body in chunks[1:]:
        if cid != b"MTrk":
            continue
        i = 0
        abs_tick = 0
        last_status = None
        notes_on = {}
        events = []
        name = ""
        while i < len(body):
            delta, i = read_varlen(body, i)
            abs_tick += delta
            status = body[i]
            if status == 0xFF:
                i += 1
                meta = body[i]; i += 1
                length, i = read_varlen(body, i)
                if meta == 0x03:
                    name = body[i:i + length].decode("latin1", "ignore")
                i += length
            elif status in (0xF0, 0xF7):
                i += 1
                length, i = read_varlen(body, i)
                i += length
            else:
                if status & 0x80:
                    i += 1
                    last_status = status
                else:
                    status = last_status
                kind = status & 0xF0
                if kind == 0xC0:
                    i += 1
                elif kind == 0xD0:
                    i += 1
                else:
                    d1, d2 = body[i], body[i + 1]; i += 2
                    if kind == 0x90 and d2 > 0:
                        notes_on[d1] = (abs_tick, d2)
                    elif kind == 0x80 or (kind == 0x90 and d2 == 0):
                        if d1 in notes_on:
                            start, vel = notes_on.pop(d1)
                            events.append((start, abs_tick, d1, vel))
        if events:
            events.sort(key=lambda e: e[0])
            tracks.append((name, events))
    return division, tracks


# --- Channel assignment ------------------------------------------------------

def assign_channels(tracks):
    """Returns (num_channels, list of (channel, instrument_idx, events))."""
    channel_tracks = []  # (base_channel, num_channels_for_track, events, instrument_idx)
    next_channel = 0
    for instr_idx, (name, events) in enumerate(tracks, start=1):
        max_poly = 0
        active = []
        for start, end, note, vel in events:
            active = [a for a in active if a > start]
            active.append(end)
            max_poly = max(max_poly, len(active))
        n_ch = min(max_poly, 2) if max_poly > 0 else 1
        channel_tracks.append((next_channel, n_ch, events, instr_idx))
        next_channel += n_ch
    return next_channel, channel_tracks


def build_channel_events(channel_tracks):
    """Round-robins overlapping notes within a track's allotted channels.
    Returns dict: channel -> list of (row, note, instr, vol)."""
    result = {}
    for base_ch, n_ch, events, instr_idx in channel_tracks:
        chan_free_at = [0] * n_ch  # tick each sub-channel becomes free
        for start, end, note, vel in events:
            # pick the sub-channel that's been free longest (round-robin/least-recently-used)
            sub = min(range(n_ch), key=lambda k: chan_free_at[k])
            chan_free_at[sub] = end
            ch = base_ch + sub
            row = start // TICKS_PER_ROW
            vol = max(1, min(64, vel // 2))
            note = max(0, min(119, note))
            result.setdefault(ch, []).append((row, note, instr_idx, vol))
    return result


# --- Waveform synthesis -------------------------------------------------------

def make_pulse(length=32, duty=0.25, amp=100):
    on = max(1, int(length * duty))
    return [amp if i < on else -amp for i in range(length)]


def make_triangle(length=32, amp=100):
    out = []
    for i in range(length):
        phase = i / length
        v = 4 * abs(phase - 0.5) - 1  # -1..1 triangle, starts at 0 rising... adjust:
        out.append(int(round(v * amp)))
    return out


# --- IT file writing -----------------------------------------------------------

def pack_sample_header(name, cvt_signed, flags, vol, length, loop_end, c5speed, samplepointer):
    return struct.pack(
        "<4s13sBBB26sBBIIIIIIIBBBB",
        b"IMPS", name.encode("ascii")[:12].ljust(13, b"\x00"),
        64,          # gvl (global volume)
        flags,       # flags
        vol,         # default volume (0..64)
        b"".ljust(26, b"\x00"),
        0x01 if cvt_signed else 0x00,  # cvt
        32,          # dfp (default pan, unused -- panning set per channel)
        length, 0, loop_end,  # length, loopbegin, loopend
        c5speed,
        0, 0,        # susloopbegin, susloopend
        samplepointer,
        0, 0, 0, 0,  # vis, vid, vir, vit
    )


def encode_pattern(rows_events, num_rows):
    """rows_events: dict row_idx -> {channel: (note, instr, vol)}"""
    data = bytearray()
    established = set()
    for row in range(num_rows):
        events = rows_events.get(row)
        if not events:
            data.append(0)
            continue
        for ch in sorted(events.keys()):
            note, instr, vol = events[ch]
            if ch not in established:
                data.append((ch + 1) | 0x80)
                data.append(0x07)  # mask: note+instr+vol values follow, every time
                established.add(ch)
            else:
                data.append(ch + 1)
            data.append(note)
            data.append(instr)
            data.append(vol)
        data.append(0)
    return bytes(data)


def write_it(path, num_channels, channel_events, samples, total_rows):
    num_patterns = (total_rows + ROWS_PER_PATTERN - 1) // ROWS_PER_PATTERN

    # Build each pattern's row->{channel:(note,instr,vol)} map
    pattern_rows = [dict() for _ in range(num_patterns)]
    for ch, events in channel_events.items():
        for row, note, instr, vol in events:
            pat = row // ROWS_PER_PATTERN
            local_row = row % ROWS_PER_PATTERN
            pattern_rows[pat].setdefault(local_row, {})[ch] = (note, instr, vol)

    pattern_blobs = []
    for pat in range(num_patterns):
        rows_in_pat = min(ROWS_PER_PATTERN, total_rows - pat * ROWS_PER_PATTERN)
        body = encode_pattern(pattern_rows[pat], rows_in_pat)
        header = struct.pack("<HHI", len(body), rows_in_pat, 0)
        pattern_blobs.append(header + body)

    # Sample PCM data (signed 8-bit)
    sample_pcm = [struct.pack(f"<{len(wave)}b", *wave) for _, wave, _ in samples]

    order_list = bytes(list(range(num_patterns)) + [255])
    ordnum = len(order_list)
    smpnum = len(samples)
    patnum = num_patterns

    header_size = 192
    after_header = ordnum + smpnum * 4 + patnum * 4
    smp_headers_offset = header_size + after_header
    smp_headers_size = smpnum * 80
    patterns_offset = smp_headers_offset + smp_headers_size
    pattern_offsets = []
    off = patterns_offset
    for blob in pattern_blobs:
        pattern_offsets.append(off)
        off += len(blob)
    pcm_offset = off
    pcm_offsets = []
    for pcm in sample_pcm:
        pcm_offsets.append(off)
        off += len(pcm)

    sample_headers = b"".join(
        pack_sample_header(name, True, 0x01 | 0x10, 64, len(wave), len(wave), c5speed, pcm_offsets[i])
        for i, (name, wave, c5speed) in enumerate(samples)
    )

    fileheader = struct.pack(
        "<4s26sBBHHHHHHHHBBBBBBHII64s64s",
        b"IMPM",
        b"summergames".ljust(26, b"\x00"),
        4, 16,                      # highlight minor/major (cosmetic)
        ordnum, 0, smpnum, patnum,  # ordnum, insnum(=0, sample mode), smpnum, patnum
        0x0214, 0x0200,             # cwtv, cmwt
        0x0000,                     # flags: no stereo, no instrument mode, no linear slides
        0x0000,                     # special: no message/history/highlights embedded
        128, 48,                    # globalvol, mv
        IT_SPEED, IT_TEMPO,
        128, 0,                     # sep, pwd
        0, 0,                       # msglength, msgoffset
        0,                          # reserved
        bytes([32]) * 64,           # chnpan (center)
        bytes([64]) * 64,           # chnvol (max)
    )

    smp_ptrs = b"".join(struct.pack("<I", smp_headers_offset + i * 80) for i in range(smpnum))
    pat_ptrs = b"".join(struct.pack("<I", o) for o in pattern_offsets)

    with open(path, "wb") as f:
        f.write(fileheader)
        f.write(order_list)
        f.write(smp_ptrs)
        f.write(pat_ptrs)
        f.write(sample_headers)
        for blob in pattern_blobs:
            f.write(blob)
        for pcm in sample_pcm:
            f.write(pcm)


def main():
    division, tracks = parse_midi(MIDI_PATH)
    assert division == 1024, f"expected division 1024, got {division}"

    num_channels, channel_tracks = assign_channels(tracks)
    channel_events = build_channel_events(channel_tracks)

    total_ticks = max(e[1] for _, events in tracks for e in events)
    total_rows = (total_ticks + TICKS_PER_ROW - 1) // TICKS_PER_ROW

    wave_len = 32
    samples = [
        ("lead", make_pulse(wave_len, duty=0.25, amp=100), round(wave_len * MIDDLE_C_HZ)),
        ("pad", make_triangle(wave_len, amp=100), round(wave_len * MIDDLE_C_HZ)),
    ]

    write_it(OUT_PATH, num_channels, channel_events, samples, total_rows)

    total_notes = sum(len(v) for v in channel_events.values())
    print(f"tracks={len(tracks)} channels={num_channels} total_rows={total_rows} "
          f"patterns={(total_rows + ROWS_PER_PATTERN - 1)//ROWS_PER_PATTERN} notes={total_notes}")
    print(f"wrote {OUT_PATH}")


if __name__ == "__main__":
    main()
