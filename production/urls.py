from django.urls import path
from production.views import *

urlpatterns = [
    path('', TestView.as_view(), name='test-view'),
]