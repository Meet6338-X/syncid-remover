"""
Sub-pixel Geometric Resampling & Edge-Preserving Bilateral Purification.
Disrupts convolutional spatial grid alignment (RAVEN / StegExorcist principles).
"""

import numpy as np
import cv2
from typing import Tuple, Dict, Any


class SpatialResamplerPurifier:
    """
    Applies sub-pixel projective/affine micro-transformations and bilateral edge-preserving
    filtering to destroy pixel-grid convolutional watermark correlation.
    """

    def __init__(
        self,
        subpixel_shift: float = 0.45,
        bilateral_d: int = 5,
        bilateral_sigma_color: float = 12.0,
        bilateral_sigma_space: float = 12.0,
        chroma_decorrelation: float = 0.008,
    ):
        self.subpixel_shift = subpixel_shift
        self.bilateral_d = bilateral_d
        self.bilateral_sigma_color = bilateral_sigma_color
        self.bilateral_sigma_space = bilateral_sigma_space
        self.chroma_decorrelation = chroma_decorrelation

    def process(self, img_bgr: np.ndarray) -> Tuple[np.ndarray, Dict[str, Any]]:
        h, w = img_bgr.shape[:2]

        # 1. Edge-preserving Bilateral Filter
        # Retains sharp edges while smoothing the watermark carrier in flat & subtle texture regions
        filtered_bgr = cv2.bilateralFilter(
            img_bgr,
            d=self.bilateral_d,
            sigmaColor=self.bilateral_sigma_color,
            sigmaSpace=self.bilateral_sigma_space,
        )

        # 2. Sub-pixel Translation (no rotation to preserve strict SSIM)
        # Micro-shift amounts
        dx = float(np.random.uniform(-self.subpixel_shift, self.subpixel_shift))
        dy = float(np.random.uniform(-self.subpixel_shift, self.subpixel_shift))

        # Affine translation matrix
        trans_mat = np.array([[1.0, 0.0, dx], [0.0, 1.0, dy]], dtype=np.float32)

        resampled_bgr = cv2.warpAffine(
            filtered_bgr,
            trans_mat,
            (w, h),
            flags=cv2.INTER_LANCZOS4,
            borderMode=cv2.BORDER_REFLECT_101,
        )

        # 3. Zero-mean Chroma Decorrelation (Per-pixel micro-dither, not global hue shift)
        lab = cv2.cvtColor(resampled_bgr, cv2.COLOR_BGR2LAB).astype(np.float32)
        l_chan, a_chan, b_chan = lab[:, :, 0], lab[:, :, 1], lab[:, :, 2]

        if self.chroma_decorrelation > 0:
            noise_a = np.random.normal(0, self.chroma_decorrelation * 25.0, size=(h, w)).astype(np.float32)
            noise_b = np.random.normal(0, self.chroma_decorrelation * 25.0, size=(h, w)).astype(np.float32)
            a_chan = np.clip(a_chan + noise_a, 0, 255)
            b_chan = np.clip(b_chan + noise_b, 0, 255)

        purified_lab = np.stack([l_chan, a_chan, b_chan], axis=2).astype(np.uint8)
        final_bgr = cv2.cvtColor(purified_lab, cv2.COLOR_LAB2BGR)

        return final_bgr, {
            "subpixel_dx": float(dx),
            "subpixel_dy": float(dy),
            "bilateral_applied": True,
        }
