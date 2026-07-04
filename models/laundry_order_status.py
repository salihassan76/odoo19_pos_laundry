from odoo import models, fields, api

class LaundryOrderStatus(models.Model):
    _name = "laundry.order.status"
    _description = "Laundry Order Status"
    _order = "sequence,id"

    name = fields.Char(required=True)
    active = fields.Boolean(default=True)
    sequence = fields.Integer(default=10)
    show_on_home = fields.Boolean(
        string="Show on POS Home",
        default=True,
        help="Display this status as a section on the POS customer home screen."
    )