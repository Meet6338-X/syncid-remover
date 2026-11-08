"""
C2PA, JUMBF & Deep Forensic Metadata Sanitizer.
Completely removes C2PA Content Credentials manifests, EXIF, XMP, IPTC, and AI provenance tags.
"""

import io
from PIL import Image
from typing import Tuple, Dict, Any, List


class C2PAStripper:
    """
    Scans, detects, and strips C2PA manifests (JUMBF boxes), EXIF headers,
    XMP packets, IPTC records, and generation metadata (e.g. ComfyUI / Stable Diffusion prompts).
    """

    @staticmethod
    def inspect_metadata(image_bytes: bytes) -> Dict[str, Any]:
        """
        Inspects raw image bytes for presence of C2PA, EXIF, XMP, and other AI signatures.
        """
        found_markers: List[str] = []

        # Check for C2PA JUMBF signatures
        if b"c2pa" in image_bytes or b"jumb" in image_bytes:
            found_markers.append("C2PA / JUMBF Manifest (Content Credentials)")

        # Check for XMP
        if b"<x:xmpmeta" in image_bytes or b"http://ns.adobe.com/xap/1.0/" in image_bytes:
            found_markers.append("Adobe XMP Metadata Packet")

        # Check for known AI generator signatures
        ai_generator_keywords = [
            b"SynthID",
            b"Google",
            b"Imagen",
            b"DALL-E",
            b"Midjourney",
            b"Stable Diffusion",
            b"parameters",
            b"Civitai",
            b"ComfyUI",
            b"InvokeAI",
        ]
        for kw in ai_generator_keywords:
            if kw in image_bytes:
                found_markers.append(f"AI Generator Signature ({kw.decode('utf-8', errors='ignore')})")

        # Check EXIF via PIL
        try:
            with Image.open(io.BytesIO(image_bytes)) as pil_img:
                info = pil_img.info
                if "exif" in info:
                    found_markers.append("Standard EXIF Header")
                if "icc_profile" in info:
                    found_markers.append("Color Profile Header (ICC)")
                for k in info.keys():
                    if k in ["XML:com.adobe.xmp", "prompt", "workflow"]:
                        found_markers.append(f"PNG Metadata Chunk: {k}")
        except Exception:
            pass

        return {
            "has_ai_metadata": len(found_markers) > 0,
            "detected_signatures": list(set(found_markers)),
            "byte_size": len(image_bytes),
        }

    @staticmethod
    def sanitize(
        image_bytes: bytes, output_format: str = "PNG", quality: int = 96
    ) -> Tuple[bytes, Dict[str, Any]]:
        """
        Loads pixel data only and writes a pristine, metadata-free byte stream.
        Guarantees 0 bytes of C2PA, EXIF, or provenance data in the final output.
        """
        pre_inspect = C2PAStripper.inspect_metadata(image_bytes)

        # Open image into pure RGB/RGBA bitmap
        with Image.open(io.BytesIO(image_bytes)) as img:
            # Drop all ICC profiles, exif, and info dictionaries
            data = list(img.getdata())
            clean_img = Image.new(img.mode, img.size)
            clean_img.putdata(data)

            output_io = io.BytesIO()

            if output_format.upper() in ["JPG", "JPEG"]:
                if clean_img.mode in ("RGBA", "P"):
                    clean_img = clean_img.convert("RGB")
                clean_img.save(
                    output_io,
                    format="JPEG",
                    quality=quality,
                    optimize=True,
                    subsampling=0,  # 4:4:4 sampling
                )
            else:
                clean_img.save(
                    output_io,
                    format="PNG",
                    optimize=True,
                    compress_level=6,
                )

            clean_bytes = output_io.getvalue()

        post_inspect = C2PAStripper.inspect_metadata(clean_bytes)

        return clean_bytes, {
            "original_size": len(image_bytes),
            "clean_size": len(clean_bytes),
            "stripped_signatures": pre_inspect["detected_signatures"],
            "residual_signatures": post_inspect["detected_signatures"],
            "sanitized": len(post_inspect["detected_signatures"]) == 0,
        }
