# Changelog

## 19.0.1.0.14 - 2026-09-26

- Enforce selected-shop domains and creation defaults across every Laundry
  workspace and menu action.
- Make Order Types, Order Statuses, and Payment Statuses owned by the selected
  shop's `laundry.configuration`.
- Add explicit Laundry-configuration assignments to POS Categories and
  Products for separate shop catalogs.
- Filter the POS frontend order types by the active POS configuration.
- Filter Package Rules by the selected shop.

## 19.0.1.0.13 - 2026-09-26

- Hide the Laundry section menus only on the shop-selection landing page.
- Show the standard Laundry menus immediately after a shop is selected.
- Preserve access to Odoo's main app launcher while the menus are hidden.
- Remove the landing-page menu state when navigating away from Laundry.

## 19.0.1.0.12 - 2026-09-26

- Replace the stored `res.users` Laundry shop field with a per-user system
  parameter.
- Fix module upgrade failure caused by Odoo reading `res_users` before the new
  database column could be created.
- Preserve the selected-shop menu behavior without changing the users table.

## 19.0.1.0.11 - 2026-09-26

- Restore the standard Odoo Laundry menu tree for desktop navigation.
- Add a **Workspace** menu that returns to the currently selected shop.
- Remember the current Laundry shop per user when it is selected.
- Scope Orders, Barcode, Barcode Logs, and Laundry Settings menu actions to
  the user's selected Laundry shop.
- Keep the main Laundry app action opening the shop-selection landing page.

## 19.0.1.0.10 - 2026-09-26

- Always show the shop-selection landing page when Laundry is opened from the
  main Odoo app menu, even when only one Laundry shop is enabled.
- Keep the selected shop in a separate workspace action so breadcrumbs return
  from operational pages to the correct workspace.
- Validate each selected shop's Laundry configuration on the workspace load.
- Show **Configuration Status: Complete/Incomplete** directly on the Laundry
  Settings button, matching the POS Settings validation result.
- Show the missing-item count and expose the missing setting names as a tooltip.
- Treat a missing Laundry configuration record as incomplete without creating
  records while merely viewing the landing page.

## 19.0.1.0.9 - 2026-09-26

- Preserve the selected Laundry shop while navigating through backend pages.
- Keep the Laundry workspace in Odoo's action history and breadcrumbs.
- Return to the selected shop's workspace when reopening the Laundry app.
- Clear the saved selection only when the user chooses **Change Shop** or the
  shop is no longer available for Laundry.
- Supply Odoo 19's required `views` definition when opening Laundry Settings
  from the workspace.

## 19.0.1.0.8 - 2026-09-26

- Add a Laundry app landing page listing only active POS shops with Laundry
  Workflow enabled.
- Add a shop-specific Laundry workspace for the existing operational and
  configuration pages.
- Hide the old direct submenu tree so users select a Laundry shop first.
- Scope Laundry orders and barcode logs to the selected shop.

## 19.0.1.0.7 - 2026-09-26

- Explicitly reactivate the inherited Laundry POS settings view so databases
  that installed the earlier disabled-view test display the workflow checkbox.
- Keep the obsolete standalone Laundry-only `pos.config` form inactive.

## 19.0.1.0.6 - 2026-09-26

- Restore Odoo's standard **+ New Shop** form by deactivating the obsolete
  standalone Laundry-only `pos.config` form.
- Keep **Enable Laundry Workflow** in the Point of Sale settings for the
  currently selected shop.
- Preserve the shop-specific Laundry configuration when the workflow is
  disabled.
- Standardize the module version for Odoo 19.

## 19.0.1.0.5

- Move operational Laundry settings from `pos.config` to the shop-specific
  `laundry.configuration` model.
- Keep POS frontend compatibility through flattened configuration payloads.
