"""
The Film Scoring Hans sound library: 100 base sounds in 20 categories, each played in 5
variants, for 500 patches.

The bases are modelled on instruments and production techniques that are documented in Hans
Zimmer's film scores: the low brass of Inception, the Temple Church organ of Interstellar, the
ticking watch and Shepard tones of Dunkirk, the duduk and voice of Gladiator, the throat singing
and bagpipes of Dune, the cimbalom and prepared piano of Sherlock Holmes, the pedal steel of
Man of Steel, the all-synthesizer scores of the late 1980s, and so on. They are original
synthesizer patches written in that spirit, not recreations of any recording.

Every builder returns a spec for fsh_engine.PatchBuilder. Variants are small transformations of
a spec (wider, darker, driven, slower...) or flags a builder reads itself (speed, for example).
"""

import copy
import math

from fsh_engine import note_of, rate_of, secs

AUTHOR = "Film Scoring Hans"
UNISON_TYPES = {"classic", "sine", "wt", "window", "modern", "alias"}

# -------------------------------------------------------------------------------------------
# Oscillators
# -------------------------------------------------------------------------------------------


def classic(shape=0.0, w1=0.5, w2=0.5, sub=0.0, sync=0.0, **kw):
    return dict(type="classic", p={0: shape, 1: w1, 2: w2, 3: sub, 4: sync}, **kw)


def saw(**kw):
    return classic(0.0, **kw)


def square(width=0.5, **kw):
    return classic(1.0, w1=width, **kw)


def wt(name, morph=None, sat=0.0, formant=0.0, **kw):
    """A wavetable; with no morph, the engine picks the sustained body of the table."""
    p = {2: sat, 3: formant}
    if morph is not None:
        p[0] = morph
    return dict(type="wt", wt=name, p=p, **kw)


def sine(shape=0, fb=0.0, **kw):
    return dict(type="sine", p={0: shape, 1: fb}, **kw)


def fm2(m1, r1, m2=0.0, r2=1, offset=0.0, fb=0.0, **kw):
    return dict(type="fm2", p={0: m1, 1: r1, 2: m2, 3: r2, 4: offset, 6: fb}, **kw)


def string(exciter=0, exc=1.0, d1=0.95, d2=0.95, det=0.1, bal=0.0, stiff=0.0, **kw):
    return dict(type="string", p={0: exciter, 1: exc, 2: d1, 3: d2, 4: det, 5: bal, 6: stiff},
                **kw)


# -------------------------------------------------------------------------------------------
# Effects
# -------------------------------------------------------------------------------------------


def hall(decay=3.5, size=0.45, pre=0.03, hf=0.3, lf=0.15, mod=0.45, ret=0.0):
    return dict(slot="S1", type="reverb2", p=dict(
        predelay=secs(pre), size=size, decay=math.log2(decay), diffusion=1.0, buildup=0.85,
        modulation=mod, lfdamp=lf, hfdamp=hf, width=0.0, mix=1.0), **{"return": ret})


def echo(time="1/8d", fb=0.35, lc=250, hc=4500, cross=0.25, ret=0.0):
    return dict(slot="S2", type="delay", p=dict(
        left=time, right=time, feedback=fb, crossfeed=cross, lowcut=note_of(lc),
        highcut=note_of(hc), mix=1.0), **{"return": ret})


def ins(slot, type, **p):
    return dict(slot=slot, type=type, p=p)


def chorus(slot, depth=0.3, rate=0.3, mix=0.45, fb=0.15):
    return ins(slot, "chorus", time=-6.0, rate=rate_of(rate), depth=depth, feedback=fb,
               lowcut=note_of(150), highcut=note_of(9000), mix=mix, width=3.0)


def ensemble(slot, mix=0.5, d1=1.0, d2=0.5):
    return ins(slot, "ensemble", depth1=d1, depth2=d2, mix=mix)


def tape(slot, drive=0.75, sat=0.55, mix=1.0, degrade=0.0):
    return ins(slot, "tape", drive=drive, saturation=sat, mix=mix, depth=degrade,
               amount=degrade, variance=degrade * 0.5)


def dist(slot, drive=8.0, model=0, gain=-8.0, tone=7000):
    return ins(slot, "distortion", pre_highcut=note_of(14000), drive=drive,
               post_highcut=note_of(tone), gain=gain, model=model)


def exciter(slot, drive=0.4, tone=0.65, mix=0.35):
    return ins(slot, "exciter", drive=drive, tone=tone, mix=mix)


def phaser(slot, rate=0.15, depth=0.6, fb=0.3, mix=0.5, count=6):
    return ins(slot, "phaser", rate=rate_of(rate), depth=depth, feedback=fb, mix=mix,
               count=count, stereo=0.6)


def comb(slot, center=220, fb=0.6, mix=0.5, noise=0.0):
    return ins(slot, "combulator", center=note_of(center), feedback=fb, mix=mix, noise=noise)


def ringmod(slot, freq=60, mix=0.3):
    return ins(slot, "ringmod", freq=freq, mix=mix)


# -------------------------------------------------------------------------------------------
# Spec helpers
# -------------------------------------------------------------------------------------------


def patch(**kw):
    """A spec with the defaults every builder relies on."""
    spec = dict(oscs=[], fx=[], lfos=[], mods=[], sends=[-8.0, None], steps={})
    spec.update(kw)
    return spec


def used_slots(spec):
    return {fx["slot"] for fx in spec["fx"]}


def get_fx(spec, slot):
    for fx in spec["fx"]:
        if fx["slot"] == slot:
            return fx
    return None


def has_fx(spec, *types):
    return any(fx["type"] in types for fx in spec["fx"])


def add_insert(spec, fx):
    for slot in ("A1", "A2", "A3", "A4"):
        if slot not in used_slots(spec):
            fx = dict(fx, slot=slot)
            spec["fx"].append(fx)
            return fx
    return None


def lfo_source(i):
    return f"lfo{i + 1}" if i < 6 else f"slfo{i - 5}"


def add_lfo(spec, targets, scene=False, **lfo):
    used = {l["i"] for l in spec["lfos"]}
    pool = (6, 7, 8, 9, 10, 11) if scene else (0, 1, 2, 3, 4, 5)
    i = next(k for k in pool if k not in used)
    spec["lfos"].append(dict(i=i, **lfo))
    for target, amount in targets:
        spec["mods"].append((lfo_source(i), target, amount))
    return i


def add_osc(spec, o):
    if len(spec["oscs"]) < 3:
        spec["oscs"].append(o)
    else:
        spec["oscs"][-1] = o
        idx = len(spec["oscs"])
        spec["mods"] = [m for m in spec["mods"] if not m[1].startswith(f"osc{idx}.")]


def vibrato(spec, depth=0.18, rate=5.2, delay=0.45, attack=0.6):
    add_lfo(spec, [("pitch", depth)], shape="sine", rate=rate, delay=delay, attack=attack)


def expressive(spec, cutoff=18.0, vca=4.0):
    """Mod wheel as orchestral dynamics: opens the filter and lifts the level."""
    if spec.get("f1"):
        spec["mods"].append(("modwheel", "f1.cutoff", cutoff))
    if vca:
        spec["mods"].append(("modwheel", "vca_level", vca))


def step_lfo(spec, rate, steps, trig=None, targets=(), length=None):
    """A voice step sequencer; `trig` lists the steps that retrigger both envelopes."""
    n = length or len(steps)
    i = add_lfo(spec, list(targets), shape="step", sync=rate, uni=True)
    mask = 0
    for k in (range(n) if trig is None else trig):
        mask |= 1 << k
    spec["steps"][i] = dict(steps=list(steps)[:n], trigmask=mask)
    return i


# -------------------------------------------------------------------------------------------
# Variants
# -------------------------------------------------------------------------------------------


def m_wide(spec):
    for o in spec["oscs"]:
        if o["type"] in UNISON_TYPES:
            o["unison"] = max(o.get("unison", 1), 3)
            o["detune"] = min(0.4, max(o.get("detune", 0.1), 0.1) + 0.08)
    if not has_fx(spec, "ensemble", "chorus"):
        add_insert(spec, chorus("A1", depth=0.35, rate=0.35, mix=0.45))
    spec["width"] = 1.0


def scale_cutoff(spec, k, lo=60.0, hi=16000.0):
    for key in ("f1", "f2"):
        f = spec.get(key)
        if f and f["type"] not in ("hp12", "hp24", "k35hp", "ob_hp", "comb", "comb_neg"):
            f["cutoff"] = max(lo, min(hi, f["cutoff"] * k))


def m_dark(spec):
    if spec.get("f1"):
        scale_cutoff(spec, 0.45)
    else:
        spec["f1"] = dict(type="lp12", cutoff=1400, res=0.1, kt=0.4)
    rv = get_fx(spec, "S1")
    if rv:
        rv["p"]["hfdamp"] = min(0.9, rv["p"]["hfdamp"] + 0.3)


def m_bright(spec):
    scale_cutoff(spec, 2.0)
    if not has_fx(spec, "exciter"):
        add_insert(spec, exciter("A1", drive=0.35, tone=0.7, mix=0.35))


def m_driven(spec):
    ws = spec.get("ws")
    if ws:
        ws["drive"] = min(18.0, ws.get("drive", 0.0) + 6.0)
    else:
        spec["ws"] = dict(type="soft", drive=9.0)
    if not has_fx(spec, "distortion"):
        add_insert(spec, dist("A1", drive=9.0, model=0, gain=-3.0, tone=6500))


def m_heavy(spec):
    spec["ws"] = dict(type="fuzz_soft", drive=10.0)
    add_insert(spec, dist("A1", drive=14.0, model=3, gain=-4.0, tone=5000))


def m_tight(spec):
    amp = spec.setdefault("amp", {})
    amp["r"] = amp.get("r", 0.3) * 0.35
    amp["d"] = amp.get("d", 0.4) * 0.7
    if spec["sends"][0] is not None:
        spec["sends"][0] -= 6.0
    rv = get_fx(spec, "S1")
    if rv:
        rv["p"]["decay"] = math.log2(max(0.4, 2 ** rv["p"]["decay"] * 0.6))


def m_huge(spec):
    rv = get_fx(spec, "S1")
    if rv:
        rv["p"]["decay"] = math.log2(min(30.0, 2 ** rv["p"]["decay"] * 1.7))
        rv["p"]["size"] = min(1.0, rv["p"]["size"] + 0.25)
    if spec["sends"][0] is not None:
        spec["sends"][0] = min(0.0, spec["sends"][0] + 3.0)
    m_sub(spec)


def m_soft(spec):
    amp = spec.setdefault("amp", {})
    amp["a"] = max(amp.get("a", 0.002) * 3.0, 0.12)
    scale_cutoff(spec, 0.65)
    spec["velsense"] = -18.0


def m_forte(spec):
    scale_cutoff(spec, 1.6)
    if not spec.get("ws"):
        spec["ws"] = dict(type="soft", drive=4.0)
    if not has_fx(spec, "exciter"):
        add_insert(spec, exciter("A1", drive=0.3, tone=0.6, mix=0.3))
    amp = spec.setdefault("amp", {})
    amp["a"] = amp.get("a", 0.002) * 0.6


def m_swell(spec):
    amp = spec.setdefault("amp", {})
    amp["a"] = max(amp.get("a", 0.002), 1.8)
    amp["a_s"] = 2
    feg = spec.setdefault("feg", {})
    feg["a"] = max(feg.get("a", 0.002), 1.4)


def m_sub(spec):
    lowest = min([o.get("octave", 0) for o in spec["oscs"]] or [0])
    add_osc(spec, sine(octave=max(-3, lowest - 1), level=-4.0, route="f2" if
                       spec.get("fconfig") in ("dual1", "dual2") else "both"))


def m_distant(spec):
    if spec["sends"][0] is not None:
        spec["sends"][0] = min(2.0, spec["sends"][0] + 6.0)
    rv = get_fx(spec, "S1")
    if rv:
        rv["p"]["predelay"] = secs(0.07)
        rv["p"]["decay"] = math.log2(min(30.0, 2 ** rv["p"]["decay"] * 1.4))
    if spec.get("f1"):
        scale_cutoff(spec, 0.6)
    else:
        spec["f1"] = dict(type="lp12", cutoff=3000, kt=0.3)
    spec["highpass"] = max(spec.get("highpass") or 0, 160)
    amp = spec.setdefault("amp", {})
    amp["a"] = amp.get("a", 0.002) + 0.05


def m_evolving(spec):
    targets = []
    for k, o in enumerate(spec["oscs"]):
        if o["type"] == "wt":
            # sweep the morph around the body of the table
            targets.append((f"osc{k + 1}.p0", 0.25))
            break
    if spec.get("f1"):
        targets.append(("f1.cutoff", 10.0))
    targets.append(("pan", 0.25))
    add_lfo(spec, targets, scene=True, shape="sine", rate=0.06, trig="freerun")


def m_gritty(spec):
    add_insert(spec, tape("A1", drive=0.95, sat=0.85, degrade=0.35))
    ws = spec.get("ws")
    if not ws:
        spec["ws"] = dict(type="asym", drive=6.0)


def m_echo(spec, time="1/8d", fb=0.38):
    if not get_fx(spec, "S2"):
        spec["fx"].append(echo(time, fb=fb))
    spec["sends"][1] = -7.0


def m_shimmer(spec):
    first = spec["oscs"][0]
    layer = copy.deepcopy(first)
    layer["octave"] = min(3, first.get("octave", 0) + 1)
    layer["level"] = -12.0
    layer.pop("unison", None)
    if len(spec["oscs"]) < 3:
        spec["oscs"].append(layer)
    rv = get_fx(spec, "S1")
    if rv:
        rv["p"]["decay"] = math.log2(min(30.0, 2 ** rv["p"]["decay"] * 1.6))
        rv["p"]["modulation"] = 0.85
    if spec["sends"][0] is not None:
        spec["sends"][0] = min(0.0, spec["sends"][0] + 3.0)
    if not has_fx(spec, "chorus", "ensemble"):
        add_insert(spec, chorus("A1", depth=0.25, rate=0.2, mix=0.35))


def m_lofi(spec):
    add_insert(spec, tape("A1", drive=0.8, sat=0.6, degrade=0.55))
    add_lfo(spec, [("pitch", 0.08)], shape="sine", rate=0.55, trig="freerun")
    scale_cutoff(spec, 0.6)


def m_detuned(spec):
    spec["drift"] = 0.7
    for o in spec["oscs"]:
        if o["type"] in UNISON_TYPES:
            o["unison"] = max(o.get("unison", 1), 2)
            o["detune"] = min(0.45, o.get("detune", 0.1) + 0.15)


def m_motion(spec, rate="1/4d", depth=14.0):
    if not spec.get("f1"):
        spec["f1"] = dict(type="lp12", cutoff=2500, res=0.2, kt=0.3)
    add_lfo(spec, [("f1.cutoff", depth)], shape="sine", sync=rate)


def m_intimate(spec):
    if spec["sends"][0] is not None:
        spec["sends"][0] -= 8.0
    amp = spec.setdefault("amp", {})
    amp["a"] = amp.get("a", 0.002) * 1.5
    scale_cutoff(spec, 0.75)
    spec["velsense"] = -20.0


def m_vibrato(spec):
    vibrato(spec, depth=0.28, rate=5.6, delay=0.35, attack=0.5)


def m_breathy(spec):
    if spec.get("noise") is None:
        spec["noise"] = -15.0
        spec["noise_color"] = 0.35
        spec["noise_route"] = "both"


def m_full(spec):
    first = spec["oscs"][0]
    layer = copy.deepcopy(first)
    layer["octave"] = min(3, first.get("octave", 0) + 1)
    layer["level"] = -6.0
    layer.pop("unison", None)
    add_osc(spec, layer)


def m_tremulant(spec):
    add_lfo(spec, [("vca_level", -5.0), ("pitch", 0.04)], shape="sine", rate=6.2)


def m_ethereal(spec):
    m_soft(spec)
    m_shimmer(spec)
    spec["highpass"] = 220


def m_room(spec):
    rv = get_fx(spec, "S1")
    if rv:
        rv["p"].update(decay=math.log2(1.1), size=-0.3, predelay=secs(0.01))
    if spec["sends"][0] is not None:
        spec["sends"][0] = min(0.0, spec["sends"][0] + 2.0)


def m_slow(spec):
    m_swell(spec)
    amp = spec.setdefault("amp", {})
    amp["r"] = max(amp.get("r", 0.3), 2.5)


def m_intense(spec):
    m_driven(spec)
    scale_cutoff(spec, 1.5)


def m_filtered(spec):
    if spec.get("f1"):
        scale_cutoff(spec, 0.5)
    m_motion(spec, rate="2/1", depth=24.0)


def m_synth_layer(spec):
    oct_ = spec["oscs"][0].get("octave", 0)
    add_osc(spec, saw(octave=oct_, unison=5, detune=0.2, level=-9.0))
    if not spec.get("f1"):
        spec["f1"] = dict(type="lp12", cutoff=2500, kt=0.4)


def variant(label, mods=(), flags=None, note=""):
    return dict(label=label, mods=list(mods), flags=flags or {}, note=note)


# -------------------------------------------------------------------------------------------
# Braams
# -------------------------------------------------------------------------------------------


def braam_tectonic(f):
    return patch(
        oscs=[saw(octave=-1, unison=3, detune=0.16), saw(octave=-2, level=-3.0),
              wt("vsco/Brass/SUS Tuba Loud.wav", octave=-1, level=-2.0)],
        f1=dict(type="ladder", sub=1, cutoff=320, res=0.25, env=40, kt=0.25),
        feg=dict(a=0.25, d=1.5, s=0.4, r=1.2),
        amp=dict(a=0.05, d=1.0, s=0.9, r=1.5),
        ws=dict(type="soft", drive=6.0),
        fx=[tape("A2", drive=0.7, sat=0.6), hall(5.5, 0.7)],
        sends=[-8.0, None], polylimit=8,
        mods=[("velocity", "f1.cutoff", 12.0)],
    )


def braam_collapse(f):
    s = patch(
        oscs=[wt("vsco/Brass/SUS Trombone Buzzy.wav", octave=-1, unison=2, detune=0.12),
              saw(octave=-1, unison=2, detune=0.2, level=-4.0),
              wt("vsco/Brass/SUS Tuba.wav", octave=-2, level=-3.0)],
        f1=dict(type="lp24", sub=1, cutoff=450, res=0.2, env=32, kt=0.3),
        feg=dict(a=0.4, d=2.0, s=0.5, r=1.5),
        amp=dict(a=0.15, d=1.0, s=1.0, r=2.0),
        fx=[ensemble("A2", mix=0.35), hall(7.0, 0.8)],
        sends=[-6.0, None], polylimit=8,
    )
    # The pitch sags as the note is held, like a dream slowing down
    add_lfo(s, [("pitch", -1.6)], shape="env", delay=1.2, attack=3.5, decay=1.0, sustain=1.0)
    return s


def braam_leviathan(f):
    return patch(
        oscs=[wt("vsco/Brass/SUS Tenor Trombone Loud.wav", octave=-1, unison=2, detune=0.1),
              square(octave=-2, level=-5.0),
              saw(octave=-1, pitch=0.08, level=-6.0)],
        f1=dict(type="ob24", sub=3, cutoff=550, res=0.2, env=28, kt=0.3),
        feg=dict(a=0.12, d=1.2, s=0.45, r=1.0),
        amp=dict(a=0.04, d=1.0, s=0.95, r=1.3),
        ws=dict(type="asym", drive=8.0),
        fx=[hall(5.0, 0.65)],
        sends=[-8.0, None], polylimit=8,
        mods=[("velocity", "f1.cutoff", 14.0)],
    )


def braam_abyss(f):
    return patch(
        oscs=[wt("vsco/Brass/SUS Tuba.wav", octave=-1, unison=2, detune=0.08),
              wt("vsco/Brass/SUS French Horn Loud.wav", octave=-1, level=-4.0),
              saw(octave=-2, level=-6.0)],
        f1=dict(type="diode", sub=3, cutoff=240, res=0.3, env=34, kt=0.2),
        feg=dict(a=0.8, d=2.5, s=0.5, r=2.0),
        amp=dict(a=0.3, d=1.0, s=1.0, r=2.2),
        fx=[tape("A2", drive=0.6, sat=0.5), hall(8.0, 0.85, hf=0.5)],
        sends=[-6.0, None], polylimit=8,
    )


def braam_foghorn(f):
    return patch(
        oscs=[saw(octave=-1, unison=2, detune=0.14), saw(octave=-1, pitch=7.0, level=-3.0),
              saw(octave=-2, level=-2.0)],
        f1=dict(type="lp24", sub=1, cutoff=380, res=0.15, env=36, kt=0.25),
        feg=dict(a=0.2, d=1.6, s=0.45, r=1.3),
        amp=dict(a=0.06, d=1.0, s=1.0, r=1.6),
        ws=dict(type="fuzz_soft", drive=4.0),
        fx=[hall(6.0, 0.7)],
        sends=[-8.0, None], polylimit=6,
        mods=[("velocity", "f1.cutoff", 12.0)],
    )


# -------------------------------------------------------------------------------------------
# Horns and brass
# -------------------------------------------------------------------------------------------


def horns_heroic(f):
    s = patch(
        oscs=[wt("vsco/Brass/SUS French Horn Loud.wav", unison=2, detune=0.06),
              wt("vsco/Brass/SUS French Horn.wav", level=-5.0, detune=0.1, unison=2),
              saw(level=-16.0)],
        f1=dict(type="lp12", cutoff=1600, res=0.1, env=20, kt=0.5),
        feg=dict(a=0.15, d=1.0, s=0.55, r=0.8),
        amp=dict(a=0.07, d=1.0, s=1.0, r=0.7, analog=True),
        fx=[ensemble("A1", mix=0.3), hall(3.8, 0.55)],
        sends=[-7.0, None],
    )
    vibrato(s, depth=0.12, rate=5.0, delay=0.6, attack=0.8)
    expressive(s)
    return s


def horns_choir(f):
    s = patch(
        oscs=[wt("vsco/Brass/SUS French Horn.wav", unison=3, detune=0.08),
              wt("vsco/Brass/SUS French Horn.wav", octave=-1, level=-6.0)],
        f1=dict(type="lp12", cutoff=1100, res=0.05, env=14, kt=0.5),
        feg=dict(a=0.3, d=1.4, s=0.6, r=1.0),
        amp=dict(a=0.25, d=1.0, s=1.0, r=1.0, analog=True),
        fx=[hall(4.5, 0.6)],
        sends=[-5.0, None],
    )
    vibrato(s, depth=0.08, rate=4.8, delay=0.8, attack=1.0)
    expressive(s)
    return s


def horns_muted(f):
    s = patch(
        oscs=[wt("vsco/Brass/SUS French Horn Mute.wav", unison=2, detune=0.07),
              wt("vsco/Brass/SUS Trumpet Harmon Mute.wav", octave=-1, level=-9.0)],
        f1=dict(type="lp12", cutoff=2400, res=0.15, env=10, kt=0.5),
        feg=dict(a=0.1, d=0.8, s=0.6, r=0.6),
        amp=dict(a=0.06, d=1.0, s=1.0, r=0.5),
        fx=[hall(2.8, 0.4)],
        sends=[-9.0, None],
    )
    expressive(s)
    return s


def horns_trombones(f):
    s = patch(
        oscs=[wt("vsco/Brass/SUS Tenor Trombone Loud.wav", unison=2, detune=0.07),
              wt("vsco/Brass/SUS Trombone Buzzy.wav", level=-4.0, pitch=0.06)],
        f1=dict(type="ob12", cutoff=1900, res=0.1, env=22, kt=0.5),
        feg=dict(a=0.08, d=0.9, s=0.5, r=0.6),
        amp=dict(a=0.05, d=1.0, s=1.0, r=0.6, analog=True),
        ws=dict(type="asym", drive=3.0),
        fx=[hall(3.5, 0.55)],
        sends=[-8.0, None],
        mods=[("velocity", "f1.cutoff", 14.0)],
    )
    expressive(s)
    return s


def horns_tuba(f):
    s = patch(
        oscs=[wt("vsco/Brass/SUS Tuba.wav", octave=-1, unison=2, detune=0.05),
              sine(octave=-2, level=-6.0)],
        f1=dict(type="lp12", cutoff=900, res=0.1, env=16, kt=0.4),
        feg=dict(a=0.1, d=1.0, s=0.6, r=0.7),
        amp=dict(a=0.06, d=1.0, s=1.0, r=0.8),
        fx=[hall(3.5, 0.55)],
        sends=[-9.0, None],
    )
    expressive(s, vca=3.0)
    return s


# -------------------------------------------------------------------------------------------
# String ostinatos
# -------------------------------------------------------------------------------------------

ACCENT16 = [1.0, 0.55, 0.8, 0.55] * 4


def ost_spiccato(f):
    return patch(
        oscs=[wt("vsco/String/SPIC Violin.wav", unison=2, detune=0.06),
              wt("vsco/String/SPIC Viola.wav", octave=-1, level=-3.0)],
        f1=dict(type="lp12", cutoff=4200, res=0.05, env=10, kt=0.4),
        feg=dict(a=0.0, d=0.12, s=0.0, r=0.1),
        amp=dict(a=0.002, d=0.16, s=0.0, r=0.14),
        fx=[hall(2.2, 0.4)],
        sends=[-7.0, None],
        mods=[("velocity", "f1.cutoff", 14.0)],
        render=dict(note=60, hold=0.3, tail=1.5, mode="short"),
    )


def ost_celli(f):
    s = patch(
        oscs=[wt("vsco/String/SUS Cello.wav", unison=2, detune=0.08),
              saw(level=-12.0)],
        f1=dict(type="lp12", cutoff=1500, res=0.1, env=16, kt=0.4),
        feg=dict(a=0.0, d=0.1, s=0.0, r=0.1),
        amp=dict(a=0.003, d=0.14, s=0.15, r=0.2),
        fx=[hall(2.5, 0.45)],
        sends=[-8.0, None],
    )
    step_lfo(s, "1/16", ACCENT16, targets=[("f1.cutoff", 18.0)])
    return s


def ost_gallop(f):
    s = patch(
        oscs=[wt("vsco/String/SPIC Bass 1.wav", octave=-1, unison=2, detune=0.06),
              saw(octave=-1, level=-10.0)],
        f1=dict(type="lp12", cutoff=1100, res=0.1, env=18, kt=0.4),
        feg=dict(a=0.0, d=0.1, s=0.0, r=0.1),
        amp=dict(a=0.002, d=0.12, s=0.0, r=0.15),
        fx=[hall(2.2, 0.4)],
        sends=[-9.0, None],
    )
    gallop = [0, 2, 3, 4, 6, 7, 8, 10, 11, 12, 14, 15]
    step_lfo(s, "1/16", [1.0, 0, 0.6, 0.7] * 4, trig=gallop, targets=[("f1.cutoff", 16.0)])
    return s


def ost_viola_runner(f):
    s = patch(
        oscs=[wt("vsco/String/SPIC Viola.wav", unison=2, detune=0.07),
              wt("vsco/String/SPIC Violin.wav", octave=1, level=-8.0)],
        f1=dict(type="lp12", cutoff=3500, res=0.05, env=10, kt=0.4),
        feg=dict(a=0.0, d=0.1, s=0.0, r=0.1),
        amp=dict(a=0.002, d=0.13, s=0.05, r=0.15),
        fx=[hall(2.4, 0.4)],
        sends=[-8.0, None],
    )
    step_lfo(s, "1/8t", [1.0, 0.5, 0.7] * 4, targets=[("f1.cutoff", 14.0)], length=12)
    return s


def ost_hybrid(f):
    s = patch(
        oscs=[saw(unison=3, detune=0.12), wt("vsco/String/SUS Violin.wav", level=-3.0),
              saw(octave=-1, level=-6.0)],
        f1=dict(type="lp24", sub=1, cutoff=700, res=0.3, env=36, kt=0.4),
        feg=dict(a=0.0, d=0.16, s=0.0, r=0.1),
        amp=dict(a=0.002, d=0.2, s=0.1, r=0.2),
        fx=[echo("1/8d", fb=0.3), hall(2.8, 0.5)],
        sends=[-9.0, -10.0],
    )
    step_lfo(s, "1/8", [1.0, 0.6, 0.85, 0.6, 1.0, 0.6, 0.85, 0.7], targets=[("f1.cutoff", 12.0)])
    return s


def ost_marcato(f):
    return patch(
        oscs=[wt("vsco/String/SUS Cello Vibrato.wav", unison=2, detune=0.07),
              wt("vsco/String/SPIC Bass 2.wav", octave=-1, level=-3.0)],
        f1=dict(type="lp12", cutoff=1800, res=0.05, env=16, kt=0.4),
        feg=dict(a=0.0, d=0.25, s=0.2, r=0.2),
        amp=dict(a=0.01, d=0.35, s=0.25, r=0.25),
        fx=[hall(2.8, 0.45)],
        sends=[-8.0, None],
        mods=[("velocity", "f1.cutoff", 16.0)],
        render=dict(note=48, hold=0.6, tail=1.5, mode="short"),
    )


# -------------------------------------------------------------------------------------------
# String swells and sections
# -------------------------------------------------------------------------------------------


def str_cello(f):
    s = patch(
        oscs=[wt("vsco/String/SUS Cello Vibrato.wav", unison=3, detune=0.07),
              wt("vsco/String/SUS Cello.wav", level=-4.0, unison=2, detune=0.1)],
        f1=dict(type="lp12", cutoff=2200, res=0.05, env=8, kt=0.4),
        feg=dict(a=0.4, d=1.5, s=0.7, r=1.0),
        amp=dict(a=0.35, d=1.0, s=1.0, r=1.1, analog=True),
        fx=[ensemble("A1", mix=0.25), hall(4.0, 0.55)],
        sends=[-6.0, None],
    )
    expressive(s)
    return s


def str_violins(f):
    s = patch(
        oscs=[wt("vsco/String/SUS Violin.wav", unison=3, detune=0.07),
              wt("vsco/String/SUS Violin High.wav", level=-5.0, unison=2, detune=0.09),
              wt("vsco/String/SUS Violin Low.wav", level=-6.0)],
        f1=dict(type="lp12", cutoff=4500, res=0.05, env=6, kt=0.4),
        feg=dict(a=0.4, d=1.5, s=0.7, r=1.0),
        amp=dict(a=0.3, d=1.0, s=1.0, r=1.0, analog=True),
        fx=[ensemble("A1", mix=0.25), hall(4.0, 0.55)],
        sends=[-6.0, None],
    )
    expressive(s)
    return s


def str_tremolo(f):
    s = patch(
        oscs=[wt("vsco/String/SUS Violin Trem.wav", unison=2, detune=0.08),
              wt("vsco/String/SUS Bass Trem 1.wav", octave=-1, level=-4.0)],
        f1=dict(type="lp12", cutoff=3800, res=0.05, kt=0.4),
        amp=dict(a=0.2, d=1.0, s=1.0, r=0.9),
        fx=[hall(3.8, 0.5)],
        sends=[-6.0, None],
    )
    expressive(s)
    return s


def str_low_swell(f):
    s = patch(
        oscs=[wt("vsco/String/SUS Bass Low.wav", octave=-1, unison=2, detune=0.06),
              wt("vsco/String/SUS Cello.wav", level=-6.0, unison=2, detune=0.08)],
        f1=dict(type="lp12", cutoff=1200, res=0.05, env=10, kt=0.3),
        feg=dict(a=1.0, d=2.0, s=0.7, r=1.5),
        amp=dict(a=1.0, d=1.0, s=1.0, r=1.6, a_s=2),
        fx=[hall(4.5, 0.6)],
        sends=[-6.0, None],
    )
    expressive(s)
    return s


def str_synth(f):
    s = patch(
        oscs=[saw(unison=5, detune=0.2), saw(octave=1, level=-8.0, unison=3, detune=0.15)],
        f1=dict(type="lp24", sub=1, cutoff=3000, res=0.1, env=8, kt=0.4),
        feg=dict(a=0.5, d=1.5, s=0.7, r=1.0),
        amp=dict(a=0.4, d=1.0, s=1.0, r=1.2, analog=True),
        fx=[ensemble("A1", mix=0.6), hall(4.0, 0.55)],
        sends=[-7.0, None],
    )
    expressive(s, vca=2.0)
    return s


# -------------------------------------------------------------------------------------------
# Drones
# -------------------------------------------------------------------------------------------


def drone_cello(f):
    s = patch(
        oscs=[wt("vsco/String/SUS Cello.wav", octave=-1, unison=2, detune=0.08),
              wt("vsco/String/SUS Bass Low.wav", octave=-2, level=-3.0)],
        f1=dict(type="lp12", cutoff=900, res=0.1, kt=0.3),
        amp=dict(a=2.0, d=1.0, s=1.0, r=3.0, a_s=2),
        drift=0.3,
        fx=[hall(6.0, 0.7)],
        sends=[-6.0, None],
        render=dict(note=48, hold=5.0, tail=3.0),
    )
    add_lfo(s, [("f1.cutoff", 6.0)], scene=True, shape="sine", rate=0.09, trig="freerun")
    return s


def drone_sub(f):
    s = patch(
        oscs=[sine(octave=-2), saw(octave=-2, level=-6.0), sine(octave=-1, level=-12.0)],
        f1=dict(type="lp24", sub=1, cutoff=180, res=0.15, kt=0.2),
        noise=-26.0, noise_color=-0.5,
        amp=dict(a=1.5, d=1.0, s=1.0, r=3.0, a_s=2),
        fx=[hall(6.0, 0.6)],
        sends=[-10.0, None],
        render=dict(note=48, hold=5.0, tail=3.0),
    )
    add_lfo(s, [("vca_level", -4.0)], scene=True, shape="sine", rate=0.25, trig="freerun")
    return s


def drone_throat(f):
    s = patch(
        oscs=[wt("Sampled/Vocal O Formant 1.wt", octave=-2, unison=2, detune=0.05),
              wt("Waldorf/Male AhPG.wt", octave=-1, level=-6.0)],
        fconfig="dual1",
        f1=dict(type="bp12", cutoff=550, res=0.45, kt=0.0),
        f2=dict(type="bp12", cutoff=1150, res=0.5, kt=0.0),
        ws=dict(type="asym", drive=4.0),
        amp=dict(a=1.2, d=1.0, s=1.0, r=2.5, a_s=2),
        drift=0.2,
        fx=[hall(6.0, 0.7)],
        sends=[-7.0, None],
        render=dict(note=48, hold=5.0, tail=3.0),
    )
    s["oscs"][0]["route"] = "both"
    s["oscs"][1]["route"] = "both"
    add_lfo(s, [("f2.cutoff", 7.0), ("osc1.p0", 0.3)], scene=True, shape="sine", rate=0.07,
            trig="freerun")
    return s


def drone_bagpipe(f):
    s = patch(
        oscs=[wt("vsco/Woodwinds/SUS Oboe Jittery.wav", unison=2, detune=0.04),
              wt("vsco/Woodwinds/SUS Oboe.wav", octave=-1, level=-4.0),
              wt("vsco/Woodwinds/SUS Bassoon Low.wav", octave=-1, pitch=7.0, level=-6.0)],
        f1=dict(type="lp12", cutoff=3500, res=0.2, kt=0.3),
        ws=dict(type="harm3", drive=3.0),
        amp=dict(a=0.6, d=1.0, s=1.0, r=1.8),
        fx=[hall(5.0, 0.6)],
        sends=[-7.0, None],
        render=dict(note=48, hold=4.0, tail=3.0),
    )
    return s


def drone_pedal(f):
    return patch(
        oscs=[wt("vsco/Keys/Organ Pedal.wav", octave=-1, unison=2, detune=0.04),
              sine(octave=-2, level=-4.0)],
        f1=dict(type="lp12", cutoff=650, res=0.05, kt=0.3),
        amp=dict(a=1.5, d=1.0, s=1.0, r=3.0, a_s=2),
        fx=[hall(8.0, 0.85)],
        sends=[-5.0, None],
        render=dict(note=48, hold=5.0, tail=3.0),
    )


# -------------------------------------------------------------------------------------------
# Synth basses
# -------------------------------------------------------------------------------------------

BASS_RENDER = dict(note=36, hold=1.5, tail=1.0)


def retrigger(spec):
    """Restart the oscillators on every note, so each one attacks the same way."""
    for o in spec["oscs"]:
        o["retrigger"] = True
    return spec


def bass_growl(f):
    return retrigger(patch(
        oscs=[saw(octave=-1, unison=2, detune=0.1), square(octave=-2, level=-4.0)],
        f1=dict(type="ladder", sub=1, cutoff=260, res=0.35, env=30, kt=0.3),
        feg=dict(a=0.005, d=0.5, s=0.3, r=0.3),
        amp=dict(a=0.004, d=0.8, s=0.9, r=0.25),
        ws=dict(type="fuzz_soft", drive=8.0),
        fx=[dist("A1", drive=6.0, gain=-6.0, tone=4000), hall(2.0, 0.3)],
        sends=[-16.0, None], play="mono", porta=0.03,
        mods=[("velocity", "f1.cutoff", 12.0)],
        render=BASS_RENDER,
    ))


def bass_moog(f):
    return retrigger(patch(
        oscs=[saw(octave=-1), square(octave=-1, level=-3.0, pitch=0.05),
              saw(octave=-2, level=-6.0)],
        f1=dict(type="legacy_ladder", sub=3, cutoff=380, res=0.3, env=36, kt=0.4),
        feg=dict(a=0.002, d=0.35, s=0.2, r=0.25, analog=True),
        amp=dict(a=0.002, d=0.6, s=0.85, r=0.2, analog=True),
        fx=[hall(1.8, 0.3)],
        sends=[-18.0, None], play="mono", porta=0.02,
        mods=[("velocity", "f1.cutoff", 14.0)],
        render=BASS_RENDER,
    ))


def bass_ostinato(f):
    s = retrigger(patch(
        oscs=[saw(octave=-1, unison=2, detune=0.08), sine(octave=-2, level=-3.0)],
        f1=dict(type="lp24", sub=1, cutoff=300, res=0.25, env=30, kt=0.3),
        feg=dict(a=0.0, d=0.12, s=0.0, r=0.1),
        amp=dict(a=0.002, d=0.11, s=0.1, r=0.12),
        ws=dict(type="soft", drive=5.0),
        fx=[hall(1.8, 0.3)],
        sends=[-14.0, None],
        render=dict(note=36, hold=2.0, tail=1.0),
    ))
    step_lfo(s, "1/16", ACCENT16, targets=[("f1.cutoff", 14.0)])
    return s


def bass_sub(f):
    return retrigger(patch(
        oscs=[sine(octave=-2), sine(octave=-1, level=-12.0)],
        f1=dict(type="lp12", cutoff=220, res=0.05, kt=0.5),
        ws=dict(type="soft", drive=10.0),
        amp=dict(a=0.005, d=1.0, s=1.0, r=0.3),
        fx=[],
        sends=[None, None], play="mono", porta=0.02,
        render=BASS_RENDER,
    ))


def bass_fm(f):
    s = retrigger(patch(
        oscs=[fm2(0.35, 1, m2=0.18, r2=2, octave=-1), sine(octave=-2, level=-6.0)],
        f1=dict(type="lp12", cutoff=1800, res=0.1, env=12, kt=0.4),
        feg=dict(a=0.002, d=0.4, s=0.25, r=0.3),
        amp=dict(a=0.003, d=0.8, s=0.9, r=0.25),
        fx=[hall(2.0, 0.3)],
        sends=[-16.0, None], play="mono", porta=0.02,
        render=BASS_RENDER,
    ))
    s["mods"].append(("filtereg", "osc1.p0", 0.35))
    return s


def bass_reese(f):
    s = retrigger(patch(
        oscs=[saw(octave=-1, unison=4, detune=0.25), saw(octave=-1, pitch=0.12, level=-3.0),
              sine(octave=-2, level=-6.0)],
        f1=dict(type="lp24", sub=1, cutoff=500, res=0.2, env=10, kt=0.3),
        feg=dict(a=0.01, d=0.8, s=0.5, r=0.3),
        amp=dict(a=0.004, d=0.8, s=1.0, r=0.3),
        fx=[phaser("A1", rate=0.12, depth=0.5, mix=0.35), hall(2.0, 0.3)],
        sends=[-16.0, None], play="mono", porta=0.04,
        render=BASS_RENDER,
    ))
    add_lfo(s, [("f1.cutoff", 8.0)], scene=True, shape="sine", rate=0.15, trig="freerun")
    return s


# -------------------------------------------------------------------------------------------
# Pulses and ticking
# -------------------------------------------------------------------------------------------

PULSE_RENDER = dict(note=60, hold=4.0, tail=1.5, window=0.0)


def speed_rate(base, f):
    order = ["1/1", "1/2", "1/4", "1/8", "1/16", "1/32"]
    k = order.index(base) + {0.5: -1, 1: 0, 2: 1}[f.get("speed", 1)]
    return order[max(0, min(len(order) - 1, k))]


def pulse_watch(f):
    s = retrigger(patch(
        oscs=[sine(octave=2, level=-6.0), fm2(0.6, 7, octave=2, level=-10.0)],
        noise=-4.0, noise_color=0.6,
        fconfig="serial1",
        f1=dict(type="bp12", cutoff=4200, res=0.45, kt=0.0),
        f2=dict(type="hp12", cutoff=1500, res=0.0, kt=0.0),
        amp=dict(a=0.0005, d=0.018, s=0.0, r=0.02),
        fx=[hall(1.4, 0.2)],
        sends=[-12.0, None],
        render=PULSE_RENDER,
    ))
    step_lfo(s, speed_rate("1/8", f), [1.0, 0.7] * 8, targets=[("f1.cutoff", 5.0)])
    return s


def pulse_clock(f):
    s = retrigger(patch(
        oscs=[sine(octave=1), sine(octave=2, level=-12.0)],
        noise=-12.0,
        f1=dict(type="lp12", cutoff=6000, res=0.1, kt=0.3),
        amp=dict(a=0.0005, d=0.06, s=0.0, r=0.05),
        fx=[hall(1.8, 0.25)],
        sends=[-12.0, None],
        render=PULSE_RENDER,
    ))
    # tick-tock: every other step a fourth lower
    step_lfo(s, speed_rate("1/4", f), [1.0, 0.0] * 8, targets=[("pitch", 5.0)])
    return s


def pulse_sequence(f):
    s = retrigger(patch(
        oscs=[saw(unison=2, detune=0.08), square(octave=-1, level=-6.0, width=0.3)],
        f1=dict(type="lp24", sub=1, cutoff=600, res=0.45, env=30, kt=0.4),
        feg=dict(a=0.0, d=0.1, s=0.0, r=0.1),
        amp=dict(a=0.002, d=0.12, s=0.05, r=0.12),
        fx=[echo("1/8d", fb=0.35), hall(2.5, 0.4)],
        sends=[-10.0, -9.0],
        render=PULSE_RENDER,
    ))
    step_lfo(s, speed_rate("1/16", f), [1.0, 0.3, 0.6, 0.3, 0.9, 0.3, 0.6, 0.45] * 2,
             targets=[("f1.cutoff", 20.0)])
    return s


def pulse_heartbeat(f):
    s = retrigger(patch(
        oscs=[sine(octave=-2), sine(octave=-1, level=-10.0)],
        f1=dict(type="lp12", cutoff=300, res=0.1, kt=0.2),
        feg=dict(a=0.0, d=0.07, s=0.0, r=0.05),
        amp=dict(a=0.001, d=0.18, s=0.0, r=0.15),
        ws=dict(type="soft", drive=6.0),
        fx=[hall(2.0, 0.3)],
        sends=[-14.0, None],
        render=dict(note=48, hold=4.0, tail=1.5, window=0.0),
    ))
    s["mods"].append(("filtereg", "pitch", 9.0))
    rate = speed_rate("1/16", f)
    step_lfo(s, rate, [1.0, 0, 0.75, 0] + [0] * 12, trig=[0, 2])
    return s


def pulse_morse(f):
    s = retrigger(patch(
        oscs=[square(octave=1, width=0.5), sine(octave=2, level=-10.0)],
        f1=dict(type="bp12", cutoff=1800, res=0.35, kt=0.5),
        amp=dict(a=0.001, d=0.07, s=0.0, r=0.06),
        play="mono",
        fx=[echo("1/8", fb=0.3), hall(2.2, 0.3)],
        sends=[-12.0, -10.0],
        render=PULSE_RENDER,
    ))
    step_lfo(s, speed_rate("1/16", f), [1] * 16,
             trig=[0, 1, 2, 4, 6, 7, 10, 12, 13])
    return s


# -------------------------------------------------------------------------------------------
# Shepard tones and risers
# -------------------------------------------------------------------------------------------

RISER_RENDER = dict(note=60, hold=8.0, tail=3.0)


def shepard(f, up=True):
    period = 10.0 / f.get("speed", 1.0)
    s = patch(
        oscs=[saw(octave=-1, unison=2, detune=0.06), saw(unison=2, detune=0.06),
              saw(octave=1, unison=2, detune=0.06)],
        f1=dict(type="lp12", cutoff=2600, res=0.1, kt=0.0),
        amp=dict(a=0.8, d=1.0, s=1.0, r=2.5),
        fx=[ensemble("A1", mix=0.3), hall(5.0, 0.7)],
        sends=[-6.0, None],
        render=dict(note=60, hold=period * 1.2, tail=3.0),
    )
    # One falling sawtooth LFO moves all three octaves together; the bottom voice fades in and
    # the top voice fades out over the cycle, so the stack sounds the same as it wraps.
    sign = -1.0 if up else 1.0
    targets = [(f"osc{k}.pitch", sign * 12.0) for k in (1, 2, 3)]
    if up:
        targets += [("level_o1", -1.0), ("level_o3", 1.0)]
    else:
        targets += [("level_o1", 1.0), ("level_o3", -1.0)]
    add_lfo(s, targets, scene=True, shape="saw", rate=1.0 / period, uni=True, trig="freerun")
    # The fading voices start from silence or full level; a level of None is -inf dB
    s["oscs"][0]["level"] = 0.0 if up else None
    s["oscs"][2]["level"] = None if up else 0.0
    return s


def shepard_up(f):
    return shepard(f, True)


def shepard_down(f):
    return shepard(f, False)


def riser_noise(f):
    t = 8.0 / f.get("speed", 1.0)
    s = patch(
        oscs=[saw(unison=4, detune=0.3, level=-8.0)],
        noise=0.0, noise_color=0.2,
        f1=dict(type="bp12", cutoff=250, res=0.4, kt=0.0),
        amp=dict(a=t * 0.6, d=1.0, s=1.0, r=1.5, a_s=2),
        fx=[hall(4.5, 0.6)],
        sends=[-6.0, None],
        render=dict(note=60, hold=t, tail=3.0),
    )
    add_lfo(s, [("f1.cutoff", 60.0), ("pitch", 12.0)], shape="env", attack=t, decay=1.0,
            sustain=1.0)
    return s


def riser_tension(f):
    t = 7.0 / f.get("speed", 1.0)
    s = patch(
        oscs=[saw(unison=2, detune=0.1), saw(pitch=1.0, unison=2, detune=0.1),
              saw(pitch=2.0, unison=2, detune=0.1)],
        f1=dict(type="lp24", sub=1, cutoff=500, res=0.25, kt=0.3),
        amp=dict(a=t * 0.4, d=1.0, s=1.0, r=1.5, a_s=2),
        fx=[hall(4.0, 0.55)],
        sends=[-7.0, None],
        render=dict(note=60, hold=t, tail=3.0),
    )
    add_lfo(s, [("pitch", 12.0), ("f1.cutoff", 40.0)], shape="env", attack=t, decay=1.0,
            sustain=1.0)
    vibrato(s, depth=0.3, rate=6.0, delay=0.2, attack=t)
    return s


def riser_strings(f):
    t = 6.0 / f.get("speed", 1.0)
    s = patch(
        oscs=[wt("vsco/String/SUS Violin Trem.wav", unison=2, detune=0.08),
              wt("vsco/String/SUS Cello.wav", octave=-1, level=-4.0)],
        f1=dict(type="lp12", cutoff=1200, res=0.05, kt=0.4),
        amp=dict(a=t * 0.7, d=1.0, s=1.0, r=1.5, a_s=2),
        fx=[hall(4.0, 0.6)],
        sends=[-6.0, None],
        render=dict(note=60, hold=t, tail=3.0),
    )
    add_lfo(s, [("pitch", 12.0), ("f1.cutoff", 30.0)], shape="env", attack=t, decay=1.0,
            sustain=1.0)
    return s


# -------------------------------------------------------------------------------------------
# Organs
# -------------------------------------------------------------------------------------------


def organ_tesseract(f):
    return patch(
        oscs=[wt("vsco/Keys/Organ Open.wav", unison=2, detune=0.03),
              sine(octave=-1, level=-3.0), sine(octave=1, level=-9.0)],
        f1=dict(type="lp12", cutoff=6000, res=0.0, kt=0.3),
        amp=dict(a=0.08, d=1.0, s=1.0, r=1.8),
        fx=[hall(7.0, 0.85, pre=0.05, hf=0.4)],
        sends=[-4.0, None],
    )


def organ_cathedral(f):
    return patch(
        oscs=[wt("vsco/Keys/Organ Open.wav", unison=2, detune=0.04),
              wt("Waldorf/Organs.wt", octave=1, level=-6.0),
              square(octave=-1, width=0.25, level=-10.0)],
        f1=dict(type="lp12", cutoff=7000, kt=0.3),
        amp=dict(a=0.06, d=1.0, s=1.0, r=2.0),
        fx=[hall(8.0, 0.9, pre=0.06, hf=0.35)],
        sends=[-4.0, None],
    )


def organ_pedal(f):
    return patch(
        oscs=[wt("vsco/Keys/Organ Pedal.wav", octave=-1), sine(octave=-2, level=-4.0),
              wt("vsco/Keys/Organ Pedal Quiet.wav", level=-8.0)],
        f1=dict(type="lp12", cutoff=1500, kt=0.3),
        amp=dict(a=0.1, d=1.0, s=1.0, r=2.0),
        fx=[hall(7.0, 0.85)],
        sends=[-5.0, None],
        render=dict(note=36, hold=3.0, tail=3.0),
    )


def organ_reed(f):
    return patch(
        oscs=[wt("vsco/Keys/Organ Quiet Dirty.wav", unison=2, detune=0.04),
              square(width=0.15, level=-10.0)],
        f1=dict(type="lp12", cutoff=3500, res=0.1, kt=0.4),
        amp=dict(a=0.05, d=1.0, s=1.0, r=1.2),
        fx=[hall(5.0, 0.7)],
        sends=[-6.0, None],
    )


def organ_spectral(f):
    s = patch(
        oscs=[wt("layzer/Organ/Organ 7.wt", unison=3, detune=0.05),
              wt("layzer/Organ/Organ 12.wt", octave=-1, level=-5.0)],
        f1=dict(type="lp12", cutoff=5000, kt=0.3),
        amp=dict(a=0.15, d=1.0, s=1.0, r=2.0),
        fx=[chorus("A1", depth=0.2, rate=0.25, mix=0.3), hall(7.0, 0.8)],
        sends=[-5.0, None],
    )
    add_lfo(s, [("osc1.p0", 0.4)], scene=True, shape="tri", rate=0.05, trig="freerun")
    return s


# -------------------------------------------------------------------------------------------
# Choirs and voices
# -------------------------------------------------------------------------------------------


def choir_ah(f):
    s = patch(
        oscs=[wt("Sampled/Vocal Choir 1.wt", unison=3, detune=0.1),
              wt("Sampled/Vocal Ah 1.wt", octave=-1, level=-4.0, unison=2, detune=0.08)],
        f1=dict(type="lp12", cutoff=4000, res=0.05, kt=0.3),
        amp=dict(a=0.35, d=1.0, s=1.0, r=1.2),
        fx=[ensemble("A1", mix=0.3), hall(4.5, 0.6)],
        sends=[-5.0, None],
    )
    vibrato(s, depth=0.1, rate=4.8, delay=0.5, attack=1.0)
    expressive(s, cutoff=12.0)
    return s


def choir_oh(f):
    s = patch(
        oscs=[wt("Sampled/Vocal O.wt", unison=3, detune=0.09),
              wt("Sampled/Vocal O Formant 2.wt", level=-4.0, unison=2, detune=0.1)],
        f1=dict(type="lp12", cutoff=3200, res=0.05, kt=0.3),
        amp=dict(a=0.4, d=1.0, s=1.0, r=1.3),
        fx=[ensemble("A1", mix=0.3), hall(4.5, 0.6)],
        sends=[-5.0, None],
    )
    vibrato(s, depth=0.1, rate=4.6, delay=0.5, attack=1.0)
    expressive(s, cutoff=12.0)
    return s


def choir_lament(f):
    s = patch(
        oscs=[wt("Sampled/Vocal Ah 2.wt"), wt("Sampled/Vocal Ah 1.wt", level=-8.0, pitch=0.08)],
        f1=dict(type="lp12", cutoff=3800, res=0.05, kt=0.4),
        amp=dict(a=0.18, d=1.0, s=1.0, r=0.9),
        play="mono", porta=0.09,
        fx=[echo("1/4", fb=0.3, hc=3000), hall(5.0, 0.65)],
        sends=[-5.0, -10.0],
    )
    vibrato(s, depth=0.3, rate=5.4, delay=0.4, attack=0.6)
    expressive(s, cutoff=12.0)
    return s


def choir_male(f):
    s = patch(
        oscs=[wt("Waldorf/Male AhPG.wt", octave=-1, unison=3, detune=0.08),
              wt("Sampled/Vocal Choir 2.wt", octave=-1, level=-4.0, unison=2, detune=0.1)],
        f1=dict(type="lp12", cutoff=2000, res=0.05, kt=0.3),
        amp=dict(a=0.3, d=1.0, s=1.0, r=1.2),
        fx=[hall(5.0, 0.65)],
        sends=[-5.0, None],
        render=dict(note=48, hold=3.0, tail=2.5),
    )
    vibrato(s, depth=0.08, rate=4.5, delay=0.6, attack=1.0)
    expressive(s, cutoff=12.0)
    return s


def choir_synth(f):
    s = patch(
        oscs=[wt("Sampled/Choir Formant.wt", unison=4, detune=0.12),
              wt("Generated/Several Formants.wt", level=-8.0, morph=0.4)],
        f1=dict(type="lp12", cutoff=4500, res=0.1, kt=0.3),
        amp=dict(a=0.3, d=1.0, s=1.0, r=1.4),
        fx=[ensemble("A1", mix=0.5), hall(4.5, 0.6)],
        sends=[-6.0, None],
    )
    return s


# -------------------------------------------------------------------------------------------
# Percussion
# -------------------------------------------------------------------------------------------

PERC_RENDER = dict(note=48, hold=0.5, tail=2.5, mode="short")


def drum(oscs, noise, cutoff, decay, pitch_env, pitch_decay, extra=None, noise_color=0.0,
         ftype="lp12", res=0.1):
    s = patch(
        oscs=oscs,
        noise=noise, noise_color=noise_color, noise_route="both",
        f1=dict(type=ftype, cutoff=cutoff, res=res, env=24, kt=0.2),
        feg=dict(a=0.0, d=pitch_decay, s=0.0, r=pitch_decay),
        amp=dict(a=0.001, d=decay, s=0.0, r=decay),
        fx=[hall(2.8, 0.5)],
        sends=[-10.0, None],
        velsense=-20.0,
        render=PERC_RENDER,
    )
    s["mods"].append(("filtereg", "pitch", pitch_env))
    s["mods"].append(("velocity", "f1.cutoff", 18.0))
    if extra:
        s["fx"].insert(0, extra)
    return s


def perc_taiko(f):
    return drum([sine(octave=-2), sine(octave=-1, level=-12.0)], -6.0, 900, 1.1, 14.0, 0.12,
                extra=dist("A1", drive=4.0, gain=-4.0, tone=6000))


def perc_war(f):
    s = drum([sine(octave=-3), sine(octave=-2, level=-8.0)], -8.0, 500, 1.6, 18.0, 0.16,
             noise_color=-0.4)
    s["render"] = dict(PERC_RENDER, note=48)
    return s


def perc_frame(f):
    return drum([sine(octave=-1), sine(octave=0, level=-14.0)], -4.0, 1500, 0.5, 9.0, 0.06,
                ftype="lp12", res=0.2)


def perc_anvil(f):
    s = drum([fm2(0.85, 7, m2=0.4, r2=11, offset=3.0, octave=1),
              sine(octave=2, pitch=3.3, level=-8.0)], -14.0, 9000, 0.9, 1.0, 0.01,
             noise_color=0.6)
    s["highpass"] = 400
    s["fx"].insert(0, ringmod("A1", freq=78, mix=0.25))
    return s


def perc_timpani(f):
    return drum([wt("vsco/Misc/ENV Timpani.wav", octave=-1), sine(octave=-2, level=-6.0)],
                -18.0, 1200, 2.2, 2.0, 0.08)


def perc_metal(f):
    s = drum([wt("vsco/Misc/SUS Metal.wav"), fm2(0.7, 5, offset=7.0, octave=1, level=-6.0)],
             -10.0, 7000, 1.4, 3.0, 0.05, noise_color=0.4)
    s["fx"].insert(0, comb("A1", center=310, fb=0.55, mix=0.35))
    return s


# -------------------------------------------------------------------------------------------
# Hits and impacts
# -------------------------------------------------------------------------------------------

HIT_RENDER = dict(note=48, hold=0.5, tail=3.0, mode="short")


def hit_boom(f):
    s = patch(
        oscs=[sine(octave=-3), sine(octave=-2, level=-6.0)],
        noise=-10.0, noise_color=-0.3, noise_route="both",
        f1=dict(type="lp12", cutoff=400, res=0.1, env=30, kt=0.0),
        feg=dict(a=0.0, d=0.25, s=0.0, r=0.25),
        amp=dict(a=0.001, d=2.5, s=0.0, r=2.5),
        ws=dict(type="soft", drive=6.0),
        fx=[hall(4.0, 0.6)],
        sends=[-9.0, None], velsense=-20.0,
        render=HIT_RENDER,
    )
    s["mods"].append(("filtereg", "pitch", 24.0))
    return s


def hit_orchestral(f):
    s = patch(
        oscs=[wt("Waldorf/StringHit.wt", unison=2, detune=0.08),
              wt("vsco/Brass/STAC Tenor Trombone Splat.wav", octave=-1, level=-3.0),
              saw(octave=-1, level=-8.0)],
        f1=dict(type="lp12", cutoff=3000, res=0.05, env=20, kt=0.3),
        feg=dict(a=0.0, d=0.4, s=0.0, r=0.3),
        amp=dict(a=0.002, d=0.7, s=0.0, r=0.7),
        fx=[hall(3.5, 0.6)],
        sends=[-7.0, None], velsense=-20.0,
        render=HIT_RENDER,
    )
    return s


def hit_downer(f):
    s = patch(
        oscs=[saw(octave=-1, unison=3, detune=0.15), sine(octave=-2, level=-3.0)],
        f1=dict(type="lp24", sub=1, cutoff=1800, res=0.2, env=-24, kt=0.3),
        feg=dict(a=0.0, d=1.5, s=0.0, r=1.0),
        amp=dict(a=0.002, d=2.0, s=0.0, r=2.0),
        fx=[hall(4.0, 0.6)],
        sends=[-8.0, None], velsense=-20.0,
        render=dict(HIT_RENDER, hold=1.5),
    )
    add_lfo(s, [("pitch", -24.0)], shape="env", attack=1.6, decay=1.0, sustain=1.0)
    return s


def hit_metal(f):
    s = patch(
        oscs=[fm2(0.9, 9, m2=0.5, r2=13, offset=4.0), sine(octave=-2, level=-4.0)],
        noise=-6.0, noise_color=0.3, noise_route="both",
        f1=dict(type="lp12", cutoff=8000, res=0.1, env=0, kt=0.0),
        feg=dict(a=0.0, d=0.15, s=0.0, r=0.2),
        amp=dict(a=0.001, d=1.5, s=0.0, r=1.5),
        fx=[comb("A1", center=180, fb=0.6, mix=0.35), hall(4.0, 0.6)],
        sends=[-8.0, None], velsense=-20.0,
        render=HIT_RENDER,
    )
    s["mods"].append(("filtereg", "pitch", 12.0))
    return s


def hit_reverse(f):
    return patch(
        oscs=[saw(unison=4, detune=0.2), saw(octave=-1, level=-4.0, unison=2, detune=0.15)],
        noise=-8.0,
        f1=dict(type="lp24", sub=1, cutoff=300, res=0.2, env=50, kt=0.3),
        feg=dict(a=2.0, d=0.1, s=1.0, r=0.03, a_s=2),
        amp=dict(a=2.0, d=1.0, s=1.0, r=0.02, a_s=2),
        fx=[hall(4.0, 0.6)],
        sends=[-8.0, None],
        render=dict(note=48, hold=2.2, tail=2.0),
    )


# -------------------------------------------------------------------------------------------
# Pianos and keys
# -------------------------------------------------------------------------------------------

KEYS_RENDER = dict(note=60, hold=1.5, tail=2.5, mode="short")


def keys_felt(f):
    return patch(
        oscs=[wt("Sampled/Piano Dark.wt"), wt("Sampled/Piano 1.wt", level=-8.0)],
        f1=dict(type="lp12", cutoff=1500, res=0.0, env=14, kt=0.5),
        feg=dict(a=0.0, d=1.5, s=0.2, r=0.5),
        amp=dict(a=0.004, d=3.5, s=0.0, r=0.5),
        fx=[hall(3.5, 0.55)],
        sends=[-8.0, None], velsense=-24.0,
        mods=[("velocity", "f1.cutoff", 20.0)],
        render=KEYS_RENDER,
    )


def keys_prepared(f):
    return patch(
        oscs=[wt("vsco/Keys/Upright Piano Dirty.wav"),
              fm2(0.4, 5, offset=2.5, level=-14.0)],
        f1=dict(type="lp12", cutoff=3500, res=0.1, env=10, kt=0.5),
        feg=dict(a=0.0, d=0.8, s=0.0, r=0.4),
        amp=dict(a=0.002, d=1.8, s=0.0, r=0.4),
        fx=[comb("A1", center=330, fb=0.4, mix=0.25), hall(2.5, 0.45)],
        sends=[-9.0, None], velsense=-22.0,
        render=KEYS_RENDER,
    )


def keys_celesta(f):
    return patch(
        oscs=[wt("Sampled/Music Box 1.wt", octave=1), sine(octave=2, level=-12.0)],
        f1=dict(type="lp12", cutoff=9000, kt=0.3),
        amp=dict(a=0.001, d=2.0, s=0.0, r=1.2),
        fx=[hall(3.5, 0.55)],
        sends=[-7.0, None], velsense=-20.0,
        render=KEYS_RENDER,
    )


def keys_upright(f):
    return patch(
        oscs=[wt("vsco/Keys/Upright Piano Soft.wav"), wt("vsco/Keys/Upright Piano Medium.wav",
                                                         level=-6.0)],
        f1=dict(type="lp12", cutoff=4000, env=8, kt=0.5),
        feg=dict(a=0.0, d=1.5, s=0.3, r=0.5),
        amp=dict(a=0.002, d=4.0, s=0.0, r=0.4),
        fx=[tape("A1", drive=0.5, sat=0.4), hall(2.8, 0.45)],
        sends=[-9.0, None], velsense=-22.0,
        mods=[("velocity", "f1.cutoff", 14.0)],
        render=KEYS_RENDER,
    )


# -------------------------------------------------------------------------------------------
# Plucks and mallets
# -------------------------------------------------------------------------------------------


def pluck_marimba(f):
    return patch(
        oscs=[wt("Sampled/Mallets 1.wt"), sine(octave=-1, level=-8.0), fm2(0.25, 4, level=-14.0)],
        f1=dict(type="lp12", cutoff=4500, env=12, kt=0.5),
        feg=dict(a=0.0, d=0.2, s=0.0, r=0.2),
        amp=dict(a=0.001, d=0.7, s=0.0, r=0.5),
        fx=[hall(2.2, 0.4)],
        sends=[-10.0, None], velsense=-20.0,
        mods=[("velocity", "f1.cutoff", 14.0)],
        render=KEYS_RENDER,
    )


def pluck_cimbalom(f):
    return patch(
        oscs=[string(exciter=0, exc=0.9, d1=0.97, d2=0.965, det=0.15, stiff=0.2),
              wt("Sampled/Banjo 1.wt", level=-12.0)],
        f1=dict(type="lp12", cutoff=6000, env=10, kt=0.4),
        feg=dict(a=0.0, d=0.4, s=0.0, r=0.3),
        amp=dict(a=0.001, d=2.2, s=0.0, r=1.0),
        highpass=150,
        fx=[hall(2.5, 0.45)],
        sends=[-10.0, None], velsense=-20.0,
        render=KEYS_RENDER,
    )


def pluck_harp(f):
    return patch(
        oscs=[wt("Sampled/Harp 1.wt"), string(exciter=1, exc=0.6, d1=0.98, d2=0.97, det=0.05,
                                                level=-8.0)],
        f1=dict(type="lp12", cutoff=5000, env=8, kt=0.4),
        feg=dict(a=0.0, d=0.6, s=0.0, r=0.5),
        amp=dict(a=0.001, d=2.5, s=0.0, r=1.5),
        fx=[hall(3.5, 0.55)],
        sends=[-8.0, None], velsense=-20.0,
        render=KEYS_RENDER,
    )


def pluck_kalimba(f):
    return patch(
        oscs=[wt("Sampled/Mallets 2.wt"), fm2(0.3, 3, octave=1, level=-12.0)],
        f1=dict(type="lp12", cutoff=5000, env=10, kt=0.4),
        feg=dict(a=0.0, d=0.15, s=0.0, r=0.2),
        amp=dict(a=0.001, d=1.2, s=0.0, r=0.8),
        fx=[echo("1/8d", fb=0.3), hall(2.5, 0.45)],
        sends=[-10.0, -12.0], velsense=-20.0,
        render=KEYS_RENDER,
    )


# -------------------------------------------------------------------------------------------
# Ethnic winds
# -------------------------------------------------------------------------------------------

WIND_RENDER = dict(note=60, hold=2.0, tail=2.0)


def wind(oscs, cutoff, porta, vib, noise=None, f2=None, **kw):
    s = patch(
        oscs=oscs,
        f1=dict(type="lp12", cutoff=cutoff, res=0.15, kt=0.4),
        amp=dict(a=0.08, d=1.0, s=1.0, r=0.5),
        play="mono", porta=porta,
        fx=[echo("1/4", fb=0.25, hc=3500), hall(4.0, 0.6)],
        sends=[-6.0, -12.0],
        render=WIND_RENDER,
        **kw,
    )
    if noise is not None:
        s.update(noise=noise, noise_color=0.3, noise_route="both")
    if f2:
        s.update(f2=f2, fconfig="serial1")
    vibrato(s, **vib)
    expressive(s, cutoff=10.0, vca=3.0)
    return s


def wind_duduk(f):
    return wind([wt("vsco/Woodwinds/SUS Oboe.wav", octave=-1), saw(octave=-1, level=-16.0)],
                1600, 0.09, dict(depth=0.22, rate=5.0, delay=0.5, attack=0.6), noise=-26.0,
                f2=dict(type="bp12", cutoff=900, res=0.15, kt=0.4))


def wind_shakuhachi(f):
    s = wind([wt("vsco/Woodwinds/SUS Flute Soft.wav", octave=-1)], 2500, 0.06,
             dict(depth=0.25, rate=4.5, delay=0.6, attack=0.8), noise=-14.0)
    # bend up into each note
    add_lfo(s, [("pitch", -1.0)], shape="env", attack=0.0001, decay=0.25, sustain=0.0)
    return s


def wind_panpipes(f):
    s = wind([wt("vsco/Woodwinds/SUS Flute.wav"), sine(octave=1, level=-14.0)], 4500, 0.0,
             dict(depth=0.12, rate=5.2, delay=0.4, attack=0.5), noise=-10.0,
             f2=dict(type="bp12", cutoff=2500, res=0.3, env=24, kt=0.4))
    # the breath goes through its own bandpass with a fast envelope, for the chiff
    s["noise_route"] = "f2"
    s["fconfig"] = "dual1"
    s["feg"] = dict(a=0.0, d=0.07, s=0.0, r=0.1)
    s["play"] = "poly"
    return s


def wind_erhu(f):
    return wind([string(exciter=7, exc=0.5, d1=0.995, d2=0.99, det=0.08, stiff=0.1),
                 wt("vsco/String/SUS Violin.wav", level=-10.0)], 3000, 0.12,
                dict(depth=0.35, rate=5.8, delay=0.25, attack=0.4),
                f2=dict(type="bp12", cutoff=1200, res=0.2, kt=0.5))


def wind_bansuri(f):
    return wind([wt("vsco/Woodwinds/SUS Flute High 1.wav"), sine(level=-14.0)], 5000, 0.07,
                dict(depth=0.2, rate=5.0, delay=0.4, attack=0.6), noise=-14.0)


# -------------------------------------------------------------------------------------------
# Guitars
# -------------------------------------------------------------------------------------------


def gtr_slide(f):
    s = patch(
        oscs=[wt("Sampled/Guitar Electric 1.wt"), wt("Sampled/Guitar Electric 2.wt", level=-6.0,
                                                      pitch=0.05)],
        f1=dict(type="lp12", cutoff=3200, res=0.15, env=8, kt=0.4),
        feg=dict(a=0.0, d=0.8, s=0.4, r=0.5),
        amp=dict(a=0.003, d=3.0, s=0.4, r=0.6),
        ws=dict(type="soft", drive=4.0),
        play="mono", porta=0.18,
        fx=[echo("1/4", fb=0.3), hall(2.6, 0.45)],
        sends=[-9.0, -10.0],
        render=dict(note=60, hold=1.5, tail=2.0),
    )
    vibrato(s, depth=0.25, rate=5.0, delay=0.5, attack=0.6)
    return s


def gtr_power(f):
    return patch(
        oscs=[wt("Sampled/Guitar Electric 2.wt", octave=-1), wt("Sampled/Guitar Mid.wt",
                                                                 octave=-1, pitch=7.0,
                                                                 level=-5.0),
              saw(octave=-2, level=-10.0)],
        f1=dict(type="lp12", cutoff=2500, res=0.1, kt=0.3),
        amp=dict(a=0.01, d=1.5, s=0.85, r=0.8),
        ws=dict(type="heavy_fuzz", drive=6.0),
        fx=[dist("A1", drive=10.0, gain=-10.0, tone=4500), hall(3.0, 0.5)],
        sends=[-10.0, None],
        render=dict(note=48, hold=2.0, tail=2.0),
    )


def gtr_twang(f):
    return patch(
        oscs=[wt("Sampled/Guitar Steel.wt"), string(exciter=0, exc=0.7, d1=0.985, d2=0.98,
                                                     det=0.06, level=-8.0)],
        f1=dict(type="lp12", cutoff=5000, env=10, kt=0.4),
        feg=dict(a=0.0, d=0.5, s=0.0, r=0.4),
        amp=dict(a=0.001, d=2.0, s=0.0, r=0.8),
        fx=[echo("1/16", fb=0.15, hc=3000), hall(1.6, 0.25)],
        sends=[-10.0, -6.0],
        render=KEYS_RENDER,
    )


def gtr_pedal_steel(f):
    s = patch(
        oscs=[wt("Sampled/Guitar Steel.wt", unison=2, detune=0.05),
              wt("Sampled/Guitar High.wt", level=-8.0)],
        f1=dict(type="lp12", cutoff=3500, res=0.05, kt=0.4),
        amp=dict(a=0.45, d=1.0, s=1.0, r=1.2, a_s=2),
        porta=0.25,
        fx=[chorus("A1", depth=0.2, rate=0.4, mix=0.3), hall(4.5, 0.6)],
        sends=[-6.0, None],
        render=dict(note=60, hold=2.5, tail=2.5),
    )
    vibrato(s, depth=0.1, rate=4.5, delay=0.8, attack=1.0)
    return s


# -------------------------------------------------------------------------------------------
# 80s synths
# -------------------------------------------------------------------------------------------


def eighties_brass(f):
    return patch(
        oscs=[saw(unison=2, detune=0.12), saw(pitch=0.1, level=-2.0), square(octave=-1,
                                                                              width=0.4,
                                                                              level=-8.0)],
        f1=dict(type="ob24", sub=3, cutoff=850, res=0.15, env=36, kt=0.4),
        feg=dict(a=0.06, d=0.5, s=0.4, r=0.4, analog=True),
        amp=dict(a=0.02, d=0.8, s=0.9, r=0.4, analog=True),
        fx=[chorus("A1", depth=0.3, rate=0.5, mix=0.4), hall(3.0, 0.5)],
        sends=[-9.0, None],
        mods=[("velocity", "f1.cutoff", 12.0)],
    )


def eighties_cs80(f):
    s = patch(
        oscs=[wt("Generated/Saw CS-80.wt", unison=2, detune=0.1), saw(level=-6.0, pitch=0.07)],
        f1=dict(type="lp12", cutoff=1500, res=0.3, env=20, kt=0.4),
        feg=dict(a=1.2, d=2.0, s=0.6, r=1.5),
        amp=dict(a=0.25, d=1.0, s=1.0, r=1.8, analog=True),
        fx=[chorus("A1", depth=0.25, rate=0.3, mix=0.35), hall(6.0, 0.75)],
        sends=[-5.0, None],
        mods=[("aftertouch", "f1.cutoff", 18.0), ("aftertouch", "pitch", 0.5)],
    )
    expressive(s, cutoff=16.0, vca=0.0)
    vibrato(s, depth=0.12, rate=5.5, delay=0.8, attack=1.0)
    return s


def eighties_fairlight(f):
    return patch(
        oscs=[wt("Sampled/Vocal Choir 2.wt", unison=2, detune=0.1),
              dict(type="alias", p={0: 1, 4: 6.0}, level=-20.0)],
        f1=dict(type="lp12", cutoff=5000, res=0.05, kt=0.3),
        amp=dict(a=0.25, d=1.0, s=1.0, r=1.2),
        fx=[tape("A1", drive=0.7, sat=0.5, degrade=0.3), hall(4.0, 0.6)],
        sends=[-6.0, None],
    )


def eighties_dx_bell(f):
    return patch(
        oscs=[fm2(0.45, 14, m2=0.2, r2=3, offset=1.2), sine(octave=1, level=-14.0)],
        f1=dict(type="lp12", cutoff=9000, kt=0.3),
        amp=dict(a=0.001, d=3.0, s=0.0, r=1.5),
        fx=[chorus("A1", depth=0.25, rate=0.4, mix=0.3), hall(3.5, 0.55)],
        sends=[-8.0, None], velsense=-20.0,
        mods=[("velocity", "osc1.p0", 0.2)],
        render=KEYS_RENDER,
    )


def eighties_pluck(f):
    s = patch(
        oscs=[fm2(0.35, 2, m2=0.15, r2=5), saw(level=-12.0)],
        f1=dict(type="lp24", sub=1, cutoff=1200, res=0.2, env=36, kt=0.4),
        feg=dict(a=0.0, d=0.25, s=0.0, r=0.2),
        amp=dict(a=0.001, d=0.6, s=0.0, r=0.4),
        fx=[echo("1/8d", fb=0.35), hall(2.5, 0.45)],
        sends=[-10.0, -9.0], velsense=-18.0,
        render=KEYS_RENDER,
    )
    s["mods"].append(("filtereg", "osc1.p0", 0.3))
    return s


# -------------------------------------------------------------------------------------------
# Atmospheres
# -------------------------------------------------------------------------------------------

ATMOS_RENDER = dict(note=60, hold=5.0, tail=3.0, target=-18.0)


def atmos_wind(f):
    s = patch(
        oscs=[sine(octave=-1, level=-14.0)],
        noise=0.0, noise_color=-0.3,
        f1=dict(type="bp12", cutoff=700, res=0.6, kt=0.0),
        amp=dict(a=1.5, d=1.0, s=1.0, r=3.0, a_s=2),
        fx=[hall(6.0, 0.75)],
        sends=[-6.0, None],
        render=ATMOS_RENDER,
    )
    add_lfo(s, [("f1.cutoff", 18.0)], scene=True, shape="noise", rate=0.4, trig="freerun")
    add_lfo(s, [("vca_level", -6.0)], scene=True, shape="noise", rate=0.25, trig="freerun")
    return s


def atmos_dark_matter(f):
    s = patch(
        oscs=[wt("Waldorf/Chaosweep.wt", unison=2, detune=0.1),
              wt("Waldorf/DRAIN.wt", octave=-1, level=-5.0)],
        f1=dict(type="lp24", sub=1, cutoff=1400, res=0.2, kt=0.3),
        amp=dict(a=2.0, d=1.0, s=1.0, r=3.5, a_s=2),
        drift=0.4,
        fx=[hall(7.0, 0.8)],
        sends=[-5.0, None],
        render=ATMOS_RENDER,
    )
    add_lfo(s, [("osc1.p0", 0.6), ("osc2.p0", 0.4)], scene=True, shape="tri", rate=0.04,
            trig="freerun")
    return s


def atmos_black_hole(f):
    s = patch(
        oscs=[wt("vsco/Keys/Organ Quiet 1.wav", octave=-2, unison=2, detune=0.03),
              sine(octave=-1, pitch=0.15, level=-3.0), sine(octave=-1, pitch=7.0, level=-9.0)],
        f1=dict(type="lp12", cutoff=900, kt=0.3),
        amp=dict(a=2.5, d=1.0, s=1.0, r=4.0, a_s=2),
        fx=[hall(10.0, 0.95, hf=0.5)],
        sends=[-4.0, None],
        render=dict(ATMOS_RENDER, note=48),
    )
    return s


def atmos_shimmer(f):
    s = patch(
        oscs=[wt("Generated/Sine Windowed Octaves.wt", octave=1, unison=3, detune=0.08),
              wt("Sampled/Music Box 2.wt", octave=1, level=-8.0)],
        f1=dict(type="lp12", cutoff=8000, kt=0.3),
        highpass=250,
        amp=dict(a=2.0, d=1.0, s=1.0, r=4.0, a_s=2),
        fx=[chorus("A1", depth=0.3, rate=0.2, mix=0.4), hall(9.0, 0.9, mod=0.8)],
        sends=[-4.0, None],
        render=ATMOS_RENDER,
    )
    add_lfo(s, [("osc1.p0", 0.5)], scene=True, shape="sine", rate=0.08, trig="freerun")
    return s


def atmos_ocean(f):
    s = patch(
        oscs=[sine(octave=-3), saw(octave=-2, level=-14.0)],
        noise=-8.0, noise_color=-0.7,
        f1=dict(type="lp24", sub=1, cutoff=200, res=0.2, kt=0.2),
        amp=dict(a=2.5, d=1.0, s=1.0, r=4.0, a_s=2),
        fx=[hall(8.0, 0.85)],
        sends=[-6.0, None],
        render=dict(ATMOS_RENDER, note=48),
    )
    add_lfo(s, [("f1.cutoff", 12.0), ("vca_level", -5.0)], scene=True, shape="sine",
            rate=0.08, trig="freerun")
    return s


def atmos_glacial(f):
    s = patch(
        oscs=[wt("layzer/Morphs/Morph 12.wt", unison=3, detune=0.08), saw(level=-14.0)],
        f1=dict(type="lp12", cutoff=2500, res=0.1, kt=0.3),
        amp=dict(a=2.0, d=1.0, s=1.0, r=3.5, a_s=2),
        fx=[hall(8.0, 0.85)],
        sends=[-5.0, None],
        render=ATMOS_RENDER,
    )
    add_lfo(s, [("osc1.p0", 0.7), ("f1.cutoff", 8.0)], scene=True, shape="sine", rate=0.03,
            trig="freerun")
    return s


# -------------------------------------------------------------------------------------------
# Tension and FX
# -------------------------------------------------------------------------------------------


def tension_razor(f):
    t = 10.0 * f.get("time", 1.0)
    s = patch(
        oscs=[wt("vsco/String/SUS Cello.wav", unison=2, detune=0.05), saw(level=-14.0)],
        noise=-16.0, noise_color=0.5, noise_route="f2",
        fconfig="dual1",
        f1=dict(type="lp12", cutoff=2500, res=0.2, kt=0.4),
        f2=dict(type="bp12", cutoff=3200, res=0.5, kt=0.4),
        ws=dict(type="asym", drive=5.0),
        amp=dict(a=0.8, d=1.0, s=1.0, r=2.0, a_s=2),
        fx=[hall(5.0, 0.65)],
        sends=[-6.0, None],
        render=dict(note=48, hold=t, tail=3.0),
    )
    # a single note that keeps rising, slowly, as long as it is held
    add_lfo(s, [("pitch", 5.0)], shape="env", attack=t, decay=1.0, sustain=1.0)
    add_lfo(s, [("f2.cutoff", 10.0)], shape="noise", rate=3.0)
    return s


def tension_cluster(f):
    s = patch(
        oscs=[wt("vsco/String/SUS Violin High.wav", octave=1), wt("vsco/String/SUS Violin High.wav",
                                                                  octave=1, pitch=1.0),
              wt("vsco/String/SUS Violin Trem.wav", octave=1, pitch=2.0)],
        f1=dict(type="lp12", cutoff=7000, kt=0.3),
        highpass=600,
        amp=dict(a=1.0, d=1.0, s=1.0, r=2.0, a_s=2),
        fx=[hall(5.0, 0.65)],
        sends=[-6.0, None],
        render=dict(note=60, hold=4.0, tail=3.0),
    )
    add_lfo(s, [("vca_level", -6.0)], shape="sine", rate=7.0)
    return s


def tension_rumble(f):
    s = patch(
        oscs=[sine(octave=-3), saw(octave=-3, level=-10.0)],
        noise=-6.0, noise_color=-0.8,
        f1=dict(type="lp24", sub=1, cutoff=120, res=0.3, kt=0.0),
        ws=dict(type="soft", drive=8.0),
        amp=dict(a=1.5, d=1.0, s=1.0, r=3.0, a_s=2),
        fx=[hall(6.0, 0.7)],
        sends=[-10.0, None],
        render=dict(note=48, hold=4.0, tail=3.0),
    )
    add_lfo(s, [("vca_level", -8.0), ("f1.cutoff", 8.0)], scene=True, shape="noise", rate=0.6,
            trig="freerun")
    return s


def tension_scrape(f):
    s = patch(
        oscs=[wt("vsco/Misc/ENV Brick Scrape.wav"), wt("vsco/Misc/SUS Metal Mush.wav",
                                                       level=-6.0)],
        noise=-10.0, noise_color=0.2,
        f1=dict(type="bp12", cutoff=1500, res=0.35, kt=0.3),
        amp=dict(a=0.4, d=1.0, s=1.0, r=2.0),
        fx=[comb("A1", center=140, fb=0.7, mix=0.4, noise=0.1), hall(5.0, 0.65)],
        sends=[-6.0, None],
        render=dict(note=48, hold=4.0, tail=3.0),
    )
    add_lfo(s, [("f1.cutoff", 18.0)], shape="noise", rate=1.5)
    return s


def tension_whale(f):
    s = patch(
        oscs=[sine(octave=-1, fb=0.2), saw(octave=-1, level=-12.0)],
        f1=dict(type="lp12", cutoff=1200, res=0.4, kt=0.3),
        amp=dict(a=1.0, d=1.0, s=1.0, r=3.0, a_s=2),
        fx=[comb("A1", center=110, fb=0.5, mix=0.3), hall(9.0, 0.9)],
        sends=[-4.0, None],
        render=dict(note=48, hold=4.0, tail=3.0),
    )
    add_lfo(s, [("pitch", 7.0), ("f1.cutoff", 10.0)], shape="noise", rate=0.35)
    return s


# -------------------------------------------------------------------------------------------
# Leads and themes
# -------------------------------------------------------------------------------------------

LEAD_RENDER = dict(note=60, hold=2.0, tail=2.0)


def lead_hero(f):
    s = patch(
        oscs=[saw(unison=3, detune=0.1), square(octave=-1, level=-6.0)],
        f1=dict(type="lp24", sub=1, cutoff=2500, res=0.15, env=18, kt=0.4),
        feg=dict(a=0.02, d=0.8, s=0.6, r=0.4),
        amp=dict(a=0.01, d=1.0, s=1.0, r=0.4),
        play="mono", porta=0.06,
        fx=[echo("1/8d", fb=0.3), hall(3.5, 0.55)],
        sends=[-8.0, -10.0],
        render=LEAD_RENDER,
    )
    vibrato(s, depth=0.2, rate=5.5, delay=0.5, attack=0.6)
    expressive(s, cutoff=14.0, vca=0.0)
    return s


def lead_cello(f):
    s = patch(
        oscs=[wt("vsco/String/SUS Cello Vibrato.wav"), wt("vsco/String/SUS Cello.wav",
                                                          level=-8.0, pitch=0.05)],
        f1=dict(type="lp12", cutoff=2600, res=0.05, kt=0.4),
        amp=dict(a=0.12, d=1.0, s=1.0, r=0.8, analog=True),
        play="mono", porta=0.08,
        fx=[hall(4.0, 0.6)],
        sends=[-6.0, None],
        render=dict(LEAD_RENDER, note=48),
    )
    expressive(s)
    return s


def lead_horn(f):
    s = patch(
        oscs=[wt("vsco/Brass/SUS French Horn Loud.wav"), saw(level=-9.0)],
        f1=dict(type="lp12", cutoff=1800, res=0.1, env=16, kt=0.5),
        feg=dict(a=0.1, d=1.0, s=0.6, r=0.6),
        amp=dict(a=0.06, d=1.0, s=1.0, r=0.7, analog=True),
        play="mono", porta=0.05,
        fx=[hall(4.0, 0.6)],
        sends=[-6.0, None],
        render=LEAD_RENDER,
    )
    vibrato(s, depth=0.12, rate=5.0, delay=0.6, attack=0.8)
    expressive(s)
    return s


def lead_glide(f):
    s = patch(
        oscs=[wt("Basic/Sine To Sawtooth.wt", morph=0.3), sine(octave=-1, level=-10.0)],
        f1=dict(type="lp12", cutoff=3500, res=0.05, kt=0.4),
        amp=dict(a=0.05, d=1.0, s=1.0, r=0.8),
        play="mono", porta=0.15,
        fx=[echo("1/4", fb=0.35), hall(4.5, 0.6)],
        sends=[-6.0, -9.0],
        render=LEAD_RENDER,
    )
    vibrato(s, depth=0.2, rate=5.0, delay=0.5, attack=0.8)
    s["mods"].append(("modwheel", "osc1.p0", 0.6))
    return s


# -------------------------------------------------------------------------------------------
# The catalogue
# -------------------------------------------------------------------------------------------


def base(name, builder, note, tags=()):
    return dict(name=name, builder=builder, note=note, tags=list(tags))


CATEGORIES = [
    dict(folder="Braams", render=dict(note=40, hold=3.0, tail=3.0), tags=["Brass", "Impact"],
         bases=[
             base("Tectonic Braam", braam_tectonic,
                  "Massive low brass blast in the vein of the Inception (2010) score: tuba "
                  "samples under detuned saws through a ladder filter that blooms open."),
             base("Dream Collapse", braam_collapse,
                  "Slow brass cluster whose pitch sags as it is held, after the slowed-down "
                  "music that marks the dream levels of Inception."),
             base("Leviathan Horn", braam_leviathan,
                  "Trombone section and square sub with asymmetric drive, for the big low "
                  "brass statements of Inception and The Dark Knight Rises."),
             base("Abyss Brass", braam_abyss,
                  "Dark tuba and horn swell through a diode ladder, for slow-building low "
                  "brass under hybrid scores."),
             base("Foghorn Fifths", braam_foghorn,
                  "Power-fifth saw stack with fuzz, the open-fifth low brass sound of modern "
                  "trailer-style cues."),
         ],
         variants=[variant(""), variant("Wide", [m_wide], note="Extra unison and chorus."),
                   variant("Distorted", [m_heavy], note="Heavy fuzz and distortion."),
                   variant("Swell", [m_swell], note="Slow crescendo attack."),
                   variant("Sub", [m_sub], note="Adds a sine sub an octave down.")]),
    dict(folder="Horns & Brass", render=dict(note=55, hold=2.5, tail=2.5), tags=["Brass"],
         bases=[
             base("Heroic Horns", horns_heroic,
                  "Loud French horn section with delayed vibrato, for the soaring horn themes "
                  "of Gladiator, Pirates of the Caribbean and Man of Steel."),
             base("Horn Choir", horns_choir,
                  "Soft, warm horn chorale in two octaves, for noble, hymn-like brass."),
             base("Muted Horns", horns_muted,
                  "Stopped horns with a Harmon-muted trumpet underneath, for tense, distant "
                  "brass."),
             base("Trombone Section", horns_trombones,
                  "Driving trombones, the backbone of the brass ostinatos in The Rock and "
                  "Pirates of the Caribbean."),
             base("Tuba Foundation", horns_tuba,
                  "Tuba with a sine sub, for low brass pedals."),
         ],
         variants=[variant("Soft", [m_soft], note="Softer attack and darker tone."),
                   variant("Forte", [m_forte], note="Brighter, louder, with exciter."),
                   variant("Wide", [m_wide], note="Wider section with chorus."),
                   variant("Dark Hall", [m_dark, m_distant], note="Darker, further back."),
                   variant("Synth Layer", [m_synth_layer],
                           note="Doubled with a supersaw, the hybrid brass-plus-synth "
                                "sound of Zimmer's 2000s scores.")]),
    dict(folder="String Ostinatos", render=dict(note=48, hold=2.0, tail=1.5),
         tags=["Strings", "Ostinato"],
         bases=[
             base("Spiccato Engine", ost_spiccato,
                  "Short bouncing violins and violas: play the rhythm yourself, as in the "
                  "string ostinatos of Pirates of the Caribbean and Sherlock Holmes."),
             base("Celli Sixteenths", ost_celli,
                  "Hold a chord: the cellos repeat in tempo-synced 16ths with accents, the "
                  "driving string machine of Batman Begins and Inception."),
             base("Gallop Basses", ost_gallop,
                  "Galloping basses in a tempo-synced 'da-da-dum' rhythm, as in the battle "
                  "cues of Gladiator and Pirates of the Caribbean."),
             base("Viola Runner", ost_viola_runner,
                  "Triplet-feel viola ostinato synced to tempo; hold chords and let it run."),
             base("Hybrid String Pulse", ost_hybrid,
                  "Supersaw doubled with violins and pulsing in 8ths, the hybrid synth-string "
                  "ostinato of The Dark Knight and Inception."),
             base("Two Note Marcato", ost_marcato,
                  "Heavy marcato cellos and basses for played motifs, like the two-note "
                  "figure that defines The Dark Knight's Batman theme."),
         ],
         variants=[variant(""), variant("Tight", [m_tight], note="Shorter and drier."),
                   variant("Wide", [m_wide], note="Wider section with chorus."),
                   variant("Driven", [m_driven], note="Saturated, aggressive bowing."),
                   variant("Dark", [m_dark], note="Darker tone.")]),
    dict(folder="String Swells", render=dict(note=55, hold=3.0, tail=2.5), tags=["Strings"],
         bases=[
             base("Cello Section", str_cello,
                  "Legato cello section with vibrato, the warm, central cello sound of "
                  "Gladiator, The Thin Red Line and Interstellar."),
             base("Violin Ensemble", str_violins,
                  "Layered violin section in three registers, for sustained high strings."),
             base("Tremolo Strings", str_tremolo,
                  "Tremolo violins over tremolo basses, for suspense beds."),
             base("Low String Swell", str_low_swell,
                  "Basses and cellos swelling from nothing, as in the slow-building openings "
                  "of The Dark Knight trilogy."),
             base("Synth Strings 89", str_synth,
                  "Polysynth string ensemble in the style of the all-electronic late-1980s "
                  "scores such as Rain Man and Driving Miss Daisy."),
         ],
         variants=[variant(""), variant("Slow Swell", [m_swell], note="Slow crescendo."),
                   variant("Wide Hall", [m_wide, m_huge], note="Wider, in a bigger hall."),
                   variant("Dark", [m_dark], note="Darker tone."),
                   variant("Shimmer", [m_shimmer], note="Octave-up layer, long reverb.")]),
    dict(folder="Drones", render=dict(note=48, hold=5.0, tail=3.0, target=-18.0),
         tags=["Drone", "Texture"],
         bases=[
             base("Cello Drone", drone_cello,
                  "Low cello and bass drone with slow filter drift, the sustained low "
                  "strings under 12 Years a Slave and Dune."),
             base("Sub Tension Bed", drone_sub,
                  "Sub-bass bed with slow pulsing level, felt more than heard, for the "
                  "low-frequency pressure of Dunkirk and Dune."),
             base("Throat Drone", drone_throat,
                  "Formant-filtered vocal drone two octaves down, after the processed, "
                  "otherworldly voices of Dune (2021)."),
             base("Bagpipe Drone", drone_bagpipe,
                  "Reedy chanter over fifth drones, after the bagpipes in Dune (2021)."),
             base("Organ Pedal Drone", drone_pedal,
                  "Pipe organ pedal drone, the low end of the Interstellar organ."),
         ],
         variants=[variant(""), variant("Evolving", [m_evolving], note="Slow movement."),
                   variant("Distant", [m_distant], note="Further back, more reverb."),
                   variant("Gritty", [m_gritty], note="Tape saturation and grit."),
                   variant("Wide", [m_wide], note="Wider with chorus.")]),
    dict(folder="Synth Basses", render=BASS_RENDER, tags=["Bass", "Synth"],
         bases=[
             base("Vigilante Growl", bass_growl,
                  "Fuzzed saw and square bass through a ladder filter, the distorted synth "
                  "bass of The Dark Knight."),
             base("Modular Bass", bass_moog,
                  "Saw and square through a classic ladder with snappy envelope, after "
                  "Zimmer's large Moog modular."),
             base("Pulse Ostinato Bass", bass_ostinato,
                  "Hold a note: 16th-note bass pulse synced to tempo, the electronic "
                  "ostinato bass of Batman Begins and Inception."),
             base("Sub Pressure", bass_sub,
                  "Driven sine sub for low-end weight under everything."),
             base("FM Brass Bass", bass_fm,
                  "FM bass with envelope-swept brightness, for 80s-style punch."),
             base("Reese Tension", bass_reese,
                  "Detuned saw bass with a slowly moving filter and phaser, for menace."),
         ],
         variants=[variant(""), variant("Tight", [m_tight], note="Shorter and drier."),
                   variant("Driven", [m_driven], note="More drive."),
                   variant("Wide", [m_wide], note="Wider unison."),
                   variant("Dark", [m_dark], note="Darker filter.")]),
    dict(folder="Pulses & Ticking", render=PULSE_RENDER, tags=["Rhythmic", "Tempo-Synced"],
         bases=[
             base("Pocket Watch", pulse_watch,
                  "Hold a note: a tempo-synced ticking watch, after the ticking that drives "
                  "the whole of Dunkirk."),
             base("Tick Tock", pulse_clock,
                  "Two-pitch clock tick in quarter notes, for countdowns."),
             base("Sequenced Pulse", pulse_sequence,
                  "Accented 16th-note analogue sequence, in the style of Crimson Tide, Black "
                  "Rain and the late-80s scores."),
             base("Heartbeat", pulse_heartbeat,
                  "Lub-dub sub heartbeat synced to tempo."),
             base("Morse Code", pulse_morse,
                  "Irregular synced bleeps through a bandpass, for signals and tension."),
         ],
         variants=[variant(""), variant("Fast", flags=dict(speed=2), note="Twice as fast."),
                   variant("Slow", flags=dict(speed=0.5), note="Half as fast."),
                   variant("Filtered", [m_filtered], note="Slow filter sweep."),
                   variant("Wide", [m_wide], note="Wider with chorus.")]),
    dict(folder="Shepard & Risers", render=RISER_RENDER, tags=["Riser", "Tension"],
         bases=[
             base("Shepard Ascent", shepard_up,
                  "A true Shepard tone that seems to rise forever, the illusion that builds "
                  "the tension in Dunkirk."),
             base("Shepard Descent", shepard_down,
                  "A Shepard tone that falls forever."),
             base("Noise Riser", riser_noise,
                  "Filtered noise and saws rising over eight seconds."),
             base("Cluster Riser", riser_tension,
                  "Semitone saw cluster gliding up an octave with growing vibrato."),
             base("String Riser", riser_strings,
                  "Tremolo violins and cellos gliding up an octave."),
         ],
         variants=[variant(""), variant("Fast", flags=dict(speed=2), note="Twice as fast."),
                   variant("Slow", flags=dict(speed=0.5), note="Half as fast."),
                   variant("Dark", [m_dark], note="Darker tone."),
                   variant("Wide", [m_wide], note="Wider with chorus.")]),
    dict(folder="Organs", render=dict(note=60, hold=3.0, tail=4.0), tags=["Organ"],
         bases=[
             base("Tesseract Organ", organ_tesseract,
                  "Open diapason with 16' and 4' sine ranks in a long cathedral reverb, after "
                  "the Temple Church organ of Interstellar."),
             base("Cathedral Full Organ", organ_cathedral,
                  "Full organ with a reed rank, for the big Interstellar organ climaxes."),
             base("Pedal Organ", organ_pedal,
                  "Deep pedal division with a 32'-style sine."),
             base("Reed Organ", organ_reed,
                  "Breathy reed organ, intimate and slightly dirty."),
             base("Spectral Organ", organ_spectral,
                  "Slowly morphing wavetable organ, between pipe organ and synth."),
         ],
         variants=[variant(""), variant("Full", [m_full], note="Adds an octave rank."),
                   variant("Distant", [m_distant], note="Further back."),
                   variant("Swell", [m_swell], note="Swell-box crescendo."),
                   variant("Tremulant", [m_tremulant], note="Tremulant on.")]),
    dict(folder="Choirs & Voices", render=dict(note=60, hold=3.0, tail=3.0), tags=["Choir"],
         bases=[
             base("Epic Choir Ah", choir_ah,
                  "Big mixed choir on 'ah', for the choral climaxes of Gladiator, The Da Vinci "
                  "Code and Angels & Demons."),
             base("Choir Oh", choir_oh,
                  "Rounded choir on 'oh', softer and darker."),
             base("Lament Voice", choir_lament,
                  "Solo, mournful voice with portamento and vibrato, after the vocals of "
                  "Gladiator and Black Hawk Down."),
             base("Male Chant", choir_male,
                  "Low male choir, for chant-like ostinatos and ritual."),
             base("Synth Choir 88", choir_synth,
                  "Formant synth choir in the style of the late-80s sampler choirs."),
         ],
         variants=[variant(""), variant("Soft", [m_soft], note="Softer and darker."),
                   variant("Wide", [m_wide], note="Wider ensemble."),
                   variant("Dark", [m_dark], note="Darker tone."),
                   variant("Ethereal", [m_ethereal], note="Airy, with shimmer.")]),
    dict(folder="Percussion", render=PERC_RENDER, tags=["Percussion", "Drums"],
         bases=[
             base("Taiko Ensemble", perc_taiko,
                  "Big synthesized taiko with a pitch drop, after the taiko drums of The Last "
                  "Samurai and the drum circle of Man of Steel."),
             base("War Drum", perc_war,
                  "Huge, low war drum, as in the battle cues of Gladiator."),
             base("Frame Drum", perc_frame,
                  "Tight frame drum for ostinato patterns."),
             base("Anvil Strike", perc_anvil,
                  "Inharmonic FM anvil with ring modulation, for the clanging metal accents "
                  "of hybrid action scores."),
             base("Timpani Hit", perc_timpani,
                  "Timpani with a sine body, for orchestral weight."),
             base("Metal Clang", perc_metal,
                  "Industrial metal hit through a comb filter, for hybrid percussion."),
         ],
         variants=[variant(""), variant("Tight", [m_tight], note="Shorter and drier."),
                   variant("Huge", [m_huge], note="Bigger room and sub."),
                   variant("Distorted", [m_driven], note="Saturated."),
                   variant("Room", [m_room], note="Short room reverb.")]),
    dict(folder="Hits & Impacts", render=HIT_RENDER, tags=["Impact", "FX"],
         bases=[
             base("Sub Boom", hit_boom,
                  "Sine boom with a pitch drop and a noise burst, the trailer-style impacts "
                  "of hybrid scores."),
             base("Orchestral Hit", hit_orchestral,
                  "String and brass stab for big downbeats."),
             base("Downer", hit_downer,
                  "Saws falling two octaves, the pitch-drop transition of modern trailers."),
             base("Metal Impact", hit_metal,
                  "Inharmonic metallic impact with noise and comb resonance."),
             base("Reverse Swell", hit_reverse,
                  "Swells in and stops dead when released: time it to land on the downbeat."),
         ],
         variants=[variant(""), variant("Huge", [m_huge], note="Bigger room and sub."),
                   variant("Tight", [m_tight], note="Shorter and drier."),
                   variant("Distorted", [m_driven], note="Saturated."),
                   variant("Dark", [m_dark], note="Darker tone.")]),
    dict(folder="Pianos & Keys", render=KEYS_RENDER, tags=["Keys", "Piano"],
         bases=[
             base("Felt Piano", keys_felt,
                  "Soft, felted piano, the quiet piano of Interstellar and the 'Time' theme "
                  "of Inception."),
             base("Prepared Piano", keys_prepared,
                  "Detuned, prepared upright with metallic overtones, after the broken piano "
                  "of Sherlock Holmes."),
             base("Celesta Box", keys_celesta,
                  "Celesta and music box, for wonder and childhood."),
             base("Upright Memory", keys_upright,
                  "Soft upright piano through tape, for memory and nostalgia."),
         ],
         variants=[variant(""), variant("Intimate", [m_intimate], note="Close and soft."),
                   variant("Distant", [m_distant], note="Further back."),
                   variant("Detuned", [m_detuned], note="Drifting, out of tune."),
                   variant("Lo-Fi", [m_lofi], note="Worn tape with wow.")]),
    dict(folder="Plucks & Mallets", render=KEYS_RENDER, tags=["Plucked", "Mallets"],
         bases=[
             base("Orff Marimba", pluck_marimba,
                  "Marimba in the style of True Romance's theme, which is built on Orff's "
                  "Gassenhauer."),
             base("Cimbalom", pluck_cimbalom,
                  "Struck, bright strings with banjo colour, after the cimbalom of Sherlock "
                  "Holmes."),
             base("Harp Glimmer", pluck_harp,
                  "Concert harp for glissandi and arpeggios."),
             base("Kalimba Echo", pluck_kalimba,
                  "Kalimba-like mallet with a dotted-8th echo."),
         ],
         variants=[variant(""), variant("Bright", [m_bright], note="Brighter."),
                   variant("Wide", [m_wide], note="Wider with chorus."),
                   variant("Delay", [m_echo], note="Dotted-8th delay."),
                   variant("Dark", [m_dark], note="Darker tone.")]),
    dict(folder="Ethnic Winds", render=WIND_RENDER, tags=["Winds", "Solo"],
         bases=[
             base("Duduk Lament", wind_duduk,
                  "Reedy, mournful double-reed solo, after the duduk of Gladiator."),
             base("Shakuhachi Breath", wind_shakuhachi,
                  "Breathy bamboo flute that bends into each note, after the shakuhachi of "
                  "The Last Samurai."),
             base("Pan Pipes", wind_panpipes,
                  "Chiffy pan pipes, after the synthesized ethnic flutes of Rain Man."),
             base("Erhu Lead", wind_erhu,
                  "Bowed two-string fiddle with expressive slides, after the erhu of Kung Fu "
                  "Panda."),
             base("Bansuri Air", wind_bansuri,
                  "High, airy bamboo flute."),
         ],
         variants=[variant(""), variant("Breathy", [m_breathy], note="More breath noise."),
                   variant("Distant", [m_distant], note="Further back."),
                   variant("Vibrato", [m_vibrato], note="Deeper vibrato."),
                   variant("Dark", [m_dark], note="Darker tone.")]),
    dict(folder="Guitars", render=dict(note=60, hold=1.5, tail=2.0), tags=["Guitar"],
         bases=[
             base("Desert Slide", gtr_slide,
                  "Slide electric guitar with glide and vibrato, after the slide guitar of "
                  "Thelma & Louise."),
             base("Distorted Power Drone", gtr_power,
                  "Fuzzed power-fifth guitar drone, for menace in hybrid scores."),
             base("Spaghetti Twang", gtr_twang,
                  "Twangy steel string with slapback, after the spaghetti-western score of "
                  "Rango."),
             base("Pedal Steel Swell", gtr_pedal_steel,
                  "Volume-swelled steel guitar with glide, after the pedal steel guitars of "
                  "Man of Steel."),
         ],
         variants=[variant(""), variant("Wide", [m_wide], note="Wider with chorus."),
                   variant("Driven", [m_driven], note="More drive."),
                   variant("Echo", [m_echo], note="Dotted-8th delay."),
                   variant("Dark", [m_dark], note="Darker tone.")]),
    dict(folder="80s Synths", render=dict(note=60, hold=2.0, tail=2.0), tags=["Synth", "80s"],
         bases=[
             base("Polysynth Brass", eighties_brass,
                  "Fat polysynth brass, in the style of Days of Thunder and Black Rain."),
             base("CS-80 Blade Pad", eighties_cs80,
                  "Yamaha CS-80-style brass pad with aftertouch and mod wheel, after the "
                  "CS-80 of Blade Runner 2049."),
             base("Sampler Choir", eighties_fairlight,
                  "Lo-fi early-sampler choir, after the Fairlight-era sound of Zimmer's 1980s "
                  "work."),
             base("FM Bell", eighties_dx_bell,
                  "Glassy FM bell, the digital keys of the late 80s."),
             base("Digital Pluck", eighties_pluck,
                  "FM pluck with a filter snap and dotted-8th echo."),
         ],
         variants=[variant(""), variant("Wide", [m_wide], note="Wider with chorus."),
                   variant("Bright", [m_bright], note="Brighter."),
                   variant("Dark", [m_dark], note="Darker tone."),
                   variant("Detuned", [m_detuned], note="Drifting, detuned.")]),
    dict(folder="Atmospheres", render=ATMOS_RENDER, tags=["Atmosphere", "Texture"],
         bases=[
             base("Desert Wind", atmos_wind,
                  "Resonant filtered noise gusting at random, for the deserts of Dune."),
             base("Dark Matter", atmos_dark_matter,
                  "Slowly morphing, drifting wavetables, for the unknown."),
             base("Black Hole Hum", atmos_black_hole,
                  "Low organ and beating sines in a vast reverb, after the cosmic stillness of "
                  "Interstellar."),
             base("Frozen Shimmer", atmos_shimmer,
                  "Bell-like windowed sines high up in a long, modulated reverb."),
             base("Ocean Floor", atmos_ocean,
                  "Deep sub and dark noise breathing slowly."),
             base("Glacial Pad", atmos_glacial,
                  "Very slow wavetable pad with a moving filter."),
         ],
         variants=[variant(""), variant("Evolving", [m_evolving], note="More movement."),
                   variant("Distant", [m_distant], note="Further back."),
                   variant("Dark", [m_dark], note="Darker tone."),
                   variant("Wide", [m_wide], note="Wider with chorus.")]),
    dict(folder="Tension FX", render=dict(note=48, hold=4.0, tail=3.0), tags=["Tension", "FX"],
         bases=[
             base("Razor Cello", tension_razor,
                  "A single scraped cello note that keeps rising for as long as it is held, "
                  "after the Joker's theme in The Dark Knight."),
             base("Cluster Screech", tension_cluster,
                  "High violin semitone cluster with tremolo."),
             base("Sub Rumble", tension_rumble,
                  "Driven sub and dark noise rumbling at random."),
             base("Metallic Scrape", tension_scrape,
                  "Scraped metal through a comb filter."),
             base("Whale Glide", tension_whale,
                  "Wandering, gliding resonant tone in a huge space."),
         ],
         variants=[variant(""), variant("Slow", [m_slow], flags=dict(time=2.0),
                                        note="Slower to arrive and to change."),
                   variant("Intense", [m_intense], note="Driven and brighter."),
                   variant("Distant", [m_distant], note="Further back."),
                   variant("Wide", [m_wide], note="Wider with chorus.")]),
    dict(folder="Leads & Themes", render=LEAD_RENDER, tags=["Lead", "Solo"],
         bases=[
             base("Hero Synth Lead", lead_hero,
                  "Mono saw lead with glide, for synth themes over the orchestra."),
             base("Solo Cello Theme", lead_cello,
                  "Expressive solo cello for themes, after the cello writing of 12 Years a "
                  "Slave."),
             base("Synth Horn Lead", lead_horn,
                  "Solo horn reinforced with a saw, for heroic melodies."),
             base("Glide Lead", lead_glide,
                  "Simple, gliding sine-saw lead; the mod wheel adds edge."),
         ],
         variants=[variant(""), variant("Soft", [m_soft], note="Softer and darker."),
                   variant("Wide", [m_wide], note="Wider unison."),
                   variant("Bright", [m_bright], note="Brighter."),
                   variant("Dark", [m_dark], note="Darker tone.")]),
]


def presets():
    """Yield every preset: folder, name, spec, comment, tags, render config."""
    for cat in CATEGORIES:
        for b in cat["bases"]:
            for v in cat["variants"]:
                spec = b["builder"](v["flags"])
                for m in v["mods"]:
                    m(spec)
                name = f"{b['name']} {v['label']}".strip()
                comment = b["note"] + (f" {v['label']}: {v['note']}" if v["note"] else "")
                render = dict(cat["render"])
                render.update(spec.pop("render", {}))
                tags = ["Cinematic"] + cat["tags"] + b["tags"]
                yield cat["folder"], name, spec, comment, tags, render
