from odoo import models, fields, api


class LaundryOrderType(models.Model):
    _name = "laundry.order.type"
    _description = "Laundry Order Type"
    _order = "sequence, id"

    name = fields.Char(required=True)
    prefix = fields.Char(required=True)
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    icon_class = fields.Char(
        string="fa Icon",
        help="Example: fa-gift, fa-home, fa-truck, fa-bolt"
    )

    icon_preview = fields.Html(
        string="Icon",
        compute="_compute_icon_preview",
        sanitize=False
    )

    
    icon_color = fields.Selection([
    ("text-primary", "Blue"),
    ("text-danger", "Red"),
    ("text-info", "Cyan"),
    ("text-warning", "Yellow"),
    ("text-dark", "Black"),
    ("text-success", "Green"),
    ], default="text-primary")
   

    pos_category_ids = fields.Many2many(
        "pos.category",
        string="Allowed POS Categories",
        help="Leave empty to show all POS categories."
    )
    

    sequence_id = fields.Many2one(
        "ir.sequence",
        string="Number Sequence",
        readonly=True
    )

    is_delivery = fields.Boolean(
        string="Is Delivery",   
        help="Check if this order type is for delivery orders.",
        default=False)
    
    is_pickup = fields.Boolean(
        string="Is Pickup",
        help="Check if this order type is for pickup orders.",
        default=False
    )
    is_package_sale = fields.Boolean(
        string="Is Package Sale",
        help="Check if this order type is for Selling Packages.",
        default=False
    )
    is_hidden = fields.Boolean(
        string="Is Hidden from Screen",
        help="Check if this order type should not appear in the Home Screen",
        default=False
    )
    is_package_use = fields.Boolean(
        string="Is Package Usage",
        help="Check if this order type should be used for Package Usage",
        default=False
    )

    direct_sale = fields.Boolean(
        string="Direct Sale",
        help="After saving the laundry order, go directly to the payment screen.",
        default=False
        )
    
    billing_method = fields.Selection([
            ("customer", "Customer Payment"),
        ], default="customer", required=True)




    @api.depends("icon_class")
    def _compute_icon_preview(self):
        for rec in self:
            if rec.icon_class:
                rec.icon_preview = (
                    f'<i class="fa {rec.icon_class}" '
                    'style="font-size:20px;"></i>'
                )
            else:
                rec.icon_preview = ""

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)

        for record in records:
            seq = self.env["ir.sequence"].create({
                "name": f"{record.name} Orders",
                "code": f"laundry.order.{record.id}",
                "prefix": f"{record.prefix.upper()}-%(year)s-",
                "padding": 4,
                "number_next": 1,
                "number_increment": 1,
                "use_date_range": True,
            })

            record.sequence_id = seq.id

        return records