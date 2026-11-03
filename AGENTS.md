# MH project context

Before changing this project, read `PROJECT_CONTEXT.md`. It is the canonical handoff for product intent, current implementation, constraints, and next steps.

Then consult:

- `README.md` for capabilities, local operation, website flow, and SEO.
- `BILLING_SETUP.md` for Stripe, EU billing, webhooks, test/live gates, and launch requirements.
- `AUTH_SETUP.md` for cookies, CSRF, email links, MFA, invitations, onboarding and local mail testing.
- `backend/test_security.py` and `backend/test_billing.py` for expected security and billing behavior.

Preserve these product truths unless the user explicitly changes them:

- The product serves EU companies and sells monthly or annual subscriptions plus prepaid MH tokens.
- Prices are net EUR amounts. Stripe calculates applicable tax and collects EU VAT IDs.
- Payment confirmation and entitlements come from verified Stripe webhooks, never browser redirects.
- Existing seeded demo accounts remain free; newly registered billing-managed accounts require a paid active subscription for write actions.
- Paid managed generation calls OpenAI when configured; demos use deterministic templates. A real provider call has not yet been verified.
- “Live” is an internal workflow state; it does not publish to external channels.
- Public deployment, live Stripe activation, real SMTP delivery, and legal pages are not complete. Email verification, MFA and password recovery are implemented and tested locally.

Run the full verification before handing off changes:

```sh
python3 -m unittest backend/test_security.py backend/test_billing.py backend/test_stripe_setup.py backend/test_auth.py backend/test_ai.py backend/test_gmail.py
cd frontend
npm run build
npm run test:seo
```

Never commit, print, or place Stripe/OpenAI/social-provider secrets in documentation or frontend code.
