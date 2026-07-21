from datetime import datetime, time

from odoo import api, fields, models
from odoo.osv import expression


class LaundryOrder(models.Model):
    _inherit = "laundry.order"

    @api.model
    def get_pos_dashboard_data(
        self,
        pos_config_id,
        partner_id=False,
        search_term="",
        date_filter="today",
        unpaid_only=False,
        ready_only=False,
        status_id=False,
        limit=20,
    ):
        if not pos_config_id:
            return self._empty_pos_dashboard_data()

        pos_config = self.env["pos.config"].browse(
            int(pos_config_id)
        ).exists()

        if not pos_config:
            return self._empty_pos_dashboard_data()

        company = pos_config.company_id
        currency = company.currency_id

        base_domain = [
            ("pos_config_id", "=", pos_config.id),
        ]

        today = fields.Date.context_today(self)

        start_datetime = datetime.combine(
            today,
            time.min,
        )

        end_datetime = datetime.combine(
            today,
            time.max,
        )

        today_domain = expression.AND([
            base_domain,
            [
                (
                    "order_datetime",
                    ">=",
                    fields.Datetime.to_string(
                        start_datetime
                    ),
                ),
                (
                    "order_datetime",
                    "<=",
                    fields.Datetime.to_string(
                        end_datetime
                    ),
                ),
            ],
        ])

        today_orders = self.search_count(
            today_domain
        )

        unpaid_payment_ids = self._get_unpaid_payment_status_ids(
            pos_config
        )

        unpaid_domain = list(base_domain)

        if unpaid_payment_ids:
            unpaid_domain.append(
                (
                    "payment_status_id",
                    "in",
                    unpaid_payment_ids,
                )
            )
        else:
            unpaid_domain.append(("id", "=", 0))

        unpaid_orders = self.search_count(
            unpaid_domain
        )

        ready_status_ids = self._get_ready_status_ids(
            pos_config
        )

        ready_domain = list(base_domain)

        if ready_status_ids:
            ready_domain.append(
                (
                    "status_id",
                    "in",
                    ready_status_ids,
                )
            )
        else:
            ready_domain.append(("id", "=", 0))

        ready_orders = self.search_count(
            ready_domain
        )

        today_sales = sum(
            self.search(today_domain).mapped(
                "total_amount"
            )
        )

        status_records = self.env[
            "laundry.order.status"
        ].search(
            [
                ("active", "=", True),
                ("show_on_home", "=", True),
            ],
            order="sequence, id",
        )

        statuses = []

        for status in status_records:
            status_count = self.search_count(
                expression.AND([
                    base_domain,
                    [
                        (
                            "status_id",
                            "=",
                            status.id,
                        )
                    ],
                ])
            )

            statuses.append({
                "id": status.id,
                "name": status.name,
                "color": status.color or "#6c757d",
                "order_count": status_count,
            })

        orders_domain = list(base_domain)

        if partner_id:
            orders_domain.append(
                ("customer_id", "=", int(partner_id))
            )

        if date_filter == "today":
            orders_domain = expression.AND([
                orders_domain,
                [
                    (
                        "order_datetime",
                        ">=",
                        fields.Datetime.to_string(
                            start_datetime
                        ),
                    ),
                    (
                        "order_datetime",
                        "<=",
                        fields.Datetime.to_string(
                            end_datetime
                        ),
                    ),
                ],
            ])

        if status_id:
            orders_domain.append(
                ("status_id", "=", int(status_id))
            )

        if unpaid_only:
            if unpaid_payment_ids:
                orders_domain.append(
                    (
                        "payment_status_id",
                        "in",
                        unpaid_payment_ids,
                    )
                )
            else:
                orders_domain.append(("id", "=", 0))

        if ready_only:
            if ready_status_ids:
                orders_domain.append(
                    (
                        "status_id",
                        "in",
                        ready_status_ids,
                    )
                )
            else:
                orders_domain.append(("id", "=", 0))

        if search_term:
            search_term = search_term.strip()

            search_domain = [
                "|",
                "|",
                "|",
                ("name", "ilike", search_term),
                (
                    "customer_id.name",
                    "ilike",
                    search_term,
                ),
                
                (
                    "customer_id.phone",
                    "ilike",
                    search_term,
                ),
            ]

            orders_domain = expression.AND([
                orders_domain,
                search_domain,
            ])

        orders = self.search(
            orders_domain,
            order="order_datetime desc, id desc",
            limit=max(1, min(int(limit or 20), 100)),
        )

        recent_orders = [
            self._prepare_pos_dashboard_order(
                order,
                currency,
            )
            for order in orders
        ]

        return {
            "today_orders": today_orders,
            "unpaid_orders": unpaid_orders,
            "ready_orders": ready_orders,
            "today_sales": today_sales,
            "statuses": statuses,
            "recent_orders": recent_orders,
        }

    @api.model
    def _empty_pos_dashboard_data(self):
        return {
            "today_orders": 0,
            "unpaid_orders": 0,
            "ready_orders": 0,
            "today_sales": 0,
            "statuses": [],
            "recent_orders": [],
        }

    @api.model
    def _get_unpaid_payment_status_ids(
        self,
        pos_config,
    ):
        payment_status_ids = []

        if pos_config.unpaid_payment_id:
            payment_status_ids.append(
                pos_config.unpaid_payment_id.id
            )

        if pos_config.partial_payment_id:
            payment_status_ids.append(
                pos_config.partial_payment_id.id
            )

        return payment_status_ids

    @api.model
    def _get_ready_status_ids(
        self,
        pos_config,
    ):
        ready_statuses = self.env[
            "laundry.order.status"
        ].search([
            ("active", "=", True),
            ("name", "ilike", "ready"),
        ])

        return ready_statuses.ids

    @api.model
    def _prepare_pos_dashboard_order(
        self,
        order,
        currency,
    ):
        partner = order.customer_id
        status = order.status_id
        payment_status = order.payment_status_id
        order_type = order.order_type_id

        return {
            "id": order.id,
            "name": order.name or "",
            "customer_id": partner.id or False,
            "customer_name": (
                partner.name or "Walk-In Customer"
            ),
            "customer_phone": (
                partner.phone or ""
            ),
            "order_type_id": (
                order_type.id or False
            ),
            "order_type_name": (
                order_type.name or ""
            ),
            "status_id": status.id or False,
            "status_name": status.name or "",
            "status_color": (
                status.color or "#6c757d"
            ),
            "payment_status_id": (
                payment_status.id or False
            ),
            "payment_status_name": (
                payment_status.name or ""
            ),
            "total_amount": (
                order.total_amount or 0.0
            ),
            "currency_id": currency.id,
            "currency_symbol": (
                currency.symbol or ""
            ),
            "order_datetime": (
                fields.Datetime.context_timestamp(
                    self,
                    order.order_datetime,
                ).strftime("%d/%m/%Y %I:%M %p")
                if order.order_datetime
                else ""
            ),
        }