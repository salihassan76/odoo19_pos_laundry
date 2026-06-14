from odoo import models, fields, api
from odoo.exceptions import ValidationError

class LaundryOrderLines(models.Model):
    _name = "laundry.order.line"
    _description = "Laundry Order Line"

    order_id = fields.Many2one("laundry.order", string="Order", required=True, ondelete="cascade")
    product_id = fields.Many2one("product.product", string="Product", required=True)
    product_uom_id = fields.Many2one("uom.uom", string="Unit of Measure", required=True)
    category_id = fields.Many2one("product.category", string="Category", related="product_id.categ_id", store=True, readonly=True)
    quantity = fields.Float(string="Quantity", default=1.0)
    price_unit = fields.Float(string="Unit Price", required=True)
    price_subtotal = fields.Float(string="Subtotal", compute="_compute_price_subtotal", store=True)
    task_id = fields.Many2one("project.task",string="Task",readonly=True,copy=False,)

    @api.depends('quantity', 'price_unit')
    def _compute_price_subtotal(self):
        for line in self:
            line.price_subtotal = line.quantity * line.price_unit