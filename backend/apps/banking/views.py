"""REST views for banking file uploads."""
from django.http import JsonResponse
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt

from apps.core.permissions import get_current_user_from_request


@method_decorator(csrf_exempt, name="dispatch")
class UploadStatementView(View):
    """Upload an MT940/MTA file for a specific bank account."""

    def post(self, request, account_id):
        user = get_current_user_from_request(request)
        if not user:
            return JsonResponse({"error": "Authentication required"}, status=401)

        if not user.has_perm_check("banking", "write"):
            return JsonResponse({"error": "Permission denied"}, status=403)

        from apps.banking.models import BankAccount
        from apps.banking.services import MT940Service

        # Validate account belongs to tenant
        try:
            account = BankAccount.objects.get(
                id=account_id, tenant=user.tenant
            )
        except BankAccount.DoesNotExist:
            return JsonResponse({"error": "Account not found"}, status=404)

        # Get uploaded file
        uploaded_file = request.FILES.get("file")
        if not uploaded_file:
            return JsonResponse({"error": "No file provided"}, status=400)

        # Read file content
        try:
            content = uploaded_file.read()
        except Exception as e:
            return JsonResponse({"error": f"Failed to read file: {e}"}, status=400)

        # Parse and import
        service = MT940Service(user.tenant)
        result = service.parse_and_import(account, content)

        if result.errors:
            return JsonResponse(
                {"error": result.errors[0], "errors": result.errors},
                status=400,
            )

        return JsonResponse({
            "total": result.total,
            "imported": result.imported,
            "skipped": result.skipped,
        })
