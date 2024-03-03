from django.shortcuts import render


def index(request):
    return render(request, "populator/index.html")


def populator(request):
    return render(request, "populator/populator.html")


def demo(request):
    return render(request, "populator/demo/demo_index.html")

def demo_location(request):
    return render(request, "populator/demo/demo_location.html")

def demo_factions(request):
    return render(request, "populator/demo/demo_factions.html")

def demo_characters(request):
    return render(request, "populator/demo/demo_characters.html")

def demo_summary(request):
    return render(request, "populator/demo/demo_summary.html")