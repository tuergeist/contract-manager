"""REST views for version and license information."""
import json
import os

from django.conf import settings
from django.http import HttpResponse, JsonResponse
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


class GraphQLSchemaView(View):
    """Public endpoint serving the GraphQL SDL schema for client codegen + docs."""

    def get(self, request):
        # Prefer the committed schema.graphql for stability; fall back to live schema
        path = os.path.join(settings.BASE_DIR, "schema.graphql")
        if os.path.isfile(path):
            with open(path, encoding="utf-8") as f:
                sdl = f.read()
        else:
            from config.schema import schema
            sdl = schema.as_str()
        return HttpResponse(sdl, content_type="text/plain; charset=utf-8")
