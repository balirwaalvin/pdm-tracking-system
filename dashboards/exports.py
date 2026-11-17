"""CSV downloads of list pages.

Add CsvExportMixin to a list view and define `csv_filename`, `csv_header`
and `csv_row()`. Adding ?format=csv to the page's address downloads every
row the page would show: the same role check, area scoping and filters,
without paging.
"""

import csv

from django.http import HttpResponse
from django.utils import timezone


class CsvExportMixin:
    csv_filename = "export"
    csv_header = []

    def csv_row(self, obj):
        raise NotImplementedError

    def get(self, request, *args, **kwargs):
        if request.GET.get("format") != "csv":
            return super().get(request, *args, **kwargs)
        response = HttpResponse(content_type="text/csv")
        stamp = timezone.localdate().isoformat()
        response["Content-Disposition"] = f'attachment; filename="pdm-{self.csv_filename}-{stamp}.csv"'
        writer = csv.writer(response)
        writer.writerow(self.csv_header)
        for obj in self.get_queryset():
            writer.writerow(self.csv_row(obj))
        return response
