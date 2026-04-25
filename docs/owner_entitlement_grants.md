# Owner entitlement grants

Use owner entitlement grants only for controlled testing or internal evaluation. They are not a replacement for Stripe-backed subscriptions.

## What they do

- Temporarily elevate an organization or a specific user to `executive` or `enterprise`
- Default expiry:
  - `executive`: 14 days
  - `enterprise`: 30 days
- Optional scan quota override
- Full audit trail through internal operator actions

## When to use them

- Product QA
- Controlled customer testing
- Internal demos

Do not use owner grants as a standing substitute for paid subscriptions.

## Commands

Create a grant:

```bash
python manage_owner_entitlement_grants.py grant --email user@example.com --plan executive --reason "QA trial"
```

Create an organization-scoped enterprise grant with a quota override:

```bash
python manage_owner_entitlement_grants.py grant --org-id <ORG_UUID> --plan enterprise --scan-quota-override 5000 --reason "Internal evaluation"
```

Create an explicit indefinite complimentary/internal grant:

```bash
python manage_owner_entitlement_grants.py grant --email user@example.com --plan enterprise --grant-type complimentary --indefinite --reason "Complimentary internal access"
```

Revoke a grant:

```bash
python manage_owner_entitlement_grants.py revoke --grant-id <GRANT_UUID> --reason "Testing window ended"
```

List active grants:

```bash
python manage_owner_entitlement_grants.py list --active-only
```

## Revocation and expiry

- Expired grants stop applying automatically
- Revoked grants stop applying immediately
- Active Stripe subscriptions remain the normal paid source of truth for paying customers
