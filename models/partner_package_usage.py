from odoo import models, fields, api


class PartnerPackageUsage(models.Model):
    _name = "partner.package.usage"
    _description = "Partner Package Balance"

    partner_package_id = fields.Many2one(
        "partner.package",
        required=True,
        ondelete="cascade",
    )

    package_rule_detail_id = fields.Many2one(
        "package.rule.detail",
        required=True,
    )

    product_id = fields.Many2one(
        "product.product",
        required=True,
    )

    allowed_qty = fields.Float(
        string="Allowed Qty",
        required=True,
    )

    used_qty = fields.Float(
        string="Used Qty",
        compute="_compute_used_remaining_qty",
        store=True,
    )

    remaining_qty = fields.Float(
        string="Remaining Qty",
        compute="_compute_used_remaining_qty",
        store=True,
    )

    @api.depends(
        "allowed_qty",
        "partner_package_id.usage_history_ids.product_id",
        "partner_package_id.usage_history_ids.qty",
    )
    def _compute_used_remaining_qty(self):
        for rec in self:
            used = sum(
                rec.partner_package_id.usage_history_ids.filtered(
                    lambda line: line.product_id == rec.product_id
                ).mapped("qty")
            )

            rec.used_qty = used
            rec.remaining_qty = rec.allowed_qty - used