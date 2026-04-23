# Phase 10 Account, Billing, and Entitlement Plan

## Purpose

Phase 10 defines the account, billing, and entitlement truth model for VoxaRisk before new feature wiring is added. The goal is to make future customer login, organisation activation, billing portal linkage, AI usage metering, and monitoring explainable from persisted records.

This step is doctrine-first and backend-first. It does not implement frontend account UI, team invitations, Stripe checkout UI, billing portal UI, or new product workflows.

## Doctrine

The intended truth chain is:

`identity -> organisation membership -> subscription state -> plan entitlements -> product access`

Product access must be explainable by persisted records. Client-side claims, email-only matching, and inferred billing assumptions must not silently grant premium access.

AI remains subordinate to deterministic contract analysis. AI Review Notes may explain deterministic findings and evidence, but AI must not calculate risk score, change severity, override findings, approve contracts, or replace legal review.

## Core Entities

### User

Responsibility:
- Represents an account identity that can authenticate later.
- Owns personal login credentials and active/inactive state.
- Does not itself own paid entitlement.

Source of truth:
- User identity fields are source-of-truth for account identity only.
- User role on the legacy user row is not sufficient for future multi-organisation authority.
- Customer sign-in proves identity only. It does not grant paid access.

Out of scope now:
- Open public registration.
- SSO.
- User invite UI.
- Broad profile management.

### Organisation

Responsibility:
- Represents the commercial account boundary for product access.
- Owns API keys, scans, usage logs, subscriptions, billing customer references, AI usage meters, and monitoring signals.
- Remains the entitlement boundary for backend enforcement.

Source of truth:
- Organisation identity is source-of-truth for the account boundary.
- Existing `plan_type`, `plan_status`, `plan_limit`, and Stripe fields remain legacy compatibility fields until live enforcement is migrated to the new subscription spine.

### Membership

Responsibility:
- Bridges User to Organisation.
- Defines who can act inside an organisation and with what status.
- Allows the future platform to support teams without granting access from email alone.

Ownership:
- A Membership belongs to one User and one Organisation.
- An Organisation may have many Memberships.
- A User may belong to multiple Organisations in the future.

Minimum states:
- `active`: user is allowed to act in the organisation.
- `invited`: future invite exists but is not accepted.
- `suspended`: user should not be allowed to act.
- `removed`: historical membership should not grant access.

Out of scope now:
- Invite flows.
- Role-based permissions.
- Team admin UI.

### Subscription

Responsibility:
- Represents the billing lifecycle state for an Organisation.
- Links provider subscription state to internal plan entitlement.
- Provides a persisted record that explains why an organisation has paid, restricted, or default access.

Ownership:
- A Subscription belongs to one Organisation.
- At most one Subscription should be treated as current for entitlement resolution.

Source of truth:
- The current Subscription state should become the source-of-truth for paid entitlement once webhook and account identity wiring are complete.
- Until live migration is explicitly performed, existing Organisation billing fields remain the compatibility path for current live behaviour.

### Plan

Responsibility:
- Defines internal plan identity and baseline quotas.
- Plans are stable internal product entitlement names, not payment provider objects.

Internal names:
- `starter`
- `business`
- `executive`
- `enterprise`

Source of truth:
- Plan identity and quota policy are source-of-truth inside VoxaRisk.
- Payment provider lookup keys and price IDs are external references that map into internal plan names.

### API Key / Access Relationship

Responsibility:
- Existing API keys authenticate backend use.
- API keys belong to an Organisation and may optionally be associated with a User.
- API key authentication must continue to work until account login is added.

Access rule:
- API key proves request identity for the current backend.
- API key does not independently grant paid features; entitlement is resolved through the Organisation.
- Customer account session proves signed-in user identity; active Membership provides Organisation context.
- Account session does not replace API key flow yet and does not grant premium entitlement.

Out of scope now:
- Replacing API key auth.
- Browser login sessions.
- OAuth.

### Entitlement State

Responsibility:
- Converts subscription and plan state into product access decisions.
- Must fail closed for unknown or unsupported states.

Derived values:
- effective plan
- monthly scan limit
- paid access allowed
- AI Review Notes allowed
- fail-closed reason

Source of truth:
- Entitlement state is derived from persisted Organisation plus current Subscription.
- It is not directly trusted from the frontend.

### AI Usage Meter

Responsibility:
- Tracks AI Review Notes usage by Organisation and billing period.
- Supports future quota, cost, abuse, and monitoring controls.

Ownership:
- AI usage belongs to an Organisation.
- A usage meter may optionally reference the User that triggered usage.

Out of scope now:
- Charging per AI request.
- Frontend usage dashboards.
- Automatic AI quota UI.

### Billing Customer Reference

Responsibility:
- Stores a deterministic billing customer bridge for an Organisation.
- Enables future billing portal linkage and automatic subscription-to-organisation activation.

Fail-safe rule:
- Billing email alone must not activate paid access.
- The billing customer reference must map deterministically to the Organisation.

### Webhook Event Log / Audit Trail

Responsibility:
- Records payment provider events and processing status.
- Supports idempotency, auditability, and failure diagnosis.

Existing table:
- `stripe_webhook_events`

Required behaviour:
- Duplicate event IDs must not mutate entitlement twice.
- Invalid signatures must not mutate state.
- Unmatched events must be retained as unmatched or pending, not ignored as success.

### Monitoring Signals

Responsibility:
- Records production-relevant signals for future observability.

Minimum signals needed later:
- webhook signature failures
- unmatched billing events
- unknown subscription states
- entitlement downgrade events
- AI provider disabled/unavailable events
- AI quota exhaustion
- scan quota exhaustion
- API key authentication failures
- migration or persistence failures

Out of scope now:
- External alerting integration.
- Dashboards.
- Metrics exporters.

## Ownership Relationships

- User owns identity.
- Organisation owns product access.
- Membership connects User to Organisation.
- API Key belongs to Organisation and optionally to User.
- Billing Customer Reference belongs to Organisation.
- Subscription belongs to Organisation.
- Plan defines internal entitlement shape.
- Entitlement is derived from Organisation, current Subscription, and Plan policy.
- AI Usage Meter belongs to Organisation and optionally User.
- Webhook Event Log records provider event processing.
- Monitoring Signal belongs optionally to Organisation and records operational facts.

## Subscription and Entitlement States

### `no_subscription`

Meaning:
- No current paid subscription exists.

Behaviour:
- Use starter-safe access.
- AI Review Notes denied.

### `checkout_started`

Meaning:
- Checkout began but entitlement is not confirmed.

Behaviour:
- Use starter-safe access.
- AI Review Notes denied.
- Do not grant paid access until a verified billing state is persisted.

### `active`

Meaning:
- Subscription is active for a mapped paid plan.

Behaviour:
- Grant paid plan entitlement when the plan is `business`, `executive`, or `enterprise`.
- AI Review Notes allowed for paid plans.

### `trialing`

Meaning:
- Subscription trial is active.

Behaviour:
- Treat like active for mapped paid plans.
- AI Review Notes allowed for paid plans.

### `past_due`

Meaning:
- Payment is overdue.

Behaviour:
- Restrict to starter-safe access.
- AI Review Notes denied.

### `unpaid`

Meaning:
- Payment is not collected and subscription should not grant paid access.

Behaviour:
- Restrict to starter-safe access.
- AI Review Notes denied.

### `canceled`

Meaning:
- Subscription has ended or is canceled.

Behaviour:
- Restrict to starter-safe access.
- AI Review Notes denied.

### `incomplete`

Meaning:
- Subscription setup is incomplete.

Behaviour:
- Do not grant paid access.
- AI Review Notes denied.

### `incomplete_expired`

Meaning:
- Incomplete subscription expired.

Behaviour:
- Restrict to starter-safe access.
- AI Review Notes denied.

### `restricted`

Meaning:
- Internal safe state for access restriction.

Behaviour:
- Use starter-safe access unless an explicit manual override is persisted.
- AI Review Notes denied.

### `manual_override`

Meaning:
- Controlled internal override applied by an authorised operational process.

Behaviour:
- May grant the persisted plan entitlement only when the plan is an internal paid plan.
- Must be auditable.
- Must not be created by client request or email matching.

## Source-of-Truth vs Derived

Source-of-truth:
- User identity records.
- Organisation account boundary.
- Membership records.
- Billing customer reference.
- Current Subscription record.
- Plan definitions.
- Webhook event log records.
- AI usage meter records.

Derived:
- Effective plan.
- Paid access allowed.
- AI Review Notes allowed.
- Monthly scan limit.
- Restriction reason.
- Monitoring dashboards and alerts.

Legacy compatibility:
- Existing Organisation plan and Stripe fields remain as transitional mirror data.
- Runtime entitlement enforcement must use the Phase 10 resolver and current Subscription truth when deciding premium access, scan quota, and AI Review Notes access.
- During webhook reconciliation, Organisation billing fields may be mirrored from durable Subscription and Billing Customer Reference records only for compatibility with existing operational records and diagnostics.
- Legacy Organisation plan fields must not independently widen access when no current Subscription truth exists.

## Fail-Safe Rules

- Unknown billing state must not silently grant premium access.
- Missing subscription must resolve to starter-safe access.
- Checkout-started must not grant paid access.
- Webhook failure must not create entitlement ambiguity; it must record failure or leave the previous known state intact.
- Invalid webhook signature must not mutate state.
- Duplicate webhook event must not mutate state twice.
- Unmatched payment or subscription must remain pending/unmatched and must not upgrade by email alone.
- Webhook handlers must verify, deduplicate, persist, and reconcile durable state; entitlement decisions must remain resolver-driven and explainable from persisted records.
- AI access must remain subordinate to paid-plan entitlement.
- Deterministic scan engine must not depend on AI availability.
- Organisation access must be explainable from persisted records.
- Frontend claims must never be entitlement source-of-truth.
- Authentication must not grant premium access without resolver-backed subscription entitlement.
- Missing, inactive, or ambiguous Membership must fail closed.

## Explicitly Out of Scope for This Step

- Frontend account UI.
- Stripe UI changes.
- Billing portal implementation.
- Team invites.
- Role-based permissions.
- Login/session implementation.
- Replacing API key flow.
- Wiring live scan routes to the new resolver.
- Charging or enforcing AI usage meter quotas.
- External monitoring/alert delivery.
- Any change to deterministic scoring, findings, severity, or scan response contracts.

## Minimal Persistence Foundation Added in This Step

- `memberships`
- `billing_customer_references`
- `subscriptions`
- `ai_usage_meters`
- `monitoring_signals`

These tables are additive and preserve current live behaviour. They allow later phases to move from legacy Organisation fields to the explicit truth chain without redesigning entitlement logic under feature pressure.

## Legacy Billing Backfill

Purpose:
- Move existing production organisations from legacy Organisation billing fields into Phase 10 Subscription and Billing Customer Reference truth.
- Prevent paid organisations from remaining starter-safe after resolver-backed enforcement cutover when their billing truth has not yet been migrated.

Mechanism:
- Backend-only script: `backfill_legacy_billing.py`.
- Default mode is dry-run.
- Mutation requires explicit `--apply`.
- The script must not run automatically on application startup.

Automatic backfill eligibility:
- Organisation legacy `plan_type` is one of `business`, `executive`, or `enterprise`.
- Organisation legacy `plan_status` is recognised as active/trialing or a restricted subscription state.
- Organisation has both `stripe_customer_id` and `stripe_subscription_id`.
- Stripe customer ID is not already mapped to a different Organisation.
- Stripe subscription ID is not already mapped to a different Organisation.
- Existing current Subscription, if present, is coherent with the legacy Organisation fields.

Manual review outcomes:
- Missing customer or subscription ID.
- Unknown legacy plan status.
- Stripe customer ID already mapped to another Organisation.
- Stripe subscription ID already mapped to another Organisation.
- Existing current Subscription conflicts with legacy Organisation fields.
- Any record where the mapping cannot be explained deterministically from persisted fields.

Backfill writes on `--apply`:
- Upserts `billing_customer_references`.
- Upserts current `subscriptions` with `source = legacy_backfill`.
- Writes `monitoring_signals` audit record with:
  - org ID
  - previous legacy fields
  - new Subscription details
  - new Billing Customer Reference details
  - method `legacy_backfill`
  - timestamp from the monitoring signal row

Dry-run behaviour:
- Reports `dry_run`, `skipped`, or `manual_review` decisions.
- Does not create Subscription records.
- Does not create Billing Customer Reference records.
- Does not create Monitoring Signal records.
- Does not change runtime entitlement.

Runtime relationship:
- Backfill is a migration aid only.
- Runtime enforcement still reads resolver-backed Phase 10 truth.
- Legacy Organisation fields do not become primary authority again.
- Ambiguous records must remain starter-safe until reviewed and reconciled explicitly.

## Entitlement Diagnostics

Purpose:
- Give operators a narrow backend-safe way to explain an Organisation's effective entitlement state.
- Support support investigation, webhook review, and legacy backfill review before customer-facing account and billing features exist.
- Show what the system believes and why without mutating billing or entitlement records.

Mechanism:
- Service function: `build_entitlement_diagnostics`.
- CLI script: `inspect_entitlement.py <org_id>`.
- No customer-facing UI.
- No broad admin dashboard.
- No entitlement repair logic.

Diagnostics output includes:
- Organisation ID.
- Legacy Organisation billing field snapshot.
- Current Phase 10 Subscription snapshot.
- Billing Customer Reference snapshot.
- Resolver-backed effective entitlement.
- AI Review Notes entitlement.
- Monthly scan quota interpretation.
- Recent related Stripe webhook events.
- Backfill audit signals.
- Mismatch and ambiguity flags.

Mismatch flags:
- Legacy paid fields but no current Subscription row.
- Active current Subscription without Billing Customer Reference.
- Legacy Organisation subscription ID differs from current Subscription truth.
- Legacy Organisation customer ID differs from Billing Customer Reference truth.
- Stripe customer ID mapped across multiple Organisations.
- Stripe subscription ID mapped across multiple Organisations.
- Legacy fields indicate paid access but resolver correctly returns starter-safe access.
- Resolver output inconsistent with active current Subscription.

Read-only rule:
- Diagnostics must not create, update, or delete records.
- Diagnostics must not backfill, repair, activate, downgrade, or override entitlement.
- Diagnostics must not become a second entitlement authority.
- Runtime enforcement remains resolver-backed.

## Customer Account Identity Bridge

Purpose:
- Allow a customer user to sign in and be linked to the correct Organisation.
- Provide minimal account recognition before broader portal, billing, profile, or team features exist.

Mechanism:
- Backend endpoints:
  - `POST /account/login`
  - `GET /account/me`
  - `POST /account/logout`
- Frontend proxy routes:
  - `/api/account/login`
  - `/api/account/me`
  - `/api/account/logout`
- Customer-facing pages:
  - `/signin`
  - `/account`

Rules:
- Password authentication proves user identity.
- Exactly one active Membership is required for Organisation account context.
- Membership determines which Organisation the signed-in user is attached to.
- Resolver-backed Subscription truth determines paid access, quota, and AI Review Notes access.
- Login does not directly grant premium access.
- User records must not contain premium flags.
- Missing, inactive, or ambiguous Membership fails closed.
- API key flow remains in place for analysis endpoints.

Out of scope:
- Registration.
- Customer billing portal.
- Team invites.
- Role management UI.
- Broad account settings.
- Replacing API key authentication for scan endpoints.

## Controlled Account Provisioning and Password Recovery

Purpose:
- Let an operator provision a legitimate customer user for an existing Organisation.
- Let that user set an initial password or reset a password without creating an open registration path.
- Preserve the separation between identity, Membership, and resolver-backed entitlement.

Mechanism:
- Backend service: `account_provisioning.py`.
- Operator CLI: `provision_account.py --org-id <org_id> --email <email>`.
- Operator reset CLI: `issue_password_reset.py --email <email>`.
- Backend endpoints:
  - `POST /account/password/setup`
  - `POST /account/password/reset/request`
  - `POST /account/password/reset/complete`
- Frontend proxy routes:
  - `/api/account/password/setup`
  - `/api/account/password/reset/request`
  - `/api/account/password/reset/complete`
- Customer-facing pages:
  - `/account/setup`
  - `/forgot-password`
  - `/reset-password`

Provisioning rules:
- The Organisation must already exist.
- Provisioning creates or reuses a User and creates an active Membership only for the specified Organisation.
- Provisioning does not create a Subscription, Billing Customer Reference, Plan, API key, or paid entitlement.
- Provisioning emits a setup token for controlled delivery by the operator; it is not an open signup mechanism.
- Existing inactive Membership records are not silently reactivated.

Password token rules:
- Setup tokens are single-purpose and expire after 72 hours.
- Reset tokens are single-purpose and expire after 2 hours.
- Tokens are stored only as SHA-256 hashes.
- Creating a new token invalidates previous unused tokens for the same user and purpose.
- Completing setup or reset marks the token used.
- Used, expired, invalid, missing, or wrong-purpose tokens fail closed.

Authority rules:
- Password setup proves control of an operator-provisioned account only.
- Password reset proves control of an existing user account only; until email delivery exists, reset-link issuance is operator-controlled.
- Neither setup nor reset changes Organisation Membership, Subscription, Billing Customer Reference, Plan, API key, quota, or AI entitlement.
- Active Membership is still required before a token can complete into an account session.
- Resolver-backed Subscription truth remains the only paid-access authority.
- Missing, inactive, or ambiguous Membership fails closed.

Out of scope:
- Open public signup.
- Self-serve Organisation creation.
- Team invites.
- Role management UI.
- Customer billing portal.
- Broad profile settings.
## Customer Billing Portal Linkage

Purpose:
- Allow an authenticated customer account to open the Stripe billing portal for its Organisation when a deterministic billing customer reference exists.
- Keep billing portal access attached to identity plus Membership, while entitlement decisions remain resolver-backed.

Mechanism:
- Backend service: `billing_portal.py`.
- Backend endpoint: `POST /account/billing/portal`.
- Frontend proxy route: `/api/account/billing/portal`.
- Customer-facing surface: `Manage billing` button on `/account`.

Required gates before portal creation:
- Valid account session.
- Exactly one active Membership for the authenticated User.
- Deterministic Organisation context from that Membership.
- Exactly one Stripe `BillingCustomerReference` for that Organisation.
- `STRIPE_SECRET_KEY` configured server-side.
- Absolute HTTP(S) return URL.

Failure behaviour:
- Missing account session returns unauthorized.
- Invalid, inactive, missing, or ambiguous Membership returns forbidden.
- Missing Billing Customer Reference returns forbidden and does not call Stripe.
- Missing Stripe server configuration returns service unavailable.
- Stripe provider failure returns bad gateway.

Authority rules:
- Billing portal linkage does not create, update, or delete Subscription truth.
- Billing portal linkage does not grant paid access.
- Billing portal linkage does not change AI entitlement or scan quota.
- Runtime entitlement remains resolver-backed from persisted Subscription state.
- The frontend never receives or stores Stripe customer IDs.

Out of scope:
- Customer portal settings UI beyond the portal launch action.
- Team billing seats or invites.
- Subscription editing inside VoxaRisk.
- Billing customer repair or mapping from the frontend.
## Governed Team Access Foundation

Purpose:
- Allow an owner or admin to invite legitimate users into the same Organisation.
- Keep Membership as the organisation-context bridge and keep entitlement at Organisation level.

Mechanism:
- Persistence table: `organization_invites`.
- Backend service: `team_invites.py`.
- Backend endpoints:
  - `GET /account/team`
  - `POST /account/team/invites`
  - `POST /account/team/invites/accept`
- Frontend proxy routes mirror those endpoints under `/api/account/team`.
- Customer-facing surfaces:
  - team context and invite creation on `/account`
  - invite acceptance on `/team/accept`

Role model:
- `owner`: can invite `admin` and `member` users.
- `admin`: can invite `member` users.
- `member`: cannot create team invites.

Invite rules:
- Invites are token-based and expire after 7 days.
- Invite tokens are stored only as hashes.
- Invites are single-use and transition from `pending` to `accepted` or `expired`.
- Invite acceptance requires the invited email to match the invite record.
- Existing active membership blocks invite acceptance because organisation switching is not introduced yet.
- Duplicate pending invites for the same Organisation and email fail safely.

Authority rules:
- Role controls team actions only.
- Role does not grant paid access, AI access, billing access, or quota.
- Organisation Subscription truth remains the entitlement authority.
- Missing or ambiguous Membership still fails closed.

Out of scope:
- Organisation switching UI.
- Broad owner/admin dashboard.
- Advanced RBAC matrix.
- Team invite email delivery automation.
- External sharing.
## Internal Operations Console

Purpose:
- Provide a narrow internal platform-admin surface for inspecting organisations, memberships, billing references, subscription truth, resolver-backed entitlement, usage, scans, invites, webhook events, and monitoring signals.
- Keep platform governance visible without creating a second entitlement authority.

Mechanism:
- Backend service: `internal_ops.py`.
- Backend endpoints:
  - `GET /internal/ops/organizations`
  - `GET /internal/ops/organizations/{org_id}`
- Frontend proxy route: `/api/internal/ops/organizations`.
- Customer-facing route is not used; internal route is `/internal/operations`.

Access control:
- User must have a valid account session.
- User must also be explicitly listed in `INTERNAL_ADMIN_EMAILS`.
- Customer organisation roles such as `owner` or `admin` do not grant internal operations access.

Data surfaced:
- Organisations list with effective entitlement, subscription summary, billing customer reference summary, member count, pending invite count, and scan count.
- Organisation detail with membership rows, recent invites, recent scans, usage logs, monitoring signals, webhook rows, and entitlement diagnostics.

Manual controls:
- None in this step.
- The console is read-only and must not mutate Organisation, Membership, Subscription, Billing Customer Reference, Plan, or entitlement records.

Authority rule:
- Internal dashboard state is observation only.
- Resolver-backed Subscription truth remains product-access authority.
- Any future mutation must be explicit, bounded, audited, and separately tested.
## Phase 11 Internal Support Workflow Guardrails

The internal operations console may expose a narrow support workflow layer for platform operators only. This layer is not a customer surface, not a CRM, and not an entitlement authority.

### Audit Path

Operator workflow mutations must be recorded in `internal_operator_actions` before they are treated as complete. Each audit record includes:

- `actor_user_id`: the authenticated internal platform operator.
- `org_id`: the organisation context when applicable.
- `target_type` and `target_id`: the affected organisation, invite, or other bounded object.
- `action_type`: the narrow internal action performed.
- `reason`: the operator-supplied investigation reason.
- `before_json` and `after_json`: snapshots sufficient to explain what changed.
- `created_at`: database timestamp for review.

### Allowed Step 3 Actions

Phase 11 Step 3 allows only these bounded workflow actions:

- `operator_note`: records an internal investigation note against an organisation with the current diagnostics snapshot.
- `invite_cancelled`: cancels a pending, unused organisation invite and records before/after invite state.

No plan editing, subscription editing, billing-customer editing, entitlement override, quota override, or scan-result mutation is part of this workflow layer.

### Authority Boundary

Runtime entitlement remains resolver-backed. Internal workflow actions may provide support context or bounded containment around invites, but they must not grant premium access, deny premium access, alter risk scoring, or override subscription truth. Customer organisation owners/admins are not internal platform admins and must not access these workflow endpoints.