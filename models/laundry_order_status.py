from odoo import models, fields, api

class LaundryOrderStatus(models.Model):
    _name = "laundry.order.status"
    _description = "Laundry Order Status"
    _order = "id"

    name = fields.Char(required=True)
    active = fields.Boolean(default=True)