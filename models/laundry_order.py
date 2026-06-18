from odoo import models, fields, api
from odoo.exceptions import ValidationError

class LaundryOrder(models.Model):
    _name = "laundry.order"
    _description = "Laundry Order"
    name = fields.Char(string="Order Reference", required=True, copy=False, readonly=True, default=lambda self: self.env['ir.sequence'].next_by_code('laundry.order'))
    customer_id = fields.Many2one("res.partner", string="Customer", required=True)
    order_line_ids = fields.One2many("laundry.order.line", "order_id", string="Order Lines")
    total_amount = fields.Float(string="Total Amount", compute="_compute_total_amount", store=True)
    order_type_id=fields.Many2one("laundry.order.type",string="Order Type",required=True)
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
    is_package= fields.Boolean(string="Package Usage")
    package_rule_id = fields.Many2one('package.rule',string="Package")
    currency_id = fields.Many2one("res.currency",string="Currency",default=lambda self: self.env.company.currency_id,)
    pos_order_id = fields.Many2one("pos.order", string="POS Order", readonly=True, copy=False)
    order_note = fields.Text(string="Order Note")
    order_internal_note = fields.Text(string="Internal Note")
    
    
    
    
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
    
    @api.depends("order_line_ids.price_subtotal")
    def _compute_total_amount(self):
        for order in self:
            order.total_amount = sum(order.order_line_ids.mapped("price_subtotal"))

    @api.model
    def process_pos_laundry_order(self, data):
        if not data.get("partner_id"):
            raise ValidationError("Customer is required.")

        if not data.get("laundry_order_type_id"):
            raise ValidationError("Laundry order type is required.")

        laundry_order = self._create_laundry_order(data)

        partner_package = self._create_partner_package(
            data,
            laundry_order,
        )

        pos_order = self._create_pos_order(data)

        self._link_laundry_order(
            laundry_order,
            pos_order,
        )

        self._link_partner_package(
            partner_package,
            pos_order,
        )

        return {
            "laundry_order_id": laundry_order.id,
            "partner_package_id": partner_package.id if partner_package else False,
            "pos_order_id": pos_order.id if pos_order else False,
        }
    
    def _create_laundry_order(self, data):
        return self.create({
            "customer_id": data.get("partner_id"),
            "order_type_id": data.get("laundry_order_type_id"),
            "package_rule_id": data.get("package_rule_id") or False,
            "is_package": data.get("is_package_sell", False),
            "notes": data.get("notes") or "",
        })
    
    def _create_partner_package(self, data, laundry_order):
        """
        Create a partner package when selling a package from POS.
        Returns the created partner.package record or False.
        """

        if not data.get("is_package_sale"):
            return False

        package_rule_id = data.get("package_rule_id")
        if not package_rule_id:
            raise ValidationError("Package is required for package sale.")

        return self.env["partner.package"].create({
            "partner_id": data.get("partner_id"),
            "package_rule_id": package_rule_id,
            "laundry_order_id": laundry_order.id,
        })
    def _create_pos_order(self, data):
        pos_result = self.env["pos.order"].create_from_ui([data])

        if not pos_result:
            return False

        pos_order_id = pos_result[0].get("id")
        if not pos_order_id:
            return False

        return self.env["pos.order"].browse(pos_order_id)
    
    def _link_laundry_order(self, laundry_order, pos_order):
        """
        Link the Laundry Order with the created POS Order.
        """

        if not laundry_order or not pos_order:
            return

        laundry_order.write({
            "pos_order_id": pos_order.id,
        })

    def _link_partner_package(self, partner_package, pos_order):
        """
        Link the Partner Package with the created POS Order.
        """

        if not partner_package or not pos_order:
            return

        partner_package.write({
            "pos_order_id": pos_order.id,
        })