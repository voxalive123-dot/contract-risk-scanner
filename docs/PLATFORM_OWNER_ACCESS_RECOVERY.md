# Platform Owner Access Recovery

Use this runbook only for the verified VoxaRisk platform owner identity:

```bash
python repair_platform_owner.py --email admin.dashboard@voxarisk.com
```

In the Render backend shell, run the command from the deployed backend root after database migrations are current. The script uses the production `DATABASE_URL` already present in the Render environment.

## What It Repairs

- Ensures the owner user exists for `admin.dashboard@voxarisk.com`.
- Ensures the canonical VoxaRisk Platform organisation exists or reuses the existing canonical/legacy platform organisation.
- Sets the owner user to active and clears `disabled`, `suspended`, `closure_requested`, and `soft_deleted` account states.
- Ensures exactly one active owner membership for the owner account on the platform organisation.
- Ensures the user has a valid password hash format.
- Issues a password setup link using the existing token system when no direct password is provided.
- Prints diagnostics before and after repair.

## What It Must Never Do

- It must never print password hashes or plaintext passwords.
- It must never create a public admin bypass.
- It must never grant owner bypass to testers, managers, assistants, customers, or invited organisation users.
- It must never mark tester access as paid revenue.
- It must never hard-delete users, organisations, billing records, scan records, or audit records.

## Optional Password Recovery

To set a password from the shell without exposing it in command history:

```bash
python repair_platform_owner.py --email admin.dashboard@voxarisk.com --prompt-password
```

Prefer the setup link flow unless an operator explicitly needs to set the password during a controlled recovery window.

## Expected Result

The command should finish with `platform_owner_repair_ready` and show:

- `is_active: true`
- `account_status: active`
- `membership_status: active`
- `membership_role: owner`
- `signin_url: /signin?next=/internal/command-centre`

After signing in, the owner should be able to access `/dashboard`, `/account`, `/internal/command-centre`, legacy `/internal/operations`, and all protected owner/internal APIs without requiring a paid subscription.
