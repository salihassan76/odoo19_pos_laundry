from odoo import models, fields, api

class LaundryOrderPayStatus(models.Model):
    _name = "laundry.order.payment.status"
    _description = "Laundry Order Payment Status"
    _order = "id"

    name = fields.Char(required=True)
    active = fields.Boolean(default=True)