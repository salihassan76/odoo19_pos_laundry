from odoo import models, _
from odoo.exceptions import ValidationError


class LaundryPosPayment(models.Model):
    _inherit = "laundry.pos.payment"

    def _validate_payment(self):
        super()._validate_payment()

        for payment in self:
            if not payment.pos_session_id:
                raise ValidationError(_("POS session is required."))

            if payment.pos_session_id.state not in ("opened", "opening_control"):
                raise ValidationError(_("The selected POS session is not open."))

            if payment.pos_session_id.config_id != payment.pos_config_id:
                raise ValidationError(_("POS session does not match the laundry order POS."))

            if payment.payment_method_id not in payment.pos_session_id.config_id.payment_method_ids:
                raise ValidationError(_("Payment method is not allowed in this POS."))

            if payment.payment_method_id.journal_id != payment.journal_id:
                raise ValidationError(_("Payment journal does not match the POS payment method journal."))

        return True
