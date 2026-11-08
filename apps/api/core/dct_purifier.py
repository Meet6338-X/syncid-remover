"""
Block Discrete Cosine Transform (DCT) Mid-Frequency Scrambler.
Neutralizes block-synchronized watermark residual patterns (8x8 grid steganography).
"""

import numpy as np
import cv2
from typing import Tuple, Dict, Any


class DCTBlockPurifier:
    """
    Performs block-wise 8x8 DCT decomposition and introduces randomized perturbation
    into the mid-frequency AC band where steganographic neural watermarks embed.
    """

    def __init__(self, block_size: int = 8, jitter_scale: float = 0.45, threshold: float = 1.2):
        self.block_size = block_size
        self.jitter_scale = jitter_scale
        self.threshold = threshold

        # Zig-zag mask for 8x8 mid-frequency selection
        # Frequencies with u + v in [3, 9] represent the typical watermark carrier band
        self.mid_freq_mask = np.zeros((8, 8), dtype=bool)
        for u in range(8):
            for v in range(8):
                if 2 <= (u + v) <= 9 and not (u == 0 and v == 0):
                    self.mid_freq_mask[u, v] = True

    def process(self, img_bgr: np.ndarray) -> Tuple[np.ndarray, Dict[str, Any]]:
        """
        Transforms BGR image to YCrCb, applies 8x8 DCT mid-frequency perturbation to Y & chrominance,
        and converts back to BGR.
        """
        h, w, c = img_bgr.shape
        # Pad to multiple of block_size if necessary
        pad_h = (self.block_size - (h % self.block_size)) % self.block_size
        pad_w = (self.block_size - (w % self.block_size)) % self.block_size

        if pad_h > 0 or pad_w > 0:
            padded_img = cv2.copyMakeBorder(
                img_bgr, 0, pad_h, 0, pad_w, cv2.BORDER_REFLECT_101
            )
        else:
            padded_img = img_bgr

        # Convert to YCrCb for perceptual separation of luminance and chrominance
        ycrcb = cv2.cvtColor(padded_img, cv2.COLOR_BGR2YCrCb).astype(np.float32)
        ph, pw, _ = ycrcb.shape

        perturbed_count = 0
        total_blocks = (ph // self.block_size) * (pw // self.block_size) * 3

        for ch in range(3):
            channel = ycrcb[:, :, ch]
            # Process each 8x8 block
            for r in range(0, ph, self.block_size):
                for col in range(0, pw, self.block_size):
                    block = channel[r : r + self.block_size, col : col + self.block_size]
                    dct_block = cv2.dct(block)

                    # Extract mid-frequency coefficients
                    mid_coeffs = dct_block[self.mid_freq_mask]

                    # Subtle dead-zone shrinkage + micro-jitter
                    abs_coeffs = np.abs(mid_coeffs)
                    sign_coeffs = np.sign(mid_coeffs)
                    shrunk = sign_coeffs * np.maximum(0.0, abs_coeffs - self.threshold)

                    # Micro jitter
                    jitter = np.random.uniform(
                        -self.jitter_scale, self.jitter_scale, size=mid_coeffs.shape
                    )
                    dct_block[self.mid_freq_mask] = shrunk + jitter
                    perturbed_count += 1

                    # Inverse DCT
                    idct_block = cv2.idct(dct_block)
                    channel[r : r + self.block_size, col : col + self.block_size] = idct_block

            ycrcb[:, :, ch] = channel

        # Crop back to original dimensions
        ycrcb_unpadded = ycrcb[:h, :w, :]
        cleaned_bgr = cv2.cvtColor(
            np.clip(ycrcb_unpadded, 0, 255).astype(np.uint8), cv2.COLOR_YCrCb2BGR
        )

        return cleaned_bgr, {
            "dct_blocks_processed": total_blocks,
            "mid_frequency_jitter": self.jitter_scale,
        }
