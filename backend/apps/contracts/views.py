"""REST views for contract attachments."""
from django.http import JsonResponse, FileResponse
from django.views import View
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt

from apps.core.permissions import get_current_user_from_request
from .models import ContractAttachment


@method_decorator(csrf_exempt, name="dispatch")
class AttachmentDownloadView(View):
    """REST endpoint for downloading contract attachments."""

    def get(self, request, attachment_id):
        """
        Download a contract attachment.

        Requires authentication and verifies tenant ownership.
        """
        # Authenticate
        user = get_current_user_from_request(request)
        if not user:
            return JsonResponse({"error": "Authentication required"}, status=401)

        if not user.tenant:
            return JsonResponse({"error": "No tenant assigned"}, status=403)

        # Find attachment (with tenant verification)
        attachment = ContractAttachment.objects.filter(
            tenant=user.tenant,
            id=attachment_id,
        ).first()

        if not attachment:
            return JsonResponse({"error": "Attachment not found"}, status=404)

        # Serve file
        try:
            response = FileResponse(
                attachment.file.open("rb"),
                content_type=attachment.content_type,
            )
            # Check if preview mode (inline viewing) is requested
            preview = request.GET.get("preview", "").lower() in ("true", "1")
            disposition = "inline" if preview else "attachment"
            response["Content-Disposition"] = f'{disposition}; filename="{attachment.original_filename}"'
            response["Content-Length"] = attachment.file_size
            return response
        except FileNotFoundError:
            return JsonResponse({"error": "File not found on storage"}, status=404)
