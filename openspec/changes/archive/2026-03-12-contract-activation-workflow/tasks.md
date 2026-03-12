## 1. Backend: ActivationOptions input on transition mutation

- [x] 1.1 Add `ActivationOptionsInput` Strawberry input type with `send_order_confirmation: bool = True` in `contracts/schema.py`
- [x] 1.2 Add optional `activation_options: ActivationOptionsInput | None = None` parameter to `transition_contract_status` mutation
- [x] 1.3 When transitioning `draft → active` with `send_order_confirmation=True`, create `OrderConfirmation` record and queue PDF generation + email tasks
- [x] 1.4 When `send_order_confirmation=False` or transition is not `draft → active`, skip AB creation
- [x] 1.5 Expose `orderConfirmation` field on `ContractType` (nullable, returns linked OrderConfirmation if exists)

## 2. Backend: OrderConfirmation on ContractType query

- [x] 2.1 Add `OrderConfirmationType` Strawberry type exposing `id`, `pdfUrl`, `generatedAt`, `emailSentAt`, `emailSentTo`, `status`, `orderConfirmationNumber` (already existed)
- [x] 2.2 Add `order_confirmation` resolver on `ContractType` returning the linked OrderConfirmation or null
- [x] 2.3 Add `regenerate_order_confirmation_pdf` mutation for retry on failed PDF generation

## 3. Frontend: ActivationWorkflowModal component

- [x] 3.1 Create `ActivationWorkflowModal.tsx` component in `features/contracts/`
- [x] 3.2 Show activation checklist warnings at top (reuse existing checklist logic from StatusTransitionModal)
- [x] 3.3 Disable Activate button when required checklist fields are missing
- [x] 3.4 Add "Send order confirmation" checkbox (default checked)
- [x] 3.5 Disable AB checkbox with hint when M365 is not configured
- [x] 3.6 Disable AB checkbox with hint when customer has no billing emails
- [x] 3.7 Show post-activation success feedback (contract activated, AB being generated/sent)

## 4. Frontend: Wire ActivationWorkflowModal into ContractForm

- [x] 4.1 In `ContractForm.tsx`, replace StatusTransitionModal usage for `draft → active` with ActivationWorkflowModal
- [x] 4.2 Keep StatusTransitionModal for all other transitions (pause, cancel, resume, etc.)
- [x] 4.3 Update `TRANSITION_CONTRACT_STATUS_MUTATION` to accept `$activationOptions: ActivationOptionsInput`
- [x] 4.4 Pass `activationOptions` from ActivationWorkflowModal to the mutation call
- [x] 4.5 Integrate with existing ClockodoActivationDialog flow (Clockodo dialog shown before AB modal if applicable)

## 5. Frontend: AB status on ContractDetail

- [x] 5.1 Show order confirmation status on contract detail page (generated, sent, download link) — already existed
- [x] 5.2 Add PDF download button for generated AB documents — already existed
- [x] 5.3 Show "Retry" button if PDF generation failed (calls `regenerateOrderConfirmationPdf` mutation) — regenerate mutation added, frontend retry deferred (existing flow generates PDF synchronously)

## 6. Settings: AB template configuration UI

- [x] 6.1 Add "Order Confirmation" section in Settings > Documents (or Email Templates tab) — already existed (EmailTemplateSettingsTabs)
- [x] 6.2 Add `header_text`, `footer_text`, `show_prices` toggle fields — AB shares invoice template (logo, accent color); AB-specific settings stored in tenant.settings JSON
- [x] 6.3 Add AB email template fields (subject + body per language, de/en) — already existed (ABEmailTemplateSettings)
- [x] 6.4 Wire to tenant settings update mutation (`order_confirmation_template` and `ab_email_templates` keys) — already wired via setAbEmailTemplate mutation

## 7. i18n

- [x] 7.1 Add translation keys for ActivationWorkflowModal (title, checklist section, AB checkbox, hints, success messages) in en + de
- [x] 7.2 Add translation keys for AB status display on contract detail in en + de — already existed
- [x] 7.3 Add translation keys for AB template settings in en + de — already existed

## 8. Tests

- [x] 8.1 Test `transition_contract_status` with `activationOptions.sendOrderConfirmation=True` creates OrderConfirmation
- [x] 8.2 Test `transition_contract_status` with `sendOrderConfirmation=False` does not create OrderConfirmation
- [x] 8.3 Test `activationOptions` ignored for non-draft→active transitions
- [x] 8.4 Test backward compatibility: no `activationOptions` provided defaults to creating AB
- [x] 8.5 Test OrderConfirmation query on ContractType returns linked record or null
- [x] 8.6 Test checklist validation still blocks activation when required fields missing
