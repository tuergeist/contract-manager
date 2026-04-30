## 1. Sheet Width

- [ ] 1.1 In `IncomingInvoiceDetail.tsx`, change `<SheetContent>` className from `sm:max-w-2xl` to `sm:max-w-3xl`.

## 2. Resizable PDF Container

- [ ] 2.1 Wrap iframe in a div with `style.resize='vertical'`, `overflow:hidden`, and a min/max derived from viewport (`min-height: 70vh; max-height: 80vh`).
- [ ] 2.2 Add `GripHorizontal` icon at the bottom edge as visual hint, tooltip "Höhe anpassen / Resize".
- [ ] 2.3 Use a ResizeObserver on the wrapper to persist `clientHeight` to `localStorage` under key `cm:incoming:pdfHeight`.
- [ ] 2.4 On mount, read the persisted value and apply as inline style; if absent, leave the CSS default.

## 3. i18n

- [ ] 3.1 Add tooltip key: `incomingInvoices.detail.resizeHint`.

## 4. Tests

- [ ] 4.1 Vitest: ResizeObserver writes to localStorage on size change.
- [ ] 4.2 Vitest: persisted value is read on mount.
- [ ] 4.3 Visual check across 1366px and 1920px widths.

## 5. Verification

- [ ] 5.1 Type check.
- [ ] 5.2 Manual smoke test on 1366×768 and 1920×1080.
