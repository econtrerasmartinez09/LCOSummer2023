from django.urls import path, include
from django.contrib import admin


from . import views

urlpatterns = [
	path("",views.query,name='query'),
	path("",views.main_func,name='main_func'),
]
