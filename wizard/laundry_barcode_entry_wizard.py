from odoo import fields, models, _
from odoo.exceptions import UserError


class LaundryBarcodeEntryWizard(
    models.TransientModel
):
    _name = "laundry.barcode.entry.wizard"
    _description = "Laundry Barcode Entry"

    barcode = fields.Char(
        string="Laundry Barcode",
        required=True,
    )

    def action_open_order(self):
        self.ensure_one()

        barcode = (
            self.barcode or ""
        ).strip().upper()

        if not barcode:
            raise UserError(
                _("Please enter a barcode.")
            )

        result = self.env[
            "laundry.order"
        ].process_laundry_barcode(
            scanned_barcode=barcode,
            source="backend",
        )

        order_data = (
            result.get("popup_data", {})
            .get("order", {})
        )

        order_id = order_data.get("id")

        if not order_id:
            raise UserError(
                _(
                    "The laundry order could "
                    "not be opened."
                )
            )

        return {
            "type": "ir.actions.act_window",
            "name": _("Laundry Order"),
            "res_model": "laundry.order",
            "res_id": order_id,
            "view_mode": "form",
            "target": "current",
        }