from odoo import models, _
from odoo.exceptions import ValidationError


class LaundryPosPayment(models.Model):
    _inherit = "laundry.pos.payment"

    def _validate_payment(self):
        super()._validate_payment()

        for payment in self:
            if payment.state != "draft":
                raise ValidationError(_("Only draft payments can be posted."))

            if not payment.laundry_order_id:
                raise ValidationError(_("Laundry order is required."))

            if not payment.partner_id:
                raise ValidationError(_("Customer is required."))

            if not payment.journal_id:
                raise ValidationError(_("Payment journal is required."))

            if payment.amount <= 0:
                raise ValidationError(_("Payment amount must be greater than zero."))

            # Future invoice validation when invoice_id is added to laundry.order:
            invoice = payment.laundry_order_id.invoice_id
            if not invoice:
                raise ValidationError(_("No invoice was found for this laundry order."))
            if invoice.state != "posted":
                raise ValidationError(_("The invoice must be posted before receiving payment."))
            if payment.amount > invoice.amount_residual:
                raise ValidationError(_("Payment amount cannot exceed the remaining balance."))

        return True

    def _create_account_payment(self):
        self.ensure_one()

        if self.account_payment_id:
            return self.account_payment_id

        account_payment = self.env["account.payment"].create(
            self._prepare_account_payment_vals()
        )
        account_payment.action_post()

        self.write({"account_payment_id": account_payment.id})

        return account_payment

    def _prepare_account_payment_vals(self):
        self.ensure_one()

        return {
            "payment_type": "inbound",
            "partner_type": "customer",
            "partner_id": self.partner_id.id,
            "amount": self.amount,
            "currency_id": self.currency_id.id,
            "date": self.payment_date.date(),
            "journal_id": self.journal_id.id,
            "memo": self.name,
        }

    def _reconcile_invoice(self, account_payment=False):
        self.ensure_one()

        invoice = self.laundry_order_id.invoice_id

        if not invoice:
            return True
        
        if invoice.payment_state == "paid":
            return True

        if invoice.state != "posted":
            raise ValidationError(_("The laundry invoice must be posted before reconciliation."))

        if invoice.move_type not in ("out_invoice", "out_receipt"):
            raise ValidationError(_("Only customer invoices can be reconciled."))

        if not account_payment:
            account_payment = self.account_payment_id

        if not account_payment:
            raise ValidationError(_("Accounting payment was not created."))

        receivable_lines = invoice.line_ids.filtered(
            lambda line: (
                line.account_id.account_type == "asset_receivable"
                and not line.reconciled
            )
        )

        payment_lines = account_payment.move_id.line_ids.filtered(
            lambda line: (
                line.account_id.account_type == "asset_receivable"
                and not line.reconciled
            )
        )

        lines_to_reconcile = receivable_lines + payment_lines

        if lines_to_reconcile:
            lines_to_reconcile.reconcile()

        return True

    def _after_receive_payment(self, account_payment=False):
        """
        V1 placeholder.

        Later this can update laundry order payment status, print receipts,
        notify customer, or trigger other post-payment logic.
        """
        return super()._after_receive_payment(account_payment)

    def _cancel_account_payment(self):
        for payment in self:
            account_payment = payment.account_payment_id

            if not account_payment:
                continue

            if account_payment.state == "posted":
                account_payment.action_draft()

            account_payment.action_cancel()

        return True
