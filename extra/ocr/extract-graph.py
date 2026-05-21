# OCR extraction of graph in image
# Fidelity is very, very low:
# - many characters are not recognized correctly
# - graph structure is ignored

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path

from PIL import Image, ImageFilter, ImageOps


def preprocess(src: Path, out_dir: Path, stem: str) -> list[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    img = Image.open(src)
    outputs: list[Path] = []

    gray = ImageOps.autocontrast(img.convert("L")).resize((img.width * 6, img.height * 6))
    gray = gray.filter(ImageFilter.MedianFilter(size=3)).filter(ImageFilter.SHARPEN)
    gray_path = out_dir / f"{stem}_gray.png"
    gray.save(gray_path)
    outputs.append(gray_path)

    bw = gray.point(lambda p: 255 if p > 180 else 0)
    bw_path = out_dir / f"{stem}_bw.png"
    bw.save(bw_path)
    outputs.append(bw_path)

    w, h = img.size
    boxes = {
        "top_left": (0, 0, w // 2, h // 2),
        "top_right": (w // 2, 0, w, h // 2),
        "bottom_left": (0, h // 2, w // 2, h),
        "bottom_right": (w // 2, h // 2, w, h),
    }
    for label, box in boxes.items():
        crop = img.crop(box).resize(((box[2] - box[0]) * 4, (box[3] - box[1]) * 4))
        path = out_dir / f"{stem}_{label}.png"
        crop.save(path)
        outputs.append(path)

    return outputs


def run_tesseract(image_path: Path, psm: int = 11) -> str:
    out_base = image_path.with_suffix("")
    subprocess.run([
        "tesseract",
        str(image_path),
        str(out_base),
        "--psm",
        str(psm),
    ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return out_base.with_suffix(".txt").read_text()


def extract_ocr(src: Path, out_dir: Path) -> dict:
    stem = src.stem
    images = preprocess(src, out_dir, stem)
    ocr = {}
    for image in images:
        psm = 4 if image.name.endswith("_gray.png") else 11
        try:
            ocr[image.name] = run_tesseract(image, psm=psm)
        except subprocess.CalledProcessError as e:
            ocr[image.name] = f"ERROR: {e}"
    return ocr


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("images", nargs="+", type=Path)
    parser.add_argument("--out-dir", type=Path, default=Path("tmp/ocr"))
    parser.add_argument("--json-out", type=Path)
    args = parser.parse_args()

    data = {str(image): extract_ocr(image, args.out_dir) for image in args.images}
    text = json.dumps(data, indent=2)
    if args.json_out:
        args.json_out.write_text(text)
    else:
        print(text)


if __name__ == "__main__":
    main()
