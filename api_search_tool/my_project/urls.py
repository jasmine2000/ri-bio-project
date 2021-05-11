from django.urls import path

from . import views

urlpatterns = [
    path('search_tool', views.views.search_tool, name='search_tool'),
]