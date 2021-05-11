from django.urls import path

from . import views

urlpatterns = [
    path('', views.views.search_tool, name='search_tool'),
    path('search_tool', views.views.search_tool, name='search_tool'),
]