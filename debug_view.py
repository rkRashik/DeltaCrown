# Quick debug view - add this temporarily to test
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse

def debug_buttons(request):
    """Debug script to check tournament mode and team settings"""
    html_content = open('DEBUG_BUTTONS.html', 'r').read()
    return HttpResponse(html_content)
