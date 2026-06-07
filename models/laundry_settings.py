from odoo import models, fields


class LaundrySettings(models.TransientModel):
    _inherit = "res.config.settings"

    laundry_package_pos_category_id = fields.Many2one(
        "pos.category",
        string="Package POS Category",
        config_parameter="pos_laundry.package_pos_category_id"
    )