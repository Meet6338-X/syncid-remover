"""
Perceptual & Mathematical Quality Assessment Metrics.
Measures PSNR, Structural Similarity (SSIM), High-Frequency SSIM, Delta-E, and MAE.
"""

import numpy as np
import cv2
from typing import Dict, Any


class QualityMetrics:
    """
    Computes rigorous fidelity metrics between original and purified images.
    """

    @staticmethod
    def compute_all(img_orig_bgr: np.ndarray, img_clean_bgr: np.ndarray) -> Dict[str, Any]:
        h, w = img_orig_bgr.shape[:2]
        ch, cw = img_clean_bgr.shape[:2]

        # Ensure matching dimensions
        if (h, w) != (ch, cw):
            img_clean_bgr = cv2.resize(img_clean_bgr, (w, h), interpolation=cv2.INTER_LANCZOS4)

        orig_f = img_orig_bgr.astype(np.float64)
        clean_f = img_clean_bgr.astype(np.float64)

        # 1. MSE & PSNR
        mse = np.mean((orig_f - clean_f) ** 2)
        if mse == 0:
            psnr = 99.9
        else:
            psnr = 10.0 * np.log10((255.0**2) / mse)

        # 2. MAE (Mean Absolute Error)
        mae = float(np.mean(np.abs(orig_f - clean_f)))

        # 3. SSIM (Full Frame & Channel Average)
        ssim_val = QualityMetrics._calculate_ssim(orig_f, clean_f)

        # 4. High-Frequency SSIM (measures texture sharpness retention)
        orig_blur = cv2.GaussianBlur(orig_f, (7, 7), 2.0)
        clean_blur = cv2.GaussianBlur(clean_f, (7, 7), 2.0)
        orig_high = orig_f - orig_blur + 128.0
        clean_high = clean_f - clean_blur + 128.0
        high_freq_ssim = QualityMetrics._calculate_ssim(orig_high, clean_high)

        # 5. Delta-E (Color shift in CIE-Lab)
        orig_lab = cv2.cvtColor(img_orig_bgr, cv2.COLOR_BGR2LAB).astype(np.float64)
        clean_lab = cv2.cvtColor(img_clean_bgr, cv2.COLOR_BGR2LAB).astype(np.float64)
        delta_e = float(np.mean(np.sqrt(np.sum((orig_lab - clean_lab) ** 2, axis=2))))

        return {
            "psnr_db": round(float(psnr), 2),
            "ssim": round(float(ssim_val), 4),
            "high_freq_ssim": round(float(high_freq_ssim), 4),
            "mae": round(float(mae), 3),
            "delta_e_color_diff": round(float(delta_e), 3),
            "perceptual_grade": "Flawless (Visually Lossless)" if ssim_val > 0.96 and delta_e < 1.5 else "Good",
        }

    @staticmethod
    def _calculate_ssim(img1: np.ndarray, img2: np.ndarray) -> float:
        """Standard windowed SSIM calculation across 3 color channels."""
        c1 = (0.01 * 255) ** 2
        c2 = (0.03 * 255) ** 2

        ssims = []
        for ch in range(3):
            i1 = img1[:, :, ch]
            i2 = img2[:, :, ch]

            mu1 = cv2.GaussianBlur(i1, (11, 11), 1.5)
            mu2 = cv2.GaussianBlur(i2, (11, 11), 1.5)

            mu1_sq = mu1**2
            mu2_sq = mu2**2
            mu1_mu2 = mu1 * mu2

            sigma1_sq = cv2.GaussianBlur(i1**2, (11, 11), 1.5) - mu1_sq
            sigma2_sq = cv2.GaussianBlur(i2**2, (11, 11), 1.5) - mu2_sq
            sigma12 = cv2.GaussianBlur(i1 * i2, (11, 11), 1.5) - mu1_mu2

            ssim_map = ((2 * mu1_mu2 + c1) * (2 * sigma12 + c2)) / (
                (mu1_sq + mu2_sq + c1) * (sigma1_sq + sigma2_sq + c2)
            )
            ssims.append(np.mean(ssim_map))

        return float(np.mean(ssims))
