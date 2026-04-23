# Phase 10 Entitlement Operations Runbook

## Purpose

This runbook explains how to inspect and operate the Phase 10 account, billing, and entitlement spine safely before customer-facing account, billing portal, login, or team features exist.

The runbook is for backend/operator use only. It is not a customer-facing workflow, not a broad admin dashboard, and not a second entitlement authority.

## Source-of-Truth Chain

Runtime entitlement follows this chain:

`identity -> organisation membership -> subscription state -> plan entitlements -> product access`

Current backend enforcement is resolver-backed:

- API key identifies the Organisation for current backend requests.
- The entitlement resolver reads current Phase 10 Subscription truth.
- Effective plan, scan quota, and AI Review Notes access are derived from resolver output.
- Legacy Organisation billing fields are mirror-only and must not independently widen access.

Operational doctrine:

- Webhook events do not directly grant access.
- Webhook events verify, deduplicate, persist, and reconcile durable state.
- Diagnostics is read-only.
- Backfill is a migration aid, not permanent authority.
- Mutation must be explicit, narrow, auditable, and intentional.

## Tools

### `inspect_entitlement.py`

Command:

```bash
python inspect_entitlement.py <org_id>
```

Optional webhook limit:

```bash
python inspect_entitlement.py <org_id> --webhook-limit 10
```

Use for:

- Inspecting effective entitlement state for one Organisation.
- Explaining why an Organisation is starter, paid, restricted, or ambiguous.
- Reviewing resolver output.
- Reviewing legacy Organisation billing fields.
- Reviewing current Subscription truth.
- Reviewing Billing Customer Reference truth.
- Reviewing related webhook events.
- Reviewing legacy backfill audit signals.
- Identifying mismatch flags.

Not for:

- Repairing records.
- Activating paid access.
- Downgrading access.
- Editing billing state.
- Customer-facing account support screens.

### `backfill_legacy_billing.py`

Dry-run command:

```bash
python backfill_legacy_billing.py
```

Apply command:

```bash
python backfill_legacy_billing.py --apply
```

Use for:

- Migrating eligible legacy-paid Organisations into Phase 10 Subscription truth.
- Producing explicit `dry_run`, `skipped`, and `manual_review` decisions.
- Writing auditable backfill records only when `--apply` is used.

Not for:

- Blind mass activation.
- Inventing missing Stripe identifiers.
- Resolving ambiguous records automatically.
- Replacing webhook reconciliation.
- Running automatically on every deploy or application boot.

## Diagnostics Output Checklist

When reviewing `inspect_entitlement.py` output, check:

- `found`
- `read_only`
- `legacy_organization_billing`
- `phase_10_subscription`
- `billing_customer_reference`
- `effective_entitlement`
- `effective_ai_entitlement`
- `effective_quota`
- `last_webhook_events`
- `backfill`
- `mismatch_flags`

Expected healthy paid Organisation:

- `phase_10_subscription.status` is `active` or `trialing`.
- `phase_10_subscription.plan_name` is `business`, `executive`, or `enterprise`.
- `billing_customer_reference.external_customer_id` is present.
- `effective_entitlement.paid_access` is `true`.
- `effective_ai_entitlement.ai_review_notes_allowed` is `true`.
- `mismatch_flags` is empty or informational only.

Expected starter Organisation:

- `phase_10_subscription` is absent or non-paid.
- `effective_entitlement.effective_plan` is `starter`.
- `effective_ai_entitlement.ai_review_notes_allowed` is `false`.
- `effective_quota.monthly_scan_limit` is starter-safe.

Expected restricted Organisation:

- `phase_10_subscription.status` is `past_due`, `unpaid`, `canceled`, `incomplete`, `incomplete_expired`, or `restricted`.
- `effective_entitlement.effective_plan` is `starter`.
- `effective_ai_entitlement.ai_review_notes_allowed` is `false`.

## Common Mismatch Flags

### `legacy_paid_without_current_subscription`

Meaning:

- Legacy Organisation fields look paid.
- No current Phase 10 Subscription exists.

Do:

- Run diagnostics.
- Run backfill dry-run.
- Apply backfill only if dry-run marks the Organisation eligible.

Do not:

- Manually change runtime enforcement.
- Treat legacy fields as access authority.

### `active_subscription_missing_customer_reference`

Meaning:

- A current active Subscription exists.
- Billing Customer Reference is missing.

Do:

- Review recent webhook events.
- Confirm whether a customer reference should exist.
- Prefer webhook reconciliation or a controlled backfill/reconciliation path.

Do not:

- Create customer references by email-only inference.

### `legacy_subscription_id_mismatch`

Meaning:

- Legacy Organisation subscription ID differs from current Subscription truth.

Do:

- Review webhook events and backfill audit signals.
- Confirm which subscription is current in Stripe.
- Escalate to manual review before any mutation.

### `legacy_customer_id_mismatch`

Meaning:

- Legacy Organisation customer ID differs from Billing Customer Reference truth.

Do:

- Review webhook events and payment provider records.
- Confirm deterministic mapping.
- Escalate to manual review before mutation.

### `stripe_customer_id_conflicts_across_orgs`

Meaning:

- The same Stripe customer ID maps to more than one Organisation.

Do:

- Stop mutation.
- Treat as critical.
- Manually inspect all affected Organisations.

### `stripe_subscription_id_conflicts_across_orgs`

Meaning:

- The same Stripe subscription ID maps to more than one Organisation.

Do:

- Stop mutation.
- Treat as critical.
- Manually inspect all affected Organisations.

### `legacy_paid_but_resolver_starter_safe`

Meaning:

- Legacy fields indicate paid.
- Resolver correctly returns starter-safe because no current Subscription truth grants access.

Do:

- Run backfill dry-run if this is an existing paid customer.
- Apply only if eligible.

### `resolver_inconsistent_with_subscription`

Meaning:

- Active current Subscription and resolver output disagree.

Do:

- Stop mutation.
- Run targeted tests if local reproduction is possible.
- Review resolver, subscription state, plan name, and migration status.

## Investigation Flow: Customer Says Paid But Access Denied

1. Identify the Organisation ID used by the customer's API key or backend context.
2. Run diagnostics:

```bash
python inspect_entitlement.py <org_id> --webhook-limit 10
```

3. Check `effective_entitlement.effective_plan`.
4. Check `effective_ai_entitlement.ai_review_notes_allowed` if the issue is AI Review Notes.
5. Check `phase_10_subscription`.
6. Check `billing_customer_reference`.
7. Check `mismatch_flags`.
8. Check recent webhook events.

If `legacy_paid_without_current_subscription` appears:

```bash
python backfill_legacy_billing.py
```

Review the dry-run output for the Organisation.

Apply only if:

- the Organisation is eligible,
- customer/subscription IDs are present,
- no ambiguity flags exist,
- the operator can explain the mapping.

Apply:

```bash
python backfill_legacy_billing.py --apply
```

Post-apply verification:

```bash
python inspect_entitlement.py <org_id> --webhook-limit 10
```

Confirm:

- current Subscription exists,
- source is `legacy_backfill`,
- Billing Customer Reference exists,
- resolver grants the expected plan,
- mismatch flags are clear or explainable.

## Investigation Flow: Access Exists But Should Be Restricted

1. Run diagnostics:

```bash
python inspect_entitlement.py <org_id> --webhook-limit 10
```

2. Check `phase_10_subscription.status`.
3. Check recent webhook events for cancellation, failed payment, or unpaid state.
4. Confirm whether the latest relevant webhook was received and processed.
5. If Stripe shows restricted state but the local Subscription is active, review webhook delivery and event log.
6. Do not manually downgrade by editing legacy Organisation fields; runtime reads resolver-backed Subscription truth.
7. If containment is urgent, prefer a controlled database update to the current Subscription status with a documented operational record, followed by diagnostics verification.

Post-containment check:

```bash
python inspect_entitlement.py <org_id>
```

Expected restricted output:

- `effective_entitlement.effective_plan` is `starter`.
- `effective_ai_entitlement.ai_review_notes_allowed` is `false`.
- `effective_quota.monthly_scan_limit` is starter-safe.

## Investigation Flow: Webhook Mismatch or Unmatched Event

1. Run diagnostics with a larger webhook window:

```bash
python inspect_entitlement.py <org_id> --webhook-limit 20
```

2. Check `last_webhook_events`.
3. Look for:

- `processing_status = unmatched`
- missing `org_id`
- missing customer/subscription identifiers
- missing price lookup key
- errors in the event row

4. Confirm whether Stripe metadata contained a deterministic `org_id`.
5. Confirm whether a Billing Customer Reference already exists.
6. If the event lacks deterministic mapping, do not grant access.
7. If the customer is known and legacy fields are coherent, use dry-run backfill rather than manual activation.

Dry-run:

```bash
python backfill_legacy_billing.py
```

Manual review required when:

- the event has no deterministic organisation mapping,
- customer ID maps to multiple organisations,
- subscription ID maps to multiple organisations,
- price lookup key is missing or unknown,
- legacy fields conflict with Subscription truth.

## Investigation Flow: Legacy Paid Org With No Subscription Row

1. Run diagnostics:

```bash
python inspect_entitlement.py <org_id>
```

2. Confirm mismatch flags:

- `legacy_paid_without_current_subscription`
- `legacy_paid_but_resolver_starter_safe`

3. Run dry-run:

```bash
python backfill_legacy_billing.py
```

4. Locate the Organisation decision in output.
5. If decision is `dry_run` and `eligible = true`, verify:

- plan is recognised,
- status is recognised,
- customer ID exists,
- subscription ID exists,
- no cross-org conflict exists.

6. Apply:

```bash
python backfill_legacy_billing.py --apply
```

7. Re-run diagnostics:

```bash
python inspect_entitlement.py <org_id>
```

8. Confirm resolver-backed entitlement changed because Subscription truth now exists, not because legacy fields were trusted.

## Dry-Run Backfill Procedure

Before running:

- Confirm database target is production only if intended.
- Confirm recent backup or snapshot exists.
- Confirm no broad incident is in progress unless this is part of containment.

Command:

```bash
python backfill_legacy_billing.py
```

Review output:

- `dry_run`: candidate would be migrated if `--apply` is used.
- `skipped`: no paid legacy plan should be migrated.
- `manual_review`: do not apply until investigated.

Do not proceed to apply if:

- any target Organisation is `manual_review`,
- target has missing customer/subscription ID,
- target has conflicts across organisations,
- operator cannot explain the mapping.

## Apply Backfill Procedure

Only after dry-run review:

```bash
python backfill_legacy_billing.py --apply
```

Expected writes:

- `billing_customer_references`
- `subscriptions`
- `monitoring_signals`

Expected source:

- `subscriptions.source = legacy_backfill`

Expected audit:

- `monitoring_signals.category = billing_backfill`
- `monitoring_signals.signal_type = legacy_backfill_applied`
- `details_json` includes legacy snapshot, subscription details, customer reference details, and method.

## Post-Apply Verification Checklist

For each migrated Organisation:

```bash
python inspect_entitlement.py <org_id> --webhook-limit 10
```

Confirm:

- `phase_10_subscription` exists.
- `phase_10_subscription.source` is `legacy_backfill`.
- `billing_customer_reference` exists.
- `backfill.was_backfilled` is `true`.
- `effective_entitlement.effective_plan` matches expected plan for active/trialing paid plans.
- `effective_ai_entitlement.ai_review_notes_allowed` matches paid entitlement.
- `effective_quota.monthly_scan_limit` matches the plan.
- `mismatch_flags` is empty or understood.

## Production Safety Warnings

- Do not use legacy Organisation fields as runtime access authority.
- Do not infer access from billing email.
- Do not activate from unmatched webhook events.
- Do not apply backfill without dry-run review.
- Do not mutate records to silence diagnostics flags unless the source-of-truth chain is understood.
- Do not change deterministic scan output while handling billing.
- Do not expose diagnostics output to customers.
- Do not run backfill automatically at boot.

## Audit Expectations

Every applied backfill must be explainable from:

- legacy Organisation fields before migration,
- created or updated Subscription record,
- created or updated Billing Customer Reference,
- Monitoring Signal audit row,
- operator dry-run review record outside the application where applicable.

Webhook-driven changes must be explainable from:

- Stripe event ID,
- `stripe_webhook_events.processing_status`,
- mapped Organisation,
- reconciled Subscription record,
- Billing Customer Reference where available.

## Rollback and Containment Guidance

Preferred containment is fail-closed:

- Set current Subscription status to a restricted state only through a controlled database operation when urgent containment is required.
- Re-run diagnostics immediately.
- Confirm resolver returns starter-safe access.
- Preserve webhook and monitoring audit records.

If a backfill was applied incorrectly:

1. Do not edit legacy Organisation fields to control runtime access.
2. Inspect the Organisation:

```bash
python inspect_entitlement.py <org_id> --webhook-limit 20
```

3. Identify created Subscription and Billing Customer Reference.
4. Mark the Subscription non-current or restricted only through a documented operational action.
5. Re-run diagnostics.
6. Record the reason externally until a formal admin audit workflow exists.

## When Not To Mutate Anything

Do not mutate when:

- Organisation mapping is unclear.
- Customer ID or subscription ID is missing.
- There are cross-org Stripe identifier conflicts.
- Webhook event shape is unknown.
- Stripe status differs from local records and the latest event history is incomplete.
- The issue is only a customer-facing misunderstanding rather than persisted entitlement mismatch.
- You cannot explain how the resolver would derive access after the change.

## Step 6 Boundary

This runbook does not implement:

- login UI,
- customer portal UI,
- team invites,
- admin dashboard,
- billing editing endpoints,
- automatic repair logic,
- customer-facing entitlement display.

The runbook exists to keep operations disciplined until those features are added in bounded future steps.

## Customer Billing Portal Procedure

Purpose:
- Give a signed-in customer access to Stripe-hosted billing management only when the account context and billing customer reference are deterministic.
- Avoid building a local billing-editing authority inside VoxaRisk.

Customer path:
1. Customer signs in at `/signin`.
2. Customer opens `/account`.
3. Customer selects `Manage billing`.
4. Frontend calls `/api/account/billing/portal`.
5. Backend validates the account session, active Membership, Organisation context, and Billing Customer Reference.
6. Backend creates a Stripe billing portal session and returns only the portal URL.

Operator checks if portal access fails:
1. Confirm the user can sign in and `/account` shows exactly one active Membership.
2. Inspect entitlement and billing references:

```bash
python inspect_entitlement.py <org_id> --webhook-limit 20
```

3. Confirm `billing_customer_reference.external_customer_id` exists for the Organisation.
4. Confirm `STRIPE_SECRET_KEY` and `BILLING_PORTAL_RETURN_URL` are configured server-side.
5. If no billing customer reference exists, do not create one from email alone. Review Stripe webhook history or controlled backfill evidence.

Safety rules:
- Billing portal access is read-through to Stripe and must not mutate VoxaRisk entitlement records.
- Billing portal access is not proof of paid entitlement.
- Resolver-backed Subscription truth remains the product access authority.
- Missing customer mapping must fail closed rather than routing a user to the wrong billing customer.

Phase 10 closure boundary:
- Phase 10 now includes account sign-in, controlled provisioning, password setup/reset, resolver-backed entitlement, webhook reconciliation, diagnostics, backfill, runbook, and billing portal linkage.
- Phase 10 still excludes team invites, broad admin dashboard, local subscription editing UI, open registration, and customer-facing role management.
## Phase 11 Internal Support Workflow Procedure

The internal operations console includes a narrow support workflow layer for platform operators. This workflow is for investigation notes and bounded invite containment only. It does not grant, remove, or override entitlement.

### Access Rule

Only an authenticated account whose email is listed in `INTERNAL_ADMIN_EMAILS` may use the internal workflow endpoints or internal console workflow panel. Customer organisation `owner`, `admin`, or `member` roles are not internal platform-admin roles.

### Workflow View

Use the organisation workflow view when a support case requires operator context:

```bash
GET /internal/ops/organizations/{org_id}/workflow
```

The view shows:

- the existing read-only organisation operations detail,
- resolver-backed entitlement diagnostics,
- mismatch flags,
- recent webhook/backfill/monitoring context already surfaced by diagnostics,
- recent internal operator action history,
- the bounded manual controls currently allowed.

### Record Investigation Note

Use an operator note to document support reasoning without mutating entitlement truth:

```bash
POST /internal/ops/organizations/{org_id}/workflow/notes
{"reason":"Customer paid access investigation note with clear context"}
```

This writes an `internal_operator_actions` row with the actor, organisation, reason, diagnostics snapshot, and timestamp. It does not alter subscription, plan, quota, billing customer reference, or resolver output.

### Cancel Pending Invite

Use invite cancellation only for pending, unused invites that should no longer be accepted:

```bash
POST /internal/ops/invites/{invite_id}/cancel
{"reason":"Duplicate invite created during support review"}
```

This action is rejected for accepted, used, non-pending, or missing invites. Successful cancellation writes before/after invite state to `internal_operator_actions`.

### What Not To Do

Do not use the workflow layer for plan changes, subscription repair, billing-customer edits, quota overrides, AI entitlement changes, or scan-result changes. Use webhook reconciliation, diagnostics, and documented backfill procedures for billing truth issues. If the resolver does not explain access, investigate persisted truth rather than overriding frontend state.