from django.urls import path
from . import views

app_name = 'notifications'
urlpatterns = [
    path('', views.liste, name='liste'),
    path('<int:pk>/lue/', views.marquer_lue, name='marquer_lue'),
]
