"""Celery tasks for time tracking data sync and order confirmation sending."""

import logging
import time
from collections import defaultdict

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=30,
    retry_kwargs={"max_retries": 2},
    acks_late=True,
)
def sync_time_tracking_mapping_task(self, mapping_id: int) -> bool:
    """Sync cached time tracking data for a single mapping."""
    from apps.contracts.services.time_tracking import sync_mapping_data

    return sync_mapping_data(mapping_id)


@shared_task(acks_late=True)
def refresh_all_time_tracking_data() -> int:
    """Refresh cached data for all active-tenant time tracking mappings.

    Groups mappings by tenant to send per-tenant notification summaries.
    Paces requests with a 5-second gap between each mapping to avoid
    hitting Clockodo's rate limits.

    Returns:
        Number of mappings synced.
    """
    from apps.contracts.models import TimeTrackingProjectMapping
    from apps.contracts.services.time_tracking import sync_mapping_data
    from apps.core.notifications import notify
    from apps.tenants.models import User

    mappings = list(
        TimeTrackingProjectMapping.objects.filter(
            tenant__is_active=True,
        ).select_related("tenant")
    )

    logger.info("Refreshing time tracking data for %d mappings", len(mappings))

    # Group by tenant
    tenant_stats = defaultdict(lambda: {"synced": 0, "failed": 0, "total": 0})

    total_synced = 0
    for mapping in mappings:
        tenant_id = mapping.tenant_id
        tenant_stats[tenant_id]["total"] += 1
        tenant_stats[tenant_id]["tenant"] = mapping.tenant

        try:
            if sync_mapping_data(mapping.id):
                total_synced += 1
                tenant_stats[tenant_id]["synced"] += 1
        except Exception:
            logger.exception("Failed to sync mapping %s", mapping.id)
            tenant_stats[tenant_id]["failed"] += 1
        time.sleep(5)  # Pace between mappings

    # Notify admin users per tenant
    for tenant_id, stats in tenant_stats.items():
        tenant = stats["tenant"]
        admins = list(
            User.objects.filter(tenant=tenant, is_active=True, is_admin=True)
        )
        if admins:
            notify(
                tenant,
                "time_tracking_sync_completed",
                recipients=admins,
                synced=stats["synced"],
                total=stats["total"],
                failed=stats["failed"],
            )

    logger.info(
        "Finished refreshing time tracking data: %d/%d synced",
        total_synced,
        len(mappings),
    )
    return total_synced


@shared_task(acks_late=True)
def auto_link_time_tracking_projects() -> int:
    """Auto-link time tracking projects based on pattern rules.

    For each active tenant with a configured provider:
    1. Fetch all projects once
    2. Match against active auto-link rules (non-cancelled contracts)
    3. Create mappings for new matches

    Returns:
        Number of new mappings created.
    """
    from apps.contracts.models import AutoLinkRule, Contract, TimeTrackingProjectMapping
    from apps.contracts.services.time_tracking import get_provider, matches_project_name
    from apps.tenants.models import Tenant

    tenants = Tenant.objects.filter(is_active=True)
    total_created = 0

    for tenant in tenants:
        provider = get_provider(tenant)
        if not provider:
            continue

        try:
            projects = provider.get_projects()
        except Exception:
            logger.exception("Failed to fetch projects for tenant %s", tenant.id)
            continue

        rules = list(
            AutoLinkRule.objects.filter(
                tenant=tenant,
                is_active=True,
            ).exclude(
                contract__status=Contract.Status.CANCELLED,
            ).select_related("contract", "contract_item").order_by("created_at")
        )

        if not rules:
            continue

        # Get already-linked project IDs for this tenant
        linked_ids = set(
            TimeTrackingProjectMapping.objects.filter(
                tenant=tenant,
            ).values_list("external_project_id", flat=True)
        )

        for rule in rules:
            for project in projects:
                if project.id in linked_ids:
                    continue
                if not matches_project_name(rule.pattern, rule.match_type, project.name):
                    continue

                TimeTrackingProjectMapping.objects.create(
                    tenant=tenant,
                    contract=rule.contract,
                    contract_item=rule.contract_item,
                    external_project_id=project.id,
                    external_project_name=project.name,
                    external_customer_name=project.customer_name,
                    link_source=TimeTrackingProjectMapping.LinkSource.AUTO,
                    auto_link_rule=rule,
                )
                linked_ids.add(project.id)
                total_created += 1

                # Trigger async data sync for new mapping
                mapping = TimeTrackingProjectMapping.objects.get(
                    tenant=tenant, external_project_id=project.id,
                )
                sync_time_tracking_mapping_task.delay(mapping.id)

    logger.info("Auto-link created %d new mappings", total_created)
    return total_created


@shared_task(bind=True, acks_late=True)
def send_order_confirmation_email_task(self, order_confirmation_id: int, user_id: int | None = None) -> bool:
    """Send an order confirmation email via M365 Graph API.

    No automatic retry to avoid duplicate sends.
    """
    from apps.contracts.order_confirmation_models import OrderConfirmation
    from apps.contracts.services.order_confirmation import OrderConfirmationService

    try:
        ab = OrderConfirmation.objects.select_related(
            "contract", "contract__customer", "tenant"
        ).get(id=order_confirmation_id)
    except OrderConfirmation.DoesNotExist:
        logger.error("OrderConfirmation %s not found for email sending", order_confirmation_id)
        return False

    service = OrderConfirmationService(ab.tenant)
    return service.send_order_confirmation(ab)


@shared_task(bind=True, acks_late=True)
def send_scheduled_reports(self):
    from datetime import date, timedelta
    from apps.tenants.models import ReportSchedule

    today = date.today()
    schedules = ReportSchedule.objects.filter(
        enabled=True,
        send_day_of_month=today.day,
    ).select_related("tenant")

    for schedule in schedules:
        try:
            prev_month_end = today.replace(day=1) - timedelta(days=1)
            year, month = prev_month_end.year, prev_month_end.month

            if schedule.report_type == "absence":
                _send_scheduled_absence_report(schedule, year, month)
            elif schedule.report_type == "department_time":
                _send_scheduled_dept_time_report(schedule, year, month)
        except Exception:
            logger.exception(
                "Failed to send scheduled %s report for tenant %s",
                schedule.report_type, schedule.tenant_id,
            )


def _send_scheduled_absence_report(schedule, year, month):
    from apps.contracts.services.absence_report import AbsenceReportService
    from apps.contracts.models import AbsenceReport

    service = AbsenceReportService(schedule.tenant)

    report = AbsenceReport.objects.filter(
        tenant=schedule.tenant, year=year, month=month
    ).first()
    if not report:
        report = service.generate_report(year, month)

    if schedule.auto_finalize and report.status == AbsenceReport.Status.DRAFT:
        report = service.finalize_report(report.id)

    if report.status == AbsenceReport.Status.FINALIZED:
        service.send_report(report.id, schedule.recipients)
    else:
        logger.warning("Absence report %s/%s not finalized, skipping send", year, month)


def _send_scheduled_dept_time_report(schedule, year, month):
    from apps.contracts.services.department_time_csv import generate_department_time_xlsx
    from apps.core.m365 import send_mail

    xlsx_bytes, filename = generate_department_time_xlsx(schedule.tenant, year, month)

    MONTH_NAMES_DE = {
        1: "Januar", 2: "Februar", 3: "März", 4: "April",
        5: "Mai", 6: "Juni", 7: "Juli", 8: "August",
        9: "September", 10: "Oktober", 11: "November", 12: "Dezember",
    }
    month_name = MONTH_NAMES_DE.get(month, str(month))

    send_mail(
        schedule.tenant,
        to=schedule.recipients,
        subject=f"Abteilungs-Zeitanalyse {month_name} {year}",
        body_html=f"<p>Abteilungs-Zeitanalyse für {month_name} {year} im Anhang.</p>",
        attachments=[{
            "name": filename,
            "content_type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "content_bytes": xlsx_bytes,
        }],
    )
