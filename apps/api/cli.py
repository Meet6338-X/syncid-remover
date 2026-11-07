#!/usr/bin/env python3
"""
DeSynth CLI: Command-Line Interface for Batch AI Watermark & SynthID Neutralization.
Usage:
    python cli.py purify input.png -o clean.png --preset balanced
    python cli.py analyze input.png
    python cli.py batch ./input_dir/ -o ./clean_dir/
"""

import argparse
import json
import os
import sys
from pathlib import Path

# Add parent directory to path so relative imports work
sys.path.insert(0, str(Path(__file__).parent))

import cv2
import numpy as np
from core.pipeline import DeSynthPipeline
from core.detector_oracle import DetectorOracle
from core.c2pa_stripper import C2PAStripper


def format_table(data: dict) -> str:
    lines = []
    lines.append("-" * 65)
    for k, v in data.items():
        if isinstance(v, dict):
            lines.append(f"[{k.upper()}]")
            for sub_k, sub_v in v.items():
                lines.append(f"  • {sub_k:30s} : {sub_v}")
        else:
            lines.append(f"  • {k:32s} : {v}")
    lines.append("-" * 65)
    return "\n".join(lines)


def cmd_analyze(args):
    print(f"\n[DeSynth] Analyzing forensic watermark signatures: {args.input}")
    with open(args.input, "rb") as f:
        raw_bytes = f.read()

    meta = C2PAStripper.inspect_metadata(raw_bytes)
    img = cv2.imdecode(np.frombuffer(raw_bytes, np.uint8), cv2.IMREAD_COLOR)
    if img is None:
        print("Error: Could not decode image.")
        sys.exit(1)

    eval_result = DetectorOracle.evaluate(img, has_c2pa=meta["has_ai_metadata"])

    print("\n--- FORENSIC ANALYSIS REPORT ---")
    print(format_table(eval_result))
    print("\n--- METADATA & PROVENANCE ---")
    print(format_table(meta))


def cmd_purify(args):
    print(f"\n[DeSynth] Neutralizing AI Watermark: {args.input}")
    print(f"[Mode] Preset: {args.preset.upper()} | Output: {args.output}")

    with open(args.input, "rb") as f:
        input_bytes = f.read()

    pipeline = DeSynthPipeline(preset=args.preset)
    result = pipeline.process_bytes(
        input_bytes,
        output_format="PNG" if args.output.lower().endswith(".png") else "JPEG",
        output_quality=args.quality,
    )

    # Save output
    os.makedirs(os.path.dirname(os.path.abspath(args.output)), exist_ok=True)
    with open(args.output, "wb") as f:
        f.write(result["clean_bytes"])

    print(f"\n[Success] Purified image written to: {args.output} ({result['elapsed_ms']}ms)")
    print("\n--- QUALITY & FIDELITY BENCHMARK ---")
    print(format_table(result["quality"]))

    print("\n--- FORENSIC RISK REDUCTION ---")
    before_score = result["forensics"]["before"]["overall_ai_confidence_percent"]
    after_score = result["forensics"]["after"]["overall_ai_confidence_percent"]
    print(f"  • AI Confidence Before : {before_score}% ({result['forensics']['before']['verdict']})")
    print(f"  • AI Confidence After  : {after_score}% ({result['forensics']['after']['verdict']})")
    print(f"  • Net Risk Reduction   : -{result['forensics']['risk_reduction_percent']}%")
    print(f"  • C2PA Manifests Purged: {result['metadata_sanitized']}")

    if args.json:
        report_path = args.output + ".desynth.json"
        with open(report_path, "w") as jf:
            json.dump({k: v for k, v in result.items() if k != "clean_bytes"}, jf, indent=2)
        print(f"  • JSON Audit Report    : {report_path}")


def cmd_batch(args):
    in_dir = Path(args.input_dir)
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    image_exts = {".png", ".jpg", ".jpeg", ".webp"}
    files = [f for f in in_dir.iterdir() if f.suffix.lower() in image_exts]

    print(f"\n[DeSynth Batch] Found {len(files)} images to process in {in_dir}")
    pipeline = DeSynthPipeline(preset=args.preset)

    for i, file_path in enumerate(files, 1):
        out_path = out_dir / file_path.name
        try:
            with open(file_path, "rb") as f:
                raw_bytes = f.read()
            res = pipeline.process_bytes(raw_bytes)
            with open(out_path, "wb") as f:
                f.write(res["clean_bytes"])
            print(f"[{i}/{len(files)}] Processed: {file_path.name} -> {out_path.name} (SSIM: {res['quality']['ssim']})")
        except Exception as e:
            print(f"[{i}/{len(files)}] Failed {file_path.name}: {e}")

    print("\n[DeSynth Batch] Batch operation completed successfully.")


def main():
    parser = argparse.ArgumentParser(description="DeSynth: Forensic AI Watermark & SynthID Neutralizer")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Purify single image
    p_purify = subparsers.add_parser("purify", help="Neutralize watermarks from a single image")
    p_purify.add_argument("input", help="Path to input image")
    p_purify.add_argument("-o", "--output", default="clean.png", help="Path to save purified image")
    p_purify.add_argument("--preset", choices=["gentle", "balanced", "hardcore", "spectral_clean"], default="balanced")
    p_purify.add_argument("--quality", type=int, default=96, help="JPEG quality (if JPEG output)")
    p_purify.add_argument("--json", action="store_true", help="Export JSON audit report")
    p_purify.set_defaults(func=cmd_purify)

    # Analyze single image
    p_analyze = subparsers.add_parser("analyze", help="Inspect image for AI watermarks and C2PA metadata")
    p_analyze.add_argument("input", help="Path to input image")
    p_analyze.set_defaults(func=cmd_analyze)

    # Batch process
    p_batch = subparsers.add_parser("batch", help="Batch process entire directory of images")
    p_batch.add_argument("input_dir", help="Directory of source images")
    p_batch.add_argument("-o", "--output_dir", required=True, help="Directory to save clean images")
    p_batch.add_argument("--preset", choices=["gentle", "balanced", "hardcore", "spectral_clean"], default="balanced")
    p_batch.set_defaults(func=cmd_batch)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
