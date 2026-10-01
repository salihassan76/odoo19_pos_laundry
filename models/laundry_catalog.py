from odoo import fields, models


class PosCategory(models.Model):
    _inherit = "pos.category"

    laundry_configuration_ids = fields.Many2many(
        "laundry.configuration",
        "pos_category_laundry_configuration_rel",
        "category_id",
        "configuration_id",
        string="Laundry Configurations",
    )


class ProductTemplate(models.Model):
    _inherit = "product.template"

    laundry_configuration_ids = fields.Many2many(
        "laundry.configuration",
        "product_template_laundry_configuration_rel",
        "product_tmpl_id",
        "configuration_id",
        string="Laundry Configurations",
    )
