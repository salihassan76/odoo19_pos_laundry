from odoo import models, fields


class PartnerPackageUsageLine(models.Model):
    _name = "partner.package.usage.line"
    _description = "Package Usage History"
    _order = "id desc"

    partner_package_id = fields.Many2one(
        "partner.package",
        required=True,
        ondelete="cascade",
    )

    laundry_order_id = fields.Many2one(
        "laundry.order",
        required=True,
        ondelete="restrict",
    )

    product_id = fields.Many2one(
        "product.product",
        required=True,
    )

    qty = fields.Float(
        required=True,
    )

    date = fields.Datetime(
        default=fields.Datetime.now,
        readonly=True,
    )
    package_rule_detail_id = fields.Many2one(
        "package.rule.detail",
        string="Package Detail",
        required=True,
    )