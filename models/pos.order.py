from odoo import api, models


class PosOrder(models.Model):
    _inherit = "pos.order"

    @api.model
    def create_from_ui(self, orders, draft=False):
        result = super().create_from_ui(orders, draft)

        for res in result:
            pos_order = self.browse(res.get("id"))
            if not pos_order:
                continue

            complete_status = pos_order.config_id.complete_order_status_id
            if not complete_status:
                continue

            laundry_orders = self.env["laundry.order"].search([
                ("pos_order_id", "=", pos_order.id)
            ])

            laundry_orders.write({
                "status_id": complete_status.id,
            })

        return result