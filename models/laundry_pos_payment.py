from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class LaundryPosPayment(models.Model):
    _name = "laundry.pos.payment"
    _description = "Laundry POS Payment"
    _order = "payment_date desc, id desc"
    _rec_name = "name"

    name = fields.Char(
        string="Payment Reference",
        required=True,
        copy=False,
        readonly=True,
        default="New",
    )

    laundry_order_id = fields.Many2one(
        "laundry.order",
        string="Laundry Order",
        required=True,
        ondelete="restrict",
        index=True,
    )

    partner_id = fields.Many2one(
        "res.partner",
        string="Customer",
        related="laundry_order_id.customer_id",
        store=True,
        readonly=True,
    )

    pos_config_id = fields.Many2one(
        "pos.config",
        string="POS",
        related="laundry_order_id.pos_config_id",
        store=True,
        readonly=True,
    )

    pos_session_id = fields.Many2one(
        "pos.session",
        string="POS Session",
        required=True,
        ondelete="restrict",
        index=True,
    )

    cashier_id = fields.Many2one(
        "res.users",
        string="Cashier",
        default=lambda self: self.env.user,
        readonly=True,
    )

    payment_method_id = fields.Many2one(
        "pos.payment.method",
        string="Payment Method",
        required=True,
    )

    journal_id = fields.Many2one(
        "account.journal",
        string="Journal",
        related="payment_method_id.journal_id",
        store=True,
        readonly=True,
    )

    amount = fields.Monetary(
        string="Amount",
        required=True,
    )

    currency_id = fields.Many2one(
        "res.currency",
        string="Currency",
        default=lambda self: self.env.company.currency_id,
        required=True,
    )

    payment_date = fields.Datetime(
        string="Payment Date",
        default=fields.Datetime.now,
        required=True,
    )

    account_payment_id = fields.Many2one(
        "account.payment",
        string="Accounting Payment",
        readonly=True,
        copy=False,
        ondelete="restrict",
    )

    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("posted", "Posted"),
            ("cancelled", "Cancelled"),
        ],
        string="Status",
        default="draft",
        readonly=True,
    )

    note = fields.Text(
        string="Notes",
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", "New") == "New":
                vals["name"] = (
                    self.env["ir.sequence"].next_by_code("laundry.pos.payment")
                    or "New"
                )
        return super().create(vals_list)

    @api.model
    def receive_payment_from_pos(self, data):
        laundry_order_id = data.get("laundry_order_id")
        pos_session_id = data.get("pos_session_id")
        payment_method_id = data.get("payment_method_id")
        amount = data.get("amount")

        if not laundry_order_id:
            raise ValidationError(_("Laundry order is required."))

        if not pos_session_id:
            raise ValidationError(_("POS session is required."))

        if not payment_method_id:
            raise ValidationError(_("Payment method is required."))

        if not amount or amount <= 0:
            raise ValidationError(_("Payment amount must be greater than zero."))

        payment_method = self.env["pos.payment.method"].browse(payment_method_id)
        if not payment_method.exists():
            raise ValidationError(_("Selected payment method was not found."))

        if not payment_method.journal_id:
            raise ValidationError(_("Selected payment method has no journal."))

        payment = self.create({
            "laundry_order_id": laundry_order_id,
            "pos_session_id": pos_session_id,
            "payment_method_id": payment_method.id,
            "amount": amount,
            "note": data.get("note") or "",
        })

        payment.action_receive_payment()

        return payment._get_pos_payment_result()

    def action_receive_payment(self):
        self.ensure_one()

        self._validate_payment()
        self._before_receive_payment()

        account_payment = self._create_account_payment()

        self._reconcile_invoice(account_payment)
        self._after_receive_payment(account_payment)

        self.write({"state": "posted"})

        return True

    def action_cancel(self):
        self.ensure_one()

        self._cancel_account_payment()
        self.write({"state": "cancelled"})

        return True

    def action_reset_to_draft(self):
        self.ensure_one()

        if self.account_payment_id:
            raise ValidationError(
                _("You cannot reset a payment linked to an accounting payment.")
            )

        self.write({"state": "draft"})
        return True

    def _get_pos_payment_result(self):
        self.ensure_one()
        return {
            "payment_id": self.id,
            "payment_name": self.name,
            "state": self.state,
            "amount": self.amount,
            "account_payment_id": self.account_payment_id.id if self.account_payment_id else False,
        }

    # -------------------------------------------------------------------------
    # Extension Hooks
    # -------------------------------------------------------------------------

    def _validate_payment(self):
        return True

    def _before_receive_payment(self):
        return True

    def _create_account_payment(self):
        return False

    def _reconcile_invoice(self, account_payment=False):
        return True

    def _after_receive_payment(self, account_payment=False):
        for payment in self:
            order = payment.laundry_order_id
            invoice = order.invoice_id
            pos_config = order.pos_config_id

            if not order or not invoice or not pos_config:
                continue

            invoice.invalidate_recordset(["payment_state", "amount_residual"])

            vals = {}

            if invoice.payment_state == "paid" or invoice.amount_residual <= 0:
                if pos_config.paid_payment_id:
                    vals["payment_status_id"] = pos_config.paid_payment_id.id

            elif invoice.amount_residual > 0:
                if pos_config.partial_payment_id:
                    vals["payment_status_id"] = pos_config.partial_payment_id.id

            if vals:
                order.write(vals)

        return True

    def _cancel_account_payment(self):
        return True
