"""
color_processor.py
------------------
Trích xuất 2 đặc trưng từ ảnh trong data/processed/image_processed/:

    1. color_entropy      – Shannon Entropy trên histogram màu RGB 3D
                            Cao → màu phong phú/phân tán
                            Thấp → màu đơn điệu/tập trung

    2. compression_ratio  – raw_pixel_bytes / actual_file_bytes
                            Cao  → ảnh đơn giản, nén tốt
                            Thấp → ảnh phức tạp, nhiều chi tiết

Đặc điểm ảnh đầu vào (data/processed/image_processed):
    - Chiều rộng chuẩn 1000px, tỷ lệ khung hình giữ nguyên
    - Toàn bộ đã ở chuẩn RGB

Đầu ra: data/processed/features_cv.csv
    Cột: image_id, color_entropy, compression_ratio

Cách dùng:
    python color_processor.py
    python color_processor.py --input  data/processed/image_processed
    python color_processor.py --output data/processed/features_cv.csv
"""

import argparse
import csv
from pathlib import Path

import numpy as np
from PIL import Image

# ── Cấu hình mặc định ─────────────────────────────────────────────────────────
#   Vị trí file : src/features/color_processor.py
#   parents[0]  = src/features/
#   parents[1]  = src/
#   parents[2]  = AESTHETIC_PRESSURE/  ← project root

PROJECT_ROOT   = Path(__file__).resolve().parents[2]
DEFAULT_INPUT  = PROJECT_ROOT / "data" / "processed" / "image_processed"
DEFAULT_OUTPUT = PROJECT_ROOT / "data" / "processed" / "features_cv.csv"

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tiff", ".tif"}

# Số bins cho histogram mỗi kênh (32 bins → 32³ = 32768 ô màu)
HIST_BINS = 32


# ── Hàm đo Color Entropy ──────────────────────────────────────────────────────

def compute_color_entropy(img: Image.Image) -> float:
    """
    Shannon Entropy trên histogram màu 3D (R × G × B).

    H = -Σ p(i) * log2(p(i))

    - Histogram 3D với HIST_BINS bins mỗi kênh
    - Normalize thành phân phối xác suất
    - Tính entropy (bỏ qua bin p=0 để tránh log(0))

    Returns:
        float: entropy tính bằng bits
    """
    arr = np.array(img, dtype=np.float32)  # shape (H, W, 3)

    hist, _ = np.histogramdd(
        arr.reshape(-1, 3),
        bins=HIST_BINS,
        range=[[0, 256], [0, 256], [0, 256]]
    )

    total = hist.sum()
    if total == 0:
        return 0.0

    prob    = hist / total
    nonzero = prob[prob > 0]
    entropy = float(-np.sum(nonzero * np.log2(nonzero)))
    return round(entropy, 6)


# ── Hàm đo Compression Ratio ──────────────────────────────────────────────────

def compute_compression_ratio(img: Image.Image, file_path: Path) -> float:
    """
    Tỉ lệ nén dựa trên kích thước RGB thuần vs kích thước file thực tế.

    raw_size  = width × height × 3  (bytes nếu lưu thô, 3 kênh RGB × 1 byte/kênh)
    file_size = dung lượng file thực trên đĩa (bytes)
    ratio     = raw_size / file_size

    Returns:
        float: compression_ratio
    """
    file_size = file_path.stat().st_size
    if file_size == 0:
        return 0.0

    w, h     = img.size      # kích thước ảnh (width=1000px)
    raw_size = w * h * 3     # 3 kênh RGB, 1 byte/kênh

    return round(raw_size / file_size, 6)


# ── Hàm chính ─────────────────────────────────────────────────────────────────

def extract_features(input_dir: Path, output_csv: Path) -> None:
    """
    Duyệt toàn bộ ảnh trong input_dir, trích xuất 2 đặc trưng,
    ghi ra output_csv.
    """
    if not input_dir.exists():
        print(f"[LOI] Khong tim thay thu muc: {input_dir}")
        return

    image_files = sorted(
        f for f in input_dir.rglob("*")
        if f.is_file() and f.suffix.lower() in IMAGE_EXTENSIONS
    )

    if not image_files:
        print(f"[LOI] Khong co anh nao trong: {input_dir}")
        return

    print(f"Tim thay {len(image_files)} anh trong: {input_dir}")
    print(f"Dang trich xuat dac trung...\n")
    print(f"{'#':<6} {'image_id':<22} {'kich_thuoc':<14} "
          f"{'color_entropy':>14} {'compression_ratio':>18}")
    print("-" * 78)

    rows   = []
    errors = []

    for i, img_path in enumerate(image_files, 1):
        image_id = img_path.stem   # vd: fac_001

        try:
            with Image.open(img_path) as img:
                img.load()

                entropy = compute_color_entropy(img)
                ratio   = compute_compression_ratio(img, img_path)

            rows.append({
                "image_id":          image_id,
                "color_entropy":     entropy,
                "compression_ratio": ratio,
            })

            size_str = f"{img.size[0]}x{img.size[1]}"
            print(f"{i:<6} {image_id:<22} {size_str:<14} "
                  f"{entropy:>14.6f} {ratio:>18.6f}")

        except Exception as e:
            errors.append((image_id, str(e)))
            print(f"{i:<6} {image_id:<22} [LOI] {e}")

    # ── Ghi CSV ───────────────────────────────────────────────────────────────
    output_csv.parent.mkdir(parents=True, exist_ok=True)

    with open(output_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f, fieldnames=["image_id", "color_entropy", "compression_ratio"]
        )
        writer.writeheader()
        writer.writerows(rows)

    # ── Tổng kết ──────────────────────────────────────────────────────────────
    print("\n" + "=" * 60)
    print(f"Hoan tat!")
    print(f"   Tong anh xu ly    : {len(image_files)}")
    print(f"   Thanh cong        : {len(rows)}")
    print(f"   Loi               : {len(errors)}")
    print(f"   Output CSV        : {output_csv}")
    print("=" * 60)

    if errors:
        print("\nDanh sach loi:")
        for eid, emsg in errors:
            print(f"   {eid}: {emsg}")


# ── CLI ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Trich xuat color_entropy va compression_ratio tu anh RGB"
    )
    parser.add_argument(
        "--input",  type=Path, default=DEFAULT_INPUT,
        help=f"Thu muc anh dau vao (mac dinh: {DEFAULT_INPUT})"
    )
    parser.add_argument(
        "--output", type=Path, default=DEFAULT_OUTPUT,
        help=f"Duong dan CSV dau ra (mac dinh: {DEFAULT_OUTPUT})"
    )
    args = parser.parse_args()
    extract_features(args.input, args.output)