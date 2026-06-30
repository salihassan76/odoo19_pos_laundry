from odoo import models, fields, api, _
from odoo.exceptions import UserError


class LaundryConfiguration(models.Model):
    _name = "laundry.configuration"
    _description = "Laundry Configuration"
    _rec_name = "name"
    name = fields.Char(string="Configuration Name", default="Laundry Configuration", readonly=True)
    package_pos_category_id = fields.Many2one("pos.category",string="Package POS Category")
    is_project = fields.Boolean(string="Enable Project",default=False)
    project_id = fields.Many2one("project.project",string="Project")
    unpaid_payment_id = fields.Many2one(
    "laundry.order.payment.status",
    string="Unpaid Status",
    required=True,
    )

    partial_payment_id = fields.Many2one(
        "laundry.order.payment.status",
        string="Partial Paid Status",
    )

    paid_payment_id = fields.Many2one(
        "laundry.order.payment.status",
        string="Paid Status",
        required=True,
    )

    package_payment_id = fields.Many2one(
        "laundry.order.payment.status",
        string="Package Payment Status",
        required=True,
    )

    cancelled_payment_id = fields.Many2one(
        "laundry.order.payment.status",
        string="Cancelled Status",
    )

    refund_payment_id = fields.Many2one(
        "laundry.order.payment.status",
        string="Refund Status",
    )

    order_status_id = fields.Many2one(
        "laundry.order.status",
        string="Default Order Status",
    )


    direct_print=fields.Boolean(string="Print After Save/Validate",default=False)
    show_receipt_preview=fields.Boolean(string="Show Receipt Preview",default=True)

    @api.model_create_multi
    def create(self, vals_list):
        existing = self.search([], limit=1)
        if existing:
            return existing
        return super().create(vals_list)

    @api.model
    def action_open_laundry_configuration(self):
        config = self.search([], limit=1)

        if not config:
            config = self.create({})

        return {
            "type": "ir.actions.act_window",
            "name": "Laundry Settings",
            "res_model": "laundry.configuration",
            "view_mode": "form",
            "res_id": config.id,
            "target": "current",
        }
    def get_configuration_status(self):
        config = self.search([], limit=1)

        items = []

        def add(name, ok):
            items.append({
                "name": name,
                "ok": bool(ok),
            })

        add(_("Laundry Configuration"), bool(config))
        add(_("Package POS Category"), bool(config and config.package_pos_category_id))
        add(_("Default Order Status"), bool(config and config.order_status_id))
        add(_("Unpaid Payment Status"), bool(config and config.unpaid_payment_id))
        add(_("Paid Payment Status"), bool(config and config.paid_payment_id))
        add(_("Package Payment Status"), bool(config and config.package_payment_id))
        add(_("Laundry Order Types"), bool(self.env["laundry.order.type"].search_count([
            ("active", "=", True),
            ("is_hidden", "=", False),
        ])))
        add(_("Laundry Order Statuses"), bool(self.env["laundry.order.status"].search_count([])))
        add(_("Laundry Payment Statuses"), bool(self.env["laundry.order.payment.status"].search_count([])))

        if config and config.is_project:
            add(_("Project"), bool(config.project_id))

        valid = all(item["ok"] for item in items)

        return {
            "valid": valid,
            "items": items,
        }


    def check_configuration(self):
        status = self.get_configuration_status()

        if status["valid"]:
            return True

        missing = [
            item["name"]
            for item in status["items"]
            if not item["ok"]
        ]

        raise UserError(_(
            "Laundry POS configuration is incomplete.\n\n"
            "Please configure:\n- %s"
        ) % "\n- ".join(missing))