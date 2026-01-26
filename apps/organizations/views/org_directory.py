"""
Organization Directory view.

Displays global organization rankings and directory.
"""

from django.shortcuts import render
from django.contrib.auth.decorators import login_required

from apps.organizations.services.org_directory_service import get_directory_context


def org_directory(request):
    """
    Display the global organization directory/rankings page.
    
    URL: /orgs/
    Template: organizations/org/org_directory.html
    
    Query params:
        - q: Search query (name/slug/public_id)
        - region: Region filter (ISO code like BD, US, SG)
        - page: Page number (default: 1)
    
    Returns:
        Rendered directory page with top 3 podium + paginated table rows.
    """
    # Parse query parameters
    q = request.GET.get('q', '').strip()
    region = request.GET.get('region', '').strip()
    page = request.GET.get('page', '1')
    
    # Convert page to int, fallback to 1 if invalid
    try:
        page = int(page)
    except (ValueError, TypeError):
        page = 1
    
    # Get directory context from service layer
    directory_context = get_directory_context(
        q=q,
        region=region,
        page=page,
        page_size=20,
    )
    
    # Merge with base context
    context = {
        'page_title': 'Global Organizations',
        'page_description': 'Browse and explore verified esports organizations worldwide',
        **directory_context,
    }
    
    return render(request, 'organizations/org/org_directory.html', context)
