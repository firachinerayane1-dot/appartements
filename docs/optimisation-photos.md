# Photos WebP

Les originaux sont conservés. Les pages servent des variantes WebP (qualité 80),
avec des largeurs de 320, 640, 960 et 1600 pixels au maximum, sans agrandissement.
L’orientation EXIF est appliquée avant conversion. Les dimensions et `srcset`
sont enregistrés : aucune conversion ni lecture d’image n’a lieu au rendu HTML.
Les nouvelles photos ajoutées via le modèle Photo sont optimisées à la sauvegarde.

Après déploiement du code, pour une base existante :

```bash
python manage.py migrate
python manage.py optimize_photos
python manage.py collectstatic --noinput
```

La commande `optimize_photos` ignore les photos déjà traitées. Les fichiers WebP
créés dans MEDIA_ROOT doivent être sauvegardés comme les autres médias.

Après remplacement d’une image statique originale :

```bash
python tools/optimize_static_photos.py
```

Si ses dimensions changent, mettre à jour les largeurs du srcset et les attributs
width/height dans les templates concernés. Le script ne supprime pas les originaux.

Vérification : tests `apartments.test_images`, puis contrôle réseau mobile dans
le navigateur. Les réductions de poids ne constituent pas une mesure de temps
d’affichage : celui-ci dépend du réseau, du cache et de l’écran.
