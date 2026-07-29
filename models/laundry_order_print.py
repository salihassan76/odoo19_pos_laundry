from collections import OrderedDict

from odoo import _, fields, models
from odoo.exceptions import UserError


class LaundryOrderPrint(models.Model):
    _inherit = "laundry.order"

    # -------------------------------------------------------------------------
    # PRINT PERMISSIONS
    # -------------------------------------------------------------------------

    def _check_print_allowed(self):
        """
        Validate whether the current laundry order can be printed.

        Explicit print actions should call this method. Receipt data
        preparation does not check permissions because it can be called
        automatically while saving an order from the POS.
        """
        self.ensure_one()

        if not self.status_id:
            raise UserError(
                _("The laundry order does not have a status.")
            )

        self.status_id.check_action_allowed("print")

        return True

    # -------------------------------------------------------------------------
    # PRINT EXTENSION HOOK
    # -------------------------------------------------------------------------

    def _extend_receipt_data(self, receipt):
        """
        Extension hook for other laundry addons.

        Other addons can inherit this method to add package, logistics,
        pickup, delivery, driver, or other receipt information.
        """
        return receipt

    # -------------------------------------------------------------------------
    # POS RECEIPT DATA
    # -------------------------------------------------------------------------

    def _get_receipt_data(self):
        """
        Prepare receipt data for POS printing and receipt preview.

        This method intentionally does not call _check_print_allowed()
        because it may be called automatically while saving an order.
        """
        self.ensure_one()

        company = (
            self.company_id
            or self.pos_config_id.company_id
            or self.env.company
        )

        currency = (
            self.currency_id
            or company.currency_id
        )

        services = OrderedDict()

        for line in self.order_line_ids:
            category = line.product_id.pos_categ_ids[:1]

            service_name = (
                category.display_name
                if category
                else _("Other")
            )

            if service_name not in services:
                services[service_name] = {
                    "name": service_name,
                    "lines": [],
                }

            services[service_name]["lines"].append({
                "id": line.id,
                "product_id": line.product_id.id,
                "product_name": (
                    line.product_id.display_name or ""
                ),
                "qty": line.quantity,
                "price_unit": line.price_unit,
                "subtotal": line.price_subtotal,
            })

        local_datetime = False

        if self.order_datetime:
            local_datetime = fields.Datetime.context_timestamp(
                self,
                self.order_datetime,
            )

        financial_values = self._get_pos_financial_values()

        customer_phone = (
            self.customer_id.phone
            if self.customer_id
            else ""
        )

        receipt = {
            # Company
            "company_name": company.name or "",
            "company_phone": company.phone or "",
            "company_email": company.email or "",

            # Order
            "order_id": self.id,
            "order_name": self.name or "",
            "barcode": self.barcode or "",

            "date": (
                local_datetime.strftime("%Y-%m-%d %H:%M")
                if local_datetime
                else ""
            ),

            # Customer
            "customer_id": (
                self.customer_id.id
                if self.customer_id
                else False
            ),
            "customer_name": (
                self.customer_id.display_name
                if self.customer_id
                else ""
            ),
            "customer_phone": customer_phone,

            # Temporary compatibility key.
            # Remove this after all receipt XML uses customer_phone.
            "customer_mobile": customer_phone,

            # Order classification
            "order_type": (
                self.order_type_id.display_name
                if self.order_type_id
                else ""
            ),

            # Status
            "status": (
                self.status_id.display_name
                if self.status_id
                else ""
            ),
            "payment_status": (
                self.payment_status_id.display_name
                if self.payment_status_id
                else ""
            ),

            # Currency
            "currency_id": (
                currency.id
                if currency
                else False
            ),
            "currency_name": (
                currency.name
                if currency
                else ""
            ),
            "currency_symbol": (
                currency.symbol
                if currency
                else ""
            ),
            "currency_position": (
                currency.position
                if currency
                else "after"
            ),
            "currency_decimal_places": (
                currency.decimal_places
                if currency
                else 2
            ),

            # Financial values
            "total": financial_values["total_amount"],
            "paid_amount": financial_values["paid_amount"],
            "balance": financial_values["balance"],
            "refundable_amount": financial_values.get(
                "refundable_amount",
                0.0,
            ),

            # Content
            "note": self.order_note or "",
            "services": list(services.values()),
        }

        return self._extend_receipt_data(receipt)

    # -------------------------------------------------------------------------
    # POS REPRINT
    # -------------------------------------------------------------------------

    def action_get_receipt_data(self):
        """
        Return receipt information when the user explicitly requests
        a receipt reprint from the POS.
        """
        self.ensure_one()
        self._check_print_allowed()

        config = self.pos_config_id

        return {
            "receipt": self._get_receipt_data(),
            "direct_print": bool(
                config and config.direct_print
            ),
            "show_receipt_preview": bool(
                config and config.show_receipt_preview
            ),
        }

    # -------------------------------------------------------------------------
    # BACKEND PDF
    # -------------------------------------------------------------------------

    def action_print_laundry_order(self):
        """
        Print the full backend laundry-order PDF.
        """
        self.ensure_one()
        self._check_print_allowed()

        report = self.env.ref(
            "pos_laundry.action_report_laundry_order",
            raise_if_not_found=False,
        )

        if not report:
            raise UserError(
                _(
                    "The Laundry Order report action "
                    "could not be found."
                )
            )

        return report.report_action(self)