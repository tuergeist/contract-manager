"""REST views for invoice export."""
from django.http import HttpResponse, JsonResponse
from django.views import View
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt

from apps.core.permissions import get_current_user_from_request
from apps.invoices.services import InvoiceService


@method_decorator(csrf_exempt, name="dispatch")
class InvoiceExportView(View):
    """REST endpoint for exporting invoices as PDF or Excel."""

    def get(self, request):
        """
        Export invoices for a given month.

        Query parameters:
            year: Year (required)
            month: Month 1-12 (required)
            format: "pdf", "pdf-individual", or "excel" (required)
            language: "de" or "en" (optional, default "de")

        Returns:
            File download response with appropriate content-type and filename.
        """
        # Authenticate
        user = get_current_user_from_request(request)
        if not user:
            return JsonResponse({"error": "Authentication required"}, status=401)

        # Parse parameters
        try:
            year = int(request.GET.get("year", ""))
            month = int(request.GET.get("month", ""))
        except (ValueError, TypeError):
            return JsonResponse(
                {"error": "year and month are required and must be integers"},
                status=400,
            )

        if month < 1 or month > 12:
            return JsonResponse({"error": "month must be between 1 and 12"}, status=400)

        export_format = request.GET.get("format", "")
        if export_format not in ("pdf", "pdf-individual", "excel"):
            return JsonResponse(
                {"error": "format must be 'pdf', 'pdf-individual', or 'excel'"},
                status=400,
            )

        language = request.GET.get("language", "de")
        if language not in ("de", "en"):
            language = "de"

        # Generate invoices
        service = InvoiceService(user.tenant)
        invoices = service.get_invoices_for_month(year, month)

        if not invoices:
            return JsonResponse(
                {"error": "No invoices found for this month"}, status=404
            )

        # Generate export
        if export_format == "pdf":
            content = service.generate_pdf(invoices, language=language)
            filename = f"invoices-{year:04d}-{month:02d}.pdf"
            content_type = "application/pdf"

        elif export_format == "pdf-individual":
            content = service.generate_individual_pdfs(
                invoices, year, month, language=language
            )
            filename = f"invoices-{year:04d}-{month:02d}.zip"
            content_type = "application/zip"

        else:  # excel
            content = service.generate_excel(invoices, year, month, language=language)
            filename = f"invoices-{year:04d}-{month:02d}.xlsx"
            content_type = (
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

        response = HttpResponse(content, content_type=content_type)
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        response["Content-Length"] = len(content)

        return response
