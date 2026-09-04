from django.contrib import admin
from .models import Notification


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('client', 'categorie', 'reservation', 'date_envoi', 'lue', 'message_court')
    list_filter = ('categorie', 'lue', 'date_envoi')
    search_fields = ('client__email', 'message')

    @admin.display(description='Message')
    def message_court(self, obj):
        return obj.message[:80]
