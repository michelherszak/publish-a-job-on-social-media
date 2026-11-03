# MH — Recruiting Workspace

> Start here when resuming work: [PROJECT_CONTEXT.md](PROJECT_CONTEXT.md). It is the canonical project handoff with the product model, architecture, current status, constraints, and next steps.

Local FastAPI + React prototype for company-specific recruiting campaigns.

## Current capabilities

- Sign in with a company account or a Platform Admin account.
- Companies, reusable customer profiles, campaigns, content, activity and pipeline counts come from the API. The token balance appears as a compact card in the left sidebar, with allocation and usage details available on demand across workspace pages.
- Dashboard “Next steps” prioritizes current feedback, pending approvals and unfinished drafts according to the user’s permissions. Each step opens its campaign in Content Studio; additional tasks and the activity history expand on demand.
- Create a briefing prefilled from the customer profile, generate channel drafts and local A/B copy, edit and save them, submit for review, request changes and approve.
- Preview Instagram posts and Meta/Facebook ads with separate platform layouts, A/B variants and feed/story placements. The outer preview stays transparent and borderless; selected photos, crop drafts and unsaved copy appear immediately. These are local visual approximations with no social actions or invented engagement.
- Inspect the campaign decision history, add channel comments, and compare saved content versions.
- Download a campaign ZIP and SVG creative for manual publication; record per-channel impressions, clicks and application counts. New packages contain Instagram and Meta copy plus a shared MH application-page description. Previously saved formats remain available in history and exports.
- Platform Admin can create and delete companies, manage users and work across companies, but cannot approve campaigns or request changes in the approval step. Deleting a company requires exact-name confirmation and removes its users, sessions and campaign data atomically. Customers with billing records are protected from deletion; no Stripe customer or subscription is changed.
- Firmen Admin can manage users and campaigns in their own company, including approval.
- User can create and edit campaigns in their own company, submit them for review, request changes and approve their own company's campaigns.
- Kunde can only read Review and Live campaigns in their own company.
- Every company-bound API request is checked against the signed-in user's company. A direct request for another company's campaign returns 404.

Paid managed accounts use OpenAI Responses with a centrally configured key; local Stripe sandbox accounts without an AI key can explicitly request labeled template test packages for 50 test credits (never production/live); briefing and company name are sent to the selected OpenAI endpoint. Demo accounts retain free local templates. No real provider call has been verified. See TOKEN_PRICING.md. Analytics shows campaign status counts plus manually entered impressions, clicks and application totals, clearly labeled by source. The SVG is a simple creative template. "Live" is a workflow state and does not publish to social platforms.

## Local access

Landing page: http://127.0.0.1:5181/
Workspace / sign in: http://127.0.0.1:5181/app
Job portal: http://127.0.0.1:5181/jobs
Backend health: http://127.0.0.1:8011/health

The first backend start creates strong local demo passwords in `backend/demo_credentials.txt` with owner-only file permissions. Keep this file private. Its accounts include one Platform Admin and a Firmen Admin for each seeded company. Additional users can be created in Settings. Platform Admin manages only the OpenAI key and model in Settings. Each Firmen Admin manages Meta, LinkedIn and XING credentials only for their own company; Platform Admin cannot edit those company keys. The OpenAI key is stored in `backend/integration_settings.json`, while company keys are scoped by organization in `backend/mh.db` (and in the separate demo database during role preview). These local files have owner-only permissions. The API reports whether a key exists but never returns its value. The central OpenAI key is used only by server-side paid campaign generation. Legacy social-provider credential fields are not used for publishing. The new Facebook flow uses encrypted company Page authorization through the central Meta app; see META_SETUP.md. No real Meta connection or post has been verified.

Sign in with the Platform Admin account. The role and company selector appears on every page. The API enforces the selected role and company for that session. Company accounts cannot use this selector. The selector is available only for localhost requests and can be disabled with `MH_DEMO_SWITCHER=0`. Entering a preview creates a copy of the primary database in `backend/mh_demo.db`; preview writes stay there. Switching roles within the preview keeps that copy. Returning to Platform Admin and entering preview again resets it from the primary database.

## Run

From the project root, `./start.sh` installs missing dependencies, loads `backend/.env.local` when that private file exists, applies any missing SQLite tables and columns in `backend/mh.db`, then starts both servers. With a configured Stripe test key it first starts the local Stripe listener and waits for its signing secret before launching the backend. Missing listener readiness or a stopped listener fails the shared run visibly. Existing rows stay in place. Ctrl+C stops the servers and listener.

```bash
cd /Users/michelherszak/Programming/Python/MH
./start.sh
```

The same processes can be started separately:

```bash
cd /Users/michelherszak/Programming/Python/MH/backend
python3 -m pip install -r requirements.txt
python3 -m uvicorn main:app --host 127.0.0.1 --port 8011
```

In another terminal:

```bash
cd /Users/michelherszak/Programming/Python/MH/frontend
npm install
npm run dev -- --host 127.0.0.1 --port 5181 --strictPort
```

The backend uses SQLite at `backend/mh.db`. Both ports bind only to localhost.

## Verification

```bash
cd /Users/michelherszak/Programming/Python/MH
python3 -m unittest backend/test_security.py backend/test_billing.py backend/test_stripe_setup.py backend/test_auth.py backend/test_ai.py backend/test_gmail.py backend/test_tracking.py backend/test_social.py backend/test_recruiting.py backend/test_campaign_images.py backend/test_job_portal.py backend/test_campaign_workflow.py
cd frontend
npm run build
npm run test:seo
npm run test:language
npm run test:job-seo
npm run test:onboarding
```

The security tests use temporary databases and cover company boundaries, demo isolation, customer read access, profiles, approval history, exports and metrics.

## Landing page and proposed pricing

The public landing page and checkout use one shared catalogue: Starter (€19/month or €190/year, 250 tokens/month, 3 editors), Team (€69/month or €690/year, 1,500 tokens/month, 10 editors), and Scale (€149/month or €1,490/year, 4,000 tokens/month, 25 editors). Prices are net; annual plans are paid upfront and still receive monthly included tokens. A successful campaign package costs 50 MH tokens. Extra packages are 250/1,000/2,500 tokens for €12/€39/€89 and add to purchased balance. See BILLING_SETUP.md. Explicit Facebook Page publishing is implemented locally and awaits real Meta verification; Instagram account connection is prepared. See META_SETUP.md.

## Guided website journey and SEO

The landing page follows four linked steps: understand the workflow → estimate packages and editor seats → choose a tier → review the plan and continue. The calculator recommends the lowest total cost among plans with enough editor seats; ties favor more seats. A plan can be downloaded as text. Selection and planning inputs persist in session storage through login and back navigation. The planning itself is not a purchase. New visitors continue to /register and /onboarding for email verification, admin MFA, Stripe Checkout, company profile and their first draft (or save the brief and go straight to the dashboard); existing customers use Abo & Tokens. See BILLING_SETUP.md.

`npm run build` now pre-renders the actual React landing component into HTML and hydrates it in the browser. Workspace JavaScript and CSS load separately. The build creates `dist/app/index.html`, `404.html`, `robots.txt` and `sitemap.xml`. Public landing HTML includes German title/description, Open Graph/Twitter tags, favicon and truthful WebPage/WebSite JSON-LD, without fictional reviews or purchasable offers.

### Publish with the real domain

1. Copy `frontend/.env.production.example` to `frontend/.env.production.local` and set `SITE_URL` to the real public HTTPS origin (no subpath).
2. Run `npm run build:public` in `frontend`; this fails without a valid origin. With no origin, regular builds remain `noindex` previews and emit no canonical URL or sitemap entries.
3. Run `npm run test:seo`. Run `npm start` to serve the built site at `127.0.0.1:4181` (PORT/HOST configurable). Put the server behind your chosen HTTPS reverse proxy for a deployment; the application API still needs its own production configuration.
4. If using another static host, map `/` to `dist/index.html`, `/app` to `dist/app/index.html`, redirect `/app/` to `/app`, and serve `dist/404.html` with HTTP 404 for unknown URLs. Do not use a catch-all 200 SPA rewrite. Send `X-Robots-Tag: noindex, nofollow` on `/app` and errors, and allow crawlers to read those responses.
5. Confirm the final HTTPS URL, canonical, sitemap, mobile rendering and status codes on the real host. Submit `/sitemap.xml` in Google Search Console after verifying the domain. Add the actual operator/contact and legal pages before public launch. No public deployment or Search Console registration is performed by this change.

Google reference: https://developers.google.com/search/docs/crawling-indexing/javascript/javascript-seo-basics

Development HTML intentionally stays noindex. Indexability and metadata of deployed routes must be verified on the production build, not only the Vite dev server. Social metadata uses a text summary; no fabricated social preview image is configured.

## EU credit-card billing

See [BILLING_SETUP.md](BILLING_SETUP.md) for Stripe configuration, test/live requirements, EU restrictions and webhook handling. No real payment provider credentials are stored in the repository. Registration works locally without Stripe keys. Checkout stays disabled until configured. See [AUTH_SETUP.md](AUTH_SETUP.md) for email verification, secure cookie sessions, MFA, password recovery, invitations and onboarding. Local messages are saved privately in backend/mail_outbox; SMTP is not connected. Full tests: `python3 -m unittest backend/test_security.py backend/test_billing.py backend/test_stripe_setup.py backend/test_auth.py`.

### Guided campaign creation

The workspace and first-run onboarding share a DE/EN four-step briefing: role and location, candidate profile and benefits, channel selection, then a review with editable answers and explicit generation cost confirmation. Company defaults are prefilled. Users can save a briefing without generating or spending tokens and resume it later; an active subscription is still required for billing-managed write actions. Generation failures preserve the saved campaign for retry. The package contains Instagram and Meta copy plus the shared job description on MH, and requires human review before export/publication. The 50-token package price is unchanged.

### Content Studio editing

Content Studio shows the current campaign as a fixed title, with two keyboard-accessible tabs for Instagram and Meta, a full-text preview on desktop and mobile, word/character counts, copying and explicit saving (including Ctrl/Cmd+S inside the editor). Unsaved text and image crops remain in memory across campaign, channel and workspace-page switches; reload/logout can discard it after a warning. Saving writes all edited texts and pending image crops of the current campaign in one transaction. Review, regeneration and export require those changes to be saved or discarded first. The shared MH job description is editable in its own expandable section; the briefing remains available in an expandable section. Content Studio ends with “Job description on MH”; the former lower approval/export, portal/distribution, tracking, Meta publishing and comments/history panels have been removed at the user’s request. Stored campaign and portal data and backend services are retained. The description feeds the existing application page, which becomes public only after approval and explicit activation. The separate public job portal provides filters for explicitly activated open listings. The preview combines the selected photo with text and is not an exact platform layout, and approval never publishes externally.

### Campaign photos

Upload up to six own JPEG, PNG or WebP photos per campaign in Content Studio (10 MiB per file, 100 px minimum per edge, at most 16 million pixels; animated files are rejected). Uploading, cropping and exporting use no MH tokens. Choose one common photo for Instagram and Meta, then adjust its position and zoom separately for Feed (4:5) and Story (9:16). Both channels preview the selected photo alongside their text. Crop changes are kept across workspace switches and saved with edited text; save or discard changes before review or export.

Uploads and photo selection are saved immediately. Photo changes return a campaign under review to Draft, and approval checks the current image revision. Approved Live campaigns cannot change images. Customer roles can inspect the photos and previews. Images are private, company-scoped SQLite records; orientation is normalized and embedded metadata including GPS is removed. The sanitized original has at most 2400 px per edge. Only the selected photo's rendered JPGs are included in the campaign ZIP: `images/feed-4x5.jpg` (1080×1350) and `images/story-9x16.jpg` (1080×1920), plus selection metadata. Image history records actions rather than storing earlier photo versions. Company deletion also removes campaign photos; demo writes remain isolated.

The current Facebook publisher sends text and a link only. Use the exported JPGs for manual posting on Facebook or Instagram. Automatic image publication, carousels, AI-generated photos and paid ad booking remain pending. Restart the backend after this update to initialize the image schema and routes; `start.sh` now checks the Pillow dependency as well.

### Platform Admin email previews

System → E-Mail-Vorschau displays the actual registration, password-reset, invitation and invoice-notification templates with fictional data. Switch between rendered mailbox and plain-text views and desktop/mobile widths. The templates remain plain-text emails; previews send nothing and expose no real tokens or recipients. The API enforces Platform Admin access and excludes demo-role previews.

### Browser language

The UI supports German and English and follows the first supported browser language preference on page load. Regional variants are supported; other preferences fall back to English. Reload after changing your browser language order. Dates, numbers and EUR prices follow the selected locale. Saved company/campaign text and actual email content remain in their original language. Static public prerendering remains German.

Run `cd frontend && npm run test:language` to check browser preferences, DE/EN rendering across all product screens, static labels, API error messages and translation placeholders. Automatic activity/history text, token ledger descriptions, recruiting questions, metadata and the planning download follow the locale; customer text and comments remain unchanged. Stripe Checkout and the billing portal receive the selected language. Restart the backend after updating the Stripe language handoff. The TypeScript build rejects unused imports, variables and parameters.

### Campaign status emails

Actual campaign status changes notify every verified account in the same company, including clients and the person who changed the status. Each email uses the recipient’s stored German/English language and shows the previous/new status, campaign title and actor. Unchanged status values and demo role previews send nothing. Delivery is queued atomically and retried in the background; failed mail does not undo the status change. Platform Admin can inspect the fifth template under Email previews. Restart the backend after updating to initialize the queue and retry worker.


### Publish on each company’s own Facebook Page

Settings → Own company Page connects a real company admin through Facebook and lets them choose an authorized Page. The Meta tab in the studio offers a separate text/link preview and explicit Publish action for internally approved campaigns. Tokens remain encrypted on the server; customer roles, Platform Admins and demo previews cannot publish. Repeated or uncertain provider calls do not automatically create another post. Public HTTPS hosting, a Meta app and an actual provider acceptance test are still required. See [META_SETUP.md](META_SETUP.md). Instagram connection discovery is prepared; Instagram image/video publishing remains pending. No paid ad booking or public deployment has been added.

### Staffing need to applicant conversation

The company team now has a **Recruiting** workspace for responsibilities, open questions, manual applicant contact, confirmed appointments, deadlines, effort/results and controlled closure/reuse. The briefing separates essential skills from skills that can be learned and records actual working hours. Incomplete needs can be saved before generation. Personal workflow notes are encrypted and expire with the application. Contact and calendar agreements happen outside MH and are explicitly documented; reply drafts do not send messages or count as responses. See [implementation and limits](docs/requirements/ZIELBILD_IMPLEMENTIERUNG.md). UC-Z12 remains deferred.

The [HTML dashboard](output/use-case-dashboard/index.html) includes all 31 use cases and local exportable evaluations. Start `python3 output/use-case-dashboard/serve.py` and open http://127.0.0.1:5190 for five-second status refresh and stale-source warnings. The embedded snapshot also opens as a file. Later implementation changes must be audited into `docs/requirements/use_case_status.json`; checksums flag changes but do not infer completeness.

Additional verification: `python3 -m unittest backend/test_recruiting.py backend/test_tracking.py backend/test_social.py backend/test_campaign_images.py backend/test_job_portal.py backend/test_campaign_workflow.py`; the complete required backend suites, frontend build, SEO and language checks still apply.

### Digital twin and batched feature removal

Open http://127.0.0.1:5190 after `python3 output/use-case-dashboard/serve.py`. The portable HTML is `output/use-case-dashboard/index.html`; regenerate it with `python3 output/use-case-dashboard/build.py`. Architecture appears first, followed by all 31 original use cases, 20 explicitly identified functional additions and five documented operations tasks. Per-case deletion prompts can be collected, reviewed as one batch and explicitly started in the local Codex project agent using the saved login. Selection alone changes no code. A source-only backup precedes execution; product data and external provider actions are outside the deletion instruction. Run status, changed source filenames and independent verification remain in the same interface. Details and limits: [DIGITALER_ZWILLING.md](docs/requirements/DIGITALER_ZWILLING.md).

## Local job portal and shared distribution plan

The user chose Germany first and local operation until a domain is available. `/jobs` lists explicitly activated, approved, open and unexpired German jobs. Search by title/company, location, company, employment and work arrangement; pagination displays 24 jobs. `/jobs/<id>` contains the shared MH description, optional selected Feed image and an application form: name/email, optional message, no account or mandatory CV. Stored applicant text is never translated. UI follows the browser's DE/EN preference. Private briefing fields and original photos are not public.

The backend supports contact/privacy/retention, structured filters, an optional deadline and explicit activation of approved MH pages. The previous **Jobportal & Verbreitung** panel has been removed from Content Studio at the user’s request; its backend and saved configuration are retained, with no replacement management screen added. Internal `Live` alone still publishes nothing. Closing, withdrawing or expiry removes the listing and blocks applications; existing legacy `/apply` pages remain compatible. Deadlines use the end of the selected day in Europe/Berlin. Demo previews cannot activate real listings. Paid accounts retain their subscription write gates.

The suggested **EUR 150 over 14 days is an optional MH test assumption**, not a provider minimum, promised outcome or approved spend. One editable budget covers Instagram/Facebook paid distribution plus retargeting together; MH subscription/tokens remain separate. Zero budget prepares organic links only. Local activation prepares stable per-channel links for organic posts, ads and retargeting without contacting Meta, booking ads or spending money. They redirect to the MH listing. For Instagram organic posts, the planned MH link placement is a profile/Story link; a future real publisher must check the actual account capabilities instead of assuming a caption link is clickable. HTTPS hosting, Meta connection, image/media publishing, advertising-account integration and marketing delivery remain pending; existing explicit Facebook text/link publishing is a separate flow (see META_SETUP.md).

**Analytics** shows aggregate server page requests (not unique visitors), consenting visits, an engagement signal, form starts, consented submissions, actual stored applications and local marketing signals. An application conversion is created by successful server storage, not a button click or browser success URL; duplicate submissions do not double count. Engagement means at least 30 active visible seconds and 80% of text sections encountered after consent; it is not proof of reading. Different steps may be skipped. Consented journey counts use the UTC visit-start cohort; all application totals use actual receipt dates. Reloads, bots and consent refusal limit comparisons.

Analytics and marketing choices are separate, unchecked by default, with equally presented reject/allow/save controls and withdrawal. Reading and applying work without consent. No form values enter engagement tracking. Only preference flags/version are remembered for 180 days; the encrypted visit token remains in page memory and the temporary server flow expires after 24 hours or is deleted on withdrawal. Anonymous daily totals remain. No Meta pixel, Conversions API, cross-visit identity, real retargeting audience or applicant scoring is active. Operational application storage and aggregate request counting are separate from optional browser measurement.

Legal basis and production disclosures must be finalized before launch. Relevant primary guidance: [DSK Digital Services guidance](https://www.datenschutz-berlin.de/fileadmin/user_upload/pdf/publikationen/DSK/2024/2024_DSK-OH_Digitale-Dienste.pdf), [EDPB technical scope](https://www.edpb.europa.eu/documents/guideline/guidelines-22023-on-technical-scope-of-art-53-of-eprivacy-directive_en), and [BDSG section 26](https://www.gesetze-im-internet.de/bdsg_2018/__26.html). Consent-based visitor analysis/marketing is implemented conservatively; these references are not a completed legal review of public operation.

## Combined local campaign workflow (5 October 2026)

The backend supports **Activate MH and start local workflow** for a saved and approved campaign. Its former Content Studio panel was removed at the user’s request; the backend workflow remains implemented, without a replacement UI entry point. This activates MH and executes the organic/paid/retargeting actions through a local provider simulator. The simulator has no network implementation or live-mode switch; production start/retry/traffic endpoints reject simulation. Actual Facebook publishing remains separate. Real Instagram/image/ad/audience adapters and their account/domain configuration still need implementation and verification before external delivery.

Persistent runs store immutable approved channel copy, landing-link placement, selected Feed/Story bytes, plan and revisions. A run keeps its IDs, delivery receipts and advertising end date across repeated activation/restarts. Failed actions can retry up to three times; uncertain delivery requires explicit reconciliation and cannot blindly repeat. Successful actions preserve their receipts. Missing Instagram media/copy creates an actionable partial result; it does not disguise an incomplete channel as published. MH remains available when an individual channel is blocked.

All simulated ad allocations share the campaign budget, including retargeting. The available remainder is split equally across the eligible planned ad actions; optional organic posts consume no ad budget. Spend already recorded across older runs stays deducted after a plan change. Each explicit **Test ad delivery locally** step creates bounded simulator receipts (at most EUR 1 / 10 impressions / 1 click per eligible ad action). The receipts are idempotent, checked for bounds and applied atomically; neither a per-action allocation nor the campaign cap can be exceeded. Invalid receipts roll back. These are scenario values, never actual platform performance, spending or visitors. Actual provider cost/cost per application remains unavailable.

Retargeting's local audience is computed only from unexpired, marketing-consenting, engaged visits that have not submitted an application. Successful server application storage, consent withdrawal and expiry remove that visit. The token remains visit scoped; returning visits/devices cannot be matched or excluded across visits. This simulator does not create a real Meta audience or transmit identities. Retargeting waits when no eligible visits remain. Changed content/plan, withdrawn/closed/expired jobs and inactive paid subscriptions pause the workflow; ad duration and budget exhaustion stop ad delivery. Historic receipts remain for inspection. Reopening requires an explicit start.

The report now groups consenting journey steps by source channel and organic/paid/retargeting variant. It measures both visit-to-application and engaged-visit-to-application rates using the original UTC visit cohort. A reading signal remains an engagement estimate, not proof of reading. Operational applications and simulator clicks/costs are shown separately.


## Job Board SEO and applicant design (5 October 2026)

The public board focuses on skilled trades and care. Compact cards show the real employer, place, employment, work arrangement and any provided salary text. Search uses real GET URLs, including crawlable pagination and a separate apprenticeship filter. Other roles remain searchable. Detail pages show key facts and an application link immediately; the mobile application link stays available while reading and disappears when the form enters the viewport. Consent controls remain voluntary and available below the application area. No invented benefits, reviews, salaries or candidate photos were added. Employer copy remains in its saved language; interface labels follow DE/EN browser preferences.

`npm run build` now builds both the browser assets and `dist/server/entry-jobs.js`. **Use the Node server (`npm start`) for SEO delivery**: it fetches the public API and renders real listing/detail content, job links, individual titles/descriptions and social-preview metadata into the initial HTML for every visitor. A static-only upload or Vite development server does not provide this dynamic SEO behavior. Keep the server bundle/manifest private; the included server rejects public requests to `/server` and `/.vite`. The interactive job module loads before replacing existing HTML, and it reuses the initial data without another page request. The employer landing-page module is loaded separately. Image dimensions are reserved, the selected detail image receives high fetch priority, and list thumbnails load lazily. These optimizations have not been assigned a Lighthouse score or field-performance rating.

For local built previews, set `JOBS_API_ORIGIN=http://127.0.0.1:8011` and run `npm start` after building. If a different backend is used for browser testing, also build with its `VITE_API_URL`. The server-to-server public API origin must have no path, credentials or query. Only public job data is fetched, no visitor cookies are forwarded, and responses are not cached. API failures produce HTTP 503 with Retry-After, rather than indexable empty content. Missing, withdrawn, closed and expired detail pages return genuine HTTP 404 without job markup. Listing search/filter URLs use noindex; unfiltered pagination has its own canonical URL. Tracking link parameters are excluded from job canonicals.

Future production setup still requires the real HTTPS `SITE_URL` during `npm run build:public`, `NODE_ENV=production`, an explicit `JOBS_API_ORIGIN`, and HTTPS reverse-proxy routing of `/api` to the configured backend for browser APIs and images. Set `JOBS_INDEXABLE=1` only for the approved public operation. Indexable job output requires **all three**: the public build origin, the explicit flag and API `test=false`. Local/test data stays noindex even when the flag is set. No public deployment or indexing request was made.

The dynamic sitemap contains only currently open approved jobs and is rechecked on every request. Individual eligible jobs receive `JobPosting` JSON-LD (never the directory), with visible employer/title/location/description, a recorded original publication date, a provided deadline, employment type and direct application. Remote jobs use DE applicant-location requirements. The first explicit portal activation stores `published_at`; retries and plan changes preserve it, and it is excluded from the editable budget plan. Existing legacy activations with no verified publication date omit job markup until explicit activation records one. Free-text salaries remain visible but are not guessed into numeric baseSalary data; street/postcode, verified salary/pay period and employer logo could further enrich future structured records. Google Indexing API/Search Console integration is not implemented. See [Google JobPosting guidance](https://developers.google.com/search/docs/appearance/structured-data/job-posting) and [Core Web Vitals](https://web.dev/articles/vitals). Search eligibility, indexing, ranking and maximum scores cannot be guaranteed.

`npm run test:job-seo` uses isolated fake APIs and temporary build copies to verify initial HTML, true 404/503, canonical/share metadata, escaped employer text, JobPosting fields/preview gates, sitemap closure behavior, CSP script hashes and server-file isolation. It is also part of the digital twin's independent verification. All normal backend/build/SEO/language checks remain required.

## Simplified first-run onboarding (7 October 2026)

The four setup milestones remain: secure account, confirmed subscription, company profile and reviewed first draft. The profile starts with three required answers; optional benefits and tone are expandable and retained. First-run billing shows subscription plans and their required consents; token purchases, account management and ledger remain in ordinary workspace billing. Green/cream cards, clear completed-step indicators, mobile layout and keyboard focus keep the visual guidance. Failed profile saves retain inputs; draft retries reuse the saved campaign and generation key. Setup completes only after explicit review and server confirmation.

`npm run test:onboarding` runs 38 isolated component/handler checks against fake API, timer and navigation adapters, including security/payment gates, resuming, failed retries and authenticator QR decoding/confirmation. The QR identifies the website from `MH_PUBLIC_URL` in the provider label and the login email as its account; both appear beside the QR in DE/EN. Workspace, billing and social entry routes share the same security panel; status failures stay visible and retryable. These are component checks, not real Stripe/OpenAI/mail end-to-end tests. Desktop/mobile browser QA used only a fictional preview API.

### Authenticator QR setup

During MFA setup, scan the locally generated QR code with your authenticator app, then enter its current six-digit code and save the recovery codes. Manual setup is expandable when a camera is unavailable. QR/secret disappear after successful confirmation. No QR image service or external secret transmission is used. `/auth/mfa/setup` returns a correctly encoded account label with explicit SHA1/6-digit/30-second settings; restart the backend and reload the frontend after updating.

The shared security card also covers existing-authenticator sign-in and recovery-code entry. Both use the onboarding palette, icon, spacing and primary action; choosing the recovery alternative clears the previous input/error. Authenticator codes use six individually labelled boxes with automatic focus progression, backspace/arrow navigation, full-code paste and one-time-code autofill support. Incomplete codes cannot be submitted. Longer recovery codes retain a separate text field. MFA policy and backend verification stay unchanged.

Existing MFA accounts can choose “Connect authenticator app”, verify an unused MH recovery code and scan their account QR. The endpoint does not unlock the session or change the stored seed; a current app code must still pass the normal challenge. If both the authenticator and recovery codes are lost, use the linked account recovery request. Mailbox confirmation is followed by independent Platform Admin/operator review; only an approved one-time email link allows a new password and mandatory fresh MFA setup. See AUTH_SETUP.md. Restart the backend for `/auth/mfa/reconnect`.

### Reviewed account recovery

`/auth?action=recover` requests recovery when both MFA and recovery codes are lost. A one-hour email link explicitly confirms mailbox access, then the user receives a case reference for their MH operator. Platform Admin → System → Account recovery lists verified requests; approval needs an independently completed ownership check, its case reference, the exact account email, and a fresh code from the reviewing admin’s own authenticator. Self-approval and demo-role review are blocked. Approval sends a one-use 30-minute reset link. It does not change the account until the owner uses it and sets a new password. That step revokes all old sessions/codes and requires a fresh QR setup for every role. Requests expire after seven days; expired/changed-account/cancelled/rejected/used links cannot reset accounts. If all Platform Admins are locked out, the trusted host operator can use the reviewed CLI in AUTH_SETUP.md. Real identity checking is performed by the operator, not automatically inferred from an email or checkbox.
