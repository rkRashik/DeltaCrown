"""The release verifier must accept the reviewed account-template URL fixes and nothing else in those files."""
import importlib.util
import os
from pathlib import Path

import pytest
from django.conf import settings


@pytest.fixture(scope="module")
def verifier():
    previous = os.environ.get("DJANGO_SETTINGS_MODULE")
    os.environ["DJANGO_SETTINGS_MODULE"] = "deltacrown.settings_brand_qa"  # the script refuses any other value on import
    try:
        spec = importlib.util.spec_from_file_location("verify_ownlobby_under_test", Path(settings.BASE_DIR) / "scripts/verify_ownlobby.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
    finally:
        if previous is None:
            os.environ.pop("DJANGO_SETTINGS_MODULE", None)
        else:
            os.environ["DJANGO_SETTINGS_MODULE"] = previous
    return module


EXTRA = "{% url 'account:signup' %}"


def _source(name):
    return (Path(settings.BASE_DIR) / name).read_text(encoding="utf-8")


def test_reviewed_files_match_their_expected_tags(verifier):
    for name in verifier.REVIEWED_URL_TAGS:
        assert not verifier.url_contract_changed(name, "baseline placeholder", _source(name)), name


@pytest.mark.parametrize("name", [
    "templates/account/password_change_done.html", "templates/account/password_change_form.html",
    "templates/account/password_reset_confirm.html", "templates/account/password_reset_done.html",
])
def test_unreviewed_changes_in_reviewed_files_are_detected(verifier, name):
    import re
    src = _source(name)
    first = re.search(verifier.URL_TAG_PATTERN, src, re.S).group(0)
    changed = {
        "added tag": src + EXTRA,
        "retargeted tag": src.replace(first, "{% url 'account:logout' %}", 1),
        "tag replaced by a hard-coded path": src.replace(first, "/hard/coded/", 1),
        "regressed to the broken route": src.replace("user_profile:profile_settings", "user_profile:settings_v3"),
    }
    for label, mutated in changed.items():
        if label == "regressed to the broken route" and "user_profile:profile_settings" not in src:
            continue
        assert verifier.url_contract_changed(name, "baseline placeholder", mutated), label


def test_other_templates_still_use_baseline_comparison(verifier):
    before = "<a href=\"{% url 'a:b' %}\">x</a>"
    assert not verifier.url_contract_changed("templates/other.html", before, before.replace("<a", "<a class='k'"))
    assert verifier.url_contract_changed("templates/other.html", before, before.replace("a:b", "a:c"))
    assert not verifier.url_contract_changed("templates/new.html", None, before)
