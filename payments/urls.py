from django.urls import path
from . import views

app_name = 'payments'
urlpatterns = [
    path('gestion/reservation/<int:reservation_id>/valider/', views.admin_valider, name='admin_valider'),
    path('reservation/<int:reservation_id>/', views.payer, name='payer'),
    path('recu/<int:pk>/', views.recu, name='recu'),
    path('gestion/', views.admin_liste, name='admin_liste'),
]
