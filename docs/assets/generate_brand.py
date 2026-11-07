"""
Generates the official DeSynth Brand Identity Assets:
1. `brand-icon.svg` - Scalable vector emblem (Prism, Spectral Frequencies, Shield)
2. `brand-icon.png` - High-resolution (1024x1024) PNG icon
3. `brand-banner.svg` & `.png` - Hero GitHub Repository Header Banner
"""

import os
from PIL import Image, ImageDraw, ImageFilter
import math

ASSETS_DIR = r"C:\Users\shahm\Projects\desynth\docs\assets"
os.makedirs(ASSETS_DIR, exist_ok=True)

# 1. Create clean SVG Brand Icon
svg_icon = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512" width="100%" height="100%">
  <defs>
    <!-- Background Gradient -->
    <linearGradient id="bgGrad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#FFFFFF"/>
      <stop offset="100%" stop-color="#F8FAFC"/>
    </linearGradient>

    <!-- Shield Border Gradient -->
    <linearGradient id="shieldBorder" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#3B82F6"/>
      <stop offset="50%" stop-color="#6366F1"/>
      <stop offset="100%" stop-color="#06B6D4"/>
    </linearGradient>

    <!-- Prism Refraction Beam -->
    <linearGradient id="beamGrad" x1="0%" y1="50%" x2="100%" y2="50%">
      <stop offset="0%" stop-color="#60A5FA" stop-opacity="0.8"/>
      <stop offset="50%" stop-color="#818CF8" stop-opacity="0.9"/>
      <stop offset="100%" stop-color="#2DD4BF" stop-opacity="0.85"/>
    </linearGradient>

    <!-- Core Glow Filter -->
    <filter id="softGlow" x="-20%" y="-20%" width="140%" height="140%">
      <feGaussianBlur stdDeviation="8" result="blur"/>
      <feComposite in="SourceGraphic" in2="blur" operator="over"/>
    </filter>
  </defs>

  <!-- Canvas Base -->
  <rect width="512" height="512" rx="112" fill="url(#bgGrad)"/>
  <rect width="512" height="512" rx="112" fill="none" stroke="#E2E8F0" stroke-width="4"/>

  <!-- Frequency Grid Rings (Background Watermark Dissolution) -->
  <g opacity="0.45" stroke="#CBD5E1" stroke-width="1.5" stroke-dasharray="4 6" fill="none">
    <circle cx="256" cy="256" r="190"/>
    <circle cx="256" cy="256" r="145"/>
    <circle cx="256" cy="256" r="95"/>
  </g>

  <!-- Outer Protective Shield Contour -->
  <path d="M 256,84 L 388,146 C 388,272 334,364 256,428 C 178,364 124,272 124,146 Z"
        fill="#FFFFFF"
        stroke="url(#shieldBorder)"
        stroke-width="10"
        stroke-linejoin="round"
        filter="drop-shadow(0 16px 32px rgba(99,102,241,0.12))"/>

  <!-- Inner Spectral Wave Lines (Disrupted Frequency Patterns) -->
  <path d="M 168,220 Q 212,185 256,220 T 344,220" fill="none" stroke="#93C5FD" stroke-width="4" stroke-linecap="round"/>
  <path d="M 160,256 Q 208,215 256,256 T 352,256" fill="none" stroke="url(#beamGrad)" stroke-width="5" stroke-linecap="round"/>
  <path d="M 172,292 Q 214,250 256,292 T 340,292" fill="none" stroke="#5EEAD4" stroke-width="4" stroke-linecap="round"/>

  <!-- Central Optical Prism Diamond -->
  <polygon points="256,150 316,256 256,362 196,256"
           fill="url(#beamGrad)"
           opacity="0.18"/>
  <polygon points="256,150 316,256 256,362 196,256"
           fill="none"
           stroke="#4F46E5"
           stroke-width="5"
           stroke-linejoin="round"/>

  <!-- Core Pure Refraction Focal Point -->
  <circle cx="256" cy="256" r="14" fill="#4F46E5" filter="url(#softGlow)"/>
  <circle cx="256" cy="256" r="6" fill="#FFFFFF"/>
</svg>
"""

with open(os.path.join(ASSETS_DIR, "brand-icon.svg"), "w", encoding="utf-8") as f:
    f.write(svg_icon)


# 2. Render a high-resolution PIL Icon (1024x1024) with pristine mathematical geometry
def create_png_icon():
    size = 1024
    img = Image.new("RGBA", (size, size), (255, 255, 255, 0))
    draw = ImageDraw.Draw(img)

    # Rounded rectangle background
    rx = 224
    draw.rounded_rectangle([(32, 32), (size - 32, size - 32)], radius=rx, fill=(255, 255, 255, 255), outline=(226, 232, 240, 255), width=8)

    cx, cy = size // 2, size // 2

    # Draw subtle concentric frequency rings
    for r in [380, 290, 190]:
        draw.ellipse([cx - r, cy - r, cx + r, cy + r], outline=(203, 213, 225, 120), width=3)

    # Draw Shield outline
    shield_pts = [
        (cx, 168),
        (cx + 264, 292),
        (cx + 264, 544),
        (cx, 856),
        (cx - 264, 544),
        (cx - 264, 292),
    ]
    draw.polygon(shield_pts, fill=(248, 250, 252, 255), outline=(79, 70, 229, 255))

    # Inner spectral wave curves
    for y_offset, color in [(-72, (96, 165, 250)), (0, (79, 70, 229)), (72, (45, 212, 191))]:
        wave_pts = []
        for x in range(cx - 180, cx + 181, 4):
            dx = (x - cx) / 180.0
            y = cy + y_offset + math.sin(dx * math.pi * 2.2) * 42.0
            wave_pts.append((x, int(y)))
        for i in range(len(wave_pts) - 1):
            draw.line([wave_pts[i], wave_pts[i + 1]], fill=color + (255,), width=10)

    # Central Prism Diamond
    diamond_pts = [(cx, cy - 212), (cx + 120, cy), (cx, cy + 212), (cx - 120, cy)]
    draw.polygon(diamond_pts, fill=(238, 242, 255, 180), outline=(67, 56, 202, 255))

    # Center beam circle
    draw.ellipse([cx - 28, cy - 28, cx + 28, cy + 28], fill=(79, 70, 229, 255))
    draw.ellipse([cx - 12, cy - 12, cx + 12, cy + 12], fill=(255, 255, 255, 255))

    img.save(os.path.join(ASSETS_DIR, "brand-icon.png"), "PNG")
    print("Created brand-icon.svg and brand-icon.png successfully!")

create_png_icon()
