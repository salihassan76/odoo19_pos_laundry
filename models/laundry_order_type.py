from odoo import models, fields, api


class LaundryOrderType(models.Model):
    _name = "laundry.order.type"
    _description = "Laundry Order Type"
    _order = "sequence, id"

    name = fields.Char(required=True)
    laundry_configuration_id = fields.Many2one(
        "laundry.configuration",
        string="Laundry Configuration",
        index=True,
        ondelete="cascade",
    )
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
        domain="[('laundry_configuration_ids', 'in', laundry_configuration_id)]",
        help="Leave empty to show all POS categories."
    )
    

    sequence_id = fields.Many2one(
        "ir.sequence",
        string="Number Sequence",
        readonly=True
    )

    
    is_hidden = fields.Boolean(
        string="Is Hidden from Screen",
        help="Check if this order type should not appear in the Home Screen",
        default=False
    )
    
    allow_pay = fields.Boolean(
        string="Allow Payments",
        help="Check if this order type can be paid.",
        default=True
    )

    allow_refund = fields.Boolean(
        string="Allow Refunds",
        help="Check if this order type can be refunded.",
        default=True
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

    @api.model
    def get_pos_allowed_category_ids(self, order_type_id, configuration_id):
        """Resolve the shop-scoped category IDs used by the POS frontend."""
        order_type = self.browse(order_type_id).exists()
        configuration = self.env["laundry.configuration"].browse(
            configuration_id
        ).exists()
        if (
            not order_type
            or not configuration
            or order_type.laundry_configuration_id != configuration
            or configuration.pos_config_id.company_id not in self.env.companies
        ):
            return []

        categories = order_type.pos_category_ids.filtered(
            lambda category: configuration in category.laundry_configuration_ids
        )
        if not categories:
            categories = self.env["pos.category"].search(
                [("laundry_configuration_ids", "in", [configuration.id])]
            )
        return categories.ids

    @api.model_create_multi
    def create(self, vals_list):
        default_configuration_id = self.env.context.get("default_laundry_configuration_id")
        for vals in vals_list:
            vals.setdefault("laundry_configuration_id", default_configuration_id)
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
