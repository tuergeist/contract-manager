"""REST views for version and license information."""
import json
import os

from django.http import JsonResponse
from django.views import View


BUILD_INFO_PATH = os.path.join("/app", "build-info.json")
LICENSES_BACKEND_PATH = os.path.join("/app", "licenses-backend.json")


class VersionView(View):
    """Public endpoint returning build version and date."""

    def get(self, request):
        try:
            with open(BUILD_INFO_PATH) as f:
                data = json.load(f)
            return JsonResponse(data)
        except (FileNotFoundError, json.JSONDecodeError):
            return JsonResponse({"version": "dev", "buildDate": ""})


class BackendLicensesView(View):
    """Public endpoint returning backend OSS dependency licenses."""

    def get(self, request):
        try:
            with open(LICENSES_BACKEND_PATH) as f:
                data = json.load(f)
            return JsonResponse(data, safe=False)
        except (FileNotFoundError, json.JSONDecodeError):
            return JsonResponse([], safe=False)
