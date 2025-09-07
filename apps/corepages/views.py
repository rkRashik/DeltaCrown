# apps/corepages/views.py
from django.shortcuts import render
from django.contrib.auth.decorators import login_required

def about(request):
    return render(request, "pages/about.html", {})

def community(request):
    return render(request, "pages/community.html", {})

@login_required
def notifications_index(request):
    # You can hydrate from your model later; render empty safely
    return render(request, "notifications/list.html", {"notifications": []})
