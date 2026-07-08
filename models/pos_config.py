from odoo import api, models, fields, _
from odoo.exceptions import UserError


class PosConfig(models.Model):
    _inherit = "pos.config"

    enable_laundry_workflow = fields.Boolean(
        string="Enable Laundry Workflow",
        default=False,
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
    )

    partial_payment_id = fields.Many2one(
        "laundry.order.payment.status",
        string="Partial Paid Status",
    )

    paid_payment_id = fields.Many2one(
        "laundry.order.payment.status",
        string="Paid Status",
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
    def _load_pos_data_read(self, records, config):
        data = super()._load_pos_data_read(records, config)

        fields_to_load = [
            "enable_laundry_workflow",
            "is_project",
            "project_id",
            "unpaid_payment_id",
            "partial_payment_id",
            "paid_payment_id",
            "cancelled_payment_id",
            "refund_payment_id",
            "order_status_id",
            "direct_print",
            "show_receipt_preview",
        ]

        for record in data:
            pos_config = self.browse(record["id"])
            for field_name in fields_to_load:
                if field_name not in record:
                    value = pos_config[field_name]

                    if hasattr(value, "id"):
                        record[field_name] = value.id or False
                    else:
                        record[field_name] = value

        return data

    def get_laundry_configuration_status(self):
        self.ensure_one()

        items = []

        def add(name, ok):
            items.append({
                "name": name,
                "ok": bool(ok),
            })

        
        add(_("Default Order Status"), self.order_status_id)
        add(_("Unpaid Payment Status"), self.unpaid_payment_id)
        add(_("Paid Payment Status"), self.paid_payment_id)
        

        add(_("Laundry Order Types"), self.env["laundry.order.type"].search_count([
            ("active", "=", True),
            ("is_hidden", "=", False),
        ]))

        add(_("Laundry Order Statuses"), self.env["laundry.order.status"].search_count([]))
        add(_("Laundry Payment Statuses"), self.env["laundry.order.payment.status"].search_count([]))

        if self.is_project:
            add(_("Project"), self.project_id)

        return {
            "valid": all(item["ok"] for item in items),
            "items": items,
        }

    def check_laundry_configuration(self):
        for config in self:
            if not config.enable_laundry_workflow:
                continue

            status = config.get_laundry_configuration_status()

            if status["valid"]:
                continue

            missing = [
                item["name"]
                for item in status["items"]
                if not item["ok"]
            ]

            raise UserError(_(
                "Laundry POS configuration is incomplete for '%s'.\n\n"
                "Please configure:\n- %s"
            ) % (config.name, "\n- ".join(missing)))

        return True

    def _check_before_creating_new_session(self):
        res = super()._check_before_creating_new_session()
        self.check_laundry_configuration()
        return res