from django.urls import path
from warehouse.views import *


urlpatterns = [
    path('test/', TestView.as_view()),
]
