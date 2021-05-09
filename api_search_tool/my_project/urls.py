from django.urls import path

from . import views

urlpatterns = [
    path('publications_request', views.all_data_view.publications_request, name='publications_request'),
    path('authors_request', views.author_view.authors_request, name='authors_request'),
]