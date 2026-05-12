"""Export the GraphQL SDL schema to a file for client codegen + docs."""
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Export the full GraphQL schema as SDL to backend/schema.graphql"

    def add_arguments(self, parser):
        parser.add_argument(
            "--output",
            default=None,
            help="Output path (default: <BASE_DIR>/schema.graphql)",
        )

    def handle(self, *args, **options):
        from config.schema import schema

        sdl = schema.as_str()
        path = Path(options["output"]) if options["output"] else Path(settings.BASE_DIR) / "schema.graphql"
        path.write_text(sdl, encoding="utf-8")
        self.stdout.write(self.style.SUCCESS(f"Wrote {len(sdl)} chars to {path}"))
