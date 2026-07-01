from odoo import models, fields, api, _
from odoo.exceptions import UserError


class LaundryConfiguration(models.Model):
    _name = "laundry.configuration"
    _description = "Laundry Configuration"
    _rec_name = "name"

    _sql_constraints = [
        (
            "unique_pos_config",
            "unique(pos_config_id)",
            "Each POS can only have one Laundry Configuration.",
        ),
    ]

    name = fields.Char(
        string="Configuration Name",
        default="Laundry Configuration",
        readonly=True,
    )

    pos_config_id = fields.Many2one(
        "pos.config",
        string="Point of Sale",
        required=True,
        ondelete="cascade",
    )

    package_pos_category_id = fields.Many2one(
        "pos.category",
        string="Package POS Category",
    )

    is_project = fields.Boolean(
        string="Enable Project",
        default=False,
    )

    project_id = fields.Many2one(
        "project.project",
        string="Project",
    )

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

    direct_print = fields.Boolean(
        string="Print After Save/Validate",
        default=False,
    )

    show_receipt_preview = fields.Boolean(
        string="Show Receipt Preview",
        default=True,
    )

    @api.model
    def _get_pos_config_from_context(self):
        pos_config_id = (
            self.env.context.get("default_pos_config_id")
            or self.env.context.get("pos_config_id")
        )

        if pos_config_id:
            return self.env["pos.config"].browse(pos_config_id)

        return self.env["pos.config"]

    @api.model
    def action_open_laundry_configuration(self):
        pos_config = self._get_pos_config_from_context()

        if not pos_config:
            raise UserError(_("Please select a Point of Sale first."))

        config = self.search([
            ("pos_config_id", "=", pos_config.id),
        ], limit=1)

        if not config:
            config = self.create({
                "pos_config_id": pos_config.id,
            })

        return {
            "type": "ir.actions.act_window",
            "name": _("Laundry Settings"),
            "res_model": "laundry.configuration",
            "view_mode": "form",
            "res_id": config.id,
            "target": "current",
        }

    @api.model
    def get_configuration_status(self, pos_config=False):
        if not pos_config:
            pos_config = self._get_pos_config_from_context()

        config = False
        if pos_config:
            config = self.search([
                ("pos_config_id", "=", pos_config.id),
            ], limit=1)

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

        return {
            "valid": all(item["ok"] for item in items),
            "items": items,
        }

    def check_configuration(self):
        self.ensure_one()

        status = self.get_configuration_status(self.pos_config_id)

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