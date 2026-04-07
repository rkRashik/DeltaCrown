import logging
import warnings

from whitenoise.storage import CompressedManifestStaticFilesStorage

logger = logging.getLogger(__name__)


class RobustStaticFilesStorage(CompressedManifestStaticFilesStorage):
    """
    WhiteNoise storage with three production hardening tweaks:

    1. manifest_strict = False
       Prevents ValueError / 500 crash when a template references a static
       file that wasn't collected (e.g. a missing asset slips through).
       Django falls back to the un-hashed path instead of raising.

    2. max_post_process_passes = 20
       The default (5) is too low for projects with deeply nested CSS
       url() chains.

    3. Suppressed "Max post-process passes exceeded" RuntimeError
       Intercepts the RuntimeError that Django yields from post_process()
       before collectstatic can re-raise it and abort the build.
       The manifest is still saved with all files that *were* resolved,
       so the deployment succeeds instead of rolling back to broken code.
    """

    manifest_strict = False
    max_post_process_passes = 20

    def post_process(self, *args, **kwargs):
        for name, hashed_name, processed in super().post_process(*args, **kwargs):
            if isinstance(processed, RuntimeError) and "post-process" in str(processed):
                logger.warning(
                    "collectstatic: suppressed '%s' for path(s) %r — "
                    "manifest saved with all resolved files.",
                    processed,
                    name[:200],
                )
                continue  # do NOT re-raise; allow the manifest to be written
            yield name, hashed_name, processed
