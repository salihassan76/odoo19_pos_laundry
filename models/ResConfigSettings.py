from odoo import models, fields

class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    laundry_package_category_id = fields.Many2one(
        "pos.category",
        string="Package POS Category",
        config_parameter="pos_laundry.laundry_package_category_id"
    )