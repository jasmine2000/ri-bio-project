from django.urls import path

from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('lens_patent_request', views.lens_patent_request, name='lens_patent_request'),
    path('publications_request', views.publications_request, name='publications_request'),
]