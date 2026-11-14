"""WebP derivatives generated on upload, never during page rendering."""
from io import BytesIO
from PIL import Image, ImageOps

WIDTHS = (320, 640, 960, 1600)


def webp_variants(source):
    with Image.open(source) as original:
        image = ImageOps.exif_transpose(original)
        image = image.convert('RGBA' if 'A' in image.getbands() or 'transparency' in image.info else 'RGB')
        widths = sorted({min(width, image.width) for width in WIDTHS})
        for width in widths:
            resized = image.resize(
                (width, max(1, round(image.height * width / image.width))),
                Image.Resampling.LANCZOS,
            )
            output = BytesIO()
            resized.save(output, format='WEBP', quality=80, method=6)
            yield resized.width, resized.height, output.getvalue()
