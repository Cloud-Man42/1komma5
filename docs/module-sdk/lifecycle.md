# Lifecycle

States: **Available** (staged), **Installed** (disk + DB), **Enabled** (per-site via existing Step 4 flow).

Package states: `available | installed | update_available | disabled | broken | quarantined | removing`.

Install ≠ enable. After install the module appears in the registry; site enable remains unchanged until configured per site.
