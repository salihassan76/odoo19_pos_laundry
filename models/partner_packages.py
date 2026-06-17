from odoo import models, fields, api
from dateutil.relativedelta import relativedelta


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
            if rec.start_date:
                rec.end_date = rec.start_date + relativedelta(
                    months=rec.package_rule_id.duration
                )

    @api.depends("end_date")
    def _compute_state(self):
        today = fields.Date.today()
        for rec in self:
            rec.state = "expired" if rec.end_date < today else "active"