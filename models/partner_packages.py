from odoo import models, fields, api
from dateutil.relativedelta import relativedelta
from datetime import timedelta


class PartnerPackage(models.Model):
    _name = "partner.package"
    _description = "Customer Package"
    _order = "id desc"

    name = fields.Char(
        string="Package No.",
        readonly=True,
        copy=False,
        default=lambda self: self.env["ir.sequence"].next_by_code("partner.package") or "New",
    )

    partner_id = fields.Many2one(
        "res.partner",
        required=True,
    )

    package_rule_id = fields.Many2one(
        "package.rule",
        required=True,
    )

    laundry_order_id = fields.Many2one(
        "laundry.order",
        string="Purchase Order",
        required=True,
        readonly=True,
        ondelete="restrict",
    )

    pos_order_id = fields.Many2one(
        "pos.order",
        string="POS Order",
        readonly=True,
        copy=False,
    )

    start_date = fields.Date(
        default=fields.Date.context_today,
        required=True,
    )

    end_date = fields.Date(
        compute="_compute_end_date",
        store=True,
    )

    state = fields.Selection(
        [
            ("active", "Active"),
            ("expired", "Expired"),
        ],
        compute="_compute_state",
        store=True,
    )

    usage_ids = fields.One2many(
        "partner.package.usage",
        "partner_package_id",
        string="Package Balance",
    )

    usage_history_ids = fields.One2many(
        "partner.package.usage.line",
        "partner_package_id",
        string="Usage History",
    )

    @api.depends("start_date", "package_rule_id.duration")
    def _compute_end_date(self):
        for rec in self:
            if rec.start_date and rec.package_rule_id and rec.package_rule_id.duration:
                rec.end_date = rec.start_date + timedelta(
                    days=rec.package_rule_id.duration
                )
            else:
                rec.end_date = False

    

    @api.depends("end_date")
    def _compute_state(self):
        today = fields.Date.today()
        for rec in self:
            if rec.end_date and rec.end_date < today:
                rec.state = "expired"
            else:
                rec.state = "active"
    
    @api.model
    def get_active_packages_for_pos(self, partner_id):
        packages = self.search([
            ("partner_id", "=", partner_id),
            ("state", "=", "active"),
        ])

        result = []

        for package in packages:
            allowed_product_ids = []
            allowed_category_ids = []
            details = []

            for detail in package.package_rule_id.detail_ids:
                product_ids = detail.product_ids.ids
                category = detail.pos_category_id

                allowed_product_ids.extend(product_ids)

                if category:
                    allowed_category_ids.append(category.id)

                usage_lines = package.usage_history_ids.filtered(
                    lambda line: line.package_rule_detail_id.id == detail.id
                )

                used_qty = sum(usage_lines.mapped("qty"))
                remaining_qty = detail.qty - used_qty


                details.append({
                    "category_id": category.id if category else False,
                    "category_name": category.name if category else "",
                    "product_ids": product_ids,
                    "allowed_qty": detail.qty,
                    "used_qty": used_qty,
                    "remaining_qty": remaining_qty if remaining_qty > 0 else 0,
                })

            result.append({
                "id": package.id,
                "name": package.name,
                "package_rule_id": [
                    package.package_rule_id.id,
                    package.package_rule_id.name,
                ],
                "package_rule_name": package.package_rule_id.name,
                "start_date": package.start_date,
                "end_date": package.end_date,
                "state": package.state,
                "allowed_product_ids": list(set(allowed_product_ids)),
                "allowed_category_ids": list(set(allowed_category_ids)),
                "details": details,
            })

        return result