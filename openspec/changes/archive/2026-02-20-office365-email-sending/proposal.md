## Why

The system generates invoices (ZUGFeRD PDFs) but has no way to send them. Users must manually download and email each invoice. Connecting to a Microsoft 365 mailbox allows sending invoices (and later order confirmations) directly from the app using a real company mailbox as the sender, maintaining professional appearance and reply-to capability.

## What Changes

- Add Microsoft 365 OAuth2 configuration in tenant settings (Azure AD client credentials)
- Add a settings UI to configure and test the M365 connection, and select which shared mailbox to use as sender
- Add a "Send Invoice" action on generated invoices that composes and sends the email via Microsoft Graph API with the ZUGFeRD PDF attached
- Add email sending status tracking on invoices (sent/not sent, sent date, recipient)
- Use `msal` library for authentication and Microsoft Graph API for sending

## Capabilities

### New Capabilities

- `m365-connection`: Azure AD app credentials configuration, token management, mailbox discovery via Microsoft Graph API
- `email-sending`: Composing and sending emails via Graph API with PDF attachments, tracking send status on invoices, email templates

### Modified Capabilities

_None_ — this is additive functionality. Invoice generation and PDF storage are unchanged.

## Impact

- **Backend**: New `msal` dependency, new fields on `InvoiceRecord` for send tracking, new Celery task for async sending, M365 config stored in `Tenant.settings`
- **Frontend**: Settings page gets M365 configuration section, invoice list gets "Send" action button and sent status indicator
- **Infrastructure**: Requires Azure AD app registration with `Mail.Send` application permission (admin consent)
- **No breaking changes** to existing functionality
