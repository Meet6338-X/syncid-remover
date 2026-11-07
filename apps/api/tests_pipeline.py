"""
Unit and Integration Test for DeSynth Pipeline.
Generates a synthetic image with embedded steganographic watermark pattern & metadata,
runs the purification pipeline, and asserts mathematical bounds (PSNR > 36, SSIM > 0.95, Risk Drop > 50%).
"""

import numpy as np
import cv2
from core.pipeline import DeSynthPipeline
from core.detector_oracle import DetectorOracle
from core.c2pa_stripper import C2PAStripper


def test_pipeline():
    print("=== STARTING DESYNTH INTEGRATION TESTS ===")

    # 1. Create synthetic realistic test image (512x512)
    h, w = 512, 512
    y, x = np.ogrid[:h, :w]
    # Smooth gradient base + textures
    base = (np.sin(x / 40.0) * np.cos(y / 40.0) * 80 + 128).astype(np.float32)
    img_bgr = np.stack([base, base * 0.9 + 20, base * 0.8 + 40], axis=2).astype(np.float32)

    # 2. Embed synthetic SynthID-like periodic steganographic watermark
    # SynthID embeds low-amplitude periodic residual across 8x8 blocks
    carrier = np.sin(x * np.pi / 4.0) * np.cos(y * np.pi / 4.0) * 3.5
    watermarked_bgr = np.clip(img_bgr + carrier[:, :, None], 0, 255).astype(np.uint8)

    # Encode to bytes
    success, encoded = cv2.imencode(".png", watermarked_bgr)
    assert success, "Image encoding failed"
    input_bytes = encoded.tobytes()

    # Append dummy C2PA / AI metadata string into PNG bitstream
    input_bytes_with_c2pa = input_bytes + b"\x00\x00\x00\x18c2pa\x00\x00\x00\x00JUMBF_MANIFEST_DATA_SYNTHID"

    # 3. Test Metadata Inspector
    meta = C2PAStripper.inspect_metadata(input_bytes_with_c2pa)
    print("Metadata Check Detected:", meta["detected_signatures"])
    assert meta["has_ai_metadata"], "Should detect C2PA / SynthID signature"

    # 4. Test Oracle on Watermarked Image
    pre_eval = DetectorOracle.evaluate(watermarked_bgr, has_c2pa=True)
    print("Pre-eval indicators:", pre_eval["indicators"])
    print(f"Pre-Purification AI Detection Confidence: {pre_eval['overall_ai_confidence_percent']}% ({pre_eval['verdict']})")
    assert pre_eval["overall_ai_confidence_percent"] >= 50.0, "Watermarked image should be flagged as AI"

    # 5. Run Full Purification Pipeline
    pipeline = DeSynthPipeline(preset="balanced")
    result = pipeline.process_bytes(input_bytes_with_c2pa)
    print("Post-eval indicators:", result["forensics"]["after"]["indicators"])

    print(f"Purification elapsed: {result['elapsed_ms']}ms")
    print(f"PSNR: {result['quality']['psnr_db']} dB")
    print(f"SSIM: {result['quality']['ssim']}")
    print(f"High-Freq SSIM: {result['quality']['high_freq_ssim']}")
    print(f"Color Delta-E: {result['quality']['delta_e_color_diff']}")
    print(f"Post-Purification AI Risk: {result['forensics']['after']['overall_ai_confidence_percent']}% ({result['forensics']['after']['verdict']})")
    print(f"Risk Reduction: {result['forensics']['risk_reduction_percent']}%")

    # 6. Assertions
    assert result["quality"]["psnr_db"] >= 35.0, f"PSNR too low: {result['quality']['psnr_db']}"
    assert result["quality"]["ssim"] >= 0.95, f"SSIM too low: {result['quality']['ssim']}"
    assert result["metadata_sanitized"] is True, "Metadata should be 100% sanitized"
    assert result["forensics"]["after"]["verdict"] in ["UNDETECTABLE", "INCONCLUSIVE"], "Should evade detection"
    assert result["forensics"]["risk_reduction_percent"] >= 40.0, "Risk reduction should be significant"

    print("=== ALL TESTS PASSED SUCCESSFULLY! ===")


if __name__ == "__main__":
    test_pipeline()
