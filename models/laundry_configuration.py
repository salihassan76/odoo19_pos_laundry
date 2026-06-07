
from odoo import models, fields

class LaundryConfiguration(models.Model):
    _name = "laundry.configuration"
    _description = "Laundry Configuration"
    _rec_name = "name"

    name = fields.Char(
        default="Laundry Settings",
        required=True
    )

    package_pos_category_id = fields.Many2one(
        "pos.category",
        string="Package POS Category",
        required=True
    )

    _sql_constraints = [
        ('laundry_configuration_singleton',
         'unique(name)',
         'Only one Laundry Configuration record is allowed.')
    ]