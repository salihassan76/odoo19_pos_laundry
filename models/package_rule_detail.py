from odoo import models, fields, api


class PackageRuleDetail(models.Model):
    _name = "package.rule.detail"
    _description = "Package Template Detail"

    package_rule_id = fields.Many2one(
        "package.rule",
        string="Package Rule",
        required=True,
        ondelete="cascade"
    )

    pos_category_id = fields.Many2one(
        "pos.category",
        string="Service Type",
        required=True
    )

    product_ids = fields.Many2many(
        "product.product",
        string="Allowed Products",
        required=True,
        domain="[('pos_categ_ids', 'in', pos_category_id)]"
    )

    qty = fields.Float(string="Allowed Qty", required=True)

    value = fields.Float(
        string="Actual Value",
        compute="_compute_value",
        store=True
    )


    @api.depends("product_ids", "product_ids.lst_price", "qty")
    def _compute_value(self):
        for rec in self:
            total_product_price = sum(rec.product_ids.mapped("lst_price"))
            rec.value = total_product_price * rec.qty