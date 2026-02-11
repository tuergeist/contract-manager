from django.db import models
from django.core.exceptions import ValidationError

from apps.core.models import TenantModel


class TodoItem(TenantModel):
    """A todo item linked to a contract, contract item, or customer."""

    text = models.TextField(
        help_text="The todo item description",
    )
    reminder_date = models.DateField(
        null=True,
        blank=True,
        help_text="Optional reminder date for this todo",
    )
    is_public = models.BooleanField(
        default=False,
        help_text="If True, visible to all tenant users. If False, only visible to creator.",
    )
    is_completed = models.BooleanField(
        default=False,
        help_text="Whether this todo has been completed",
    )
    completed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When this todo was marked as completed",
    )
    created_by = models.ForeignKey(
        "tenants.User",
        on_delete=models.CASCADE,
        related_name="created_todos",
        help_text="The user who created this todo",
    )
    assigned_to = models.ForeignKey(
        "tenants.User",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="assigned_todos",
        help_text="The user this todo is assigned to (if different from creator)",
    )

    # Entity references - exactly one must be set
    contract = models.ForeignKey(
        "contracts.Contract",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="todos",
        help_text="The contract this todo is linked to",
    )
    contract_item = models.ForeignKey(
        "contracts.ContractItem",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="todos",
        help_text="The contract item this todo is linked to",
    )
    customer = models.ForeignKey(
        "customers.Customer",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="todos",
        help_text="The customer this todo is linked to",
    )

    class Meta:
        ordering = ["reminder_date", "-created_at"]

    def __str__(self):
        return f"{self.text[:50]}..." if len(self.text) > 50 else self.text

    def clean(self):
        """Validate that exactly one entity reference is set."""
        super().clean()
        entity_count = sum([
            self.contract_id is not None,
            self.contract_item_id is not None,
            self.customer_id is not None,
        ])
        if entity_count == 0:
            raise ValidationError(
                "A todo must be linked to a contract, contract item, or customer."
            )
        if entity_count > 1:
            raise ValidationError(
                "A todo can only be linked to one entity (contract, contract item, or customer)."
            )

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    @property
    def entity_type(self):
        """Return the type of entity this todo is linked to."""
        if self.contract_id:
            return "contract"
        if self.contract_item_id:
            return "contract_item"
        if self.customer_id:
            return "customer"
        return None

    @property
    def entity_name(self):
        """Return a display name for the linked entity."""
        if self.contract:
            return self.contract.name or f"Contract {self.contract.id}"
        if self.contract_item:
            item = self.contract_item
            product_name = item.product.name if item.product else "Item"
            contract_name = item.contract.name or f"Contract {item.contract.id}"
            return f"{product_name} ({contract_name})"
        if self.customer:
            return self.customer.name
        return None

    @property
    def comment_count(self):
        """Return the number of comments on this todo."""
        return self.comments.count()


class TodoComment(TenantModel):
    """An immutable comment on a todo item."""

    todo = models.ForeignKey(
        TodoItem,
        on_delete=models.CASCADE,
        related_name="comments",
        help_text="The todo this comment belongs to",
    )
    text = models.TextField(
        help_text="The comment text",
    )
    author = models.ForeignKey(
        "tenants.User",
        on_delete=models.CASCADE,
        related_name="todo_comments",
        help_text="The user who wrote this comment",
    )

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"Comment by {self.author} on {self.todo}"
