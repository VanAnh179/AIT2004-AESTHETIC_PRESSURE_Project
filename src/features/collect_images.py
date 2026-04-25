
import argparse
import shutil
from pathlib import Path

# ── Cấu hình đường dẫn ────────────────────────────────────────────────────────
#
#   Vị trí file: src/features/collect_images.py
#   parents[0] = src/features/
#   parents[1] = src/
#   parents[2] = AESTHETIC_PRESSURE/   ← project root
#
PROJECT_ROOT = Path(__file__).resolve().parents[2]
RAW_DIR      = PROJECT_ROOT / "data" / "raw"

SOURCE_DIRS = {
    "facebook":  RAW_DIR / "facebook",
    "shopee":    RAW_DIR / "shopee",
    "instagram": RAW_DIR / "instagram",
}

DEST_DIR = RAW_DIR / "image"

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp", ".tiff", ".tif"}


# ── Helpers ───────────────────────────────────────────────────────────────────

def build_dest_name(source_name: str, source_root: Path, img_path: Path) -> str:
    parts = img_path.relative_to(source_root).parts   # tuple các thành phần
    return f"{source_name}_{'_'.join(parts)}"


def unique_dest(dest_path: Path) -> Path:
    """Thêm hậu tố _1, _2, … cho đến khi không trùng."""
    if not dest_path.exists():
        return dest_path
    stem, suffix = dest_path.stem, dest_path.suffix
    i = 1
    while True:
        candidate = dest_path.with_name(f"{stem}_{i}{suffix}")
        if not candidate.exists():
            return candidate
        i += 1


# ── Hàm chính ─────────────────────────────────────────────────────────────────

def collect_images(dry_run: bool = False, move: bool = False) -> None:
    action = "di chuyển" if move else "sao chép"
    prefix = "[DRY-RUN] " if dry_run else ""

    if not dry_run:
        DEST_DIR.mkdir(parents=True, exist_ok=True)
    else:
        print(f"📁  Thư mục đích (sẽ tạo nếu chưa có): {DEST_DIR}\n")

    total = 0
    renamed = 0

    for source_name, source_root in SOURCE_DIRS.items():

        if not source_root.exists():
            print(f"⚠️  Không tìm thấy thư mục: {source_root}  →  bỏ qua.\n")
            continue

        # rglob lấy TẤT CẢ ảnh ở mọi cấp (kể cả nằm thẳng trong root)
        images = sorted(
            f for f in source_root.rglob("*")
            if f.is_file() and f.suffix.lower() in IMAGE_EXTENSIONS
        )

        print(f"📂  {source_name.upper():<12} │ {len(images):>4} ảnh  ({source_root})")

        if not images:
            print("      ℹ️  Không có ảnh nào.\n")
            continue

        for img in images:
            dest_name = build_dest_name(source_name, source_root, img)
            dest      = DEST_DIR / dest_name
            resolved  = unique_dest(dest)

            if resolved != dest:
                renamed += 1
                print(f"      ⚠️  Trùng tên → {resolved.name}")

            rel = img.relative_to(source_root)
            print(f"      {prefix}{action}: {rel}  →  {resolved.name}")

            if not dry_run:
                if move:
                    shutil.move(str(img), resolved)
                else:
                    shutil.copy2(img, resolved)

            total += 1

        print()

    # ── Tổng kết ──────────────────────────────────────────────────────────────
    print("─" * 60)
    print(f"✅  {'[DRY-RUN] ' if dry_run else ''}Hoàn tất!")
    print(f"   Tổng ảnh đã {action:<13}: {total}")
    print(f"   Đổi tên do trùng       : {renamed}")
    print(f"   Thư mục đích           : {DEST_DIR}")
    print("─" * 60)


# ── CLI ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Gom ảnh từ facebook/shopee/instagram → data/raw/image/"
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Chỉ in danh sách, không thực sự copy/move"
    )
    parser.add_argument(
        "--move", action="store_true",
        help="Di chuyển file thay vì sao chép"
    )
    args = parser.parse_args()
    collect_images(dry_run=args.dry_run, move=args.move)