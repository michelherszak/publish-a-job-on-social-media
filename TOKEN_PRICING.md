# MH token model and AI cost estimate

28 September 2026. Current pilot catalogue; commercial assumptions remain unvalidated.

## Customer credits

MH tokens are prepaid product credits, not OpenAI tokens. One successful Instagram/Meta campaign package with its shared MH job description consumes 50 MH tokens. Editing, viewing, uploading/cropping own campaign photos and exports use no MH tokens. The 50-token unit still covers text generation; AI image generation and ad spend are not included. No deduction if the provider fails or returns incomplete output. Included monthly credits are consumed first; purchased credits accumulate across top-ups. Purchased credits remain stored but require an active paid subscription. Included credits expire/reset on each monthly renewal: after a paid monthly invoice or on a monthly anniversary within a paid annual term. Initial credits and purchased credits require verified Stripe payment webhooks.

Current top-ups: 250 for €12, 1,000 for €39 and 2,500 for €89 net. The implied MH-token rate falls from €0.048 to €0.0356 with larger packages; one additional 50-token campaign package costs about €2.40, €1.95 or €1.78 respectively. Subscriptions: €19/250, €69/1,500 and €149/4,000 monthly, or €190/€690/€1,490 annually upfront with the same monthly token allotment. Their effective package prices include workspace access and seats and cannot be compared directly with API costs.

## Provider cost assumptions

Baseline model: gpt-4.1-mini-2025-04-14. Official standard text rates checked today: $0.40 per million input tokens, $0.10 cached input, $1.60 output. Source: https://developers.openai.com/api/docs/models/gpt-4.1-mini . No caching discount assumed below.

Planning case: 2000 input and 2500 output tokens -> $0.0048 per campaign. Larger case: 6000 input and 4000 output -> $0.0088. With a planning conversion of $1 = €1 (assumption, not a current exchange quote), and 25% allowance for retries/waste -> €0.006 / €0.011 respectively. These are estimates, not observed usage or invoice totals. Generation is capped at 4000 output tokens and 20000 input characters; characters are not a precise token count. Failed requests can still incur provider costs although the customer is not charged MH credits.

Formula: ((input - cached) * 0.40 + cached * 0.10 + output * 1.60) / 1000000 * EUR_per_USD * retry_factor. Applies only to this model and these rates; other models require new rates.

Recommendation: retain the 50-credit package unit during a measured pilot and validate the new catalogue against real usage. Product prices are NOT a direct AI cost pass-through. Validate quality and customer willingness to pay before launch. Hosting/database/backups, payment fees, subscriptions to Billing/Tax, email, support, acquisition and profit are separate. VAT is not revenue. Do not infer profit from the tiny AI cost alone.

Required business inputs: expected packages/company/month, desired quality/model, annual hosting and support cost, payment-fee contract, target margin, acquisition cost, cancellation/refund policy and whether purchased credits should require an active subscription. Measure at least 30 representative briefings before finalising rates. Example scenario: €100 monthly shared operating costs divided by 100 packages = €1/package before payment fees, support/acquisition and profit; €100 is an assumption, not a vendor quote.

## Implementation and configuration

Paid managed accounts now call OpenAI Responses with strict three-field JSON schema (`social`, `meta`, `jobAd`). Save a central key under Platform Admin → Settings → OpenAI; alternatively OPENAI_API_KEY server environment. No keys in chat/source/frontend. Default model above unless explicitly overridden in Settings. OPENAI_BASE_URL accepts only https://api.openai.com/v1 or https://eu.api.openai.com/v1 . EU endpoint requires an eligible configured regional project; selecting the URL alone is not a residency guarantee. Confirm provider agreement, privacy notice and regional project first. Docs: https://developers.openai.com/api/docs/guides/your-data . store=false does not itself remove all provider retention.

Successful calls record actual input/output/cached tokens, response/model IDs and charged MH credits in ai_usage, scoped by organization. Briefing contents and keys are not recorded there. The ledger and content persist in the same transaction, preventing duplicate charges. A failed call rolls the transaction back. Current SQLite implementation holds a write transaction for the bounded provider request (20-second network timeout); move generation to queued jobs/reservations before high concurrency. Timeouts after provider completion may result in provider spend without customer credits; automatic retries are deliberately disabled.

No actual OpenAI call has been verified yet. The user’s Team Stripe sandbox payment and signed invoice credit were verified on 8 October 2026; the local template test consumed 50 of its 1,500 test credits. Broader Stripe/production acceptance remains open.

Local development only: verified Stripe test accounts can explicitly generate a labeled template test package for 50 test credits, with the same atomic debit and idempotency behavior. When no AI key exists, the wallet advertises this mode and the UI labels its button, disclosure, saved result and export. The request must select `test_package=true`; normal managed generation still requires OpenAI. Live mode, production and non-local public origins reject this test option. Template generation records no artificial OpenAI usage; seeded demos remain free.
