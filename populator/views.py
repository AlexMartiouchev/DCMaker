from django.shortcuts import render


def index(request):
    return render(request, "populator/index.html")


def populator(request):
    return render(request, "populator/populator.html")
