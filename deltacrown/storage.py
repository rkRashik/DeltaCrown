from whitenoise.storage import CompressedManifestStaticFilesStorage


class RobustStaticFilesStorage(CompressedManifestStaticFilesStorage):
    """
    WhiteNoise storage retaining legacy missing-manifest compatibility.

    1. manifest_strict = False
       Prevents ValueError / 500 crash when a template references a static
       file that wasn't collected (e.g. a missing asset slips through).
       Django falls back to the un-hashed path instead of raising.

    2. max_post_process_passes = 20
       The default (5) is too low for projects with deeply nested CSS
       url() chains.

    Processing failures deliberately propagate and stop collectstatic. A cyclic
    import (even inside a CSS comment) must be fixed at its source, never hidden.
    """

    manifest_strict = False
    max_post_process_passes = 20
