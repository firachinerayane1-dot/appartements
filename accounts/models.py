from django.db import models
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.contrib.auth.base_user import BaseUserManager


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
    ENSEIGNANT = 'ENSEIGNANT'
    ADMINISTRATEUR = 'ADMINISTRATEUR'

    ROLE_CHOICES = [
        (CLIENT_REGULIER, 'Client Régulier'),
        (ENSEIGNANT, 'Enseignant'),
        (ADMINISTRATEUR, 'Administrateur'),
    ]

    # --- Fields from your diagram ---
    email = models.EmailField(unique=True)
    nom = models.CharField(max_length=100)
    prenom = models.CharField(max_length=100)
    telephone = models.CharField(max_length=20, blank=True)

    # --- Role system (replaces Client/ClientRegulier/Enseignant/Administrateur as separate tables) ---
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default=CLIENT_REGULIER)
    matricule = models.CharField(max_length=50, blank=True, null=True)  # only used when role = ENSEIGNANT

    # --- Django bookkeeping fields ---
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)  # controls access to /admin
    date_joined = models.DateTimeField(auto_now_add=True)

    objects = UtilisateurManager()

    USERNAME_FIELD = 'email'       # login with email instead of username
    REQUIRED_FIELDS = ['nom', 'prenom']  # asked when running createsuperuser

    def __str__(self):
        return f"{self.prenom} {self.nom} ({self.email})"

    # --- Business logic methods from your diagram ---
    def est_enseignant(self):
        return self.role == self.ENSEIGNANT

    def est_client_regulier(self):
        return self.role == self.CLIENT_REGULIER

    def est_administrateur(self):
        return self.role == self.ADMINISTRATEUR or self.is_superuser

    def taux_reduction(self):
        """
        Corresponds to the 'réduction' logic you mentioned for holiday bookings.
        Returns a discount rate; we'll wire this into Appartement.calculerPrix() later.
        """
        if self.role == self.ENSEIGNANT:
            return 0.15  # example: 15% off — adjust to your real business rule
        return 0.0

    @property
    def type_client(self):
        """Alias métier conservant le vocabulaire Client/Enseignant."""
        return self.role if self.role != self.ADMINISTRATEUR else None
