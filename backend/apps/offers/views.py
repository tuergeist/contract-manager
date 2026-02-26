"""REST views for offer file serving."""
from django.http import HttpResponse, JsonResponse
from django.views import View

from apps.core.permissions import get_current_user_from_request


class OfferRecordPdfView(View):
    """REST endpoint for serving an offer record PDF."""

    def get(self, request, record_id):
        user = get_current_user_from_request(request)
        if not user:
            return JsonResponse({"error": "Authentication required"}, status=401)

        if not user.has_perm_check("offers", "read"):
            return JsonResponse({"error": "Permission denied"}, status=403)

        from apps.offers.models import OfferRecord

        try:
            record = OfferRecord.objects.get(id=record_id, tenant=user.tenant)
        except OfferRecord.DoesNotExist:
            return JsonResponse({"error": "Offer not found"}, status=404)

        if not record.pdf_file:
            return JsonResponse({"error": "No PDF available"}, status=404)

        filename = f"offer-{record.offer_number}.pdf"
        record.pdf_file.open("rb")
        content = record.pdf_file.read()
        record.pdf_file.close()
        response = HttpResponse(content, content_type="application/pdf")
        response["Content-Disposition"] = f'inline; filename="{filename}"'
        response["Content-Length"] = len(content)
        return response
