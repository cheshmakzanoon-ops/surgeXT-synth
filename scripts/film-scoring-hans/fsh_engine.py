"""
Engine layer for the Film Scoring Hans patch generator.

A patch is described as a plain dictionary (a "spec") in musical units: seconds, Hz, dB,
semitones. This module turns a spec into a real Surge XT patch through the surgepy bindings,
renders it to check it plays, level-matches it, and writes the .fxp with its metadata.

Building through the engine rather than writing XML by hand means every patch is streamed at
the current revision, with every parameter present and every wavetable embedded.
"""

import math
import re
import struct
from pathlib import Path
from xml.sax.saxutils import quoteattr

import numpy as np
import surgepy
from surgepy import constants as C

REPO = Path(__file__).resolve().parents[2]
DATA = REPO / "resources" / "data"
TEMPLATE = DATA / "patches_factory" / "Templates" / "Init Saw.fxp"

SAMPLE_RATE = 48000

OSC_TYPES = {
    "classic": 0,
    "sine": 1,
    "wt": 2,
    "noise": 3,
    "fm3": 5,
    "fm2": 6,
    "window": 7,
    "modern": 8,
    "string": 9,
    "twist": 10,
    "alias": 11,
}

FILTER_TYPES = {
    "off": 0,
    "lp12": 1,
    "lp24": 2,
    "legacy_ladder": 3,
    "hp12": 4,
    "hp24": 5,
    "bp12": 6,
    "notch12": 7,
    "comb": 8,
    "snh": 9,
    "ladder": 10,
    "ob12": 11,
    "ob24": 12,
    "k35lp": 13,
    "k35hp": 14,
    "diode": 15,
    "warp_lp": 16,
    "warp_hp": 17,
    "warp_notch": 18,
    "warp_bp": 19,
    "ob_hp": 20,
    "ob_notch": 21,
    "ob_bp": 22,
    "bp24": 23,
    "notch24": 24,
    "comb_neg": 25,
    "allpass": 26,
    "reso_lp": 28,
    "reso_hp": 29,
    "reso_bp": 31,
    "tripole": 33,
    "svf": 34,
}

WAVESHAPERS = {
    "off": 0,
    "soft": 1,
    "hard": 2,
    "asym": 3,
    "sine": 4,
    "digital": 5,
    "harm2": 6,
    "harm3": 7,
    "fullwave": 10,
    "rectify": 13,
    "fold": 14,
    "doublefold": 15,
    "westfold": 16,
    "add_saw": 22,
    "fuzz": 24,
    "fuzz_soft": 25,
    "heavy_fuzz": 26,
    "medium": 40,
    "ojd": 41,
    "soft_fold": 42,
}

FX_TYPES = {
    "delay": 1,
    "reverb1": 2,
    "phaser": 3,
    "rotary": 4,
    "distortion": 5,
    "eq": 6,
    "freqshift": 7,
    "conditioner": 8,
    "chorus": 9,
    "reverb2": 11,
    "flanger": 12,
    "ringmod": 13,
    "resonator": 17,
    "exciter": 19,
    "ensemble": 20,
    "combulator": 21,
    "nimbus": 22,
    "tape": 23,
    "waveshaper": 25,
    "bonsai": 28,
    "floaty": 30,
}

# The FX parameters by name, in slot order. A None marks a slot this generator never sets.
FX_PARAMS = {
    "delay": ["left", "right", "feedback", "crossfeed", "lowcut", "highcut", "rate", "depth",
              "channel", None, "mix", "width"],
    "reverb1": ["predelay", "shape", "size", "decay", "hfdamp", "lowcut", "peakfreq", "peakgain",
                "highcut", "mix", "width"],
    "phaser": ["center", "feedback", "sharpness", "rate", "depth", "stereo", "mix", "width",
               "count", "spread", "waveform", "tone"],
    "distortion": ["pre_gain", "pre_freq", "pre_bw", "pre_highcut", "drive", "feedback",
                   "post_gain", "post_freq", "post_bw", "post_highcut", "gain", "model"],
    "eq": ["gain1", "freq1", "bw1", "gain2", "freq2", "bw2", "gain3", "freq3", "bw3", "gain",
           "mix"],
    "freqshift": ["shift", "right", "time", "feedback", "mix"],
    "conditioner": ["bass", "treble", "width", "balance", "threshold", "attack", "release",
                    "gain", "side_lowcut"],
    "chorus": ["time", "rate", "depth", "feedback", "lowcut", "highcut", "mix", "width"],
    "reverb2": ["predelay", "size", "decay", "diffusion", "buildup", "modulation", "lfdamp",
                "hfdamp", "width", "mix"],
    "flanger": ["mode", "waveform", "rate", "depth", "count", "base", "spacing", "feedback",
                "damping", "width", "mix"],
    "ringmod": ["shape", "freq", "detune", "voices", "bias", "linear", "lowcut", "highcut", "mix"],
    "resonator": ["freq1", "res1", "gain1", "freq2", "res2", "gain2", "freq3", "res3", "gain3",
                  "mode", "gain", "mix"],
    "exciter": ["drive", "tone", "attack", "release", "mix"],
    "ensemble": ["aa", "rate1", "depth1", "rate2", "depth2", "type", "clock", "saturation",
                 "feedback", "width", "mix", "recon"],
    "combulator": ["noise", "center", "offset2", "offset3", "feedback", "tone", "comb1", "comb2",
                   "comb3", "pan2", "pan3", "mix"],
    "nimbus": ["mode", "quality", "position", "size", "pitch", "density", "texture", "spread",
               "freeze", "feedback", "reverb", "mix"],
    "tape": ["drive", "saturation", "bias", "tone", "speed", "gap", "spacing", "thickness",
             "depth", "amount", "variance", "mix"],
    "waveshaper": ["pre_lowcut", "pre_highcut", "shape", "bias", "drive", "post_lowcut",
                   "post_highcut", "gain", "mix"],
    "bonsai": ["gain", "bass_amount", "distort", "bias_filter", "type", "noise", "sensitivity",
               "noise_gain", "dull", "out_gain", "mix"],
    "floaty": ["time", "playrate", "feedback", "cutoff", "resonance", "rate", "width",
               "pitch_depth", "filter_depth", "lowcut", "mix"],
}

FX_SLOTS = {"A1": 0, "A2": 1, "B1": 2, "B2": 3, "S1": 4, "S2": 5, "G1": 6, "G2": 7,
            "A3": 8, "A4": 9, "B3": 10, "B4": 11, "S3": 12, "S4": 13, "G3": 14, "G4": 15}

LFO_SHAPES = {"sine": 0, "tri": 1, "square": 2, "saw": 3, "noise": 4, "snh": 5, "env": 6,
              "step": 7}

LFO_TRIGGER = {"freerun": 0, "keytrigger": 1, "random": 2}

PLAY_MODES = {"poly": 0, "mono": 1, "mono_st": 2, "mono_fp": 3, "mono_st_fp": 4}

FILTER_CONFIGS = {"serial1": 0, "serial2": 1, "serial3": 2, "dual1": 3, "dual2": 4,
                  "stereo": 5, "ring": 6, "wide": 7}

ROUTES = {"f1": 0, "both": 1, "f2": 2}

MOD_SOURCES = {
    "velocity": C.ms_velocity,
    "keytrack": C.ms_keytrack,
    "aftertouch": C.ms_aftertouch,
    "polyat": C.ms_polyaftertouch,
    "modwheel": C.ms_modwheel,
    "ampeg": C.ms_ampeg,
    "filtereg": C.ms_filtereg,
    "random": C.ms_random_bipolar,
    "random_uni": C.ms_random_unipolar,
    "alternate": C.ms_alternate_bipolar,
}
for _i in range(6):
    MOD_SOURCES[f"lfo{_i + 1}"] = getattr(C, f"ms_lfo{_i + 1}")
    MOD_SOURCES[f"slfo{_i + 1}"] = getattr(C, f"ms_slfo{_i + 1}")
for _i in range(8):
    MOD_SOURCES[f"macro{_i + 1}"] = getattr(C, f"ms_ctrl{_i + 1}")

# Note values for tempo-synced rates, in quarter notes
NOTE_VALUES = {
    "1/1": 4.0, "1/2": 2.0, "1/2d": 3.0, "1/4": 1.0, "1/4d": 1.5, "1/4t": 2 / 3,
    "1/8": 0.5, "1/8d": 0.75, "1/8t": 1 / 3, "1/16": 0.25, "1/16d": 0.375, "1/16t": 1 / 6,
    "1/32": 0.125, "2/1": 8.0, "4/1": 16.0, "8/1": 32.0,
}


def secs(t):
    """Envelope and time parameters are stored as log2 seconds."""
    return max(-8.0, min(5.0, math.log2(max(t, 1e-6))))


def note_of(hz):
    """Cutoffs and frequencies are stored as semitones from A440."""
    return 12.0 * math.log2(hz / 440.0)


def rate_of(hz):
    return math.log2(hz)


def sync_rate(note):
    """A tempo-synced LFO rate, as Surge stores it (log2 Hz at 120 BPM)."""
    return math.log2(2.0 / NOTE_VALUES[note])


def sync_time(note):
    """A tempo-synced delay time, as Surge stores it (log2 seconds at 120 BPM)."""
    return math.log2(NOTE_VALUES[note] * 0.5)


def level(db):
    """Oscillator, scene and send levels are cubic amplitudes: dB = 60 log10(value)."""
    if db is None or db <= -96:
        return 0.0
    return 10.0 ** (db / 60.0)


class PatchBuilder:
    """Applies a spec to a fresh Surge XT instance."""

    def __init__(self):
        self.s = surgepy.createSurge(SAMPLE_RATE)
        self.s.loadPatch(str(TEMPLATE))
        self.settle()
        self.p = self.s.getPatch()
        self.sc = self.p["scene"][0]

    def settle(self, n=4):
        for _ in range(n):
            self.s.process()

    def set(self, param, value):
        self.s.setParamVal(param, float(value))

    def param(self, path):
        """
        Resolve a dotted path to a parameter: 'f1.cutoff', 'osc2.pitch', 'osc1.p3', 'amp.a',
        'feg.d', 'lfo3.rate', 'ws.drive', 'fx.A1.mix', 'send1', or any scene key like 'level_o1'.
        """
        parts = path.split(".")
        head = parts[0]
        sc = self.sc

        if head.startswith("osc"):
            o = sc["osc"][int(head[3]) - 1]
            if parts[1].startswith("p") and parts[1][1:].isdigit():
                return o["p"][int(parts[1][1:])]
            return o[parts[1]]
        if head in ("f1", "f2"):
            return sc["filterunit"][int(head[1]) - 1][parts[1]]
        if head == "amp":
            return sc["adsr"][0][parts[1]]
        if head == "feg":
            return sc["adsr"][1][parts[1]]
        if head.startswith("lfo"):
            return sc["lfo"][int(head[3:]) - 1][parts[1]]
        if head == "ws":
            return sc["wsunit"][parts[1]]
        if head == "fx":
            slot = self.p["fx"][FX_SLOTS[parts[1]]]
            if parts[2] == "return":
                return slot["return_level"]
            names = FX_PARAMS[self.fx_types[parts[1]]]
            return slot["p"][names.index(parts[2])]
        if head in ("send1", "send2"):
            return sc["send_level"][int(head[4]) - 1]
        if head in ("global_volume", "polylimit"):
            return self.p["volume" if head == "global_volume" else head]
        return sc[head]

    # ---------------------------------------------------------------------------------------
    # Spec application
    # ---------------------------------------------------------------------------------------

    def build(self, spec):
        s = self.s
        sc = self.sc
        self.fx_types = {}

        self.set(self.p["polylimit"], spec.get("polylimit", 16))
        self.set(sc["filterblock_configuration"], FILTER_CONFIGS[spec.get("fconfig", "serial1")])

        oscs = spec.get("oscs", [])

        for i in range(3):
            o = oscs[i] if i < len(oscs) else None
            self.set(sc["osc"][i]["type"], OSC_TYPES[o["type"]] if o else 0)
        self.settle()

        for i in range(3):
            o = oscs[i] if i < len(oscs) else None
            mute = sc[f"mute_o{i + 1}"]

            if not o:
                self.set(mute, 1)
                continue

            op = sc["osc"][i]

            if o["type"] in ("wt", "window"):
                path = resolve_wavetable(o["wt"])
                s.loadWavetable(0, i, str(path))
                if 0 not in o["p"]:
                    o["p"][0] = sustain_morph(path)

            self.set(mute, 0)
            self.set(sc[f"level_o{i + 1}"], level(o.get("level", 0.0)))
            self.set(sc[f"route_o{i + 1}"], ROUTES[o.get("route", "f1")])
            self.set(op["octave"], o.get("octave", 0))
            self.set(op["keytrack"], 1 if o.get("keytrack", True) else 0)
            self.set(op["retrigger"], 1 if o.get("retrigger", False) else 0)

            pitch = o.get("pitch", 0.0)
            if abs(pitch) > 7:
                s.setExtend(op["pitch"], True)
                pitch /= 12.0
            self.set(op["pitch"], pitch)

            for k, v in o.get("p", {}).items():
                self.set(op["p"][k], v)

            # Unison lives in params 5 and 6 on every oscillator type that has it
            if o["type"] in ("classic", "sine", "wt", "noise", "window", "modern", "alias"):
                if "unison" in o:
                    self.set(op["p"][6], o["unison"])
                if "detune" in o:
                    self.set(op["p"][5], o["detune"])

        self.mixer(spec)

        for idx, key in ((0, "f1"), (1, "f2")):
            f = spec.get(key)
            fu = sc["filterunit"][idx]
            self.set(fu["type"], FILTER_TYPES[f["type"]] if f else 0)
            self.settle(2)
            if not f:
                continue
            if "sub" in f:
                self.set(fu["subtype"], f["sub"])
            self.set(fu["cutoff"], note_of(f.get("cutoff", 2000.0)))
            self.set(fu["resonance"], f.get("res", 0.0))
            self.set(fu["envmod"], f.get("env", 0.0))
            self.set(fu["keytrack"], f.get("kt", 0.0))

        if spec.get("f2_offset"):
            self.set(sc["f2_cutoff_is_offset"], 1)
        self.set(sc["feedback"], spec.get("feedback", 0.0))
        self.set(sc["filter_balance"], spec.get("fbalance", 0.0))

        ws = spec.get("ws")
        self.set(sc["wsunit"]["type"], WAVESHAPERS[ws["type"]] if ws else 0)
        self.settle(2)
        if ws:
            self.set(sc["wsunit"]["drive"], ws.get("drive", 0.0))

        for idx, key in ((0, "amp"), (1, "feg")):
            env = spec.get(key, {})
            a = sc["adsr"][idx]
            self.set(a["a"], secs(env.get("a", 0.002)))
            self.set(a["d"], secs(env.get("d", 0.4)))
            self.set(a["s"], env.get("s", 1.0 if key == "amp" else 0.0))
            self.set(a["r"], secs(env.get("r", 0.3)))
            self.set(a["mode"], 1 if env.get("analog") else 0)
            for shape in ("a_s", "d_s", "r_s"):
                if shape in env:
                    self.set(a[shape], env[shape])

        self.scene_params(spec)

        for lfo in spec.get("lfos", []):
            self.lfo(lfo)

        for fx in spec.get("fx", []):
            self.effect(fx)

        for m in spec.get("mods", []):
            self.mod(*m)

        self.settle(8)

    def mixer(self, spec):
        sc = self.sc
        noise = spec.get("noise")
        self.set(sc["mute_noise"], 0 if noise is not None else 1)
        if noise is not None:
            self.set(sc["level_noise"], level(noise))
            self.set(sc["route_noise"], ROUTES[spec.get("noise_route", "f1")])
            self.set(sc["noise_colour"], spec.get("noise_color", 0.0))

        for key, ring in (("ring12", "12"), ("ring23", "23")):
            r = spec.get(key)
            self.set(sc[f"mute_ring_{ring}"], 0 if r is not None else 1)
            if r is not None:
                self.set(sc[f"level_ring_{ring}"], level(r))

        fm = spec.get("fm")
        self.set(sc["fm_switch"], fm[0] if fm else 0)
        if fm:
            self.set(sc["fm_depth"], fm[1])

    def scene_params(self, spec):
        sc = self.sc
        self.set(sc["octave"], spec.get("octave", 0))
        self.set(sc["pitch"], spec.get("pitch", 0.0))
        self.set(sc["drift"], spec.get("drift", 0.0))
        self.set(sc["polymode"], PLAY_MODES[spec.get("play", "poly")])
        porta = spec.get("porta")
        self.set(sc["portamento"], secs(porta) if porta else -8.0)
        self.set(sc["pbrange_up"], spec.get("bend", 2))
        self.set(sc["pbrange_dn"], spec.get("bend", 2))
        self.set(sc["vca_velsense"], spec.get("velsense", -12.0))
        self.set(sc["vca_level"], spec.get("vca", 0.0))
        self.set(sc["level_pfg"], spec.get("pfg", 0.0))
        self.set(sc["width"], spec.get("width", 1.0))
        self.set(sc["pan"], 0.0)
        self.set(sc["volume"], level(spec.get("scene_db", 0.0)))
        hp = spec.get("highpass")
        self.set(sc["lowcut"], note_of(hp) if hp else -72.0)
        for i, db in enumerate(spec.get("sends", [None, None])):
            self.set(sc["send_level"][i], level(db))
        self.set(self.p["volume"], spec.get("global_db", -2.0))

    def lfo(self, lfo):
        s = self.s
        L = self.sc["lfo"][lfo["i"]]
        self.set(L["shape"], LFO_SHAPES[lfo.get("shape", "sine")])
        self.settle(2)

        if "sync" in lfo:
            s.setTempoSync(L["rate"], True)
            self.set(L["rate"], sync_rate(lfo["sync"]))
        else:
            self.set(L["rate"], rate_of(lfo.get("rate", 1.0)))

        self.set(L["magnitude"], lfo.get("mag", 1.0))
        self.set(L["start_phase"], lfo.get("phase", 0.0))
        self.set(L["deform"], lfo.get("deform", 0.0))
        self.set(L["trigmode"], LFO_TRIGGER[lfo.get("trig", "keytrigger")])
        self.set(L["unipolar"], 1 if lfo.get("uni") else 0)
        self.set(L["delay"], secs(lfo["delay"]) if lfo.get("delay") else -8.0)
        self.set(L["attack"], secs(lfo["attack"]) if lfo.get("attack") else -8.0)
        self.set(L["hold"], secs(lfo["hold"]) if lfo.get("hold") else -8.0)
        self.set(L["decay"], secs(lfo.get("decay", 1.0)))
        self.set(L["sustain"], lfo.get("sustain", 1.0))
        rel = lfo.get("release")
        self.set(L["release"], secs(rel) if rel else 5.0)

    def effect(self, fx):
        s = self.s
        slot = fx["slot"]
        p = self.p["fx"][FX_SLOTS[slot]]
        self.set(p["type"], FX_TYPES[fx["type"]])
        self.settle(4)
        self.fx_types[slot] = fx["type"]
        names = FX_PARAMS[fx["type"]]

        for k, v in fx.get("p", {}).items():
            param = p["p"][names.index(k)]
            if isinstance(v, str):
                s.setTempoSync(param, True)
                v = sync_time(v) if fx["type"] == "delay" else sync_rate(v)
            self.set(param, v)

        if slot.startswith("S"):
            self.set(p["return_level"], level(fx.get("return", 0.0)))

    def mod(self, source, target, amount, index=0):
        """Route a modulation; the amount is in the target's own units."""
        s = self.s
        param = self.param(target)
        span = s.getParamMax(param) - s.getParamMin(param)
        src = s.getModSource(MOD_SOURCES[source])
        if not s.isValidModulation(param, src):
            raise ValueError(f"Can't modulate {target} from {source}")
        s.setModDepth01(param, src, amount / span, 0, index)


WT_ALIASES = {
    "vsco/": "wavetables_3rdparty/Emu VSCO/",
    "emu/": "wavetables_3rdparty/Emu/",
    "layzer/": "wavetables_3rdparty/Layzer/",
    "favre/": "wavetables_3rdparty/Philippe Favre/",
    "aos/": "wavetables_3rdparty/Art of Sound/",
    "oss/": "wavetables_3rdparty/Ocean Swift Synthesis/",
    "tnmg/": "wavetables_3rdparty/TNMG/",
    "venus/": "wavetables_3rdparty/Venus Theory/",
    "qon/": "wavetables_3rdparty/Qonundrai/",
    "aliv/": "wavetables_3rdparty/A.Liv/",
    "": "wavetables/",
}


def wavetable_frames(path):
    """The RMS level in dB of each frame of a .wt or framed .wav wavetable, or None for a sample."""
    d = Path(path).read_bytes()

    if d[:4] == b"vawt":
        size, count, flags = struct.unpack("<IHH", d[4:12])
        if flags & 1:
            return None
        dtype, width, scale = ("<i2", 2, 32768.0) if flags & 4 else ("<f4", 4, 1.0)
        raw = np.frombuffer(d[12:12 + size * count * width], dtype=dtype)
        data = raw.astype(np.float64) / scale
    else:
        i, size, fmt, data = 12, None, None, None
        while i + 8 <= len(d):
            cid = d[i:i + 4]
            n = struct.unpack("<I", d[i + 4:i + 8])[0]
            body = d[i + 8:i + 8 + n]
            if cid == b"fmt ":
                fmt = struct.unpack("<HHIIHH", body[:16])
            elif cid in (b"srge", b"srgo"):
                size = struct.unpack("<II", body[:8])[1]
            elif cid == b"clm ":
                m = re.match(rb"<!>(\d+)", body)
                size = int(m.group(1)) if m else size
            elif cid == b"data":
                data = body
            i += 8 + n + (n & 1)
        if not size or fmt is None or data is None:
            return None
        if fmt[0] == 3:
            x = np.frombuffer(data, dtype="<f4")
        elif fmt[5] == 16:
            x = np.frombuffer(data, dtype="<i2") / 32768.0
        else:
            return None
        data = x.astype(np.float64)[::fmt[1]]
        count = len(data) // size

    frames = data[:size * count].reshape(count, size)
    return 10.0 * np.log10((frames ** 2).mean(axis=1) + 1e-12)


def sustain_morph(path):
    """
    A morph position in the body of a wavetable. Many sampled tables start with the quiet onset
    of the recorded note, so frame 0 can be 40 dB down on the sustain; take the middle of the
    frames that are within 3 dB of the loudest.
    """
    levels = wavetable_frames(path)
    if levels is None or len(levels) < 2:
        return 0.0
    loud = np.flatnonzero(levels >= levels.max() - 3.0)
    return float(np.median(loud) / (len(levels) - 1))


def resolve_wavetable(name):
    for prefix, folder in WT_ALIASES.items():
        if name.startswith(prefix):
            path = DATA / folder / name[len(prefix):]
            if path.exists():
                return path
            raise FileNotFoundError(path)
    raise FileNotFoundError(name)


# -------------------------------------------------------------------------------------------
# Rendering and analysis
# -------------------------------------------------------------------------------------------

BLOCK = 32


def render(s, notes, hold, tail, velocity=100):
    """Play `notes` together for `hold` seconds, release, and render `tail` more seconds."""
    s.allNotesOff()
    pre = s.createMultiBlock(int(0.5 * SAMPLE_RATE / BLOCK))
    s.processMultiBlock(pre)

    n_hold = max(1, int(hold * SAMPLE_RATE / BLOCK))
    n_tail = max(1, int(tail * SAMPLE_RATE / BLOCK))
    buf = s.createMultiBlock(n_hold + n_tail)

    for n in notes:
        s.playNote(0, n, velocity, 0)
    s.processMultiBlock(buf, 0, n_hold)
    for n in notes:
        s.releaseNote(0, n, 0)
    s.processMultiBlock(buf, n_hold, n_tail)
    s.allNotesOff()
    return buf


def analyse(buf, hold, window=0.5):
    """
    Levels of a render from `render`: 'rms' is the average over the held note from `window`
    of the way through, once it has settled; 'short' is the loudest 50 ms, for percussive
    sounds. Both use the stereo power, so neither depends on how the channels sum to mono.
    """
    finite = bool(np.all(np.isfinite(buf)))
    x = np.nan_to_num(buf).astype(np.float64)
    power = (x ** 2).mean(axis=0)
    held = power[int(hold * SAMPLE_RATE * window):int(hold * SAMPLE_RATE)]
    return {
        "finite": finite,
        "peak": float(np.max(np.abs(x))) if x.size else 0.0,
        "dc": float(abs(x.mean())),
        "rms": float(np.sqrt(held.mean())) if held.size else 0.0,
        "short": loudest(power, SAMPLE_RATE // 20),
    }


def loudest(power, win):
    """The RMS of the loudest window of `win` samples."""
    if len(power) < win:
        return float(np.sqrt(power.mean()))
    c = np.concatenate(([0.0], np.cumsum(power)))
    return float(np.sqrt(max(0.0, (c[win:] - c[:-win]).max() / win)))


def db(x):
    return 20.0 * math.log10(max(x, 1e-9))


# -------------------------------------------------------------------------------------------
# Patch file metadata
# -------------------------------------------------------------------------------------------


def write_patch(src, dest, name, category, author, comment, tags=(), steps=None, macros=None):
    """
    Rewrite the patch Surge saved at `src` into `dest` with our metadata, step sequences and
    macro names, fixing up the sizes in the fxp and patch headers.
    """
    data = Path(src).read_bytes()
    fxp = list(struct.unpack(">4si4siiii28si", data[:60]))
    head = list(struct.unpack("<4s7i", data[60:92]))
    xmlsize = head[1]
    xml = data[92:92 + xmlsize].decode("utf-8")
    rest = data[92 + xmlsize:]

    tag_xml = "".join(f"<tag tag={quoteattr(t)} />" for t in tags)
    meta = (f"<meta name={quoteattr(name)} category={quoteattr(category)} "
            f"comment={quoteattr(comment)} author={quoteattr(author)}>"
            f"<tags>{tag_xml}</tags></meta>")
    xml, n = re.subn(r"<meta\b[^>]*?/>|<meta\b.*?</meta>", lambda _: meta, xml, count=1,
                     flags=re.S)
    assert n == 1, "patch has no meta element"

    for lfo, seq in (steps or {}).items():
        xml = set_step_sequence(xml, lfo, seq)

    for i, label in (macros or {}).items():
        xml, n = re.subn(rf'<entry i="{i}" bipolar="(\d)" v="([^"]*)" label="[^"]*" />',
                         lambda m: f'<entry i="{i}" bipolar="{m.group(1)}" v="{m.group(2)}" '
                                   f'label={quoteattr(label)} />', xml, count=1)
        assert n == 1, f"no macro {i} in patch"

    body = xml.encode("utf-8")
    head[1] = len(body)
    chunk = struct.pack("<4s7i", *head) + body + rest
    fxp[7] = name.encode("utf-8")[:28]
    fxp[8] = len(chunk)
    Path(dest).write_bytes(struct.pack(">4si4siiii28si", *fxp) + chunk)


def set_step_sequence(xml, lfo, seq):
    """Replace the step sequence of voice/scene LFO `lfo` (0-based) on scene A."""
    steps = seq["steps"]
    attrs = "".join(f' s{i}="{v:.6f}"' for i, v in enumerate(steps) if v != 0)
    trig = seq.get("trigmask", 0)
    new = (f'<sequence scene="0" i="{lfo}"{attrs} loop_start="0" loop_end="{len(steps) - 1}" '
           f'shuffle="{seq.get("shuffle", 0.0):.6f}" trigmask="{trig}" '
           f'trigmask_0to15="{trig & 0xFFFF}" trigmask_16to31="0" trigmask_32to47="0" />')
    pattern = rf'<sequence scene="0" i="{lfo}"[^>]*/>'
    if re.search(pattern, xml):
        return re.sub(pattern, lambda _: new, xml, count=1)
    if "<stepsequences>" in xml:
        return xml.replace("<stepsequences>", "<stepsequences>" + new, 1)
    return xml.replace("</parameters>", "</parameters><stepsequences>" + new + "</stepsequences>",
                       1)
