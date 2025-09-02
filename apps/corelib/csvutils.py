# apps/corelib/csvutils.py
from django.http import HttpResponse
from django.utils import timezone
import csv
from typing import Iterable, Sequence


def stream_csv(filename_prefix: str, header: Sequence[str], rows_iter: Iterable[Sequence]):
    """
    Create a CSV HttpResponse with a stable header and stream rows from an iterable.

    This is intentionally tiny; callers keep their own queryset logic and just yield
    rows that match the header shape. This preserves all existing behavior.
    """
    ts = timezone.now().strftime("%Y%m%d-%H%M%S")
    filename = f"{filename_prefix}-{ts}.csv"

    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'

    writer = csv.writer(response)
    writer.writerow(list(header))

    for row in rows_iter:
        writer.writerow(list(row))

    return response
