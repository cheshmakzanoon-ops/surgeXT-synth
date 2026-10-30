# Aurora skin tools

Aurora is Surge XT's default skin: a night sky with soft aurora light behind translucent glass
panels, and a colour spectrum that flows across the synth, with each section in its own colour:

| Section                          | Colour          |
|----------------------------------|-----------------|
| Oscillators, mixer               | cyan            |
| Bend depth, play mode, scene     | sky blue        |
| FM routing                       | azure           |
| Filter configuration and filters | violet → pink   |
| Scene output                     | magenta         |
| Keytrack, waveshaper             | pink            |
| Filter EG / Amp EG               | rose / coral    |
| Modulators, LFOs, MSEG           | gold            |
| Effects                          | mint            |

Interactive states share one vocabulary everywhere: **pink** means selected, **cyan** means in use
or hovered, and **mint** means armed for modulation.

## Files

- `generate_aurora_skin.py` builds `resources/data/skins/aurora.surge-skin` from scratch. The
  background, slider handles and every colour in `skin.xml` are generated here. The other widget
  sprites come from the Surge Dark skin with their palette remapped, so the two skins keep the
  same layout. Requires `pip install fonttools`.
- `screenshot.sh` runs the standalone on a virtual X display and saves a screenshot of the synth.
  The [UI Screenshot workflow](../../.github/workflows/ui-screenshot.yml) uses it to keep the
  README image current.

```bash
python3 scripts/aurora-skin/generate_aurora_skin.py
```

```bash
scripts/aurora-skin/screenshot.sh "build/surge_xt_products/Surge XT" aurora.png 200 "Pads/Communication"
```

The skin ships the [Outfit](https://github.com/Outfitio/Outfit-Fonts) typeface under the SIL Open
Font License (see `resources/data/skins/aurora.surge-skin/fonts/OFL-Outfit.txt`).
