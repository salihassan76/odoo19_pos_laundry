from odoo import models, fields


class LaundryPosPayment(models.Model):
    _name = "laundry.pos.payment"
    _description = "Laundry POS Payment"
    _order = "payment_date desc, id desc"

    name = fields.Char(default="New", readonly=True)

    laundry_order_id = fields.Many2one(
        "laundry.order",
        required=True,
        ondelete="restrict",
    )

    partner_id = fields.Many2one(
        "res.partner",
        related="laundry_order_id.customer_id",
        store=True,
        readonly=True,
    )

    pos_session_id = fields.Many2one(
        "pos.session",
        required=True,
        ondelete="restrict",
    )

    cashier_id = fields.Many2one(
        "res.users",
        default=lambda self: self.env.user,
        readonly=True,
    )

    payment_method_id = fields.Many2one(
        "pos.payment.method",
        required=True,
    )

    amount = fields.Monetary(required=True)

    currency_id = fields.Many2one(
        "res.currency",
        default=lambda self: self.env.company.currency_id,
        required=True,
    )

    payment_date = fields.Datetime(
        default=fields.Datetime.now,
        required=True,
    )

    account_payment_id = fields.Many2one(
        "account.payment",
        readonly=True,
        ondelete="restrict",
    )

    state = fields.Selection([
        ("draft", "Draft"),
        ("posted", "Posted"),
        ("cancelled", "Cancelled"),
    ], default="draft", readonly=True)

    notes = fields.Char()