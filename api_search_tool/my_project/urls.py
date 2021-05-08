from django.urls import path

from . import views

urlpatterns = [
    path('publications_request', views.all_data_view.publications_request, name='publications_request'),
]