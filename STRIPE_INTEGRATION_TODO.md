# Stripe Checkout integration

This is the single source of truth for the remaining Stripe Checkout setup.

## Values to Replace

The existing application already supplies real, server-owned values for every `sample_only` field. There are no Checkout placeholder values to replace.

**Files containing placeholders:**

- None.

| Field | Current Value | What to Set |
|---|---|---|
| `mode` | Server-owned product type (`payment` or `subscription`) | No change required. |
| `success_url` | `MH_PUBLIC_URL/app?billing=success` | No change required; set `MH_PUBLIC_URL` per environment. |
| `cancel_url` | `MH_PUBLIC_URL/app?billing=cancelled` | No change required; set `MH_PUBLIC_URL` per environment. |
| `line_items[].price` | Server-owned `STRIPE_PRICE_*` value | No change required; configure the existing server-only environment variables. |

## Configured Parameters

These parameters were configured in Checkout Studio and are set in the existing Checkout Session call.

**Files containing these parameters:**

- [backend/billing.py](backend/billing.py)

| Parameter | Value |
|---|---|
| `ui_mode` | `hosted_page` |
| `billing_address_collection` | `required` |
| `phone_number_collection.enabled` | `false` |
| `automatic_tax.enabled` | `true` |
| `tax_id_collection.enabled` | `true` |
| `allow_promotion_codes` | `false` |
| `payment_method_collection` | `always` for subscription mode only |
| `submit_type` | `auto` |
| `integration_identifier` | `hosted_web_0001` |
| `origin_context` | `web` |

The project does not install a Stripe SDK; it calls Stripe's REST API server-side. `hosted_page` is the required fallback when an SDK version cannot be determined and is present in the connected Checkout API specification.

## Setup and next steps

### Environment and dependencies

- Keep `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET`, and all nine `STRIPE_PRICE_*` values server-side in `backend/.env.local` for local testing and in the deployment secret manager for production.
- Do not prefix server secrets with `VITE_`. The browser does not need a Stripe key for hosted Checkout.
- Run `python3 -m backend.stripe_test verify` to validate the test catalogue.
- Run `python3 -m backend.stripe_test listen` in a separate terminal for local webhook forwarding, then restart the backend.
- No Stripe SDK dependency is required by this implementation.

### Project structure

- [backend/billing.py](backend/billing.py) creates hosted Checkout Sessions and handles verified webhooks.
- [backend/stripe_test.py](backend/stripe_test.py) validates test configuration and runs the local listener.
- [pricing_catalog.json](pricing_catalog.json) is the server-owned product catalogue.
- No new route or infrastructure file was created for Checkout.

### Flow

1. The authenticated company admin selects a server-owned subscription or token SKU.
2. The backend resolves and validates its configured Stripe Price.
3. The backend creates a hosted Checkout Session and returns its Stripe URL.
4. The browser redirects to Stripe and later returns to the existing success or cancellation URL.
5. Entitlements must continue to come only from verified Stripe webhooks, never from the browser redirect.

### Required validation before use

- The secure server-owned association is restored: Checkout receives the existing Stripe Customer, local order metadata, downstream subscription/payment metadata, and a bounded expiry. The webhook still retrieves current Stripe objects and matches customer, order, product, amount, mode, and country before granting anything.
- Automatic Tax, mandatory billing address, tax-ID collection, card-only payment, and invoice creation for token purchases are enabled to preserve the EU B2B billing design.
- Stripe Tax must be `active`, its default product tax code must be configured, and only real tax registrations may be entered before an end-to-end payment test.
- Appropriate Stripe Radar rules must block missing and non-EU billing addresses before payment. The application also holds entitlements if a later webhook reports a non-EU address.
- Test subscription and one-time modes separately. Confirm that `payment_method_collection=always` appears only for subscriptions.
- Verify success, cancellation, webhook signature rejection, duplicate webhooks, decline, 3D Secure, renewal, failed renewal, cancellation, top-up, refund, EU/non-EU billing addresses, and invoice delivery.
- Test cards in Stripe test mode include `4242 4242 4242 4242` for success, `4000 0000 0000 0002` for decline, and `4000 0025 0000 3155` for 3D Secure. Use any future expiry and test CVC.

### Products, fulfillment, and tracking

- Keep Price IDs mapped to the existing SKUs; never accept arbitrary Price IDs from the browser.
- Continue retrieving Stripe objects during webhook processing and preserve idempotent event and token-ledger handling.
- Keep test and live keys, webhooks, customers, and databases separated.
- Stripe support: https://support.stripe.com
- Stripe MCP documentation: https://docs.stripe.com/mcp
