# PromptPay Plugin (Backend)

Direct Thai PromptPay QR issuance + bank-webhook reconciliation
(KBank, SCB). No aggregator fee — merchant settles directly to their
Thai bank account.

## API Routes

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/api/v1/plugins/promptpay/payments` | Issue EMVCo QR |
| GET | `/api/v1/plugins/promptpay/payments/:invoice/status` | Status |
| POST | `/api/v1/plugins/promptpay/webhooks/<bank>` | Bank webhook receiver (kbank / scb) |

## Reconciliation

1. Preferred: match by the QR reference (tag 62.01).
2. Fallback: amount + timestamp window — exactly one pending
   candidate wins; 0 or >1 leaves the payment open and surfaces for
   manual review.

## Database

`promptpay_payments` — one row per invoice; stores the QR payload,
the reference, expiry, and matched bank tx on settlement.

## Frontend bundles

- User: [`vbwd-fe-user-plugin-promptpay-payment`](https://github.com/VBWD-platform/vbwd-fe-user-plugin-promptpay-payment)
- Admin: [`vbwd-fe-admin-plugin-promptpay-admin`](https://github.com/VBWD-platform/vbwd-fe-admin-plugin-promptpay-admin)

---

**Core:** [vbwd-backend](https://github.com/VBWD-platform/vbwd-backend)
