#!/usr/bin/env python3
"""
Generate the Film Scoring Hans patches into resources/data/patches_3rdparty/Film Scoring Hans.

This needs the surgepy module: configure Surge with -DSURGE_BUILD_PYTHON_BINDINGS=ON, build the
surgepy target, and put the build's src/surge-python directory on PYTHONPATH.

Every patch is built through the engine and saved, then reloaded from disk, rendered and
level-matched, saved again, and finally reloaded and rendered once more to check that what is
on disk plays as intended.
"""

import argparse
import multiprocessing
import os
import shutil
import sys
import tempfile
from pathlib import Path

import numpy as np
import surgepy

import fsh_engine as E
import fsh_recipes as R

OUT = E.DATA / "patches_3rdparty" / "Film Scoring Hans"
LISTING = Path(__file__).resolve().parent / "PRESETS.md"

MACROS = {0: "Brightness", 1: "Attack", 2: "Space"}

# Loudness targets: the average once a held note has settled, or the loudest 50 ms of a short
# sound. A category can override them with a 'target' in its render settings.
TARGET = {"rms": -16.0, "short": -10.0}
CEILING = -3.0
CHORD_CEILING = -3.5
# How far a reload may drift from the level it was trimmed to. Drift, noise and oscillator
# phases move short, sparse sounds by a few dB between renders; a broken reload (a lost
# wavetable or step sequence) moves them by far more.
TOLERANCE = {"rms": 6.0, "short": 6.0}


def add_macros(spec):
    if spec.get("f1"):
        spec["mods"].append(("macro1", "f1.cutoff", 24.0))
    spec["mods"].append(("macro2", "amp.a", 4.0))
    if R.get_fx(spec, "S1"):
        spec["mods"].append(("macro3", "send1", 0.6))


def load(path):
    s = surgepy.createSurge(E.SAMPLE_RATE)
    s.loadPatch(str(path))
    for _ in range(8):
        s.process()
    return s


def measure(path, render, notes=None, repeats=2):
    """
    Render a patch freshly loaded from disk, so free-running LFOs always start alike. Drift,
    noise and free-running oscillator phases vary between renders, so take the mean loudness
    and the worst peak of a few.
    """
    runs = []
    for _ in range(repeats):
        buf = E.render(load(path), notes or [render["note"]], render["hold"], render["tail"])
        runs.append(E.analyse(buf, render["hold"], render.get("window", 0.5)))
    out = dict(runs[0])
    for key in ("rms", "short"):
        out[key] = float(np.sqrt(np.mean([r[key] ** 2 for r in runs])))
    out["peak"] = max(r["peak"] for r in runs)
    out["finite"] = all(r["finite"] for r in runs)
    return out


def loudness(a, mode):
    return E.db(a[mode])


def apply_gain(s, gain):
    """Trim with the global volume, and lift the VCA if the patch needs more than 0 dB."""
    p = s.getPatch()
    vol = p["volume"]
    vca = p["scene"][0]["vca_level"]
    new = s.getParamVal(vol) + gain
    extra = max(0.0, new)
    s.setParamVal(vol, max(-48.0, min(0.0, new)))
    if extra:
        s.setParamVal(vca, min(48.0, s.getParamVal(vca) + extra))
    for _ in range(8):
        s.process()


def make(folder, name, spec, comment, tags, render, tmp):
    add_macros(spec)

    b = E.PatchBuilder()
    b.build(spec)
    raw = tmp / "raw.fxp"
    b.s.savePatch(str(raw))

    staged = tmp / "staged.fxp"
    E.write_patch(raw, staged, name, folder, R.AUTHOR, comment, tags, steps=spec["steps"],
                  macros=MACROS)

    mode = render.get("mode", "rms")
    poly = spec.get("play", "poly") == "poly"

    target = render.get("target", TARGET[mode])
    root = render["note"]
    chord_notes = [root, root + 7, root + 12, root + 16]

    # Trim, then measure again: drive and compression after the VCA mean a trim doesn't
    # always move the output by the same amount
    current = staged
    total = 0.0
    warning = None
    for it in range(6):
        a = measure(current, render)
        if not a["finite"] or a["peak"] < 1e-4:
            raise RuntimeError(f"silent or unstable: {a}")
        want = target - loudness(a, mode)
        gain = min(want, CEILING - E.db(a["peak"]))
        if poly:
            chord = measure(current, render, chord_notes)
            gain = min(gain, CHORD_CEILING - E.db(chord["peak"]))
        if abs(gain) < 1.0:
            break
        s = load(current)
        apply_gain(s, gain)
        total += gain
        current = tmp / f"leveled{it}.fxp"
        s.savePatch(str(current))
    else:
        # drive after the VCA can stop a trim from getting all the way there
        a = measure(current, render)
        warning = f"settled at {loudness(a, mode):.1f} dB, aiming for {target:.1f} dB"

    done = tmp / "final.fxp"
    E.write_patch(current, done, name, folder, R.AUTHOR, comment, tags, macros=MACROS)

    # Check the finished file: it plays, doesn't clip, and sounds as it did when it was leveled
    final = measure(done, render)
    level = loudness(final, mode)
    peak = final["peak"]
    if poly:
        peak = max(peak, measure(done, render, chord_notes)["peak"])
    if not final["finite"] or E.db(peak) > 0.0:
        raise RuntimeError(f"clips or is unstable on reload: peak {E.db(peak):.1f} dB")
    if abs(level - loudness(a, mode)) > TOLERANCE[mode]:
        raise RuntimeError(f"reloads at {level:.1f} dB, leveled at {loudness(a, mode):.1f} dB")

    dest = OUT / folder / f"{name}.fxp"
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(done, dest)

    return dict(folder=folder, name=name, comment=comment, mode=mode, level=level,
                peak=E.db(peak), gain=total, warning=warning)


def write_listing(presets):
    lines = ["# Film Scoring Hans presets", "",
             f"{len(presets)} Surge XT patches for hybrid orchestral film scoring, generated by "
             "`generate.py`. They are original patches modelled on instruments and techniques "
             "documented in Hans Zimmer's scores; the notes say which.", "",
             "All patches have three macros: **Brightness** (filter cutoff), **Attack** (amp "
             "envelope attack) and **Space** (reverb send). On sustained orchestral sounds the "
             "mod wheel works as dynamics. The tempo-synced patches (most of String Ostinatos, "
             "Pulse Ostinato Bass and all of Pulses & Ticking) play their rhythm for as long as "
             "a note is held."]
    folder = None
    for p in presets:
        if p[0] != folder:
            folder = p[0]
            lines += ["", f"## {folder}", "", "| Preset | Notes |", "|---|---|"]
        lines.append(f"| {p[1]} | {p[3]} |")
    LISTING.write_text("\n".join(lines) + "\n", encoding="utf-8")


PRESETS = None
TMP = None


def worker_init(parent):
    global PRESETS, TMP
    PRESETS = list(R.presets())
    TMP = Path(tempfile.mkdtemp(dir=parent))
    # Each worker gets its own Surge user folder, so their favourites databases don't contend
    os.environ["HOME"] = str(TMP)


def run(i):
    folder, name, spec, comment, tags, render = PRESETS[i]
    try:
        return i, make(folder, name, spec, comment, tags, render, TMP), None
    except Exception as e:  # report every failure, not just the first
        return i, None, f"{folder}/{name}: {e}"


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--only", help="only build presets whose 'folder/name' contains this")
    ap.add_argument("--keep", action="store_true", help="don't clear the output folder first")
    ap.add_argument("--jobs", type=int, default=os.cpu_count(), help="worker processes")
    ap.add_argument("--listing", action="store_true", help="only rewrite PRESETS.md")
    args = ap.parse_args()

    all_presets = list(R.presets())
    names = [f"{p[0]}/{p[1]}" for p in all_presets]
    assert len(set(names)) == len(names), "duplicate preset names"
    wanted = [i for i, n in enumerate(names) if not args.only or args.only in n]

    if args.listing:
        write_listing(all_presets)
        return

    if not args.only and not args.keep and OUT.exists():
        shutil.rmtree(OUT)

    results = {}
    failures = []
    with tempfile.TemporaryDirectory() as parent, \
            multiprocessing.Pool(args.jobs, initializer=worker_init, initargs=(parent,)) as pool:
        for i, r, err in pool.imap_unordered(run, wanted):
            if err:
                failures.append(err)
                print(f"FAILED {err}", file=sys.stderr)
                continue
            results[i] = r
            print(f"[{len(results):3d}/{len(wanted)}] {r['folder']}/{r['name']}: "
                  f"{r['level']:.1f} dB {r['mode']}, peak {r['peak']:.1f} dB, "
                  f"trim {r['gain']:+.1f} dB" + (f" ({r['warning']})" if r["warning"] else ""),
                  flush=True)

    if not args.only:
        write_listing(all_presets)

    print(f"\n{len(results)} presets written to {OUT}")
    if failures:
        print(f"{len(failures)} failed:", *sorted(failures), sep="\n  ", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
