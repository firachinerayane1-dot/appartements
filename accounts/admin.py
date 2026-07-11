from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import Utilisateur


class UtilisateurAdmin(UserAdmin):
    model = Utilisateur

    # Columns shown in the user list page
    list_display = ('email', 'nom', 'prenom', 'role', 'is_staff', 'is_active')

    # Filters shown in the sidebar
    list_filter = ('role', 'is_staff', 'is_active')
    readonly_fields = ('last_login', 'date_joined')

    # Fields shown when viewing/editing an existing user
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Informations personnelles', {'fields': ('nom', 'prenom', 'telephone', 'role', 'matricule')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Dates importantes', {'fields': ('last_login', 'date_joined')}),
    )

    # Fields shown on the "add new user" form
    add_fieldsets = (
        (None, {
            'fields': ('email', 'nom', 'prenom', 'role', 'password1', 'password2'),
        }),
    )

    ordering = ('email',)
    search_fields = ('email', 'nom', 'prenom')


admin.site.register(Utilisateur, UtilisateurAdmin)