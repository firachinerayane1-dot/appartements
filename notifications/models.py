from django.conf import settings
from django.db import models
from django.utils import timezone


class Notification(models.Model):
    client = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notifications')
    message = models.TextField()
    date_envoi = models.DateTimeField(null=True, blank=True)
    lue = models.BooleanField(default=False)

    class Meta:
        ordering = ('-date_envoi', '-pk')

    def __str__(self):
        return f"Notification pour {self.client}"

    def marquer_lue(self):
        if not self.lue:
            self.lue = True
            self.save(update_fields=('lue',))
        return self

    def envoyer(self):
        if not self.date_envoi:
            self.date_envoi = timezone.now()
            self.save(update_fields=('date_envoi',))
        return self
