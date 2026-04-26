from apps.accounts.emails import normalize_from_email


def test_normalize_from_email_wraps_plain_address():
    assert normalize_from_email("noreply@deltacrown.xyz") == "DeltaCrown <noreply@deltacrown.xyz>"


def test_normalize_from_email_repairs_nested_display_name():
    assert (
        normalize_from_email("DeltaCrown <DeltaCrown <noreply@deltacrown.xyz>>")
        == "DeltaCrown <noreply@deltacrown.xyz>"
    )
