"""Regenerate responsive static WebP assets from preserved originals."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from apartments.image_processing import webp_variants

ROOT = Path(__file__).resolve().parents[1]


def main():
    before = after = 0
    for source in sorted((ROOT / 'static/img').rglob('*')):
        if source.suffix.lower() not in {'.jpeg', '.jpg', '.png'}:
            continue
        variants = list(webp_variants(source))
        for width, height, content in variants:
            source.with_name(f'{source.stem}-{width}.webp').write_bytes(content)
        source.with_suffix('.webp').write_bytes(variants[-1][2])
        before += source.stat().st_size
        after += len(variants[-1][2])
    print(f'Images statiques, grandes versions : {before} → {after} octets ({1-after/before:.0%} de réduction)')


if __name__ == '__main__':
    main()
