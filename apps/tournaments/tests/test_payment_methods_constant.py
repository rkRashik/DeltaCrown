def test_payment_methods_reexport_and_shape():
    from apps.tournaments.models import PAYMENT_METHODS
    assert isinstance(PAYMENT_METHODS, list)
    assert all(isinstance(x, tuple) and len(x) == 2 for x in PAYMENT_METHODS)
    # Wallet rails the forms expect:
    keys = {k for (k, _v) in PAYMENT_METHODS}
    for k in ("bkash", "nagad", "rocket"):
        assert k in keys
