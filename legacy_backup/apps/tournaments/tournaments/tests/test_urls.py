import pytest
from django.urls import reverse, resolve


@pytest.mark.parametrize(
    "name,kwargs",
    [
        ("tournaments:hub", {}),
        ("tournaments:detail", {"slug": "sample"}),
        ("tournaments:register", {"slug": "sample"}),
        ("tournaments:registration_receipt", {"slug": "sample"}),
        ("tournaments:check_in", {"slug": "sample"}),
        ("tournaments:ics", {"slug": "sample"}),
        ("tournaments:my_matches", {}),
    ],
)
def test_named_urls_resolve(name, kwargs):
    url = reverse(name, kwargs=kwargs if kwargs else None)
    match = resolve(url)
    assert match.view_name == name
