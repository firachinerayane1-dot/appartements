from django.urls import path
from . import views

app_name = 'payments'
urlpatterns = [
    path('reservation/<int:reservation_id>/', views.payer, name='payer'),
    path('recu/<int:pk>/', views.recu, name='recu'),
    path('gestion/', views.admin_liste, name='admin_liste'),
]
