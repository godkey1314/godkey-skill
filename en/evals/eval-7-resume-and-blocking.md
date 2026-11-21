# eval-7: Cross-Session Resume & Blocking Invariants

## Preconditions

- A `full`-mode Git repository with an unfinished package in `02-active/2026-11-20_order-coupons/` (`01-plan.md` specifies remaining points-redemption integration, `02-progress.md` records first half done);
- Intentional conflict: `04-feature-design/orders.md` states "canceling an order refunds the coupon automatically", whereas current source code voids the coupon permanently.

## User Prompts (Two Clean Sessions)

- **Session A (Cross-Session Resume)**: > Finish the remaining part of the order coupons feature.
- **Session B (Blueprint vs. Code Conflict)**: > Also tweak the coupon status handling when an order is canceled.

## Expected Behavior Checklist

- [ ] **Session A**: Runs `godkey_gate.py audit`, detects `02-active/2026-11-20_order-coupons`, **reads existing `01-plan.md` and `02-progress.md`**, and continues inside that exact package (never creates a duplicate package)
- [ ] **Session B**: Detects the mismatch between `04-feature-design/orders.md` and current source code, **stops immediately under Blocking Invariants, and asks the user which behavior is authoritative** before editing any code

## Failure Alarms (Instant Fail)

- ❌ Ignores the active package in `02-active/` and creates a second duplicate package
- ❌ Silently picks either refund or void without asking the user to resolve the design conflict
