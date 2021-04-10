from django.urls import path

from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('patent_comp/<str:id_list>', views.patent_comp, name='patent_comp'),
    path('clincialtrials_request', views.clincialtrials_request, name='clincialtrials_request'),
]