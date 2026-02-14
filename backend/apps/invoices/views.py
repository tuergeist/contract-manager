"""REST views for invoice export."""
from django.http import HttpResponse, JsonResponse
from django.views import View
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt

from apps.core.permissions import get_current_user_from_request
from apps.invoices.services import InvoiceService


@method_decorator(csrf_exempt, name="dispatch")
class InvoicePreviewView(View):
    """REST endpoint for generating a sample invoice PDF with current template settings."""

    def get(self, request):
        user = get_current_user_from_request(request)
        if not user:
            return JsonResponse({"error": "Authentication required"}, status=401)

        language = request.GET.get("language", "de")
        if language not in ("de", "en"):
            language = "de"

        service = InvoiceService(user.tenant)
        content = service.generate_preview_pdf(language=language)

        response = HttpResponse(content, content_type="application/pdf")
        response["Content-Disposition"] = 'inline; filename="invoice-preview.pdf"'
        response["Content-Length"] = len(content)
        return response


@method_decorator(csrf_exempt, name="dispatch")
class InvoiceExportView(View):
    """REST endpoint for exporting invoices as PDF, Excel, or ZUGFeRD."""

    def get(self, request):
        """
        Export invoices for a given month.

        Query parameters:
            year: Year (required)
            month: Month 1-12 (required)
            format: "pdf", "pdf-individual", "excel", "zugferd", or "zugferd-single" (required)
            language: "de" or "en" (optional, default "de")
            invoice_id: Invoice record ID (required for "zugferd-single")

        Returns:
            File download response with appropriate content-type and filename.
        """
        # Authenticate
        user = get_current_user_from_request(request)
        if not user:
            return JsonResponse({"error": "Authentication required"}, status=401)

        # Check permission
        if not user.has_perm_check("invoices", "export"):
            return JsonResponse({"error": "Permission denied"}, status=403)

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

        valid_formats = ("pdf", "pdf-individual", "excel", "zugferd", "zugferd-single")
        export_format = request.GET.get("format", "")
        if export_format not in valid_formats:
            return JsonResponse(
                {"error": f"format must be one of: {', '.join(valid_formats)}"},
                status=400,
            )

        language = request.GET.get("language", "de")
        if language not in ("de", "en"):
            language = "de"

        service = InvoiceService(user.tenant)

        # ZUGFeRD formats use persisted InvoiceRecords
        if export_format in ("zugferd", "zugferd-single"):
            return self._handle_zugferd_export(
                request, service, user, year, month, export_format, language
            )

        # Standard formats use on-demand calculated invoices
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

    def _handle_zugferd_export(self, request, service, user, year, month, fmt, language):
        """Handle ZUGFeRD export formats using persisted InvoiceRecords."""
        from apps.invoices.models import CompanyLegalData, InvoiceRecord

        # Validate company legal data exists
        try:
            user.tenant.legal_data
        except CompanyLegalData.DoesNotExist:
            return JsonResponse(
                {"error": "Company legal data must be configured for ZUGFeRD export."},
                status=400,
            )

        if fmt == "zugferd-single":
            # Single invoice export
            invoice_id = request.GET.get("invoice_id", "")
            if not invoice_id:
                return JsonResponse(
                    {"error": "invoice_id is required for zugferd-single format"},
                    status=400,
                )
            try:
                record = InvoiceRecord.objects.get(
                    id=int(invoice_id),
                    tenant=user.tenant,
                    status=InvoiceRecord.Status.FINALIZED,
                )
            except (InvoiceRecord.DoesNotExist, ValueError):
                return JsonResponse(
                    {"error": "Finalized invoice not found"}, status=404
                )

            content = service.generate_zugferd_pdf_for_record(record, language)
            filename = f"invoice-{record.invoice_number}.pdf"
            content_type = "application/pdf"

        else:
            # Batch ZUGFeRD export
            records = list(
                InvoiceRecord.objects.filter(
                    tenant=user.tenant,
                    billing_date__year=year,
                    billing_date__month=month,
                    status=InvoiceRecord.Status.FINALIZED,
                ).select_related("customer", "contract").order_by(
                    "customer_name", "billing_date"
                )
            )

            if not records:
                return JsonResponse(
                    {
                        "error": (
                            "No finalized invoices for this month. "
                            "Please generate invoices first."
                        )
                    },
                    status=404,
                )

            content = service.generate_individual_zugferd_pdfs(
                records, year, month, language
            )
            filename = f"invoices-zugferd-{year:04d}-{month:02d}.zip"
            content_type = "application/zip"

        response = HttpResponse(content, content_type=content_type)
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        response["Content-Length"] = len(content)
        return response
