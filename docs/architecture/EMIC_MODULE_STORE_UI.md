# EMIC Module Store UI

**Date:** 2026-09-08

---

## Information architecture

```text
Modules & Devices
└── Module Store
    ├── Discover          /config/modules-devices/store
    ├── Categories        /store/categories
    ├── Installed         /store/installed
    ├── Updates           /store/updates
    ├── Publishers        /store/publishers
    └── Security          /store/security
```

Module detail: `/store/{moduleId}`  
Install wizard: `/store/{moduleId}/install`

Legacy `/marketplace/security` redirects to `/store/security`.

---

## Components

| Component | Purpose |
|-----------|---------|
| `ModuleStoreShell` | Sub-nav + marketplace status banner |
| `DiscoverView` | Landing, search, category chips, card grid |
| `ModuleCard` | Trust/security badges, primary action |
| `ModuleDetailView` | Hero + tabbed sections |
| `InstallWizard` | 7-step flow using preflight API |
| `SecurityCenterView` | Aggregated security dashboard |
| `SafeMarkdown` / `SafeText` | XSS-safe publisher content |

---

## UX rules

- Primary action buttons reflect backend `primary_action` only
- Control modules show informational banner (not error styling)
- `RUNTIME_NOT_PERMITTED` is a security state, not a failure
- Secret config fields never redisplay values

---

## Styling

Uses EMIC config hub CSS (`config-hub.css`) with `.store-*` grid and wizard classes. Supports existing dark theme via CSS variables.
