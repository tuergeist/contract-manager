"""HubSpot integration service for customer and product sync."""
import logging
from datetime import datetime, timezone, date
import decimal
from decimal import Decimal
from typing import Any

import httpx
from django.db import models

from apps.customers.models import Customer
from apps.contracts.models import Contract, ContractItem
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
                        "error": f"API error: {response.status_code}",
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
                        "error": f"API error: {response.status_code}",
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

    def sync_companies(self) -> dict[str, Any]:
        """Sync companies from HubSpot to local customers."""
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

        try:
            with httpx.Client() as client:
                after = None
                has_more = True

                while has_more:
                    params = {
                        "limit": 100,
                        "properties": "name,address,city,zip,country,phone,website,domain,lifecyclestage",
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
                            "error": f"API error: {response.status_code}",
                            "created": created,
                            "updated": updated,
                        }

                    data = response.json()
                    companies = data.get("results", [])

                    for company in companies:
                        try:
                            # Only import customers with lifecycle stage "customer" or "evangelist"
                            properties = company.get("properties", {})
                            lifecycle_stage = properties.get("lifecyclestage", "")
                            if lifecycle_stage not in ("customer", "evangelist"):
                                # Remove if previously imported but no longer qualifies
                                self._remove_non_qualifying_company(company)
                                continue

                            result = self._sync_company(company)
                            if result == "created":
                                created += 1
                            elif result == "updated":
                                updated += 1
                        except Exception as e:
                            errors.append(f"Company {company.get('id')}: {str(e)}")
                            logger.exception(f"Failed to sync company {company.get('id')}")

                    # Check for pagination
                    paging = data.get("paging", {})
                    next_page = paging.get("next", {})
                    after = next_page.get("after")
                    has_more = bool(after)

            # Update last sync time
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

    def _remove_non_qualifying_company(self, company_data: dict) -> None:
        """Mark a previously imported company as inactive if lifecycle stage no longer qualifies."""
        hubspot_id = str(company_data["id"])
        customer = Customer.objects.filter(
            tenant=self.tenant,
            hubspot_id=hubspot_id,
        ).first()
        if customer and customer.is_active:
            customer.is_active = False
            customer.synced_at = datetime.now(timezone.utc)
            customer.save(update_fields=["is_active", "synced_at"])

    def _sync_company(self, company_data: dict) -> str:
        """Sync a single company from HubSpot."""
        hubspot_id = str(company_data["id"])
        properties = company_data.get("properties", {})

        # Build address JSON
        address = {
            "street": properties.get("address", ""),
            "city": properties.get("city", ""),
            "zip": properties.get("zip", ""),
            "country": properties.get("country", ""),
        }

        # Try to find existing customer
        customer = Customer.objects.filter(
            tenant=self.tenant,
            hubspot_id=hubspot_id,
        ).first()

        if customer:
            # Update existing (reactivate if previously deactivated)
            customer.name = properties.get("name", "") or f"Company {hubspot_id}"
            customer.address = address
            customer.is_active = True
            customer.synced_at = datetime.now(timezone.utc)
            customer.hubspot_deleted_at = None
            customer.save()
            return "updated"
        else:
            # Create new
            Customer.objects.create(
                tenant=self.tenant,
                hubspot_id=hubspot_id,
                name=properties.get("name", "") or f"Company {hubspot_id}",
                address=address,
                synced_at=datetime.now(timezone.utc),
            )
            return "created"

    def sync_products(self) -> dict[str, Any]:
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

        try:
            with httpx.Client() as client:
                after = None
                has_more = True

                while has_more:
                    params = {
                        "limit": 100,
                        "properties": "name,description,price,hs_sku,hs_recurring_billing_period,createdate",
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
                            "error": f"API error: {response.status_code}",
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

                    # Check for pagination
                    paging = data.get("paging", {})
                    next_page = paging.get("next", {})
                    after = next_page.get("after")
                    has_more = bool(after)

            # Update last product sync time
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
        billing_period = properties.get("hs_recurring_billing_period")
        product_type = Product.ProductType.SUBSCRIPTION if billing_period else Product.ProductType.ONE_OFF
        billing_frequency = self._map_billing_period(billing_period)

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

    def sync_deals(self) -> dict[str, Any]:
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

        try:
            with httpx.Client() as client:
                after = None
                has_more = True

                while has_more:
                    params = {
                        "limit": 100,
                        "properties": "dealname,closedate,amount,dealstage",
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
                            "error": f"API error: {response.status_code}",
                            "created": created,
                            "skipped": skipped,
                        }

                    data = response.json()
                    deals = data.get("results", [])

                    for deal in deals:
                        try:
                            properties = deal.get("properties", {})
                            dealstage = properties.get("dealstage", "")

                            # Only process closed won deals
                            if dealstage != "closedwon":
                                continue

                            result = self._sync_deal(deal, client)
                            if result == "created":
                                created += 1
                            elif result == "skipped":
                                skipped += 1
                        except Exception as e:
                            errors.append(f"Deal {deal.get('id')}: {str(e)}")
                            logger.exception(f"Failed to sync deal {deal.get('id')}")

                    # Check for pagination
                    paging = data.get("paging", {})
                    next_page = paging.get("next", {})
                    after = next_page.get("after")
                    has_more = bool(after)

            # Update last deal sync time
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

    def _sync_deal(self, deal_data: dict, client: httpx.Client) -> str:
        """Sync a single closed won deal as a contract draft."""
        hubspot_deal_id = str(deal_data["id"])
        properties = deal_data.get("properties", {})

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
            is_active=True,
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
            billing_interval=Contract.BillingInterval.MONTHLY,  # Will be updated after line items
            billing_anchor_day=1,
        )

        # Fetch and create line items, then update billing interval from products
        self._sync_deal_line_items(contract, hubspot_deal_id, client)
        self._update_contract_billing_interval_from_items(contract)

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

        # Create contract item
        ContractItem.objects.create(
            tenant=self.tenant,
            contract=contract,
            product=product,
            quantity=quantity,
            unit_price=unit_price,
            price_source=price_source,
            start_date=contract.start_date,
            billing_start_date=contract.billing_start_date,
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
