## Why

When a contract is activated, the team currently has to manually create corresponding Clockodo projects for time tracking. This is error-prone (forgotten projects, inconsistent naming) and tedious, especially for contracts with multiple items. Since Clockodo is already integrated for reading time data, extending it with write operations (customer and project creation) enables automatic project setup on contract activation.

## What Changes

- Link CM customers to Clockodo customers (bidirectional mapping)
- On contract activation (draft → active), automatically create Clockodo projects if not already mapped:
  - Recurring items → one shared "Wartungsvertrag" project per customer (name configurable, reused across contracts)
  - One-off items → user decides: one project for all one-offs in a contract, or one per one-off item
- Add write operations to ClockodoProvider (create customer, create project)
- Add Clockodo customer ID to CM Customer model for linking
- Show a confirmation dialog on activation when new Clockodo projects would be created

## Capabilities

### New Capabilities

- `clockodo-project-provisioning`: Automatic Clockodo project and customer creation on contract activation, customer linking, configurable naming templates

### Modified Capabilities

_None — existing time tracking read functionality stays unchanged._

## Impact

- **Backend**: New methods on ClockodoProvider (POST customer, POST project), customer linking field, activation hook in contract status mutation, Celery task for project creation
- **Frontend**: Customer linking UI, activation confirmation dialog with project creation options, configuration for naming templates
- **Database**: New field on Customer model (clockodo_customer_id), new ClockodoProjectTemplate config model or tenant settings
- **External**: Write API calls to Clockodo (creating customers and projects)
