from odoo import models, fields, api

class LaundryOrderPayStatus(models.Model):
    _name = "laundry.order.payment.status"
    _description = "Laundry Order Payment Status"
    _order = "id"

    name = fields.Char(required=True)
    laundry_configuration_id = fields.Many2one(
        "laundry.configuration",
        string="Laundry Configuration",
        index=True,
        ondelete="cascade",
    )
    active = fields.Boolean(default=True)
    sequence = fields.Integer(default=10)

    @api.model_create_multi
    def create(self, vals_list):
        configuration_id = self.env.context.get("default_laundry_configuration_id")
        for vals in vals_list:
            if configuration_id:
                vals.setdefault("laundry_configuration_id", configuration_id)
        return super().create(vals_list)
