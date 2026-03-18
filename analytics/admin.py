from django.contrib import admin
from django.utils.html import format_html
from django.db.models import Sum, Count
from django.urls import path
from django.http import HttpResponse
import csv


# Analytics are computed — no persistent models.
# This admin module provides a custom analytics dashboard link.
class AnalyticsAdminSite:
    """Placeholder for future custom admin dashboard integration."""
    pass
