"""
Forensic AI Detection Oracle & SynthID Verification Simulator.
Simulates state-of-the-art AI watermarking & detector engines (SynthID, Hive, Illuminarty, C2PA).
"""

import numpy as np
import cv2
from scipy.stats import kurtosis
from typing import Dict, Any


class DetectorOracle:
    """
    Evaluates an image against known forensic detection vectors:
    - Steganographic cross-correlation (SynthID simulation)
    - High-frequency Fourier grid harmonics (Diffusion fingerprint)
    - Noise residual kurtosis & spectral entropy (Sensor vs Artificial noise)
    - C2PA / Content Credentials metadata presence
    """

    @staticmethod
    def evaluate(img_bgr: np.ndarray, has_c2pa: bool = False) -> Dict[str, Any]:
        h, w = img_bgr.shape[:2]
        gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY).astype(np.float32)

        # 1. High-frequency residual extraction
        # Subtract low-frequency content with an adaptive bilateral or median filter
        # to isolate fine noise and watermark carriers from natural smooth gradients
        smooth = cv2.GaussianBlur(gray, (15, 15), 3.0)
        residual = gray - smooth

        # 2. Steganographic Periodic Correlation (SynthID Proxy)
        # SynthID embeds an artificial key pattern with periodic block symmetry
        # Watermark residuals exhibit cross-correlation spikes at fixed offsets (e.g. 8px)
        if h > 32 and w > 32:
            sub_r = residual[8:h-8, 8:w-8]
            shift_x = residual[8:h-8, 16:w]
            shift_y = residual[16:h, 8:w-8]

            norm_sub = np.linalg.norm(sub_r) + 1e-6
            corr_x = float(np.sum(sub_r * shift_x) / (norm_sub * np.linalg.norm(shift_x) + 1e-6))
            corr_y = float(np.sum(sub_r * shift_y) / (norm_sub * np.linalg.norm(shift_y) + 1e-6))
            
            # Steganographic correlation is mapped from raw autocorrelation
            # A completely random natural texture has autocorrelation < 0.25
            # An untouched SynthID watermarked image has autocorrelation > 0.85
            raw_corr = (abs(corr_x) + abs(corr_y)) / 2.0
            synthid_corr = float(np.clip((raw_corr - 0.25) / 0.65, 0.0, 1.0))
        else:
            synthid_corr = 0.05

        # 3. Fourier Grid Harmonics (Diffusion / Upscaler Checkerboard Artifacts)
        f_transform = np.fft.fft2(gray)
        f_shift = np.fft.fftshift(f_transform)
        magnitude_spectrum = np.log(np.abs(f_shift) + 1.0)

        # Radial profile calculation
        cy, cx = h / 2.0, w / 2.0
        y, x = np.ogrid[:h, :w]
        r = np.sqrt((x - cx) ** 2 + (y - cy) ** 2)
        norm_r = r / (np.sqrt(cx**2 + cy**2) + 1e-6)

        high_band = (norm_r > 0.45) & (norm_r < 0.90)
        high_band_energy = float(np.mean(magnitude_spectrum[high_band]))
        all_energy = float(np.mean(magnitude_spectrum))

        # Peak-to-average ratio in high frequencies (spikes indicate periodic watermark)
        high_band_max = float(np.max(magnitude_spectrum[high_band]))
        spectral_spike_ratio = float(high_band_max / (high_band_energy + 1e-6))
        fourier_harmonic_score = float(np.clip((spectral_spike_ratio - 1.45) / 0.8, 0.0, 1.0))

        # 4. Noise Residual Kurtosis
        # Natural photographic noise has Gaussian kurtosis ~ 3.0 (excess kurtosis ~ 0)
        # Steganographic signals bias the tail distribution
        excess_kurt = float(np.abs(kurtosis(residual.ravel(), fisher=True)))
        kurtosis_anomaly = float(np.clip(excess_kurt / 2.5, 0.0, 1.0))

        # 5. C2PA Score
        c2pa_score = 1.0 if has_c2pa else 0.0

        # Ensemble AI Detection Confidence
        # Weighted combination of all forensic indicators
        ensemble_score = (
            0.40 * synthid_corr
            + 0.25 * fourier_harmonic_score
            + 0.15 * kurtosis_anomaly
            + 0.20 * c2pa_score
        )
        ensemble_percent = round(float(np.clip(ensemble_score * 100.0, 1.2, 99.8)), 1)

        # Categorize detection status
        if ensemble_percent < 25.0:
            classification = "Human / Authentic Image (Zero Watermark Trace)"
            verdict = "UNDETECTABLE"
        elif ensemble_percent < 50.0:
            classification = "Inconclusive / Heavy Photographic Processing"
            verdict = "INCONCLUSIVE"
        else:
            classification = "AI-Generated Media (High Confidence Match)"
            verdict = "DETECTED"

        return {
            "overall_ai_confidence_percent": ensemble_percent,
            "verdict": verdict,
            "classification": classification,
            "indicators": {
                "synthid_correlation_risk": round(synthid_corr * 100, 1),
                "fourier_harmonic_anomaly": round(fourier_harmonic_score * 100, 1),
                "residual_kurtosis_risk": round(kurtosis_anomaly * 100, 1),
                "c2pa_provenance_flag": bool(has_c2pa),
            },
            "spectral_stats": {
                "high_band_energy": round(high_band_energy, 3),
                "spectral_spike_ratio": round(spectral_spike_ratio, 3),
                "residual_std": round(float(np.std(residual)), 3),
            },
        }
