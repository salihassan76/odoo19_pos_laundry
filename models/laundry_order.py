from odoo import models, fields, api
from odoo.exceptions import ValidationError

class LaundryOrder(models.Model):
    _name = "laundry.order"
    _description = "Laundry Order"
    name = fields.Char(string="Order Reference", required=True, copy=False, readonly=True, default=lambda self: self.env['ir.sequence'].next_by_code('laundry.order'))
    customer_id = fields.Many2one("res.partner", string="Customer", required=True)
    order_line_ids = fields.One2many("laundry.order.line", "order_id", string="Order Lines")
    total_amount = fields.Float(string="Total Amount", compute="_compute_total_amount", store=True)
    order_type=fields.many2one("laundry.order.type",string="Order Type",required=True)
    status_id = fields.Many2one("laundry.order.status", string="Status", required=True, default=lambda self: self.env['laundry.order.status'].search([], limit=1).id)
    is_delivery = fields.Boolean(string="Is Delivery", related="order_type.is_delivery", store=True)
    delivery_team_id = fields.Many2one(
        "laundry.delivery.team", 
        string="Delivery Team", 
        domain="[('id', 'in', order_type.delivery_team_ids)]", 
        help="Select delivery team for this order. Only applicable if the order type is for delivery.")
    