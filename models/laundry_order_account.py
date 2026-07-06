from odoo import fields, models, _
from odoo.exceptions import ValidationError


class LaundryOrder(models.Model):
    _inherit = "laundry.order"

    def action_create_invoice(self):
        """Create and post the customer invoice for this laundry order."""
        
        self.ensure_one()

        if self.invoice_id:
            invoice = self.invoice_id
        else:
            self._validate_customer_invoice()
            invoice = self._create_customer_invoice()
            invoice.action_post()
            self.invoice_id = invoice.id

        return {
            "invoice_id": invoice.id,
            "invoice_name": invoice.name,
            "state": invoice.state,
        }

    def _validate_customer_invoice(self):
        self.ensure_one()

        if not self.customer_id:
            raise ValidationError(_("Customer is required to create invoice."))

        if not self.order_line_ids:
            raise ValidationError(_("Cannot create invoice without order lines."))

        return True

    def _create_customer_invoice(self):
        self.ensure_one()

        invoice_vals = self._prepare_customer_invoice_vals()
        return self.env["account.move"].create(invoice_vals)

    def _prepare_customer_invoice_vals(self):
        self.ensure_one()

        return {
            "move_type": "out_invoice",
            "partner_id": self.customer_id.id,
            "invoice_date": fields.Date.context_today(self),
            "invoice_origin": self.name,
            "ref": self.name,
            "invoice_line_ids": [
                (0, 0, vals)
                for vals in self._prepare_customer_invoice_line_vals()
            ],
        }

    def _prepare_customer_invoice_line_vals(self):
        self.ensure_one()

        lines = []

        for line in self.order_line_ids:
            if not line.product_id:
                continue

            income_account = (
                line.product_id.property_account_income_id
                or line.product_id.categ_id.property_account_income_categ_id
            )

            if not income_account:
                raise ValidationError(
                    _("Please configure an income account for product %s.")
                    % line.product_id.display_name
                )

            lines.append({
                "product_id": line.product_id.id,
                "name": line.product_id.display_name,
                "quantity": line.quantity,
                "price_unit": line.price_unit,
                "account_id": income_account.id,
            })

        if not lines:
            raise ValidationError(_("No valid invoice lines were found."))

        return lines
