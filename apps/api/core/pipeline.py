"""
Unified Multi-Stage DeSynth Purification Pipeline.
Orchestrates C2PA sanitization, spatial jitter, Gaussian frequency split, and DCT scrambling.
"""

import io
import time
import numpy as np
import cv2
from typing import Dict, Any, Optional

from .frequency_split import FrequencySplitPurifier
from .dct_purifier import DCTBlockPurifier
from .spatial_resampler import SpatialResamplerPurifier
from .c2pa_stripper import C2PAStripper
from .detector_oracle import DetectorOracle
from .metrics import QualityMetrics


class DeSynthPipeline:
    """
    Complete end-to-end multi-vector AI watermark removal engine.
    """

    PRESETS = {
        "gentle": {
            "spatial_shift": 0.15,
            "bilateral_color": 6.0,
            "gaussian_sigma": 1.2,
            "residual_threshold": 1.6,
            "noise_dither": 0.3,
            "dct_jitter": 0.25,
            "fft_phase_jitter": 0.02,
        },
        "balanced": {
            "spatial_shift": 0.25,
            "bilateral_color": 8.0,
            "gaussian_sigma": 1.5,
            "residual_threshold": 2.0,
            "noise_dither": 0.5,
            "dct_jitter": 0.35,
            "fft_phase_jitter": 0.04,
        },
        "hardcore": {
            "spatial_shift": 0.45,
            "bilateral_color": 14.0,
            "gaussian_sigma": 2.0,
            "residual_threshold": 3.2,
            "noise_dither": 1.0,
            "dct_jitter": 0.60,
            "fft_phase_jitter": 0.08,
        },
        "spectral_clean": {
            "spatial_shift": 0.20,
            "bilateral_color": 8.0,
            "gaussian_sigma": 1.8,
            "residual_threshold": 2.4,
            "noise_dither": 0.4,
            "dct_jitter": 0.50,
            "fft_phase_jitter": 0.06,
        },
    }

    def __init__(self, preset: str = "balanced", custom_params: Optional[Dict[str, Any]] = None):
        cfg = self.PRESETS.get(preset, self.PRESETS["balanced"]).copy()
        if custom_params:
            cfg.update(custom_params)

        self.cfg = cfg
        self.preset_name = preset

        # Initialize sub-modules
        self.spatial = SpatialResamplerPurifier(
            subpixel_shift=cfg["spatial_shift"],
            bilateral_sigma_color=cfg["bilateral_color"],
            bilateral_sigma_space=cfg["bilateral_color"],
        )
        self.freq_split = FrequencySplitPurifier(
            gaussian_sigma=cfg["gaussian_sigma"],
            residual_threshold=cfg["residual_threshold"],
            noise_dither_strength=cfg["noise_dither"],
            fft_phase_jitter=cfg["fft_phase_jitter"],
        )
        self.dct = DCTBlockPurifier(
            block_size=8,
            jitter_scale=cfg["dct_jitter"],
            threshold=cfg["residual_threshold"] * 0.5,
        )

    def process_bytes(
        self, input_bytes: bytes, output_format: str = "PNG", output_quality: int = 96
    ) -> Dict[str, Any]:
        """
        Executes full multi-stage purification on raw image bytes.
        Returns cleaned image bytes and comprehensive forensic verification metrics.
        """
        start_time = time.time()

        # Step 0: Initial Metadata & Oracle Evaluation
        meta_pre = C2PAStripper.inspect_metadata(input_bytes)
        img_array = np.frombuffer(input_bytes, np.uint8)
        img_orig_bgr = cv2.imdecode(img_array, cv2.IMREAD_COLOR)

        if img_orig_bgr is None:
            raise ValueError("Failed to decode image from provided bytes.")

        eval_pre = DetectorOracle.evaluate(
            img_orig_bgr,
            has_c2pa=meta_pre["has_ai_metadata"],
            detected_signatures=meta_pre["detected_signatures"],
        )

        # Stage 1: Spatial Micro-Geometric Resampling & Bilateral Filtering
        stage1_bgr, s1_meta = self.spatial.process(img_orig_bgr)

        # Stage 2: Gaussian Frequency Split & Phase Dither
        stage2_bgr, s2_meta = self.freq_split.process(stage1_bgr)

        # Stage 3: Block DCT Mid-Frequency Notch Scrambler
        stage3_bgr, s3_meta = self.dct.process(stage2_bgr)

        # Stage 4: Encode clean bitmap without metadata
        success, raw_clean_encoded = cv2.imencode(".png", stage3_bgr)
        if not success:
            raise RuntimeError("Failed to encode intermediate purified image.")

        # Stage 5: Complete Bitstream C2PA & Provenance Sanitization
        clean_bytes, meta_post = C2PAStripper.sanitize(
            raw_clean_encoded.tobytes(), output_format=output_format, quality=output_quality
        )

        # Stage 6: Post-Purification Forensic Evaluation
        clean_arr = np.frombuffer(clean_bytes, np.uint8)
        img_clean_bgr = cv2.imdecode(clean_arr, cv2.IMREAD_COLOR)
        eval_post = DetectorOracle.evaluate(img_clean_bgr, has_c2pa=False)

        # Stage 7: Perceptual Quality Benchmarks
        quality_bench = QualityMetrics.compute_all(img_orig_bgr, img_clean_bgr)

        elapsed = round((time.time() - start_time) * 1000.0, 1)

        return {
            "clean_bytes": clean_bytes,
            "elapsed_ms": elapsed,
            "preset": self.preset_name,
            "forensics": {
                "before": eval_pre,
                "after": eval_post,
                "risk_reduction_percent": round(
                    eval_pre["overall_ai_confidence_percent"]
                    - eval_post["overall_ai_confidence_percent"],
                    1,
                ),
            },
            "quality": quality_bench,
            "metadata_sanitized": meta_post["sanitized"],
            "stripped_signatures": meta_pre["detected_signatures"],
        }
