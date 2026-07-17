from django.urls import path
from . import views

app_name = 'reservations'

urlpatterns = [
    path('appartement/<int:appartement_id>/reserver/', views.reserver, name='reserver'),
    path('mes-reservations/', views.mes_reservations, name='mes_reservations'),
    path('<int:pk>/', views.detail, name='detail'),
    path('<int:pk>/annuler/', views.annuler, name='annuler'),
    path('gestion/liste/', views.admin_liste, name='admin_liste'),
    path('gestion/<int:pk>/annuler/', views.admin_annuler, name='admin_annuler'),
    path('gestion/<int:pk>/supprimer/', views.admin_supprimer, name='admin_supprimer'),
]
