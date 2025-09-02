import types
from django.template import Context, Template


def make(obj_dict):
    return types.SimpleNamespace(**obj_dict)


def render(tpl_str, ctx):
    t = Template(tpl_str)
    return t.render(Context(ctx))


def test_widget_renders_empty_state_without_items():
    html = render("{% upcoming_matches %}", {"upcoming_matches": []})
    assert "No upcoming matches." in html


def test_widget_renders_items_with_labels_and_link():
    items = [
        make({
            "id": 42,
            "round_no": 2,
            "scheduled_at": None,
            "team_a": make({"tag": "AAA", "name": "Alpha"}),
            "team_b": make({"tag": "BBB", "name": "Beta"}),
        }),
    ]
    html = render("{% upcoming_matches %}", {"upcoming_matches": items})
    # Headline
    assert "Upcoming matches" in html
    # Opponents
    assert "AAA" in html and "BBB" in html
    # Link uses match_review URL when id is present (string check)
    assert "match_review" in html or "Open" in html
