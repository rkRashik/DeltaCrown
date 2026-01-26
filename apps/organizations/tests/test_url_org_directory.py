"""URL contract tests for Organization Directory page."""

from django.test import TestCase
from django.urls import reverse


class OrgDirectoryURLTests(TestCase):
    """Test URL routing for the Organization Directory page."""

    def test_org_directory_url_reverses_correctly(self):
        """Test that 'organizations:org_directory' reverses to /orgs/."""
        url = reverse('organizations:org_directory')
        self.assertEqual(url, '/orgs/')

    def test_org_directory_view_responds(self):
        """Test that GET /orgs/ returns 200 OK."""
        response = self.client.get('/orgs/')
        self.assertEqual(response.status_code, 200)

    def test_org_directory_uses_correct_template(self):
        """Test that the org_directory view uses the correct template."""
        response = self.client.get(reverse('organizations:org_directory'))
        self.assertTemplateUsed(response, 'organizations/org/org_directory.html')

    def test_org_directory_context_has_required_fields(self):
        """Test that the view provides required context variables."""
        response = self.client.get(reverse('organizations:org_directory'))
        self.assertIn('page_title', response.context)
        self.assertIn('page_description', response.context)
        self.assertEqual(response.context['page_title'], 'Global Organizations')
        self.assertEqual(response.context['page_description'], 
                         'Browse and explore verified esports organizations worldwide')
