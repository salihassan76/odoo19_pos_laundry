from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class PackageRuleDetail(models.Model):
    _name = "package.rule.detail"
    _description = "Package Template Detail"

    _sql_constraints = [
    (
        "unique_category_per_package",
        "unique(package_rule_id, pos_category_id)",
        "You can only add one line per category in the same package.",
    ),
    ]

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

    @api.constrains("pos_category_id", "package_rule_id")
    def _check_unique_category_per_package(self):
        for rec in self:
            if not rec.package_rule_id or not rec.pos_category_id:
                continue

            duplicate = self.search([
                ("id", "!=", rec.id),
                ("package_rule_id", "=", rec.package_rule_id.id),
                ("pos_category_id", "=", rec.pos_category_id.id),
            ], limit=1)

            if duplicate:
                raise ValidationError(
                    _("You can only add one line per category in the same package. "
                      "Please add all allowed products under the same category line.")
                )