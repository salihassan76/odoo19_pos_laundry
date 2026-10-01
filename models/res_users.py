from odoo import fields, models


class ResUsers(models.Model):
    _inherit = "res.users"

    laundry_pos_config_id = fields.Many2one(
        "pos.config",
        string="Current Laundry Shop",
        domain="[('enable_laundry_workflow', '=', True), ('active', '=', True)]",
        copy=False,
    )
