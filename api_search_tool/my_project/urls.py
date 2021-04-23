from django.urls import path

from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('publications_request', views.publications_request, name='publications_request'),
]