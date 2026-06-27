from odoo import models, fields, api


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