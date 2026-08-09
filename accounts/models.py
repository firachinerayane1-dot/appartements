from django.db import models
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.contrib.auth.base_user import BaseUserManager
from django.core.exceptions import ValidationError


class UtilisateurManager(BaseUserManager):
    """
    Tells Django HOW to create a user when there's no username field —
    only email + password. Django doesn't know how to do this by default,
    so we have to teach it.
    """

    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("L'email est obligatoire.")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)  # hashes the password, never store it raw
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        # This is what runs when you type: python manage.py createsuperuser
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('role', Utilisateur.ADMINISTRATEUR)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Le superuser doit avoir is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Le superuser doit avoir is_superuser=True.')

        return self.create_user(email, password, **extra_fields)


class Utilisateur(AbstractBaseUser, PermissionsMixin):
    # --- Roles, matching your class diagram's subclasses ---
    CLIENT_REGULIER = 'CLIENT_REGULIER'
    CLIENT_FM6 = 'ENSEIGNANT'
    ENSEIGNANT = CLIENT_FM6  # Alias conservé pour les anciennes données.
    ADMINISTRATEUR = 'ADMINISTRATEUR'

    ROLE_CHOICES = [
        (CLIENT_REGULIER, 'Client Régulier'),
        (CLIENT_FM6, 'Client FM6'),
        (ADMINISTRATEUR, 'Administrateur'),
    ]

    # --- Fields from your diagram ---
    email = models.EmailField(unique=True)
    nom = models.CharField(max_length=100)
    prenom = models.CharField(max_length=100)
    telephone = models.CharField(max_length=20, blank=True)

    # Le code historique ENSEIGNANT est conservé en base pour éviter une rupture
    # des comptes existants, mais il représente désormais le type Client FM6.
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default=CLIENT_REGULIER)
    matricule = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        unique=True,
        error_messages={'unique': "Ce numéro d'adhérent est déjà utilisé."},
    )
    consentement_donnees_le = models.DateTimeField(blank=True, null=True, editable=False)

    # --- Django bookkeeping fields ---
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)  # controls access to /admin
    date_joined = models.DateTimeField(auto_now_add=True)

    objects = UtilisateurManager()

    USERNAME_FIELD = 'email'       # login with email instead of username
    REQUIRED_FIELDS = ['nom', 'prenom']  # asked when running createsuperuser

    def __str__(self):
        return f"{self.prenom} {self.nom} ({self.email})"

    def clean(self):
        super().clean()
        self.matricule = (self.matricule or '').strip() or None
        if self.est_client_fm6() and not self.matricule:
            raise ValidationError({
                'matricule': "Le matricule est obligatoire pour un client FM6.",
            })

    # --- Business logic methods from your diagram ---
    def est_client_fm6(self):
        return self.role == self.CLIENT_FM6

    def est_enseignant(self):
        """Alias de compatibilité pour l'ancien nom du type Client FM6."""
        return self.est_client_fm6()

    def est_client_regulier(self):
        return self.role == self.CLIENT_REGULIER

    def est_administrateur(self):
        return self.role == self.ADMINISTRATEUR or self.is_superuser

    @property
    def type_client(self):
        """Type métier du client, hors compte administrateur."""
        return self.role if self.role != self.ADMINISTRATEUR else None
