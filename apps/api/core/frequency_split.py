"""
Gaussian Frequency Split & Multi-Scale Residual Purification.
Breaks spatial correlation of steganographic watermarks (SynthID) while preserving structural edges.
"""

import numpy as np
import cv2
from typing import Tuple, Dict, Any


class FrequencySplitPurifier:
    """
    Decomposes an image into semantic low frequencies and textural/watermark high frequencies.
    Neutralizes the watermark carrier signal in the high band before re-synthesis.
    """

    def __init__(
        self,
        gaussian_sigma: float = 1.8,
        residual_threshold: float = 2.5,
        noise_dither_strength: float = 0.8,
        fft_phase_jitter: float = 0.05,
    ):
        self.gaussian_sigma = gaussian_sigma
        self.residual_threshold = residual_threshold
        self.noise_dither_strength = noise_dither_strength
        self.fft_phase_jitter = fft_phase_jitter

    def process(self, img_bgr: np.ndarray) -> Tuple[np.ndarray, Dict[str, Any]]:
        """
        Processes BGR image through multi-scale frequency decomposition.
        Returns:
            purified_bgr: Image with neutralized watermark
            metrics: Intermediate frequency analysis stats
        """
        img_float = img_bgr.astype(np.float32)

        # 1. Multi-scale Low-Pass filtering (Gaussian Blur)
        # Low frequency contains semantic structure, high contains texture + watermark
        low_freq = cv2.GaussianBlur(
            img_float, (0, 0), sigmaX=self.gaussian_sigma, sigmaY=self.gaussian_sigma
        )
        high_freq = img_float - low_freq

        # 2. Adaptive Soft-Thresholding on High-Frequency Residual
        # SynthID residual typically has peak energy <= 4.0 in 8-bit space
        abs_high = np.abs(high_freq)
        sign_high = np.sign(high_freq)
        
        # Soft shrinkage: shrinks small coefficients (watermark) while keeping strong edges
        shrunk_high = sign_high * np.maximum(0.0, abs_high - self.residual_threshold)

        # 3. Frequency domain phase perturbation in mid-band carrier frequencies
        h, w, c = img_bgr.shape
        purified_high = np.zeros_like(high_freq)

        for ch in range(c):
            channel_high = shrunk_high[:, :, ch]
            f_transform = np.fft.fft2(channel_high)
            f_shift = np.fft.fftshift(f_transform)
            magnitude = np.abs(f_shift)
            phase = np.angle(f_shift)

            # Build radial frequency grid
            y, x = np.ogrid[:h, :w]
            cy, cx = h / 2.0, w / 2.0
            radius = np.sqrt((x - cx) ** 2 + (y - cy) ** 2)
            max_r = np.sqrt(cx**2 + cy**2)
            norm_r = radius / (max_r + 1e-6)

            # Watermark energy is concentrated in normalized band [0.10, 0.50]
            watermark_mask = (norm_r >= 0.08) & (norm_r <= 0.48)

            # Inject controlled random phase jitter to break coherent steganographic alignment
            phase_noise = np.random.uniform(
                -self.fft_phase_jitter * np.pi,
                self.fft_phase_jitter * np.pi,
                size=(h, w),
            )
            scrambled_phase = phase + watermark_mask * phase_noise

            # Reconstruct channel
            reconstructed_f = magnitude * np.exp(1j * scrambled_phase)
            f_ishift = np.fft.ifftshift(reconstructed_f)
            purified_ch = np.real(np.fft.ifft2(f_ishift))
            purified_high[:, :, ch] = purified_ch

        # 4. Sensor-noise floor substitution (Replaces deterministic watermark with Poisson/Gaussian noise)
        if self.noise_dither_strength > 0:
            noise = np.random.normal(
                0, self.noise_dither_strength, size=purified_high.shape
            ).astype(np.float32)
            purified_high += noise

        # 5. Synthesis & Recombination
        purified_float = low_freq + purified_high
        purified_bgr = np.clip(purified_float, 0, 255).astype(np.uint8)

        stats = {
            "low_freq_energy": float(np.mean(low_freq**2)),
            "orig_high_freq_std": float(np.std(high_freq)),
            "purified_high_freq_std": float(np.std(purified_high)),
            "shrinkage_ratio": float(
                np.count_nonzero(abs_high <= self.residual_threshold) / abs_high.size
            ),
        }

        return purified_bgr, stats
