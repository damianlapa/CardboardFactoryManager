from django.shortcuts import render, HttpResponse
from django.views import View


class TestView(View):
    def get(self, request):
        return HttpResponse('Test passed!')
