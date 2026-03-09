"""HubSpot integration service for customer and product sync."""
import logging
from datetime import datetime, timezone, date
import decimal
from decimal import Decimal
from typing import Any

import httpx
from django.db import models, transaction

from apps.customers.models import Customer, CustomerNote, CustomerAttachment, CustomerLink
from apps.contracts.models import Contract, ContractGroup, ContractItem
from apps.products.models import Product, ProductPrice
from apps.tenants.models import Tenant

logger = logging.getLogger(__name__)

HUBSPOT_API_BASE = "https://api.hubapi.com"


class HubSpotError(Exception):
    """HubSpot API error."""

    pass


class HubSpotService:
    """Service for syncing customers and products from HubSpot."""

    def __init__(self, tenant: Tenant):
        self.tenant = tenant
        self.config = tenant.hubspot_config or {}
        self.api_key = self.config.get("api_key", "")

    @property
    def is_configured(self) -> bool:
        """Check if HubSpot integration is configured."""
        return bool(self.api_key)

    def _get_headers(self) -> dict[str, str]:
        """Get headers for HubSpot API requests."""
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    @staticmethod
    def _api_error_message(status_code: int, context: str = "") -> str:
        """Return a user-friendly error message for HubSpot API errors."""
        prefix = f"{context}: " if context else ""
        if status_code == 401:
            return f"{prefix}Invalid or expired API key (HTTP 401)"
        if status_code == 403:
            return f"{prefix}Insufficient API key permissions — check scopes in HubSpot (HTTP 403)"
        return f"{prefix}API error: {status_code}"

    async def test_connection(self) -> dict[str, Any]:
        """Test the HubSpot API connection."""
        if not self.is_configured:
            return {"success": False, "error": "API key not configured"}

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{HUBSPOT_API_BASE}/crm/v3/objects/companies",
                    headers=self._get_headers(),
                    params={"limit": 1},
                    timeout=10.0,
                )

                if response.status_code == 200:
                    return {"success": True, "error": None}
                elif response.status_code == 401:
                    return {"success": False, "error": "Invalid API key"}
                else:
                    return {
                        "success": False,
                        "error": self._api_error_message(response.status_code),
                    }
        except httpx.TimeoutException:
            return {"success": False, "error": "Connection timeout"}
        except Exception as e:
            logger.exception("HubSpot connection test failed")
            return {"success": False, "error": str(e)}

    def test_connection_sync(self) -> dict[str, Any]:
        """Synchronous version of test_connection."""
        if not self.is_configured:
            return {"success": False, "error": "API key not configured"}

        try:
            with httpx.Client() as client:
                response = client.get(
                    f"{HUBSPOT_API_BASE}/crm/v3/objects/companies",
                    headers=self._get_headers(),
                    params={"limit": 1},
                    timeout=10.0,
                )

                if response.status_code == 200:
                    # Also fetch portal ID for building HubSpot URLs
                    self._fetch_and_store_portal_id(client)
                    return {"success": True, "error": None}
                elif response.status_code == 401:
                    return {"success": False, "error": "Invalid API key"}
                else:
                    return {
                        "success": False,
                        "error": self._api_error_message(response.status_code),
                    }
        except httpx.TimeoutException:
            return {"success": False, "error": "Connection timeout"}
        except Exception as e:
            logger.exception("HubSpot connection test failed")
            return {"success": False, "error": str(e)}

    def _fetch_and_store_portal_id(self, client: httpx.Client) -> None:
        """Fetch and store HubSpot portal ID for building URLs."""
        try:
            response = client.get(
                f"{HUBSPOT_API_BASE}/account-info/v3/details",
                headers=self._get_headers(),
                timeout=10.0,
            )
            if response.status_code == 200:
                data = response.json()
                portal_id = data.get("portalId")
                if portal_id:
                    self.tenant.hubspot_config["portal_id"] = str(portal_id)
                    self.tenant.save(update_fields=["hubspot_config"])
        except Exception as e:
            logger.warning(f"Failed to fetch HubSpot portal ID: {e}")

    def _get_company_filters(self) -> list[dict]:
        """Get company filters from tenant config."""
        return self.config.get("company_filters", [])

    def _get_company_properties(self) -> str:
        """Build the list of HubSpot properties to fetch, including filter properties."""
        base = {"name", "address", "city", "zip", "country_list", "phone", "website", "domain", "lifecyclestage", "hs_merged_object_ids", "vatid"}
        for f in self._get_company_filters():
            prop = f.get("property_name", "")
            if prop:
                base.add(prop)
        return ",".join(sorted(base))

    def list_company_properties(self) -> dict[str, Any]:
        """List all available company properties from HubSpot.

        Returns:
            {
                "success": bool,
                "error": str | None,
                "properties": list[dict] | None,  # [{name, label, type, options}]
            }
        """
        if not self.is_configured:
            return {"success": False, "error": "API key not configured", "properties": None}

        try:
            with httpx.Client() as client:
                response = client.get(
                    f"{HUBSPOT_API_BASE}/crm/v3/properties/companies",
                    headers=self._get_headers(),
                    timeout=10.0,
                )

                if response.status_code != 200:
                    return {
                        "success": False,
                        "error": self._api_error_message(response.status_code),
                        "properties": None,
                    }

                data = response.json()
                properties = []

                for prop in data.get("results", []):
                    prop_type = prop.get("type", "")
                    options = None
                    if prop_type == "enumeration":
                        options = [opt.get("value") for opt in prop.get("options", [])]

                    properties.append({
                        "name": prop.get("name", ""),
                        "label": prop.get("label", ""),
                        "type": prop_type,
                        "options": options,
                    })

                # Sort by label for easier browsing
                properties.sort(key=lambda p: p.get("label", "").lower())

                return {
                    "success": True,
                    "error": None,
                    "properties": properties,
                }

        except httpx.TimeoutException:
            return {"success": False, "error": "Connection timeout", "properties": None}
        except Exception as e:
            logger.exception("HubSpot list properties failed")
            return {"success": False, "error": str(e), "properties": None}

    def check_company_property(self, property_name: str) -> dict[str, Any]:
        """Check if a company property exists and get its available options.

        Returns:
            {
                "success": bool,
                "error": str | None,
                "exists": bool,
                "options": list[str] | None,  # Available values for enumeration properties
                "property_type": str | None,  # e.g., "enumeration", "string", "number"
            }
        """
        if not self.is_configured:
            return {"success": False, "error": "API key not configured", "exists": False}

        try:
            with httpx.Client() as client:
                response = client.get(
                    f"{HUBSPOT_API_BASE}/crm/v3/properties/companies/{property_name}",
                    headers=self._get_headers(),
                    timeout=10.0,
                )

                if response.status_code == 404:
                    return {
                        "success": True,
                        "error": None,
                        "exists": False,
                        "options": None,
                        "property_type": None,
                    }

                if response.status_code != 200:
                    return {
                        "success": False,
                        "error": self._api_error_message(response.status_code),
                        "exists": False,
                    }

                data = response.json()
                property_type = data.get("type", "")

                # Get options for enumeration properties
                options = None
                if property_type == "enumeration":
                    options = [opt.get("value") for opt in data.get("options", [])]

                return {
                    "success": True,
                    "error": None,
                    "exists": True,
                    "options": options,
                    "property_type": property_type,
                }

        except httpx.TimeoutException:
            return {"success": False, "error": "Connection timeout", "exists": False}
        except Exception as e:
            logger.exception("HubSpot property check failed")
            return {"success": False, "error": str(e), "exists": False}

    def list_contact_association_labels(self) -> dict[str, Any]:
        """List available association labels for company-to-contact relationships.

        Returns:
            {
                "success": bool,
                "error": str | None,
                "labels": list[dict] | None,  # [{type_id, label, category}]
            }
        """
        if not self.is_configured:
            return {"success": False, "error": "API key not configured", "labels": None}

        try:
            with httpx.Client() as client:
                response = client.get(
                    f"{HUBSPOT_API_BASE}/crm/v4/associations/companies/contacts/labels",
                    headers=self._get_headers(),
                    timeout=10.0,
                )

                if response.status_code != 200:
                    return {
                        "success": False,
                        "error": self._api_error_message(response.status_code),
                        "labels": None,
                    }

                data = response.json()
                labels = [
                    {
                        "type_id": r.get("typeId"),
                        "label": r.get("label"),
                        "category": r.get("category"),
                    }
                    for r in data.get("results", [])
                    if r.get("label")  # Skip unlabeled associations
                ]

                return {"success": True, "error": None, "labels": labels}

        except httpx.TimeoutException:
            return {"success": False, "error": "Connection timeout", "labels": None}
        except Exception as e:
            logger.exception("HubSpot list association labels failed")
            return {"success": False, "error": str(e), "labels": None}

    def _company_matches_filters(self, properties: dict) -> bool:
        """Check if a company matches the configured filters.

        If no filters are configured, all companies are considered active.
        If filters are configured, company must match ALL filters (AND logic).
        Each filter checks if the property value is in the allowed values list.
        """
        filters = self._get_company_filters()

        # No filters = all companies are active
        if not filters:
            return True

        # Check each filter (AND logic)
        for f in filters:
            property_name = f.get("property_name", "")
            allowed_values = f.get("values", [])

            if not property_name or not allowed_values:
                continue

            property_value = properties.get(property_name, "")
            if property_value not in allowed_values:
                return False

        return True

    def fetch_company(self, hubspot_id: str) -> dict | None:
        """Fetch a single company from HubSpot CRM API.

        Returns the company dict or None if not found (404).
        """
        with httpx.Client() as client:
            response = client.get(
                f"{HUBSPOT_API_BASE}/crm/v3/objects/companies/{hubspot_id}",
                headers=self._get_headers(),
                params={"properties": self._get_company_properties()},
                timeout=30.0,
            )
        if response.status_code == 404:
            return None
        if response.status_code != 200:
            raise HubSpotError(self._api_error_message(response.status_code, "Fetch company"))
        return response.json()

    def fetch_product(self, hubspot_id: str) -> dict | None:
        """Fetch a single product from HubSpot CRM API."""
        with httpx.Client() as client:
            response = client.get(
                f"{HUBSPOT_API_BASE}/crm/v3/objects/products/{hubspot_id}",
                headers=self._get_headers(),
                params={"properties": "name,description,price,hs_sku,hs_recurring_billing_period"},
                timeout=30.0,
            )
        if response.status_code == 404:
            return None
        if response.status_code != 200:
            raise HubSpotError(self._api_error_message(response.status_code, "Fetch product"))
        return response.json()

    def fetch_deal(self, hubspot_id: str) -> dict | None:
        """Fetch a single deal from HubSpot CRM API."""
        with httpx.Client() as client:
            response = client.get(
                f"{HUBSPOT_API_BASE}/crm/v3/objects/deals/{hubspot_id}",
                headers=self._get_headers(),
                params={"properties": "dealname,dealstage,amount,closedate,pipeline"},
                timeout=30.0,
            )
        if response.status_code == 404:
            return None
        if response.status_code != 200:
            raise HubSpotError(self._api_error_message(response.status_code, "Fetch deal"))
        return response.json()

    def _search_objects(
        self,
        client: httpx.Client,
        object_type: str,
        properties: list[str],
        modified_since: date | None = None,
        modified_until: date | None = None,
    ) -> list[dict]:
        """Search HubSpot objects with optional date filters using the search API."""
        filters = []
        if modified_since:
            filters.append({
                "propertyName": "hs_lastmodifieddate",
                "operator": "GTE",
                "value": datetime.combine(modified_since, datetime.min.time(), tzinfo=timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z"),
            })
        if modified_until:
            filters.append({
                "propertyName": "hs_lastmodifieddate",
                "operator": "LTE",
                "value": datetime.combine(modified_until, datetime.max.time().replace(microsecond=0), tzinfo=timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.999Z"),
            })

        results = []
        after = 0
        has_more = True

        while has_more:
            body: dict[str, Any] = {
                "limit": 100,
                "properties": properties,
                "filterGroups": [{"filters": filters}] if filters else [],
            }
            if after:
                body["after"] = str(after)

            response = client.post(
                f"{HUBSPOT_API_BASE}/crm/v3/objects/{object_type}/search",
                headers=self._get_headers(),
                json=body,
                timeout=30.0,
            )

            if response.status_code != 200:
                raise HubSpotError(self._api_error_message(response.status_code, f"Search {object_type}"))

            data = response.json()
            results.extend(data.get("results", []))

            paging = data.get("paging", {})
            next_page = paging.get("next", {})
            after = next_page.get("after")
            has_more = bool(after)

        return results

    def _get_closed_won_stages(self, client: httpx.Client) -> set[str]:
        """Fetch all pipeline stages that represent closed-won deals.

        HubSpot stages have metadata.isClosed="true" for both won and lost.
        We distinguish won from lost by probability: 1.0 = won, 0.0 = lost.
        """
        response = client.get(
            f"{HUBSPOT_API_BASE}/crm/v3/pipelines/deals",
            headers=self._get_headers(),
            timeout=30.0,
        )
        if response.status_code != 200:
            logger.warning("Failed to fetch deal pipelines: %s, falling back to 'closedwon'", response.status_code)
            return {"closedwon"}

        won_stages: set[str] = set()
        for pipeline in response.json().get("results", []):
            for stage in pipeline.get("stages", []):
                metadata = stage.get("metadata", {})
                if metadata.get("isClosed") == "true" and metadata.get("probability") == "1.0":
                    won_stages.add(stage["id"])

        if not won_stages:
            won_stages.add("closedwon")
        logger.info("Resolved closed-won stages: %s", won_stages)
        return won_stages

    def sync_companies(self, modified_since: date | None = None, modified_until: date | None = None) -> dict[str, Any]:
        """Sync companies from HubSpot to local customers.

        Imports ALL companies but only marks those matching the configured
        filters as active. If no filters are configured, all companies are active.
        """
        if not self.is_configured:
            return {
                "success": False,
                "error": "API key not configured",
                "created": 0,
                "updated": 0,
            }

        created = 0
        updated = 0
        errors = []
        is_partial = modified_since is not None or modified_until is not None

        try:
            with httpx.Client() as client:
                if is_partial:
                    # Use search API for date-filtered syncs
                    companies = self._search_objects(
                        client, "companies",
                        properties=self._get_company_properties().split(","),
                        modified_since=modified_since,
                        modified_until=modified_until,
                    )
                    for company in companies:
                        try:
                            props = company.get("properties", {})
                            is_active = self._company_matches_filters(props)
                            result = self._sync_company(company, is_active=is_active)
                            if result == "created":
                                created += 1
                            elif result == "updated":
                                updated += 1
                        except Exception as e:
                            errors.append(f"Company {company.get('id')}: {str(e)}")
                            logger.exception(f"Failed to sync company {company.get('id')}")
                else:
                    after = None
                    has_more = True

                    while has_more:
                        params = {
                            "limit": 100,
                            "properties": self._get_company_properties(),
                        }
                        if after:
                            params["after"] = after

                        response = client.get(
                            f"{HUBSPOT_API_BASE}/crm/v3/objects/companies",
                            headers=self._get_headers(),
                            params=params,
                            timeout=30.0,
                        )

                        if response.status_code != 200:
                            return {
                                "success": False,
                                "error": self._api_error_message(response.status_code),
                                "created": created,
                                "updated": updated,
                            }

                        data = response.json()
                        companies = data.get("results", [])

                        for company in companies:
                            try:
                                properties = company.get("properties", {})
                                is_active = self._company_matches_filters(properties)

                                result = self._sync_company(company, is_active=is_active)
                                if result == "created":
                                    created += 1
                                elif result == "updated":
                                    updated += 1
                            except Exception as e:
                                errors.append(f"Company {company.get('id')}: {str(e)}")
                                logger.exception(f"Failed to sync company {company.get('id')}")

                        paging = data.get("paging", {})
                        next_page = paging.get("next", {})
                        after = next_page.get("after")
                        has_more = bool(after)

                # Sync billing contacts (after all companies are synced)
                billing_label = self.config.get("billing_contact_label")
                if billing_label:
                    self._sync_all_billing_contacts(client, billing_label, errors)

            # Don't update last_sync for partial syncs
            if not is_partial:
                self.tenant.hubspot_config["last_sync"] = datetime.now(timezone.utc).isoformat()
                self.tenant.save(update_fields=["hubspot_config"])

            return {
                "success": True,
                "error": None,
                "created": created,
                "updated": updated,
                "errors": errors if errors else None,
            }

        except httpx.TimeoutException:
            return {
                "success": False,
                "error": "Connection timeout",
                "created": created,
                "updated": updated,
            }
        except Exception as e:
            logger.exception("HubSpot sync failed")
            return {
                "success": False,
                "error": str(e),
                "created": created,
                "updated": updated,
            }

    def _sync_company(self, company_data: dict, is_active: bool = True) -> str:
        """Sync a single company from HubSpot.

        Args:
            company_data: The company data from HubSpot API
            is_active: Whether the company should be marked as active.
                       Based on company_filters configuration.
        """
        hubspot_id = str(company_data["id"])
        properties = company_data.get("properties", {})

        # Build address JSON
        address = {
            "street": properties.get("address", ""),
            "city": properties.get("city", ""),
            "zip": properties.get("zip", ""),
            "country": properties.get("country_list", ""),
        }

        # Try to find existing customer
        customer = Customer.objects.filter(
            tenant=self.tenant,
            hubspot_id=hubspot_id,
        ).first()

        # VAT ID: only update if HubSpot has a value (don't clear manual entries)
        hubspot_vat_id = properties.get("vatid", "")

        if customer:
            # Update existing
            customer.name = properties.get("name", "") or f"Company {hubspot_id}"
            customer.address = address
            customer.is_active = is_active
            customer.synced_at = datetime.now(timezone.utc)
            customer.hubspot_deleted_at = None
            if hubspot_vat_id:
                customer.vat_id = hubspot_vat_id
            customer.save()
            result = "updated"
        else:
            # Create new
            customer = Customer.objects.create(
                tenant=self.tenant,
                hubspot_id=hubspot_id,
                name=properties.get("name", "") or f"Company {hubspot_id}",
                address=address,
                is_active=is_active,
                synced_at=datetime.now(timezone.utc),
                vat_id=hubspot_vat_id,
            )
            result = "created"

        # Handle HubSpot company merges
        merged_ids_raw = properties.get("hs_merged_object_ids") or ""
        if merged_ids_raw:
            old_ids = [
                mid.strip() for mid in merged_ids_raw.split(";")
                if mid.strip() and mid.strip() != hubspot_id
            ]
            if old_ids:
                old_customers = Customer.objects.filter(
                    hubspot_id__in=old_ids, tenant=self.tenant
                )
                for old_customer in old_customers:
                    logger.info(
                        "Detected HubSpot merge: %s (%s) -> %s (%s)",
                        old_customer.hubspot_id, old_customer.name,
                        hubspot_id, customer.name,
                    )
                    self._merge_customer(old_customer, customer)

        return result

    def _merge_customer(self, source: Customer, target: Customer) -> None:
        """Merge source customer into target by reassigning all dependent objects.

        After reassignment, source is deactivated (not deleted) to preserve
        audit trail and prevent re-creation on next sync.
        """
        from apps.todos.models import TodoItem
        from apps.invoices.models import InvoiceRecord, ImportedInvoice
        from apps.banking.models import Counterparty

        with transaction.atomic():
            # Contracts (PROTECT — must reassign before any deletion)
            contracts_moved = Contract.objects.filter(customer=source).update(customer=target)

            # ContractGroups — consolidate duplicates by name
            groups_moved = 0
            groups_deleted = 0
            for src_group in ContractGroup.objects.filter(customer=source):
                existing_target_group = ContractGroup.objects.filter(
                    customer=target, name=src_group.name
                ).first()
                if existing_target_group:
                    # Move contracts from source group to existing target group
                    Contract.objects.filter(group=src_group).update(group=existing_target_group)
                    src_group.delete()
                    groups_deleted += 1
                else:
                    src_group.customer = target
                    src_group.save(update_fields=["customer"])
                    groups_moved += 1

            # Simple reassignments
            notes_moved = CustomerNote.objects.filter(customer=source).update(customer=target)
            attachments_moved = CustomerAttachment.objects.filter(customer=source).update(customer=target)
            links_moved = CustomerLink.objects.filter(customer=source).update(customer=target)
            todos_moved = TodoItem.objects.filter(customer=source).update(customer=target)
            invoices_moved = InvoiceRecord.objects.filter(customer=source).update(customer=target)
            imported_moved = ImportedInvoice.objects.filter(customer=source).update(customer=target)
            counterparties_moved = Counterparty.objects.filter(customer=source).update(customer=target)

            # Deactivate the old customer
            source.is_active = False
            source.hubspot_deleted_at = datetime.now(timezone.utc)
            source.save(update_fields=["is_active", "hubspot_deleted_at"])

        logger.info(
            "Merged customer '%s' (hubspot_id=%s) into '%s' (hubspot_id=%s): "
            "%d contracts, %d groups moved, %d groups consolidated, "
            "%d notes, %d attachments, %d links, %d todos, "
            "%d invoices, %d imported invoices, %d counterparties",
            source.name, source.hubspot_id,
            target.name, target.hubspot_id,
            contracts_moved, groups_moved, groups_deleted,
            notes_moved, attachments_moved, links_moved, todos_moved,
            invoices_moved, imported_moved, counterparties_moved,
        )

    def _sync_all_billing_contacts(
        self, client: httpx.Client, billing_label: str, errors: list[str]
    ) -> None:
        """Sync billing contact emails for all customers with active contracts."""
        # Only sync for customers that have at least one active contract
        customers_with_contracts = Customer.objects.filter(
            tenant=self.tenant,
            hubspot_id__isnull=False,
            is_active=True,
            contracts__status__in=[
                Contract.Status.ACTIVE,
                Contract.Status.PAUSED,
            ],
        ).exclude(hubspot_id="").distinct()

        for customer in customers_with_contracts:
            try:
                self._sync_billing_contacts_for_customer(
                    client, customer, billing_label
                )
            except Exception as e:
                errors.append(
                    f"Billing contacts for {customer.name} ({customer.hubspot_id}): {str(e)}"
                )
                logger.exception(
                    "Failed to sync billing contacts for customer %s", customer.hubspot_id
                )

    def _sync_billing_contacts_for_customer(
        self, client: httpx.Client, customer: Customer, billing_label: str
    ) -> None:
        """Fetch billing contacts from HubSpot and update customer billing_emails."""
        # Get associations with labels via v4 API
        response = client.get(
            f"{HUBSPOT_API_BASE}/crm/v4/objects/companies/{customer.hubspot_id}/associations/contacts",
            headers=self._get_headers(),
            timeout=10.0,
        )

        if response.status_code != 200:
            msg = self._api_error_message(
                response.status_code, "Billing contacts"
            )
            logger.warning(
                "Failed to fetch contact associations for company %s: %s",
                customer.hubspot_id, response.status_code,
            )
            raise HubSpotError(msg)

        data = response.json()

        # Find contact IDs with the matching billing label
        billing_contact_ids = []
        for assoc in data.get("results", []):
            for assoc_type in assoc.get("associationTypes", []):
                if assoc_type.get("label") == billing_label:
                    billing_contact_ids.append(str(assoc["toObjectId"]))
                    break

        if not billing_contact_ids:
            # No billing contacts — clear if previously set by sync
            if customer.billing_emails:
                customer.billing_emails = []
                customer.save(update_fields=["billing_emails"])
            return

        # Fetch email addresses for billing contacts
        emails = []
        for contact_id in billing_contact_ids:
            contact_resp = client.get(
                f"{HUBSPOT_API_BASE}/crm/v3/objects/contacts/{contact_id}",
                headers=self._get_headers(),
                params={"properties": "email"},
                timeout=10.0,
            )
            if contact_resp.status_code == 200:
                email = (
                    contact_resp.json()
                    .get("properties", {})
                    .get("email", "")
                )
                if email:
                    emails.append(email.strip().lower())
            else:
                logger.warning(
                    "Failed to fetch contact %s for billing email: %s",
                    contact_id, contact_resp.status_code,
                )

        # Deduplicate and sort
        emails = sorted(set(emails))

        # Update only if changed
        if emails != (customer.billing_emails or []):
            customer.billing_emails = emails
            customer.save(update_fields=["billing_emails"])
            logger.info(
                "Updated billing emails for '%s' (%s): %s",
                customer.name, customer.hubspot_id, emails,
            )

    def sync_products(self, modified_since: date | None = None, modified_until: date | None = None) -> dict[str, Any]:
        """Sync products from HubSpot to local products."""
        if not self.is_configured:
            return {
                "success": False,
                "error": "API key not configured",
                "created": 0,
                "updated": 0,
            }

        created = 0
        updated = 0
        errors = []
        is_partial = modified_since is not None or modified_until is not None
        product_props = ["name", "description", "price", "hs_sku", "hs_recurring_billing_period", "hs_status", "createdate"]

        try:
            with httpx.Client() as client:
                if is_partial:
                    # Use search API for date-filtered syncs
                    products = self._search_objects(
                        client, "products",
                        properties=product_props,
                        modified_since=modified_since,
                        modified_until=modified_until,
                    )
                    for product in products:
                        try:
                            result = self._sync_product(product)
                            if result == "created":
                                created += 1
                            elif result == "updated":
                                updated += 1
                        except Exception as e:
                            errors.append(f"Product {product.get('id')}: {str(e)}")
                            logger.exception(f"Failed to sync product {product.get('id')}")
                else:
                    # Step 1: Sync non-archived products
                    after = None
                    has_more = True

                    while has_more:
                        params = {
                            "limit": 100,
                            "properties": ",".join(product_props),
                        }
                        if after:
                            params["after"] = after

                        response = client.get(
                            f"{HUBSPOT_API_BASE}/crm/v3/objects/products",
                            headers=self._get_headers(),
                            params=params,
                            timeout=30.0,
                        )

                        if response.status_code != 200:
                            return {
                                "success": False,
                                "error": self._api_error_message(response.status_code),
                                "created": created,
                                "updated": updated,
                            }

                        data = response.json()
                        products = data.get("results", [])

                        for product in products:
                            try:
                                result = self._sync_product(product)
                                if result == "created":
                                    created += 1
                                elif result == "updated":
                                    updated += 1
                            except Exception as e:
                                errors.append(f"Product {product.get('id')}: {str(e)}")
                                logger.exception(f"Failed to sync product {product.get('id')}")

                        paging = data.get("paging", {})
                        next_page = paging.get("next", {})
                        after = next_page.get("after")
                        has_more = bool(after)

                    # Step 2: Check archived products - mark existing ones as inactive
                    after = None
                    has_more = True

                    while has_more:
                        params = {
                            "limit": 100,
                            "archived": "true",
                        }
                        if after:
                            params["after"] = after

                        response = client.get(
                            f"{HUBSPOT_API_BASE}/crm/v3/objects/products",
                            headers=self._get_headers(),
                            params=params,
                            timeout=30.0,
                        )

                        if response.status_code != 200:
                            logger.warning(f"Failed to fetch archived products: {response.status_code}")
                            break

                        data = response.json()
                        archived_products = data.get("results", [])

                        for product in archived_products:
                            hubspot_id = str(product["id"])
                            existing = Product.objects.filter(
                                tenant=self.tenant,
                                hubspot_id=hubspot_id,
                            ).first()
                            if existing and existing.is_active:
                                existing.is_active = False
                                existing.synced_at = datetime.now(timezone.utc)
                                existing.save(update_fields=["is_active", "synced_at"])
                                updated += 1

                        paging = data.get("paging", {})
                        next_page = paging.get("next", {})
                        after = next_page.get("after")
                        has_more = bool(after)

            # Don't update last_sync for partial syncs
            if not is_partial:
                self.tenant.hubspot_config["last_product_sync"] = datetime.now(timezone.utc).isoformat()
                self.tenant.save(update_fields=["hubspot_config"])

            return {
                "success": True,
                "error": None,
                "created": created,
                "updated": updated,
                "errors": errors if errors else None,
            }

        except httpx.TimeoutException:
            return {
                "success": False,
                "error": "Connection timeout",
                "created": created,
                "updated": updated,
            }
        except Exception as e:
            logger.exception("HubSpot product sync failed")
            return {
                "success": False,
                "error": str(e),
                "created": created,
                "updated": updated,
            }

    def _map_billing_period(self, hs_billing_period: str | None) -> str | None:
        """Map HubSpot billing period to our billing frequency."""
        if not hs_billing_period:
            return None
        mapping = {
            "P1M": Product.BillingFrequency.MONTHLY,
            "P3M": Product.BillingFrequency.QUARTERLY,
            "P6M": Product.BillingFrequency.SEMI_ANNUAL,
            "P12M": Product.BillingFrequency.ANNUAL,
            # Also handle lowercase variants
            "monthly": Product.BillingFrequency.MONTHLY,
            "quarterly": Product.BillingFrequency.QUARTERLY,
            "semiannually": Product.BillingFrequency.SEMI_ANNUAL,
            "annually": Product.BillingFrequency.ANNUAL,
        }
        return mapping.get(hs_billing_period)

    def _sync_product(self, product_data: dict) -> str:
        """Sync a single product from HubSpot."""
        hubspot_id = str(product_data["id"])
        properties = product_data.get("properties", {})

        # Determine product type and billing frequency based on recurring billing period
        # If hs_recurring_billing_period is set, it's a recurring subscription
        # Otherwise, it's a one-off product
        billing_period = properties.get("hs_recurring_billing_period")
        product_type = Product.ProductType.SUBSCRIPTION if billing_period else Product.ProductType.ONE_OFF
        billing_frequency = self._map_billing_period(billing_period)

        # Determine active state: must have hs_status = "active"
        hs_status = properties.get("hs_status") or ""
        is_active = hs_status.lower() == "active"

        # Try to find existing product
        product = Product.objects.filter(
            tenant=self.tenant,
            hubspot_id=hubspot_id,
        ).first()

        name = properties.get("name", "") or f"Product {hubspot_id}"
        description = properties.get("description", "") or ""
        sku = properties.get("hs_sku", "") or ""
        price_value = properties.get("price")

        if product:
            # Update existing
            product.name = name
            product.description = description
            product.sku = sku
            product.type = product_type
            product.billing_frequency = billing_frequency
            product.is_active = is_active
            product.synced_at = datetime.now(timezone.utc)
            product.hubspot_deleted_at = None
            product.save()
            result = "updated"
        else:
            # Create new
            product = Product.objects.create(
                tenant=self.tenant,
                hubspot_id=hubspot_id,
                name=name,
                description=description,
                sku=sku,
                type=product_type,
                billing_frequency=billing_frequency,
                is_active=is_active,
                synced_at=datetime.now(timezone.utc),
            )
            result = "created"

        # Update or create price if available
        if price_value:
            try:
                price_decimal = Decimal(str(price_value))
                # Get or create current price
                current_price = ProductPrice.objects.filter(
                    product=product,
                    valid_to__isnull=True,
                ).first()

                if current_price:
                    if current_price.price != price_decimal:
                        # Price changed, close old price and create new
                        current_price.valid_to = date.today()
                        current_price.save()
                        ProductPrice.objects.create(
                            tenant=self.tenant,
                            product=product,
                            price=price_decimal,
                            valid_from=date.today(),
                        )
                else:
                    # No current price, create one
                    ProductPrice.objects.create(
                        tenant=self.tenant,
                        product=product,
                        price=price_decimal,
                        valid_from=date.today(),
                    )
            except (ValueError, TypeError):
                logger.warning(f"Invalid price value for product {hubspot_id}: {price_value}")

        return result

    def sync_deals(self, modified_since: date | None = None, modified_until: date | None = None) -> dict[str, Any]:
        """Sync closed won deals from HubSpot as contract drafts."""
        if not self.is_configured:
            return {
                "success": False,
                "error": "API key not configured",
                "created": 0,
                "skipped": 0,
            }

        created = 0
        skipped = 0
        errors = []
        is_partial = modified_since is not None or modified_until is not None
        deal_props = ["dealname", "closedate", "amount", "dealstage", "pipeline"]

        try:
            with httpx.Client() as client:
                # Resolve closed-won stages dynamically from pipeline API
                closed_won_stages = self._get_closed_won_stages(client)

                if is_partial:
                    # Use search API for date-filtered syncs
                    deals = self._search_objects(
                        client, "deals",
                        properties=deal_props,
                        modified_since=modified_since,
                        modified_until=modified_until,
                    )
                    for deal in deals:
                        try:
                            properties = deal.get("properties", {})
                            dealstage = properties.get("dealstage", "")
                            if dealstage not in closed_won_stages:
                                continue
                            result = self._sync_deal(deal, client, closed_won_stages)
                            if result == "created":
                                created += 1
                            elif result == "skipped":
                                skipped += 1
                        except Exception as e:
                            errors.append(f"Deal {deal.get('id')}: {str(e)}")
                            logger.exception(f"Failed to sync deal {deal.get('id')}")
                else:
                    after = None
                    has_more = True

                    while has_more:
                        params = {
                            "limit": 100,
                            "properties": ",".join(deal_props),
                            "associations": "companies",
                        }
                        if after:
                            params["after"] = after

                        response = client.get(
                            f"{HUBSPOT_API_BASE}/crm/v3/objects/deals",
                            headers=self._get_headers(),
                            params=params,
                            timeout=30.0,
                        )

                        if response.status_code != 200:
                            return {
                                "success": False,
                                "error": self._api_error_message(response.status_code),
                                "created": created,
                                "skipped": skipped,
                            }

                        data = response.json()
                        deals = data.get("results", [])

                        for deal in deals:
                            try:
                                properties = deal.get("properties", {})
                                dealstage = properties.get("dealstage", "")

                                # Only process closed won deals (dynamic stage detection)
                                if dealstage not in closed_won_stages:
                                    continue

                                result = self._sync_deal(deal, client, closed_won_stages)
                                if result == "created":
                                    created += 1
                                elif result == "skipped":
                                    skipped += 1
                            except Exception as e:
                                errors.append(f"Deal {deal.get('id')}: {str(e)}")
                                logger.exception(f"Failed to sync deal {deal.get('id')}")

                        paging = data.get("paging", {})
                        next_page = paging.get("next", {})
                        after = next_page.get("after")
                        has_more = bool(after)

            # Don't update last_sync for partial syncs
            if not is_partial:
                self.tenant.hubspot_config["last_deal_sync"] = datetime.now(timezone.utc).isoformat()
                self.tenant.save(update_fields=["hubspot_config"])

            return {
                "success": True,
                "error": None,
                "created": created,
                "skipped": skipped,
                "errors": errors if errors else None,
            }

        except httpx.TimeoutException:
            return {
                "success": False,
                "error": "Connection timeout",
                "created": created,
                "skipped": skipped,
            }
        except Exception as e:
            logger.exception("HubSpot deal sync failed")
            return {
                "success": False,
                "error": str(e),
                "created": created,
                "skipped": skipped,
            }

    def check_deal(self, deal_id: str) -> dict[str, Any]:
        """Fetch a single deal from HubSpot and explain sync status."""
        if not self.is_configured:
            return {"success": False, "error": "API key not configured"}

        try:
            with httpx.Client() as client:
                # Fetch deal
                response = client.get(
                    f"{HUBSPOT_API_BASE}/crm/v3/objects/deals/{deal_id}",
                    headers=self._get_headers(),
                    params={"properties": "dealname,closedate,amount,dealstage,pipeline"},
                    timeout=15.0,
                )
                if response.status_code == 404:
                    return {"success": False, "error": f"Deal {deal_id} not found in HubSpot"}
                if response.status_code != 200:
                    return {"success": False, "error": self._api_error_message(response.status_code, "Fetch deal")}

                deal = response.json()
                properties = deal.get("properties", {})
                dealstage = properties.get("dealstage", "")
                pipeline_id = properties.get("pipeline", "")
                deal_name = properties.get("dealname", "")

                # Resolve pipeline name and check if stage is closed-won
                closed_won_stages = self._get_closed_won_stages(client)
                is_closed_won = dealstage in closed_won_stages

                # Resolve pipeline name
                pipeline_name = pipeline_id
                try:
                    pipe_resp = client.get(
                        f"{HUBSPOT_API_BASE}/crm/v3/pipelines/deals/{pipeline_id}",
                        headers=self._get_headers(),
                        timeout=10.0,
                    )
                    if pipe_resp.status_code == 200:
                        pipe_data = pipe_resp.json()
                        pipeline_name = pipe_data.get("label", pipeline_id)
                        # Also resolve stage label
                        for stage in pipe_data.get("stages", []):
                            if stage["id"] == dealstage:
                                dealstage_label = stage.get("label", dealstage)
                                break
                        else:
                            dealstage_label = dealstage
                    else:
                        dealstage_label = dealstage
                except Exception:
                    dealstage_label = dealstage

                # Check associated company
                assoc_response = client.get(
                    f"{HUBSPOT_API_BASE}/crm/v3/objects/deals/{deal_id}/associations/companies",
                    headers=self._get_headers(),
                    timeout=10.0,
                )
                associated_company = None
                if assoc_response.status_code == 200:
                    companies = assoc_response.json().get("results", [])
                    if companies:
                        company_id = str(companies[0].get("id"))
                        customer = Customer.objects.filter(
                            tenant=self.tenant, hubspot_id=company_id
                        ).first()
                        associated_company = {
                            "hubspotId": company_id,
                            "name": customer.name if customer else None,
                            "synced": customer is not None,
                        }

                # Check existing contract
                existing_contract = Contract.objects.filter(
                    tenant=self.tenant, hubspot_deal_id=deal_id
                ).first()

                # Determine reason
                reasons = []
                if not is_closed_won:
                    reasons.append(f"Stage '{dealstage_label}' ({dealstage}) is not a closed-won stage")
                if not associated_company:
                    reasons.append("No associated company found")
                elif not associated_company["synced"]:
                    reasons.append(f"Associated company {associated_company['hubspotId']} not synced to system")
                if existing_contract:
                    reasons.append(f"Contract already exists (ID: {existing_contract.id})")

                return {
                    "success": True,
                    "dealName": deal_name,
                    "dealStage": dealstage_label,
                    "dealStageId": dealstage,
                    "pipeline": pipeline_name,
                    "pipelineId": pipeline_id,
                    "isClosedWon": is_closed_won,
                    "associatedCompany": associated_company,
                    "existingContractId": str(existing_contract.id) if existing_contract else None,
                    "wouldSync": is_closed_won and associated_company and associated_company["synced"] and not existing_contract,
                    "reasons": reasons if reasons else ["Ready to sync"],
                }

        except Exception as e:
            logger.exception("Failed to check deal %s", deal_id)
            return {"success": False, "error": str(e)}

    def _sync_deal(self, deal_data: dict, client: httpx.Client, closed_won_stages: set[str] | None = None) -> str:
        """Sync a single closed won deal as a contract draft."""
        hubspot_deal_id = str(deal_data["id"])
        properties = deal_data.get("properties", {})

        # Only import closed won deals
        dealstage = properties.get("dealstage", "")
        if closed_won_stages:
            if dealstage not in closed_won_stages:
                logger.debug("Deal %s stage is '%s', skipping (not closed-won)", hubspot_deal_id, dealstage)
                return "skipped"
        elif dealstage != "closedwon":
            logger.debug("Deal %s stage is '%s', skipping (not closedwon)", hubspot_deal_id, dealstage)
            return "skipped"

        # Check if contract already exists for this deal
        existing = Contract.objects.filter(
            tenant=self.tenant,
            hubspot_deal_id=hubspot_deal_id,
        ).exists()
        if existing:
            return "skipped"

        # Get associated company
        associations = deal_data.get("associations", {})
        companies = associations.get("companies", {}).get("results", [])

        if not companies:
            # Try to fetch associations separately
            assoc_response = client.get(
                f"{HUBSPOT_API_BASE}/crm/v3/objects/deals/{hubspot_deal_id}/associations/companies",
                headers=self._get_headers(),
                timeout=10.0,
            )
            if assoc_response.status_code == 200:
                companies = assoc_response.json().get("results", [])

        if not companies:
            logger.warning(f"Deal {hubspot_deal_id} has no associated company")
            return "skipped"

        # Find the customer in our system
        company_hubspot_id = str(companies[0].get("id"))
        customer = Customer.objects.filter(
            tenant=self.tenant,
            hubspot_id=company_hubspot_id,
        ).first()

        if not customer:
            logger.warning(f"Deal {hubspot_deal_id}: Company {company_hubspot_id} not found in system")
            return "skipped"

        # Parse close date
        closedate_str = properties.get("closedate")
        if closedate_str:
            # HubSpot returns ISO format: 2024-01-15T00:00:00.000Z
            closedate = datetime.fromisoformat(closedate_str.replace("Z", "+00:00")).date()
        else:
            closedate = date.today()

        # Create contract draft
        deal_name = properties.get("dealname", "") or f"Deal {hubspot_deal_id}"

        contract = Contract.objects.create(
            tenant=self.tenant,
            hubspot_deal_id=hubspot_deal_id,
            name=deal_name,
            customer=customer,
            status=Contract.Status.DRAFT,
            start_date=closedate,
            billing_start_date=closedate,
            deal_won_date=closedate,
            billing_interval=Contract.BillingInterval.MONTHLY,  # Will be updated after line items
            billing_anchor_day=1,
        )

        # Fetch and create line items, then update billing interval from products
        self._sync_deal_line_items(contract, hubspot_deal_id, client)
        self._update_contract_billing_interval_from_items(contract)

        # Notify all active tenant users about the new contract
        from apps.core.notifications import notify
        from apps.tenants.models import User
        active_users = list(User.objects.filter(tenant=self.tenant, is_active=True))
        notify(
            self.tenant,
            "hubspot_new_contract",
            recipients=active_users,
            contract_name=contract.name,
            customer_name=customer.name,
        )

        return "created"

    def _sync_deal_line_items(self, contract: Contract, deal_id: str, client: httpx.Client) -> None:
        """Fetch line items from HubSpot deal and create contract items."""
        # Fetch line items associated with the deal
        response = client.get(
            f"{HUBSPOT_API_BASE}/crm/v3/objects/deals/{deal_id}/associations/line_items",
            headers=self._get_headers(),
            timeout=10.0,
        )

        if response.status_code != 200:
            logger.warning(f"Failed to fetch line items for deal {deal_id}: {response.status_code}")
            return

        line_item_associations = response.json().get("results", [])
        if not line_item_associations:
            return

        # Fetch line item details
        line_item_ids = [str(item.get("id")) for item in line_item_associations]

        for line_item_id in line_item_ids:
            try:
                self._create_contract_item_from_line_item(contract, line_item_id, client)
            except Exception as e:
                logger.exception(f"Failed to create contract item from line item {line_item_id}: {e}")

    def _create_contract_item_from_line_item(
        self, contract: Contract, line_item_id: str, client: httpx.Client
    ) -> None:
        """Create a contract item from a HubSpot line item."""
        # Fetch line item details
        response = client.get(
            f"{HUBSPOT_API_BASE}/crm/v3/objects/line_items/{line_item_id}",
            headers=self._get_headers(),
            params={"properties": "name,quantity,price,amount,hs_product_id"},
            timeout=10.0,
        )

        if response.status_code != 200:
            logger.warning(f"Failed to fetch line item {line_item_id}: {response.status_code}")
            return

        line_item = response.json()
        properties = line_item.get("properties", {})

        # Get the product
        hs_product_id = properties.get("hs_product_id")
        product = None

        if hs_product_id:
            product = Product.objects.filter(
                tenant=self.tenant,
                hubspot_id=str(hs_product_id),
            ).first()

        if not product:
            # Try to find by name or create a placeholder
            name = properties.get("name", f"Line Item {line_item_id}")
            product = Product.objects.filter(
                tenant=self.tenant,
                name=name,
            ).first()

            if not product:
                # Create placeholder product
                product = Product.objects.create(
                    tenant=self.tenant,
                    name=name,
                    type=Product.ProductType.ONE_OFF,
                )
                logger.info(f"Created placeholder product '{name}' for line item {line_item_id}")

        # Parse quantity and price
        quantity = 1
        try:
            qty_value = properties.get("quantity")
            if qty_value:
                quantity = int(float(qty_value))
        except (ValueError, TypeError):
            pass

        unit_price = Decimal("0")
        try:
            price_value = properties.get("price")
            if price_value:
                unit_price = Decimal(str(price_value))
        except (ValueError, TypeError, decimal.InvalidOperation):
            pass

        # Determine price source by comparing with product's current list price
        price_source = ContractItem.PriceSource.CUSTOM
        today = date.today()
        current_price = ProductPrice.objects.filter(
            product=product,
            valid_from__lte=today,
        ).filter(
            models.Q(valid_to__isnull=True) | models.Q(valid_to__gte=today)
        ).order_by("-valid_from").first()

        if current_price and current_price.price == unit_price:
            price_source = ContractItem.PriceSource.LIST

        # Create contract item (start_date and billing_start_date
        # default to the contract's values when left null)
        ContractItem.objects.create(
            tenant=self.tenant,
            contract=contract,
            product=product,
            quantity=quantity,
            unit_price=unit_price,
            price_source=price_source,
        )

    def _update_contract_billing_interval_from_items(self, contract: Contract) -> None:
        """Update contract billing interval based on products' billing frequency.

        If all subscription products have the same billing frequency, use that.
        Otherwise, keep the default monthly interval.
        """
        # Map product billing frequency to contract billing interval
        frequency_to_interval = {
            Product.BillingFrequency.MONTHLY: Contract.BillingInterval.MONTHLY,
            Product.BillingFrequency.QUARTERLY: Contract.BillingInterval.QUARTERLY,
            Product.BillingFrequency.SEMI_ANNUAL: Contract.BillingInterval.SEMI_ANNUAL,
            Product.BillingFrequency.ANNUAL: Contract.BillingInterval.ANNUAL,
        }

        # Get billing frequencies from subscription products in contract items
        items = ContractItem.objects.filter(contract=contract).select_related("product")

        billing_frequencies = set()
        for item in items:
            if item.product and item.product.type == Product.ProductType.SUBSCRIPTION:
                if item.product.billing_frequency:
                    billing_frequencies.add(item.product.billing_frequency)

        # If all subscription products have the same billing frequency, use it
        if len(billing_frequencies) == 1:
            frequency = billing_frequencies.pop()
            interval = frequency_to_interval.get(frequency)
            if interval and interval != contract.billing_interval:
                contract.billing_interval = interval
                contract.save(update_fields=["billing_interval"])
