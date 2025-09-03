from django.template.loader import render_to_string

def test_modal_renders_and_has_aria():
    html = render_to_string("components/modal.html", {"id": "demo", "title": "Dialog"})
    assert 'role="dialog"' in html
    assert 'aria-modal="true"' in html
    assert 'data-modal-panel' in html
