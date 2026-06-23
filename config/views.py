from __future__ import annotations

from django.http import HttpRequest, HttpResponse
from django.shortcuts import render


def handler404(request: HttpRequest, exception) -> HttpResponse:
    """Page 404 personnalisee."""
    return render(request, "404.html", status=404)


def handler500(request: HttpRequest) -> HttpResponse:
    """Page 500 personnalisee."""
    return render(request, "500.html", status=500)
