from django.urls import path

from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('patent_comp/<str:id_list>', views.patent_comp, name='patent_comp'),
    path('cto_request', views.cto_request, name='cto_request'),
]