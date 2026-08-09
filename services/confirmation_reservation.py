from decimal import Decimal
from io import BytesIO
from pathlib import Path

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils import timezone
from PIL import Image, ImageDraw, ImageFont


LARGEUR_PAGE = 1240
HAUTEUR_PAGE = 1754
MARGE = 90

BLANC = '#FFFFFF'
IVOIRE = '#F6F1E7'
VERT = '#1F4B3F'
VERT_CLAIR = '#E5EFEA'
OR = '#C89B55'
MARINE = '#17233C'
GRIS = '#667085'
GRIS_CLAIR = '#E7E8EA'
ROUGE_CLAIR = '#F8E8E4'
ROUGE = '#923B32'

POLITIQUES = [
    (
        'Garantie',
        "Une garantie de {garantie} MAD est à remettre à l'arrivée sous forme "
        "d'espèces ou de pré-autorisation sur carte bancaire. Elle est restituée "
        "après vérification de l'état du logement et de ses équipements.",
    ),
    (
        'Attribution',
        "L'attribution du logement s'effectue le jour de l'arrivée selon les "
        "disponibilités et l'organisation de la résidence.",
    ),
    (
        'Départ tardif',
        "Tout logement non libéré à partir de l'heure de départ est facturé à 50 % "
        "au titre du Day-Use. Au-delà de 15 h, une nuit complète peut être facturée.",
    ),
    (
        'Non-présentation',
        "En cas de non-présentation, la réservation reste non modifiable, non "
        "annulable et non remboursable.",
    ),
]


def _format_montant(montant):
    return f'{Decimal(montant):,.2f}'.replace(',', ' ').replace('.', ',')


def _contexte_confirmation(paiement):
    reservation = paiement.reservation
    client = reservation.client
    garantie = _format_montant(settings.RAHAL_STAY_GUARANTEE_AMOUNT)
    politiques = [
        {'titre': titre, 'texte': texte.format(garantie=garantie)}
        for titre, texte in POLITIQUES
    ]
    return {
        'paiement': paiement,
        'reservation': reservation,
        'client': client,
        'nom_client': f'{client.prenom} {client.nom}'.strip(),
        'date_paiement': timezone.localtime(paiement.date_paiement),
        'montant': _format_montant(paiement.montant),
        'solde': _format_montant(Decimal('0')),
        'garantie': garantie,
        'politiques': politiques,
        'marque': settings.RAHAL_STAY_NAME,
        'adresse': settings.RAHAL_STAY_ADDRESS,
        'coordonnees': settings.RAHAL_STAY_COORDINATES,
        'email_contact': settings.RAHAL_STAY_CONTACT_EMAIL,
        'telephone_contact': settings.RAHAL_STAY_CONTACT_PHONE,
        'check_in': settings.RAHAL_STAY_CHECK_IN,
        'check_out': settings.RAHAL_STAY_CHECK_OUT,
    }


def _charger_police(taille, gras=False):
    candidats = [
        Path(settings.BASE_DIR) / 'static' / 'fonts' / (
            'NotoSans-Bold.ttf' if gras else 'NotoSans-Regular.ttf'
        ),
        Path('/usr/share/fonts/google-noto-vf/NotoSans[wght].ttf'),
        Path('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf' if gras else
             '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'),
    ]
    for chemin in candidats:
        if chemin.exists():
            police = ImageFont.truetype(str(chemin), taille)
            if gras:
                try:
                    police.set_variation_by_name('Bold')
                except (AttributeError, OSError, ValueError):
                    pass
            return police
    return ImageFont.load_default(size=taille)


def _lignes_ajustees(dessin, texte, police, largeur):
    lignes = []
    for paragraphe in str(texte).splitlines() or ['']:
        mots = paragraphe.split()
        if not mots:
            lignes.append('')
            continue
        ligne = mots[0]
        for mot in mots[1:]:
            essai = f'{ligne} {mot}'
            if dessin.textlength(essai, font=police) <= largeur:
                ligne = essai
            else:
                lignes.append(ligne)
                ligne = mot
        lignes.append(ligne)
    return lignes


def _texte(dessin, xy, texte, police, couleur=MARINE, largeur=None, interligne=8):
    x, y = xy
    lignes = (
        _lignes_ajustees(dessin, texte, police, largeur)
        if largeur
        else str(texte).splitlines()
    )
    hauteur = police.getbbox('Ag')[3] - police.getbbox('Ag')[1]
    for ligne in lignes:
        dessin.text((x, y), ligne, font=police, fill=couleur)
        y += hauteur + interligne
    return y


def _entete(dessin, sous_titre):
    police_logo = _charger_police(45, gras=True)
    police_marque = _charger_police(31, gras=True)
    police_sous_titre = _charger_police(19)

    dessin.ellipse((MARGE, 62, MARGE + 78, 140), fill=VERT)
    dessin.text((MARGE + 23, 70), 'F', font=police_logo, fill=BLANC)
    dessin.text((MARGE + 100, 70), settings.RAHAL_STAY_NAME.upper(), font=police_marque, fill=MARINE)
    dessin.text((MARGE + 102, 112), sous_titre, font=police_sous_titre, fill=GRIS)
    dessin.line((MARGE, 165, LARGEUR_PAGE - MARGE, 165), fill=OR, width=4)


def _pied_de_page(dessin, page):
    police = _charger_police(17)
    y = HAUTEUR_PAGE - 70
    dessin.line((MARGE, y - 18, LARGEUR_PAGE - MARGE, y - 18), fill=GRIS_CLAIR, width=2)
    dessin.text((MARGE, y), f'{settings.RAHAL_STAY_NAME} · Sidi Rahal', font=police, fill=GRIS)
    numero = f'Page {page}/2'
    largeur = dessin.textlength(numero, font=police)
    dessin.text((LARGEUR_PAGE - MARGE - largeur, y), numero, font=police, fill=GRIS)


def _champ(dessin, x, y, libelle, valeur, largeur):
    police_libelle = _charger_police(17, gras=True)
    police_valeur = _charger_police(23)
    dessin.text((x, y), libelle.upper(), font=police_libelle, fill=GRIS)
    return _texte(dessin, (x, y + 30), valeur, police_valeur, largeur=largeur, interligne=5)


def _page_confirmation(contexte):
    image = Image.new('RGB', (LARGEUR_PAGE, HAUTEUR_PAGE), BLANC)
    dessin = ImageDraw.Draw(image)
    _entete(dessin, 'Résidence Amwaj · Sidi Rahal')

    police_titre = _charger_police(39, gras=True)
    police_numero = _charger_police(32, gras=True)
    police_texte = _charger_police(21)
    police_section = _charger_police(25, gras=True)

    dessin.text((MARGE, 205), 'CONFIRMATION DE RÉSERVATION', font=police_titre, fill=VERT)
    dessin.rounded_rectangle(
        (MARGE, 272, LARGEUR_PAGE - MARGE, 365),
        radius=18,
        fill=IVOIRE,
        outline=OR,
        width=2,
    )
    dessin.text((MARGE + 28, 293), 'NUMÉRO DE RÉSERVATION', font=_charger_police(18, gras=True), fill=GRIS)
    numero = contexte['reservation'].numero_reservation
    largeur_numero = dessin.textlength(numero, font=police_numero)
    dessin.text((LARGEUR_PAGE - MARGE - 28 - largeur_numero, 290), numero, font=police_numero, fill=MARINE)

    nom_client = contexte['nom_client'].upper()
    y = _texte(
        dessin,
        (MARGE, 405),
        f'Cher(e) {nom_client},',
        _charger_police(24, gras=True),
    )
    y = _texte(
        dessin,
        (MARGE, y + 12),
        (
            f"Merci d'avoir choisi {contexte['marque']}. Votre réservation est "
            "CONFIRMÉE et votre paiement a bien été enregistré. Présentez cette "
            "confirmation lors de votre arrivée."
        ),
        police_texte,
        largeur=LARGEUR_PAGE - (2 * MARGE),
        interligne=8,
    )

    y += 26
    dessin.text((MARGE, y), 'Détails de la réservation', font=police_section, fill=VERT)
    y += 48
    largeur_colonne = (LARGEUR_PAGE - (2 * MARGE) - 50) // 2
    reservation = contexte['reservation']
    gauche = [
        ('Date de réservation', reservation.date_reservation.strftime('%d/%m/%Y')),
        ("Date d'arrivée", reservation.date_debut.strftime('%d/%m/%Y')),
        ('Date de départ', reservation.date_fin.strftime('%d/%m/%Y')),
    ]
    droite = [
        ('Nombre de nuitées', str(reservation.get_duree())),
        ('Check-In', contexte['check_in']),
        ('Check-Out', contexte['check_out']),
    ]
    y_gauche = y
    y_droite = y
    for libelle, valeur in gauche:
        y_gauche = _champ(dessin, MARGE, y_gauche, libelle, valeur, largeur_colonne) + 20
    for libelle, valeur in droite:
        y_droite = _champ(
            dessin,
            MARGE + largeur_colonne + 50,
            y_droite,
            libelle,
            valeur,
            largeur_colonne,
        ) + 20
    y = max(y_gauche, y_droite) + 10

    dessin.line((MARGE, y, LARGEUR_PAGE - MARGE, y), fill=GRIS_CLAIR, width=2)
    y += 30
    dessin.text((MARGE, y), 'Hébergement et client', font=police_section, fill=VERT)
    y += 48
    y = _champ(
        dessin,
        MARGE,
        y,
        'Type de logement',
        reservation.appartement.titre,
        largeur_colonne,
    ) + 16
    description = reservation.appartement.description
    if len(description) > 260:
        description = f'{description[:257].rstrip()}…'
    y = _champ(
        dessin,
        MARGE,
        y,
        'Description',
        description,
        LARGEUR_PAGE - (2 * MARGE),
    ) + 16
    y = _champ(
        dessin,
        MARGE,
        y,
        'Capacité',
        f"Jusqu'à {reservation.appartement.capacite} voyageur(s) · 1 logement",
        LARGEUR_PAGE - (2 * MARGE),
    ) + 22

    hauteur_tarif = 210
    dessin.rounded_rectangle(
        (MARGE, y, LARGEUR_PAGE - MARGE, y + hauteur_tarif),
        radius=18,
        fill=VERT_CLAIR,
    )
    dessin.text((MARGE + 28, y + 25), 'DÉTAILS DU TARIF', font=_charger_police(18, gras=True), fill=VERT)
    libelles = ['Total hébergement', 'Total payé', 'Montant dû']
    valeurs = [f"{contexte['montant']} MAD", f"{contexte['montant']} MAD", f"{contexte['solde']} MAD"]
    ligne_y = y + 70
    for index, (libelle, valeur) in enumerate(zip(libelles, valeurs)):
        dessin.text((MARGE + 28, ligne_y), libelle, font=police_texte, fill=MARINE)
        largeur_valeur = dessin.textlength(valeur, font=_charger_police(21, gras=index == 1))
        dessin.text(
            (LARGEUR_PAGE - MARGE - 28 - largeur_valeur, ligne_y),
            valeur,
            font=_charger_police(21, gras=index == 1),
            fill=VERT if index == 1 else MARINE,
        )
        ligne_y += 45
    y += hauteur_tarif + 28

    dessin.rounded_rectangle(
        (MARGE, y, LARGEUR_PAGE - MARGE, y + 115),
        radius=18,
        fill=VERT,
    )
    dessin.text((MARGE + 28, y + 20), 'MONTANT DE LA RÉSERVATION', font=_charger_police(17, gras=True), fill=BLANC)
    montant_final = f"{contexte['montant']} MAD"
    largeur_montant = dessin.textlength(montant_final, font=_charger_police(34, gras=True))
    dessin.text(
        (LARGEUR_PAGE - MARGE - 28 - largeur_montant, y + 48),
        montant_final,
        font=_charger_police(34, gras=True),
        fill=BLANC,
    )
    y += 145
    dessin.text((MARGE, y), 'Réservé et payé par', font=_charger_police(18, gras=True), fill=GRIS)
    dessin.text((MARGE, y + 32), contexte['nom_client'], font=_charger_police(23, gras=True), fill=MARINE)
    dessin.text((MARGE, y + 68), contexte['client'].email, font=police_texte, fill=GRIS)

    _pied_de_page(dessin, 1)
    return image


def _page_politiques(contexte):
    image = Image.new('RGB', (LARGEUR_PAGE, HAUTEUR_PAGE), BLANC)
    dessin = ImageDraw.Draw(image)
    _entete(dessin, f"Confirmation {contexte['reservation'].numero_reservation}")

    police_titre = _charger_police(38, gras=True)
    police_section = _charger_police(24, gras=True)
    police_texte = _charger_police(20)

    dessin.text((MARGE, 210), 'CONDITIONS ET POLITIQUES', font=police_titre, fill=VERT)
    dessin.rounded_rectangle(
        (MARGE, 280, LARGEUR_PAGE - MARGE, 405),
        radius=18,
        fill=ROUGE_CLAIR,
    )
    dessin.text((MARGE + 28, 305), "POLITIQUE D'ANNULATION", font=_charger_police(17, gras=True), fill=ROUGE)
    dessin.text(
        (MARGE + 28, 347),
        'NON ANNULABLE · NON REMBOURSABLE',
        font=_charger_police(27, gras=True),
        fill=ROUGE,
    )

    y = 450
    for politique in contexte['politiques']:
        dessin.text((MARGE, y), politique['titre'], font=police_section, fill=VERT)
        y = _texte(
            dessin,
            (MARGE, y + 38),
            politique['texte'],
            police_texte,
            couleur=MARINE,
            largeur=LARGEUR_PAGE - (2 * MARGE),
            interligne=7,
        ) + 26

    dessin.rounded_rectangle(
        (MARGE, y, LARGEUR_PAGE - MARGE, y + 125),
        radius=18,
        fill=IVOIRE,
    )
    dessin.text((MARGE + 28, y + 23), f"CHECK-IN : {contexte['check_in']}", font=_charger_police(22, gras=True), fill=MARINE)
    dessin.text((MARGE + 28, y + 70), f"CHECK-OUT : {contexte['check_out']}", font=_charger_police(22, gras=True), fill=MARINE)
    y += 165

    dessin.text((MARGE, y), f"Coordonnées {contexte['marque']}", font=police_section, fill=VERT)
    y += 46
    coordonnees = [
        contexte['adresse'],
        f"Coordonnées GPS : {contexte['coordonnees']}",
        contexte['email_contact'],
    ]
    if contexte['telephone_contact']:
        coordonnees.append(f"Tél. : {contexte['telephone_contact']}")
    for ligne in coordonnees:
        dessin.text((MARGE, y), ligne, font=police_texte, fill=MARINE)
        y += 38

    y += 28
    y = _texte(
        dessin,
        (MARGE, y),
        (
            "Ce document et l'e-mail associé sont générés automatiquement. "
            f"Pour toute demande supplémentaire, contactez {contexte['marque']} en indiquant "
            f"le numéro de réservation {contexte['reservation'].numero_reservation}."
        ),
        _charger_police(18),
        couleur=GRIS,
        largeur=LARGEUR_PAGE - (2 * MARGE),
        interligne=6,
    )

    _pied_de_page(dessin, 2)
    return image


def generer_pdf_confirmation(paiement):
    contexte = _contexte_confirmation(paiement)
    pages = [_page_confirmation(contexte), _page_politiques(contexte)]
    flux = BytesIO()
    pages[0].save(
        flux,
        format='PDF',
        save_all=True,
        append_images=pages[1:],
        resolution=150,
        title=f"Confirmation {contexte['reservation'].numero_reservation}",
        author=settings.RAHAL_STAY_NAME,
    )
    return flux.getvalue()


def envoyer_email_confirmation(paiement):
    contexte = _contexte_confirmation(paiement)
    numero = contexte['reservation'].numero_reservation
    expediteur = (
        f"{settings.RAHAL_STAY_NAME} <{settings.EMAIL_HOST_USER}>"
        if settings.EMAIL_HOST_USER
        else settings.DEFAULT_FROM_EMAIL
    )
    email = EmailMultiAlternatives(
        subject=(
            f'Booking Reference Number {numero} - CONFIRMED, '
            f'{settings.RAHAL_STAY_NAME.upper()}'
        ),
        body=render_to_string('reservations/emails/confirmation.txt', contexte),
        from_email=expediteur,
        to=[contexte['client'].email],
    )
    email.attach_alternative(
        render_to_string('reservations/emails/confirmation.html', contexte),
        'text/html',
    )
    email.attach(
        f'confirmation-reservation-{numero}.pdf',
        generer_pdf_confirmation(paiement),
        'application/pdf',
    )
    return email.send()
