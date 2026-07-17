from django.urls import path
from . import views

app_name = 'apartments'

urlpatterns = [
    path('', views.liste, name='liste'),
    path('<int:pk>/', views.detail, name='detail'),
    path('gestion/liste/', views.admin_liste, name='admin_liste'),
    path('gestion/creer/', views.appartement_form, name='creer'),
    path('gestion/<int:pk>/modifier/', views.appartement_form, name='modifier'),
    path('gestion/<int:pk>/supprimer/', views.appartement_supprimer, name='supprimer'),
    path('gestion/vacances/', views.vacances_liste, name='vacances_liste'),
    path('gestion/vacances/creer/', views.vacances_form, name='vacances_creer'),
    path('gestion/vacances/<int:pk>/modifier/', views.vacances_form, name='vacances_modifier'),
    path('gestion/vacances/<int:pk>/supprimer/', views.vacances_supprimer, name='vacances_supprimer'),
]
