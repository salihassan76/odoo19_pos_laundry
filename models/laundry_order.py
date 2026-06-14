from odoo import models, fields, api
from odoo.exceptions import ValidationError

class LaundryOrder(models.Model):
    _name = "laundry.order"
    _description = "Laundry Order"
    name = fields.Char(string="Order Reference", required=True, copy=False, readonly=True, default=lambda self: self.env['ir.sequence'].next_by_code('laundry.order'))
    customer_id = fields.Many2one("res.partner", string="Customer", required=True)
    order_line_ids = fields.One2many("laundry.order.line", "order_id", string="Order Lines")
    total_amount = fields.Float(string="Total Amount", compute="_compute_total_amount", store=True)
    order_type_id=fields.many2one("laundry.order.type",string="Order Type",required=True)
    payment_status_id = fields.Many2one("laundry.order.payment.status", string="Payment Status",readonly=True, required=True, default=lambda self: self.env['laundry.order.payment.status'].search([], limit=1).id)   
    status_id = fields.Many2one("laundry.order.status", string="Status",readonly=True, required=True, default=lambda self: self.env['laundry.order.status'].search([], limit=1).id)
    project_id = fields.Many2one("project.project", string="Project",readonly=True)
    order_datetime = fields.Datetime(string="Order Received",default=fields.Datetime.now,required=True,readonly=True,copy=False)
    order_date = fields.Date(string="Order Day",compute="_compute_order_datetime_parts",store=True,index=True)
    order_hour = fields.Integer(string="Order Hour",compute="_compute_order_datetime_parts",store=True,index=True)
    order_weekday = fields.Selection([
    ('0', 'Monday'),
    ('1', 'Tuesday'),
    ('2', 'Wednesday'),
    ('3', 'Thursday'),
    ('4', 'Friday'),
    ('5', 'Saturday'),
    ('6', 'Sunday'),
    ], string="Order Weekday", compute="_compute_order_datetime_parts", store=True)
    is_package = fields.Boolean(string="Package Order")
    package_rule_id = fields.Many2one('package.rule',string="Package")
    currency_id = fields.Many2one("res.currency",string="Currency",default=lambda self: self.env.company.currency_id,)
    pos_order_id = fields.Many2one("pos.order", string="POS Order", readonly=True, copy=False)
    
    
    
    @api.depends('order_datetime')
    def _compute_order_datetime_parts(self):
        for rec in self:
            if rec.order_datetime:
                dt = fields.Datetime.context_timestamp(rec, rec.order_datetime)
                rec.order_date = dt.date()
                rec.order_hour = dt.hour
                rec.order_weekday = str(dt.weekday())
            else:
                rec.order_date = False
                rec.order_hour = 0
                rec.order_weekday = False

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", "New") == "New":
                order_type = self.env["laundry.order.type"].browse(
                    vals.get("order_type_id")
                )

                vals["name"] = self.env["ir.sequence"].next_by_code(
                    f"laundry.order.{order_type.id}"
                ) or "New"

        return super().create(vals_list)
    
    