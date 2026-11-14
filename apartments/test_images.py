from io import BytesIO
from tempfile import TemporaryDirectory

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from PIL import Image

from .image_processing import webp_variants
from .models import Appartement, Photo


class PhotoOptimizationTests(TestCase):
    def setUp(self):
        self.directory = TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.settings_override = override_settings(MEDIA_ROOT=self.directory.name)
        self.settings_override.enable()
        self.addCleanup(self.settings_override.disable)
        self.appartement = Appartement.objects.create(titre='Test', prix_par_nuit=700)

    def upload(self, size=(1800, 1200)):
        output = BytesIO()
        Image.new('RGB', size, 'green').save(output, 'JPEG')
        return SimpleUploadedFile('photo.jpg', output.getvalue(), content_type='image/jpeg')

    def test_upload_generates_webp_and_preserves_original(self):
        photo = Photo.objects.create(appartement=self.appartement, image=self.upload())
        photo.refresh_from_db()
        self.assertEqual([v['width'] for v in photo.variantes], [320, 640, 960, 1600])
        self.assertTrue(photo.image.storage.exists(photo.image.name))
        for variant in photo.variantes:
            with photo.image.storage.open(variant['name']) as source, Image.open(source) as image:
                self.assertEqual(image.format, 'WEBP')
                self.assertEqual(image.size, (variant['width'], variant['height']))
        self.assertIn('-640.webp', photo.image_url)
        self.assertIn('1600w', photo.image_srcset)
        old = photo.variantes
        photo.legende = 'Nouveau texte'
        photo.save()
        self.assertEqual(photo.variantes, old)
        photo.image = self.upload((400, 300))
        photo.save()
        self.assertNotEqual(photo.variantes, old)
        self.assertEqual(photo.image_width, 400)

    def test_small_images_are_not_enlarged(self):
        variants = list(webp_variants(self.upload((100, 60))))
        self.assertEqual([(w, h) for w, h, data in variants], [(100, 60)])

    def test_exif_orientation_is_applied(self):
        output = BytesIO()
        exif = Image.Exif()
        exif[274] = 6
        Image.new('RGB', (120, 80)).save(output, 'JPEG', exif=exif)
        output.seek(0)
        variants = list(webp_variants(output))
        self.assertEqual(variants[0][:2], (80, 120))
