# Kids Math: animated K-2 math lessons

Generates short, narrated, animated explainer videos for children ages 5-8
(Kindergarten to Grade 2) with **ManimGL** (`manimlib`), macOS text-to-speech
and FFmpeg. Lessons are plain JSON specs, so a future natural-language front
end only has to produce JSON; it never produces code.

```
topic + grade + difficulty + numbers
        |  kidsmath.lessons (templates)
        v
   LessonSpec (JSON)  --validate-->  math correct? age appropriate?
        |  kidsmath.narration (macOS `say`, one WAV per step)
        |  kidsmath.render.timing (every step lasts as long as its narration)
        v
   ManimGL scene (fixed action vocabulary)  -->  FFmpeg mux  -->  MP4
        ^
   FastAPI  (POST /lessons, GET /lessons/{id}/video)
```

## Setup

Uses the existing `.venv` (Python 3.12). Requires FFmpeg and a TeX install.

```bash
source .venv/bin/activate
pip install -r requirements.txt
```

### LaTeX packages (one-time)

ManimGL's default TeX template loads packages that BasicTeX lacks. Without
admin rights, install them into your user tree:

```bash
tlmgr init-usertree
tlmgr --usermode install dsfont relsize fundus-calligra wasysym physics rsfs wasy wasy-type1 cm-super
```

(or `sudo tlmgr install ...` for a system-wide install). The lesson scenes use
plain `Text`, so they do not need LaTeX; only `manimgl test_manim.py HelloMath -w` does.

## Command line

```bash
# the starter lesson: 3 + 2 = 5, with narration
python -m kidsmath render --topic addition --grade 0 --numbers 3 2 --out output/add_3_2.mp4

# other topics
python -m kidsmath render --topic subtraction --grade 0 --numbers 5 2
python -m kidsmath render --topic counting --grade 0 --numbers 8
python -m kidsmath render --topic comparison --grade 1 --numbers 14 9
python -m kidsmath render --topic shapes --grade 1 --shape hexagon
python -m kidsmath render --topic place_value --grade 2 --numbers 345
python -m kidsmath render --topic word_problem --grade 1 --operation subtract --seed 3
python -m kidsmath render --topic addition --grade 2 --numbers 34 28   # tens and ones

# random numbers within the grade and difficulty
python -m kidsmath render --topic addition --grade 1 --difficulty hard --seed 42

# JSON only / validate / render a spec file
python -m kidsmath spec --topic addition --numbers 3 2 > lesson.json
python -m kidsmath validate lesson.json
python -m kidsmath render-spec lesson.json --out output/from_spec.mp4
python -m kidsmath render --topic addition --numbers 3 2 --silent   # no TTS
```

## API

```bash
uvicorn kidsmath.api:app --reload      # docs at http://127.0.0.1:8000/docs

curl -X POST localhost:8000/lessons -H 'content-type: application/json' \
  -d '{"topic":"addition","grade":0,"difficulty":"easy","numbers":[3,2]}'
# -> {"id": "...", "status": "queued", ...}      (202)

curl localhost:8000/lessons/<id>               # queued | rendering | done | failed
curl -o lesson.mp4 localhost:8000/lessons/<id>/video
curl localhost:8000/lessons/<id>/spec          # the JSON lesson spec
curl localhost:8000/topics
curl -X POST localhost:8000/lessons/from-spec -H 'content-type: application/json' -d @lesson.json
```

Videos render one at a time in a background worker and are stored under
`output/lessons/<id>/` (override with `KIDSMATH_OUTPUT_DIR`). Invalid or
mathematically wrong requests return 422 with a list of issues.

## 3D lessons (`--style 3d`)

```bash
python -m kidsmath render --topic addition --grade 0 --numbers 3 2 --style 3d --out output/add_3_2_3d.mp4
python -m kidsmath render --topic subtraction --grade 0 --numbers 5 2 --style 3d
python -m kidsmath render --topic addition --grade 1 --numbers 9 8 --style 3d   # two rows of toys
manimgl addition_3d.py Addition3D -w        # quick preview: estimated timing, no voice
```

Glossy 3D toys (ball, cube, cone, coin) drop onto a play mat with soft shadows. The
three red and two yellow balls are counted one by one: each hops, gets a spotlight ring
and a number badge that stays glued to it while the camera glides. Then confetti and
`3 + 2 = 5`. Every video ships with `<name>.srt` next to the MP4.

* **Narration and subtitles**: one TTS clip per step; the subtitle bar highlights each
  word as it is spoken (word windows are proportional to word length, with pauses at
  punctuation). Measured on the 3 + 2 lesson, every subtitle cue starts within 0.04 s
  of its narration in the audio track.
* **Camera**: a pure function of time (`render3d/director.py`): keyframes chosen from
  the lesson (intro, establish, merge, orbit while counting, equation, celebrate),
  eased with smoothstep plus a tiny idle sway. It never fights `play()`.
* **Supported in 3D**: addition, subtraction, counting, comparison (up to 20 toys) and
  word problems. `shapes` and `place_value` (blocks) are 2D only and are rejected with a
  clear error. The API accepts `"style": "3d"` on `POST /lessons` and `/lessons/from-spec`.
* **Wording**: 3D lessons say "balls/cubes/cones/coins" instead of "circles/squares/...".

### Reusable 3D components (`kidsmath/render3d/`)

| module | what it gives you |
| --- | --- |
| `kit.py` | `Token` (toy + soft shadow), `make_stage`, `Badge` (HUD number glued to a 3D point), `Subtitle` (karaoke bar), `drop_in`, `hop`, `arc_move`, `spotlight_ring`, `sparkles`, `hud()` |
| `scene3d.py` | `Lesson3DScene`: plays any supported `LessonSpec`; subclass and override `get_spec()` (see `addition_3d.py`) |
| `director.py` | camera keyframes from a spec, `fit_zoom`, `view_at` (pure, unit tested) |
| `layout3d.py` | overlap-free ground layouts for groups and merged rows (pure) |
| `projection.py` | world-to-screen projection that matches ManimGL's shader (pure) |
| `subtitles.py` | wrapping, spoken-word windows, SRT export (pure) |

### ManimGL 1.7.2 compatibility notes

Reference study (`references/3b1b-videos`, used for technique only; no code or assets copied):
the 3D scenes there rely on `Sphere/Cube/Cylinder/Cone` surfaces, `set_shading(reflectiveness,
gloss, shadow)`, `frame.reorient / frame.animate.reorient`, `fix_in_frame`, `z_index`,
`apply_depth_test`, `GlowDot`, `LaggedStart`, `UpdateFromAlphaFunc`. All of these exist in 1.7.2.
Things that do **not** work as in newer examples:

* `Dot3D`, `Tetrahedron`, `Octahedron`, `Polyhedron` and a `bounce` rate function do not exist.
* `Cylinder` and `Cone` are open shells (no end caps): add `Disk3D` caps (done in `kit.make_body`).
* `mob.animate.set_rate_func(...)` is not available: use `UpdateFromAlphaFunc` (`hop`, `arc_move`).
* `Text(color=...)` is ignored: call `.set_color()` afterwards.
* 3D mobjects and VMobject outlines are drawn in batches, so overlapping outlines need care
  (Milo's ears have no outline for this reason).
* `--fps` is broken; renders use the default 30 fps.

## Milo the Mouse

Lessons are explained by **Milo the Mouse**, an original mascot drawn from
ManimGL shapes (`kidsmath/render/mascot.py`). His mouth follows the loudness of
the narration audio frame by frame, he blinks, bobs, and hops when an equation
appears and at the end. He says hello in the first line. Turn him off with
`--no-mascot` (CLI), `"mascot": "none"` (API) or `mascot: "none"` in the spec.

Milo is original on purpose: Disney's Mickey Mouse is a trademarked, copyrighted
character. To use licensed artwork you own, replace `Milo` in `mascot.py` with a
class exposing `set_openness`, `set_blink` and `y_offset`.

## Lesson spec

A `LessonSpec` has `topic`, `grade` (0 = K), `difficulty`, machine-checkable
`facts`, and `steps`. Each step has a `narration` sentence and `actions` from a
closed set: `title`, `text`, `objects`, `count_item`, `merge`, `cross_out`,
`equation`, `sign`, `shape`, `blocks`, `clear` (see `kidsmath/spec.py`).
`python -c "from kidsmath.spec import LessonSpec; import json; print(json.dumps(LessonSpec.model_json_schema()))"`
prints the JSON Schema, e.g. to constrain an LLM's output.

## Safety and correctness

* Specs are data. The renderer only interprets the fixed action set; nothing
  from a spec is `eval`ed or executed. Unknown fields/actions are rejected.
* `kidsmath/validate.py` recomputes the math (strict regex parser, no `eval`),
  checks object counts and signs against the facts, enforces grade limits
  (`kidsmath/limits.py`), and checks narration (short sentences, no negative
  words, no numbers above the grade limit). Templates validate their own output.
* Grade limits: add/subtract up to 10 (K), 20 (Grade 1), 100 (Grade 2);
  Grade 2 sums beyond 20 use tens-and-ones blocks. Word problems stay within 20.

## Tests

```bash
python -m pytest            # fast unit tests (207)
python -m pytest -m slow    # also renders real 2D and 3D videos (about 40 s)
```

## Layout

```
kidsmath/spec.py, validate.py, limits.py   the contract and the checks
kidsmath/lessons/                          one template per topic
kidsmath/narration.py                      TTS backends (macOS say, silent)
kidsmath/render/{timing,layout,scene,mascot,pipeline}.py   2D renderer + Milo
kidsmath/render3d/                         3D framework (kit, scene3d, director, ...)
addition_3d.py                             3 + 2 = 5 in 3D (addition_3d_v1.py = original)
kidsmath/api.py, cli.py
tests/
```

## Notes

* ManimGL 1.7.2's `--fps` flag is broken, so renders use its default 30 fps;
  `render/timing.py` assumes that.
* Narration needs macOS `say`; elsewhere the pipeline falls back to silence.
  Add another `TTSBackend` in `narration.py` to use a different engine.
