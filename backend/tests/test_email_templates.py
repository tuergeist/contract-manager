"""Tests for configurable invoice email templates."""
import pytest
from unittest.mock import Mock

from apps.core.context import Context
from apps.invoices.tasks import EMAIL_TEMPLATES, _get_email_template
from apps.tenants.models import Tenant, User
from apps.tenants.schema import TenantMutation, TenantQuery, SetInvoiceEmailTemplateInput


def _make_context(user):
    request = Mock()
    request.tenant = user.tenant
    return Context(request=request, user=user)


@pytest.fixture
def admin_user(db, tenant):
    user = User.objects.create_user(
        email="admin@test.local",
        password="test1234",
        tenant=tenant,
        is_admin=True,
    )
    return user


class TestGetEmailTemplate:
    def test_returns_default_when_no_custom(self, tenant):
        result = _get_email_template(tenant, "de")
        assert result["subject"] == EMAIL_TEMPLATES["de"]["subject"]
        assert result["body"] == EMAIL_TEMPLATES["de"]["body"]

    def test_returns_default_en(self, tenant):
        result = _get_email_template(tenant, "en")
        assert result["subject"] == EMAIL_TEMPLATES["en"]["subject"]

    def test_returns_custom_when_configured(self, tenant):
        tenant.settings = {
            "invoice_email_templates": {
                "de": {
                    "subject": "Custom {invoice_number}",
                    "body": "<p>Custom body {invoice_number}</p>",
                }
            }
        }
        tenant.save()

        result = _get_email_template(tenant, "de")
        assert result["subject"] == "Custom {invoice_number}"
        assert result["body"] == "<p>Custom body {invoice_number}</p>"

    def test_falls_back_when_custom_incomplete(self, tenant):
        tenant.settings = {
            "invoice_email_templates": {
                "de": {"subject": "Only subject", "body": ""}
            }
        }
        tenant.save()

        result = _get_email_template(tenant, "de")
        assert result["subject"] == EMAIL_TEMPLATES["de"]["subject"]

    def test_falls_back_for_unknown_language(self, tenant):
        result = _get_email_template(tenant, "fr")
        assert result["subject"] == EMAIL_TEMPLATES["de"]["subject"]

    def test_custom_de_does_not_affect_en(self, tenant):
        tenant.settings = {
            "invoice_email_templates": {
                "de": {
                    "subject": "Custom DE",
                    "body": "<p>Custom DE</p>",
                }
            }
        }
        tenant.save()

        result_en = _get_email_template(tenant, "en")
        assert result_en["subject"] == EMAIL_TEMPLATES["en"]["subject"]


class TestEmailTemplateRendering:
    def test_fallback_on_invalid_placeholder(self, tenant):
        """Custom template with bad placeholder should not crash _get_email_template.
        The fallback happens at render time in the task, tested here as a unit."""
        tenant.settings = {
            "invoice_email_templates": {
                "de": {
                    "subject": "Invoice {bad_placeholder}",
                    "body": "<p>{invoice_number}</p>",
                }
            }
        }
        tenant.save()

        template = _get_email_template(tenant, "de")
        # The template is returned as-is; rendering failure is caught in the task
        assert "{bad_placeholder}" in template["subject"]

        # Verify rendering fails on the custom template
        kwargs = {
            "invoice_number": "INV-001",
            "total_gross": "1,000.00",
            "currency": "EUR",
            "period_start": "01.01.2026",
            "period_end": "31.01.2026",
            "company_name": "Test Co",
        }
        with pytest.raises(KeyError):
            template["subject"].format(**kwargs)

        # Verify default template renders fine
        default = EMAIL_TEMPLATES["de"]
        subject = default["subject"].format(**kwargs)
        assert subject == "Rechnung INV-001"


class TestSetInvoiceEmailTemplateMutation:
    def test_save_custom_template(self, admin_user):
        ctx = _make_context(admin_user)
        info = Mock()
        info.context = ctx

        mutation = TenantMutation()
        result = mutation.set_invoice_email_template(
            info,
            input=SetInvoiceEmailTemplateInput(
                language="de",
                subject="Custom {invoice_number}",
                body="<p>Custom body</p>",
            ),
        )
        assert result.success is True

        admin_user.tenant.refresh_from_db()
        templates = admin_user.tenant.settings["invoice_email_templates"]
        assert templates["de"]["subject"] == "Custom {invoice_number}"
        assert templates["de"]["body"] == "<p>Custom body</p>"

    def test_clear_template(self, admin_user):
        admin_user.tenant.settings = {
            "invoice_email_templates": {
                "de": {"subject": "Custom", "body": "<p>Custom</p>"}
            }
        }
        admin_user.tenant.save()

        ctx = _make_context(admin_user)
        info = Mock()
        info.context = ctx

        mutation = TenantMutation()
        result = mutation.set_invoice_email_template(
            info,
            input=SetInvoiceEmailTemplateInput(language="de", subject="", body=""),
        )
        assert result.success is True

        admin_user.tenant.refresh_from_db()
        assert "invoice_email_templates" not in admin_user.tenant.settings

    def test_rejects_unsupported_language(self, admin_user):
        ctx = _make_context(admin_user)
        info = Mock()
        info.context = ctx

        mutation = TenantMutation()
        result = mutation.set_invoice_email_template(
            info,
            input=SetInvoiceEmailTemplateInput(
                language="fr", subject="test", body="test"
            ),
        )
        assert result.success is False
        assert "Unsupported language" in result.error


class TestInvoiceEmailTemplatesQuery:
    def test_returns_defaults_when_none_configured(self, admin_user):
        ctx = _make_context(admin_user)
        info = Mock()
        info.context = ctx

        query = TenantQuery()
        result = query.invoice_email_templates(info)
        assert result.success is True
        assert len(result.templates) == 2

        de = next(t for t in result.templates if t.language == "de")
        en = next(t for t in result.templates if t.language == "en")
        assert de.is_custom is False
        assert de.subject == EMAIL_TEMPLATES["de"]["subject"]
        assert en.is_custom is False
        assert en.subject == EMAIL_TEMPLATES["en"]["subject"]

    def test_returns_custom_and_default(self, admin_user):
        admin_user.tenant.settings = {
            "invoice_email_templates": {
                "de": {"subject": "Custom DE", "body": "<p>Custom</p>"}
            }
        }
        admin_user.tenant.save()

        ctx = _make_context(admin_user)
        info = Mock()
        info.context = ctx

        query = TenantQuery()
        result = query.invoice_email_templates(info)
        assert result.success is True

        de = next(t for t in result.templates if t.language == "de")
        en = next(t for t in result.templates if t.language == "en")
        assert de.is_custom is True
        assert de.subject == "Custom DE"
        assert en.is_custom is False
        assert en.subject == EMAIL_TEMPLATES["en"]["subject"]
