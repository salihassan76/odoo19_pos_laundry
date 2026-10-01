from odoo import _, api, fields, models
from odoo.exceptions import UserError


class PosConfig(models.Model):
    _inherit = "pos.config"

    enable_laundry_workflow = fields.Boolean(string="Enable Laundry Workflow", default=False)
    laundry_configuration_ids = fields.One2many(
        "laundry.configuration", "pos_config_id", string="Laundry Configuration"
    )

    def _get_laundry_configuration(self, create=False):
        self.ensure_one()
        configuration = self.laundry_configuration_ids[:1]
        if not configuration and create:
            configuration = self.env["laundry.configuration"].create(
                {"name": self.display_name, "pos_config_id": self.id}
            )
        return configuration

    @api.model
    def _load_pos_data_read(self, records, config):
        data = super()._load_pos_data_read(records, config)
        for values in data:
            pos_config = self.browse(values["id"])
            laundry_config = pos_config._get_laundry_configuration()
            if laundry_config:
                values.update(laundry_config.as_pos_config_values())
            else:
                values["laundry_configuration_id"] = False
        return data

    def get_laundry_configuration_status(self):
        self.ensure_one()
        configuration = self._get_laundry_configuration()
        if not configuration:
            return {
                "valid": False,
                "items": [{"name": _("Laundry Configuration"), "ok": False}],
            }
        return configuration.get_configuration_status()

    def check_laundry_configuration(self):
        for pos_config in self:
            if not pos_config.enable_laundry_workflow:
                continue
            configuration = pos_config._get_laundry_configuration()
            if not configuration:
                raise UserError(
                    _("Laundry POS configuration is missing for '%s'.")
                    % pos_config.display_name
                )
            configuration.check_configuration()
        return True

    def action_open_laundry_configuration(self):
        self.ensure_one()
        configuration = self._get_laundry_configuration(create=True)
        return {
            "type": "ir.actions.act_window",
            "name": _("Laundry Configuration"),
            "res_model": "laundry.configuration",
            "view_mode": "form",
            "views": [(False, "form")],
            "res_id": configuration.id,
            "target": "current",
        }

    @api.model
    def get_laundry_landing_data(self):
        """Return shops and workspace entries available to the current user."""
        shops = self.search(
            [
                ("active", "=", True),
                ("enable_laundry_workflow", "=", True),
                ("company_id", "in", self.env.companies.ids),
            ],
            order="name, id",
        )
        workspace_groups = [
            {
                "name": _("Operations"),
                "items": [
                    {"key": "orders", "name": _("Laundry Orders"), "icon": "fa-list-alt"},
                    {"key": "barcode", "name": _("Enter Barcode"), "icon": "fa-barcode"},
                    {"key": "scan_logs", "name": _("Barcode Scan Logs"), "icon": "fa-history"},
                ],
            },
            {
                "name": _("Configuration"),
                "items": [
                    {"key": "settings", "name": _("Laundry Settings"), "icon": "fa-cogs"},
                    {"key": "order_types", "name": _("Order Types"), "icon": "fa-random"},
                    {"key": "order_statuses", "name": _("Order Status"), "icon": "fa-tasks"},
                    {"key": "payment_statuses", "name": _("Payment Status"), "icon": "fa-credit-card"},
                    {"key": "categories", "name": _("POS Categories"), "icon": "fa-tags"},
                    {"key": "products", "name": _("Products"), "icon": "fa-cubes"},
                ],
            },
        ]
        if self.env.ref("pos_laundry_packages.action_laundry_package_rule", raise_if_not_found=False):
            workspace_groups.append(
                {
                    "name": _("Packages"),
                    "items": [
                        {"key": "packages", "name": _("Package Rules"), "icon": "fa-gift"},
                    ],
                }
            )
        shop_values = []
        for shop in shops:
            configuration = shop._get_laundry_configuration()
            if configuration:
                configuration_status = configuration.get_configuration_status()
                missing_items = [
                    item["name"]
                    for item in configuration_status["items"]
                    if not item["ok"]
                ]
                is_complete = configuration_status["valid"]
            else:
                missing_items = [_('Laundry Configuration')]
                is_complete = False
            shop_values.append(
                {
                    "id": shop.id,
                    "name": shop.display_name,
                    "company": shop.company_id.display_name,
                    "configuration_id": configuration.id or False,
                    "configuration_complete": is_complete,
                    "configuration_status": _("Complete") if is_complete else _("Incomplete"),
                    "configuration_missing_count": len(missing_items),
                    "configuration_missing_items": missing_items,
                }
            )
        return {
            "shops": shop_values,
            "workspace_groups": workspace_groups,
        }

    @api.model
    def action_open_laundry_workspace_item(self, pos_config_id, item_key):
        shop = self.browse(pos_config_id).exists()
        if (
            not shop
            or not shop.active
            or not shop.enable_laundry_workflow
            or shop.company_id not in self.env.companies
        ):
            raise UserError(_("This Laundry shop is not available."))

        if item_key == "settings":
            return shop.action_open_laundry_configuration()

        configuration = shop._get_laundry_configuration()
        if not configuration and item_key not in {"orders", "barcode", "scan_logs"}:
            raise UserError(_("Open Laundry Settings first to create this shop's Laundry configuration."))

        action_map = {
            "orders": "pos_laundry.action_laundry_order",
            "barcode": "pos_laundry.action_laundry_barcode_entry_wizard",
            "scan_logs": "pos_laundry.action_laundry_order_scan_log",
            "order_types": "pos_laundry.action_laundry_order_type",
            "order_statuses": "pos_laundry.action_laundry_order_status",
            "payment_statuses": "pos_laundry.action_laundry_order_payment_status",
            "categories": "pos_laundry.action_laundry_pos_categories",
            "products": "pos_laundry.action_laundry_products",
            "packages": "pos_laundry_packages.action_laundry_package_rule",
        }
        xmlid = action_map.get(item_key)
        action_record = self.env.ref(xmlid, raise_if_not_found=False) if xmlid else False
        if not action_record:
            raise UserError(_("The requested Laundry page is not available."))

        action = action_record.read()[0]
        action["name"] = _("%(shop)s - %(page)s", shop=shop.display_name, page=action["name"])
        action["target"] = "current"
        context = dict(self.env.context)
        context.update(
            {
                "pos_config_id": shop.id,
                "default_pos_config_id": shop.id,
                "laundry_pos_config_id": shop.id,
                "laundry_configuration_id": configuration.id if configuration else False,
                "default_laundry_configuration_id": configuration.id if configuration else False,
            }
        )
        action["context"] = context
        if item_key == "orders":
            action["domain"] = [("pos_config_id", "=", shop.id)]
        elif item_key == "scan_logs":
            action["domain"] = [
                "|",
                ("origin_pos_config_id", "=", shop.id),
                ("scanning_pos_config_id", "=", shop.id),
            ]
        elif item_key in {"order_types", "order_statuses", "payment_statuses"}:
            action["domain"] = [("laundry_configuration_id", "=", configuration.id)]
        elif item_key in {"categories", "products"}:
            action["domain"] = [("laundry_configuration_ids", "in", configuration.id)]
            context["default_laundry_configuration_ids"] = [(6, 0, [configuration.id])]
            action["context"] = context
        elif item_key == "packages":
            action["domain"] = [("laundry_configuration_ids", "in", configuration.id)]
            context["default_laundry_configuration_ids"] = [(6, 0, [configuration.id])]
            action["context"] = context
        return action

    @api.model
    def select_laundry_shop(self, pos_config_id):
        shop = self.browse(pos_config_id).exists()
        if (
            not shop
            or not shop.active
            or not shop.enable_laundry_workflow
            or shop.company_id not in self.env.companies
        ):
            raise UserError(_("This Laundry shop is not available."))
        self.env["ir.config_parameter"].sudo().set_param(
            "pos_laundry.selected_shop.%s" % self.env.user.id,
            shop.id,
        )
        return True

    @api.model
    def _get_selected_laundry_shop(self):
        selected_shop_id = self.env["ir.config_parameter"].sudo().get_param(
            "pos_laundry.selected_shop.%s" % self.env.user.id
        )
        try:
            selected_shop_id = int(selected_shop_id) if selected_shop_id else False
        except (TypeError, ValueError):
            selected_shop_id = False
        shop = self.browse(selected_shop_id).exists() if selected_shop_id else self.browse()
        if (
            not shop
            or not shop.active
            or not shop.enable_laundry_workflow
            or shop.company_id not in self.env.companies
        ):
            raise UserError(_("Select a Laundry shop from the Laundry landing page first."))
        return shop

    @api.model
    def action_open_selected_laundry_workspace(self):
        shop = self._get_selected_laundry_shop()
        return {
            "type": "ir.actions.client",
            "name": shop.display_name,
            "tag": "pos_laundry.landing",
            "params": {"pos_config_id": shop.id},
            "target": "current",
        }

    @api.model
    def action_open_selected_laundry_item(self, item_key):
        shop = self._get_selected_laundry_shop()
        return self.action_open_laundry_workspace_item(shop.id, item_key)

    def _check_before_creating_new_session(self):
        result = super()._check_before_creating_new_session()
        self.check_laundry_configuration()
        return result
