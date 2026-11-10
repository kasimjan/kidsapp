"""Command line interface: python -m kidsmath.cli --help"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .lessons import TEMPLATES, generate_lesson
from .narration import MacSayBackend, SilentBackend
from .spec import LessonSpec
from .validate import SpecValidationError, validate_spec


def _add_lesson_args(p: argparse.ArgumentParser) -> None:
    p.add_argument("--topic", required=True, choices=sorted(TEMPLATES))
    p.add_argument("--grade", type=int, default=0, choices=(0, 1, 2),
                   help="0 = Kindergarten")
    p.add_argument("--difficulty", default="easy", choices=("easy", "medium", "hard"))
    p.add_argument("--numbers", type=int, nargs="*", help="example numbers, e.g. 3 2")
    p.add_argument("--seed", type=int)
    p.add_argument("--shape", help="for the shapes topic, e.g. triangle")
    p.add_argument("--operation", choices=("add", "subtract"), help="for word problems")
    p.add_argument("--no-mascot", action="store_true", help="leave Milo the Mouse out")
    p.add_argument("--style", default="2d", choices=("2d", "3d"), help="flat or 3D animation")


def _make(args) -> LessonSpec:
    return generate_lesson(args.topic, args.grade, args.difficulty, args.numbers or None,
                           args.seed, args.shape, args.operation,
                           "none" if args.no_mascot else "milo", args.style)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="kidsmath", description=__doc__)
    sub = parser.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("spec", help="print the JSON lesson spec")
    _add_lesson_args(p)

    p = sub.add_parser("render", help="generate a lesson and render it to MP4")
    _add_lesson_args(p)
    p.add_argument("--out", type=Path, default=Path("output/lesson.mp4"))
    p.add_argument("--voice", default="Samantha")
    p.add_argument("--silent", action="store_true", help="skip text-to-speech")

    p = sub.add_parser("render-spec", help="render a JSON spec file (validated first)")
    p.add_argument("spec_file", type=Path)
    p.add_argument("--style", default="2d", choices=("2d", "3d"))
    p.add_argument("--out", type=Path, default=Path("output/lesson.mp4"))
    p.add_argument("--voice", default="Samantha")
    p.add_argument("--silent", action="store_true")

    p = sub.add_parser("validate", help="validate a JSON spec file")
    p.add_argument("spec_file", type=Path)

    args = parser.parse_args(argv)
    try:
        if args.cmd == "spec":
            print(_make(args).model_dump_json(indent=2))
        elif args.cmd == "validate":
            validate_spec(LessonSpec.model_validate_json(args.spec_file.read_text()))
            print("OK: spec is valid, mathematically correct and age appropriate")
        else:
            from .render.pipeline import render_lesson
            spec = _make(args) if args.cmd == "render" else validate_spec(
                LessonSpec.model_validate_json(args.spec_file.read_text()))
            backend = SilentBackend() if args.silent or not MacSayBackend.available() \
                else MacSayBackend(args.voice)
            result = render_lesson(spec, args.out, backend=backend,
                                   cache_dir=Path(".cache/tts"), style=args.style)
            print(f"Wrote {result.video} ({result.duration:.1f}s)")
    except (SpecValidationError, ValueError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    except Exception as e:  # RenderError etc.
        print(f"error: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
