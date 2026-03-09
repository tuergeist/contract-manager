"""Clockodo project provisioning service for contract activation."""
import logging
from datetime import date

from apps.contracts.models import Contract, ContractItem, TimeTrackingProjectMapping
from apps.contracts.services.time_tracking import get_provider

logger = logging.getLogger(__name__)


def get_naming_templates(tenant) -> dict:
    """Get project naming templates from tenant config."""
    config = tenant.time_tracking_config or {}
    return {
        "maintenance": config.get("maintenance_project_template", "Wartung {customer_name}"),
        "oneoff": config.get("oneoff_project_template", "{customer_name} - {contract_name}"),
    }


def render_template(template: str, **kwargs) -> str:
    """Render a naming template with placeholders."""
    result = template
    for key, value in kwargs.items():
        result = result.replace(f"{{{key}}}", str(value))
    result = result.replace("{year}", str(date.today().year))
    return result


def preview_activation(contract: Contract) -> dict:
    """Preview what Clockodo projects would be created on activation.

    Returns dict with:
        clockodo_configured: bool
        customer_linked: bool
        customer_name: str
        clockodo_customer_id: str | None
        maintenance_needed: bool
        maintenance_project_exists: bool
        maintenance_project_name: str
        one_off_items: list[dict]  # [{id, description}]
    """
    tenant = contract.tenant
    customer = contract.customer

    provider = get_provider(tenant)
    result = {
        "clockodo_configured": provider is not None,
        "customer_linked": bool(customer.clockodo_customer_id),
        "customer_name": customer.name,
        "customer_id": customer.id,
        "clockodo_customer_id": customer.clockodo_customer_id,
        "maintenance_needed": False,
        "maintenance_project_exists": False,
        "maintenance_project_name": "",
        "one_off_items": [],
    }

    if not provider or not customer.clockodo_customer_id:
        # Still populate items info even without linking
        items = contract.items.all()
        result["maintenance_needed"] = any(not item.is_one_off for item in items)
        result["one_off_items"] = [
            {"id": item.id, "description": item.description}
            for item in items if item.is_one_off
        ]
        return result

    templates = get_naming_templates(tenant)
    items = list(contract.items.all())

    # Check recurring items
    has_recurring = any(not item.is_one_off for item in items)
    result["maintenance_needed"] = has_recurring

    if has_recurring:
        maintenance_name = render_template(
            templates["maintenance"],
            customer_name=customer.name,
            ab_number=contract.order_confirmation_number or "",
        )
        result["maintenance_project_name"] = maintenance_name

        # Check if maintenance project already exists in Clockodo
        try:
            existing_projects = provider.get_customer_projects(customer.clockodo_customer_id)
            result["maintenance_project_exists"] = any(
                p.name.lower() == maintenance_name.lower() for p in existing_projects
            )
        except Exception:
            pass

    # Collect one-off items
    result["one_off_items"] = [
        {"id": item.id, "description": item.description}
        for item in items if item.is_one_off
    ]

    return result


def provision_projects(
    contract: Contract,
    create_maintenance: bool = True,
    oneoff_strategy: str = "combined",  # "combined", "per_item", "skip"
    selected_oneoff_item_ids: list[int] | None = None,
) -> dict:
    """Create Clockodo projects and mappings for a contract.

    Args:
        contract: The contract being activated
        create_maintenance: Whether to create/link a maintenance project
        oneoff_strategy: "combined" (one project), "per_item" (one per item), "skip"
        selected_oneoff_item_ids: Optional filter for which one-off items to create projects for

    Returns:
        dict with 'success', 'created_projects' (list), 'errors' (list)
    """
    tenant = contract.tenant
    customer = contract.customer
    provider = get_provider(tenant)

    if not provider:
        return {"success": False, "created_projects": [], "errors": ["No provider configured"]}

    if not customer.clockodo_customer_id:
        return {"success": False, "created_projects": [], "errors": ["Customer not linked to Clockodo"]}

    templates = get_naming_templates(tenant)
    created = []
    errors = []

    # --- Maintenance project ---
    if create_maintenance:
        has_recurring = contract.items.filter(is_one_off=False).exists()
        if has_recurring:
            maintenance_name = render_template(
                templates["maintenance"],
                customer_name=customer.name,
                ab_number=contract.order_confirmation_number or "",
            )

            # Check if already exists
            existing_project = None
            try:
                existing_projects = provider.get_customer_projects(customer.clockodo_customer_id)
                existing_project = next(
                    (p for p in existing_projects if p.name.lower() == maintenance_name.lower()),
                    None,
                )
            except Exception as e:
                logger.warning("Failed to check existing projects: %s", e)

            if existing_project:
                # Link to existing
                _create_mapping_if_needed(
                    tenant, contract, existing_project.id, existing_project.name, customer.name
                )
                created.append({"name": existing_project.name, "action": "linked"})
            else:
                # Create new
                try:
                    result = provider.create_project(customer.clockodo_customer_id, maintenance_name)
                    _create_mapping_if_needed(
                        tenant, contract, result["id"], result["name"], customer.name
                    )
                    created.append({"name": result["name"], "action": "created"})
                except Exception as e:
                    errors.append(f"Failed to create maintenance project: {e}")

    # --- One-off projects ---
    if oneoff_strategy != "skip":
        oneoff_items = contract.items.filter(is_one_off=True)
        if selected_oneoff_item_ids:
            oneoff_items = oneoff_items.filter(id__in=selected_oneoff_item_ids)

        oneoff_items = list(oneoff_items)

        if oneoff_strategy == "combined" and oneoff_items:
            project_name = render_template(
                templates["oneoff"],
                customer_name=customer.name,
                contract_name=contract.name,
                ab_number=contract.order_confirmation_number or "",
            )
            try:
                result = provider.create_project(customer.clockodo_customer_id, project_name)
                mapping = _create_mapping_if_needed(
                    tenant, contract, result["id"], result["name"], customer.name
                )
                created.append({"name": result["name"], "action": "created"})
            except Exception as e:
                errors.append(f"Failed to create one-off project: {e}")

        elif oneoff_strategy == "per_item":
            for item in oneoff_items:
                project_name = render_template(
                    templates["oneoff"],
                    customer_name=customer.name,
                    contract_name=contract.name,
                    item_name=item.description,
                    ab_number=contract.order_confirmation_number or "",
                )
                try:
                    result = provider.create_project(customer.clockodo_customer_id, project_name)
                    _create_mapping_if_needed(
                        tenant, contract, result["id"], result["name"], customer.name,
                        contract_item=item,
                    )
                    created.append({"name": result["name"], "action": "created"})
                except Exception as e:
                    errors.append(f"Failed to create project for '{item.description}': {e}")

    return {
        "success": len(errors) == 0,
        "created_projects": created,
        "errors": errors,
    }


def _create_mapping_if_needed(
    tenant, contract, project_id, project_name, customer_name, contract_item=None
) -> TimeTrackingProjectMapping:
    """Create a TimeTrackingProjectMapping if one doesn't exist."""
    mapping, created = TimeTrackingProjectMapping.objects.get_or_create(
        tenant=tenant,
        external_project_id=project_id,
        defaults={
            "contract": contract,
            "contract_item": contract_item,
            "external_project_name": project_name,
            "external_customer_name": customer_name,
            "link_source": TimeTrackingProjectMapping.LinkSource.AUTO,
        },
    )
    if created:
        # Trigger sync
        from apps.contracts.tasks import sync_time_tracking_mapping_task
        sync_time_tracking_mapping_task.delay(mapping.id)
    return mapping
