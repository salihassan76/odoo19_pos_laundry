from odoo import models, fields, api
from odoo.exceptions import ValidationError


class PackageRule(models.Model):
    _name = "package.rule"
    _description = "Package Template"

    name = fields.Char(string="Package Rule Name", required=True)
    duration = fields.Integer(string="Duration Days", default=30)
    discount_per = fields.Float(string="Discount %")
    extra_discount_per = fields.Float(string="Extra Discount %")
    valid = fields.Boolean(string="Valid", default=True)
    product_id = fields.Many2one("product.product",string="Package Product",readonly=True)
    product_created = fields.Boolean(default=False)
    detail_ids = fields.One2many("package.rule.detail","package_rule_id",string="Package Details")
    total_value = fields.Float(string="Total Actual Value",compute="_compute_total_value",store=True)
    package_amount = fields.Float(string="Package Amount",compute="_compute_package_amount",store=True)
    usage_count = fields.Integer(string="Usage Count",compute="_compute_usage_count")
    is_locked = fields.Boolean(string="Locked",compute="_compute_usage_count")
    active = fields.Boolean(default=True)


    @api.depends("detail_ids.value")
    def _compute_total_value(self):
        for rec in self:
            rec.total_value = sum(rec.detail_ids.mapped("value"))

    @api.depends("total_value", "discount_per")
    def _compute_package_amount(self):
        for rec in self:
            rec.package_amount = rec.total_value - (
                rec.total_value * rec.discount_per / 100
            )

    @api.onchange("discount_per", "total_value")
    def _onchange_discount_per(self):
        if self.total_value:
            self.package_amount = (
                self.total_value -
                (self.total_value * self.discount_per / 100)
            )
    @api.onchange("package_amount", "total_value")
    def _onchange_package_amount(self):
        if self.total_value:
            self.discount_per = (
                (self.total_value - self.package_amount)
                / self.total_value
            ) * 100
        
    def action_create_package_product(self):
        for rec in self:
            pos_config_id = self.env.context.get("pos_config_id")

            if not pos_config_id:
                raise ValidationError("Please open package rules from a POS configuration.")

            pos_config = self.env["pos.config"].browse(pos_config_id)

            if not pos_config.exists():
                raise ValidationError("POS configuration was not found.")

            if not pos_config.package_pos_category_id:
                raise ValidationError("Package POS Category is not configured.")

            if rec.product_id:
                raise ValidationError("Package product already exists.")

            product = self.env["product.template"].create({
                "name": rec.name,
                "type": "service",
                "available_in_pos": True,
                "list_price": rec.package_amount,
                "pos_categ_ids": [(6, 0, [pos_config.package_pos_category_id.id])],
            })

            rec.product_id = product.product_variant_id.id
            rec.product_created = True

    def action_update_package_product(self):
        for rec in self:

            if rec.product_id:
                rec.product_id.write({
                    "name": rec.name,
                    "list_price": rec.package_amount,
                })
    
    def _compute_usage_count(self):
        for rec in self:
            count = 0

            if rec.product_id:
                count = self.env["pos.order.line"].search_count([
                    ("product_id", "=", rec.product_id.id)
                ])

            rec.usage_count = count
            rec.is_locked = count > 0

    def write(self, vals):

        protected_fields = [
            "name",
            "duration",
            "discount_per",
            "detail_ids",
        ]

        for rec in self:
            if rec.is_locked:
                if any(field in vals for field in protected_fields):
                    raise ValidationError(
                        "This package has already been used and cannot be modified."
                    )

        res = super().write(vals)

        # If package is archived/unarchived, update POS product visibility
        if "active" in vals or "valid" in vals:
            for rec in self:
                if rec.product_id:
                    show_in_pos = rec.active and rec.valid

                    rec.product_id.write({
                        "active": rec.active,
                    })

                    rec.product_id.product_tmpl_id.write({
                        "available_in_pos": show_in_pos,
                        "active": rec.active,
                    })


        return res

    def unlink(self):

        for rec in self:

            if rec.is_locked:
                raise ValidationError(
                    "This package has already been used and cannot be deleted."
                )

        return super().unlink()

    def action_view_package_usage(self):

        self.ensure_one()

        return {
            "name": "Package Usage",
            "type": "ir.actions.act_window",
            "res_model": "pos.order.line",
            "view_mode": "list,form",
            "domain": [
                ("product_id", "=", self.product_id.id)
            ],
            "target": "current",
        }