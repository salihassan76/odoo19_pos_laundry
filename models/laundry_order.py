import logging
from collections import OrderedDict
from datetime import timedelta

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


_logger = logging.getLogger(__name__)


class LaundryOrder(models.Model):
    _name = "laundry.order"
    _description = "Laundry Order"

    name = fields.Char(
        string="Order Reference",
        required=True,
        copy=False,
        readonly=True,
        default="New",
    )

    customer_id = fields.Many2one(
        "res.partner",
        string="Customer",
        required=True,
    )

    order_line_ids = fields.One2many(
        "laundry.order.line",
        "order_id",
        string="Order Lines",
    )

    total_amount = fields.Float(
        string="Total Amount",
        compute="_compute_total_amount",
        store=True,
    )

    order_type_id = fields.Many2one(
        "laundry.order.type",
        string="Order Type",
        required=True,
    )

    payment_status_id = fields.Many2one(
        "laundry.order.payment.status",
        string="Payment Status",
        required=True,
    )

    status_id = fields.Many2one(
        "laundry.order.status",
        string="Status",
        required=True,
    )

    project_id = fields.Many2one(
        "project.project",
        string="Project",
        readonly=True,
    )

    order_datetime = fields.Datetime(
        string="Order Received",
        default=fields.Datetime.now,
        required=True,
        readonly=True,
        copy=False,
    )

    order_date = fields.Date(
        string="Order Day",
        compute="_compute_order_datetime_parts",
        store=True,
        index=True,
    )

    order_hour = fields.Integer(
        string="Order Hour",
        compute="_compute_order_datetime_parts",
        store=True,
        index=True,
    )

    order_weekday = fields.Selection(
        [
            ("0", "Monday"),
            ("1", "Tuesday"),
            ("2", "Wednesday"),
            ("3", "Thursday"),
            ("4", "Friday"),
            ("5", "Saturday"),
            ("6", "Sunday"),
        ],
        string="Order Weekday",
        compute="_compute_order_datetime_parts",
        store=True,
    )

    currency_id = fields.Many2one(
        "res.currency",
        string="Currency",
        default=lambda self: self.env.company.currency_id,
    )

    pos_order_id = fields.Many2one(
        "pos.order",
        string="POS Order",
        readonly=True,
        copy=False,
    )

    order_note = fields.Text(
        string="Order Note",
    )

    order_internal_note = fields.Text(
        string="Internal Note",
    )

    pos_config_id = fields.Many2one(
        "pos.config",
        string="POS",
        required=True,
        readonly=True,
        index=True,
    )

    laundry_pos_payment_ids = fields.One2many(
        "laundry.pos.payment",
        "laundry_order_id",
    )

    invoice_id = fields.Many2one(
        "account.move",
        string="Customer Invoice",
        readonly=True,
        copy=False,
        ondelete="restrict",
    )

    invoice_state = fields.Selection(
        related="invoice_id.state",
        string="Invoice Status",
        store=True,
        readonly=True,
    )

    invoice_payment_state = fields.Selection(
        related="invoice_id.payment_state",
        string="Invoice Payment",
        store=True,
        readonly=True,
    )

    # -------------------------------------------------------------------------
    # COMPUTED FIELDS
    # -------------------------------------------------------------------------

    @api.depends("order_datetime")
    def _compute_order_datetime_parts(self):
        for rec in self:
            if rec.order_datetime:
                dt = fields.Datetime.context_timestamp(
                    rec,
                    rec.order_datetime,
                )
                rec.order_date = dt.date()
                rec.order_hour = dt.hour
                rec.order_weekday = str(dt.weekday())
            else:
                rec.order_date = False
                rec.order_hour = 0
                rec.order_weekday = False

    @api.depends("order_line_ids.price_subtotal")
    def _compute_total_amount(self):
        for order in self:
            order.total_amount = sum(
                order.order_line_ids.mapped(
                    "price_subtotal"
                )
            )

    # -------------------------------------------------------------------------
    # CREATE
    # -------------------------------------------------------------------------

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", "New") == "New":
                order_type = self.env[
                    "laundry.order.type"
                ].browse(
                    vals.get("order_type_id")
                )

                sequence_code = (
                    f"laundry.order.{order_type.id}"
                    if order_type
                    else "laundry.order"
                )

                vals["name"] = (
                    self.env["ir.sequence"].next_by_code(
                        sequence_code
                    )
                    or "New"
                )

        return super().create(vals_list)

    # -------------------------------------------------------------------------
    # FINANCIAL VALUES FOR POS
    # -------------------------------------------------------------------------

    def _get_pos_financial_values(self):
        """Return normalized financial values for the POS.

        The posted customer invoice is the source of truth for:
        - paid amount
        - outstanding balance

        For the current full-refund-only implementation:
        - refundable amount equals the amount actually paid.
        - after full refund, balance and refundable amount are zero.
        """
        self.ensure_one()

        invoice = self.invoice_id

        if invoice and invoice.state == "posted":
            paid_amount = max(
                invoice.amount_total
                - invoice.amount_residual,
                0.0,
            )

            balance = max(
                invoice.amount_residual,
                0.0,
            )
        else:
            paid_amount = 0.0

            balance = max(
                self.total_amount or 0.0,
                0.0,
            )

        refund_payment_status = (
            self.pos_config_id.refund_payment_id
            if self.pos_config_id
            else False
        )

        is_refunded = bool(
            refund_payment_status
            and self.payment_status_id
            == refund_payment_status
        )

        if is_refunded:
            balance = 0.0
            refundable_amount = 0.0
        else:
            refundable_amount = paid_amount

        return {
            "total_amount": self.total_amount or 0.0,
            "paid_amount": paid_amount,
            "balance": balance,
            "refundable_amount": refundable_amount,
            "is_refunded": is_refunded,
        }

    # -------------------------------------------------------------------------
    # POS SAVE FLOW - CORE ONLY
    # Package/delivery/loyalty modules should extend using the hooks below.
    # -------------------------------------------------------------------------

    @api.model
    def process_pos_laundry_order(self, data):
        """Create or update a laundry order from POS.

        Core module handles only normal laundry order creation/editing.

        Optional modules should extend behavior using:
        - _prepare_pos_laundry_order_context()
        - _validate_pos_laundry_order_data()
        - _prepare_laundry_order_vals()
        - _after_create_laundry_order_from_pos()
        - _after_update_laundry_order_from_pos()
        - _extend_pos_laundry_order_response()
        """
        self._validate_required_pos_data(data)

        pos_config = self.env["pos.config"].browse(
            data.get("pos_config_id")
        )

        if not pos_config.exists():
            raise ValidationError(
                _(
                    "Selected POS Configuration "
                    "was not found."
                )
            )

        pos_config.check_laundry_configuration()

        lines = data.get("lines") or []

        if not lines:
            raise ValidationError(
                _(
                    "Please add at least one product "
                    "before saving the laundry order."
                )
            )

        context = (
            self._prepare_pos_laundry_order_context(
                data,
                pos_config,
            )
        )

        self._validate_pos_laundry_order_data(
            data,
            pos_config,
            context,
        )

        laundry_order_id = data.get(
            "laundry_order_id"
        )

        if laundry_order_id:
            laundry_order = self.browse(
                laundry_order_id
            )

            if not laundry_order.exists():
                raise ValidationError(
                    _("Laundry order was not found.")
                )

            self._check_laundry_order_editable(
                laundry_order
            )

            self._update_laundry_order(
                laundry_order,
                data,
                pos_config,
                context,
            )

            self._replace_laundry_order_lines(
                laundry_order,
                lines,
            )

            self._after_update_laundry_order_from_pos(
                laundry_order,
                data,
                pos_config,
                context,
            )

        else:
            laundry_order = self._create_laundry_order(
                data,
                pos_config,
                context,
            )

            self._create_laundry_order_lines(
                laundry_order,
                lines,
            )

            self._after_create_laundry_order_from_pos(
                laundry_order,
                data,
                pos_config,
                context,
            )
        # -------------------------------------------------------------
        # CONFIRM ORDER AFTER SUCCESSFUL POS SAVE
        # New -> Confirmed
        # -------------------------------------------------------------
        if pos_config.confirmed_order_status_id:
            laundry_order.write({
                "status_id": (
                    pos_config.confirmed_order_status_id.id
                ),
            })


        financial_values = (
            laundry_order._get_pos_financial_values()
        )

        status_capabilities = (
            laundry_order.status_id.get_pos_capabilities()
            if laundry_order.status_id
            else {}
        )

        response = {
            "laundry_order_id": laundry_order.id,
            "laundry_order_name": laundry_order.name,
            "pos_order_id": False,

            "direct_sale": (
                laundry_order.order_type_id.direct_sale
            ),

            "direct_print": bool(
                pos_config.direct_print
            ),

            "receipt": (
                laundry_order._get_receipt_data()
            ),

            "show_receipt_preview": bool(
                pos_config.show_receipt_preview
            ),

            # Order status
            "status_id": (
                laundry_order.status_id.id
                if laundry_order.status_id
                else False
            ),

            "status_name": (
                laundry_order.status_id.display_name
                if laundry_order.status_id
                else ""
            ),

            "status": status_capabilities,

            # Payment status
            "payment_status_id": (
                laundry_order.payment_status_id.id
                if laundry_order.payment_status_id
                else False
            ),

            "payment_status_name": (
                laundry_order.payment_status_id.display_name
                if laundry_order.payment_status_id
                else ""
            ),

            # Financial values
            "total_amount": (
                financial_values["total_amount"]
            ),

            "paid_amount": (
                financial_values["paid_amount"]
            ),

            "balance": (
                financial_values["balance"]
            ),

            "refundable_amount": (
                financial_values[
                    "refundable_amount"
                ]
            ),
        }

        return (
            self._extend_pos_laundry_order_response(
                response,
                laundry_order,
                data,
                pos_config,
                context,
            )
        )

    def _validate_required_pos_data(self, data):
        if not data.get("partner_id"):
            raise ValidationError(
                _("Customer is required.")
            )

        if not data.get("laundry_order_type_id"):
            raise ValidationError(
                _("Laundry order type is required.")
            )

        if not data.get("pos_config_id"):
            raise ValidationError(
                _("POS Configuration is missing.")
            )

    def _prepare_pos_laundry_order_context(
        self,
        data,
        pos_config,
    ):
        return {}

    def _validate_pos_laundry_order_data(
        self,
        data,
        pos_config,
        context,
    ):
        return True

    def _prepare_laundry_order_vals(
        self,
        data,
        pos_config,
        context,
    ):
        vals = {
            "customer_id": data.get("partner_id"),
            "order_type_id": data.get(
                "laundry_order_type_id"
            ),
            "order_note": data.get("notes") or "",
            "status_id": pos_config.order_status_id.id,
            "payment_status_id": (
                pos_config.unpaid_payment_id.id
            ),
            "pos_config_id": pos_config.id,
        }

        if (
            pos_config.is_project
            and pos_config.project_id
        ):
            vals["project_id"] = (
                pos_config.project_id.id
            )

        return vals

    def _prepare_laundry_order_update_vals(
        self,
        data,
        pos_config,
        context,
    ):
        return {
            "customer_id": data.get("partner_id"),
            "order_type_id": data.get(
                "laundry_order_type_id"
            ),
            "order_note": data.get("notes") or "",
        }

    def _create_laundry_order(
        self,
        data,
        pos_config=False,
        context=False,
    ):
        if not pos_config:
            pos_config = self.env[
                "pos.config"
            ].browse(
                data.get("pos_config_id")
            )

        if not pos_config.exists():
            raise ValidationError(
                _(
                    "Selected POS Configuration "
                    "was not found."
                )
            )

        pos_config.check_laundry_configuration()

        return self.create(
            self._prepare_laundry_order_vals(
                data,
                pos_config,
                context or {},
            )
        )

    def _is_new_status(self, status):
        if not status:
            return False

        return (
            (status.name or "")
            .strip()
            .lower()
            == "new"
        )

    def _check_laundry_order_editable(
        self,
        laundry_order,
    ):
        laundry_order.ensure_one()

        if not self._is_new_status(
            laundry_order.status_id
        ):
            raise ValidationError(
                _(
                    "Only laundry orders with status "
                    "New can be edited from POS."
                )
            )

    def _update_laundry_order(
        self,
        laundry_order,
        data,
        pos_config=False,
        context=False,
    ):
        laundry_order.ensure_one()

        if not pos_config:
            pos_config = laundry_order.pos_config_id

        vals = (
            self._prepare_laundry_order_update_vals(
                data,
                pos_config,
                context or {},
            )
        )

        laundry_order.write(vals)

        return laundry_order

    def _replace_laundry_order_lines(
        self,
        laundry_order,
        lines,
    ):
        laundry_order.ensure_one()

        laundry_order.order_line_ids.unlink()

        self._create_laundry_order_lines(
            laundry_order,
            lines,
        )

    def _create_laundry_order_lines(
        self,
        laundry_order,
        lines,
    ):
        LaundryOrderLine = self.env[
            "laundry.order.line"
        ]

        for line in lines:
            product_id = line.get("product_id")

            if not product_id:
                continue

            product = self.env[
                "product.product"
            ].browse(product_id)

            if not product.exists():
                continue

            qty = line.get("qty") or 1.0

            price_unit = line.get("price_unit")

            if price_unit is None:
                price_unit = product.lst_price

            LaundryOrderLine.create({
                "order_id": laundry_order.id,
                "product_id": product.id,
                "product_uom_id": product.uom_id.id,
                "quantity": qty,
                "price_unit": price_unit,
            })

    def _after_create_laundry_order_from_pos(
        self,
        laundry_order,
        data,
        pos_config,
        context,
    ):
        return True

    def _after_update_laundry_order_from_pos(
        self,
        laundry_order,
        data,
        pos_config,
        context,
    ):
        return True

    def _extend_pos_laundry_order_response(
        self,
        response,
        laundry_order,
        data,
        pos_config,
        context,
    ):
        return response

    def _extend_receipt_data(self, receipt):
        return receipt

    def _extend_laundry_order_for_pos_data(
        self,
        data,
        order,
    ):
        return data

    # -------------------------------------------------------------------------
    # RECEIPTS
    # -------------------------------------------------------------------------

    def _get_receipt_data(self):
        self.ensure_one()

        company = self.env.company
        services = OrderedDict()

        for line in self.order_line_ids:
            service = (
                line.product_id.pos_categ_ids[:1].name
                if line.product_id.pos_categ_ids
                else _("Other")
            )

            if service not in services:
                services[service] = {
                    "name": service,
                    "lines": [],
                }

            services[service]["lines"].append({
                "product_name": (
                    line.product_id.display_name
                ),
                "qty": line.quantity,
                "price_unit": line.price_unit,
                "subtotal": line.price_subtotal,
            })

        receipt = {
            "company_name": company.name,
            "company_phone": company.phone or "",
            "company_email": company.email or "",
            "order_name": self.name,
            "date": fields.Datetime.to_string(
                self.order_datetime
            ),
            "customer_name": self.customer_id.name,
            "customer_mobile": (
                self.customer_id.phone or ""
            ),
            "order_type": self.order_type_id.name,
            "payment_status": (
                self.payment_status_id.name
            ),
            "status": self.status_id.name,
            "total": self.total_amount,
            "note": self.order_note or "",
            "services": list(services.values()),
        }

        return self._extend_receipt_data(receipt)

    def action_get_receipt_data(self):
        self.ensure_one()

        config = self.pos_config_id

        return {
            "receipt": self._get_receipt_data(),
            "direct_print": bool(
                config.direct_print
            ),
            "show_receipt_preview": bool(
                config.show_receipt_preview
            ),
        }

    # -------------------------------------------------------------------------
    # POS HOME
    # -------------------------------------------------------------------------

    @api.model
    def get_customer_orders_by_status_for_pos(
        self,
        partner_id,
    ):
        if not partner_id:
            return []

        statuses = self.env[
            "laundry.order.status"
        ].search(
            [
                ("active", "=", True),
                ("show_on_home", "=", True),
            ],
            order="sequence, id",
        )

        result = []
        now = fields.Datetime.now()

        for status in statuses:
            domain = [
                ("customer_id", "=", partner_id),
                ("status_id", "=", status.id),
            ]

            period_days = int(
                status.show_on_home_period or 0
            )

            if period_days > 0:
                cutoff_date = (
                    now - timedelta(days=period_days)
                )

                domain.append(
                    (
                        "order_datetime",
                        ">=",
                        cutoff_date,
                    )
                )

            status_orders = self.search(
                domain,
                order="order_datetime desc, id desc",
            )

            result.append({
                "status_id": status.id,
                "status_name": status.name,
                "status_color": status.color,
                "show_on_home_period": period_days,

                "period_label": (
                    f"{period_days} Days"
                    if period_days > 0
                    else "All"
                ),

                "orders": [
                    {
                        "id": order.id,
                        "name": order.name,

                        "total_amount": (
                            order.total_amount
                        ),

                        "order_datetime": (
                            fields.Datetime.to_string(
                                order.order_datetime
                            )
                        ),

                        "payment_status": (
                            order.payment_status_id.name
                            if order.payment_status_id
                            else ""
                        ),

                        "order_type": (
                            order.order_type_id.name
                            if order.order_type_id
                            else ""
                        ),

                        "order_type_id": (
                            order.order_type_id.id
                        ),

                        "order_type_icon": (
                            order.order_type_id.icon_class
                            or "fa-file-text-o"
                        ),

                        "order_type_color": (
                            order.order_type_id.icon_color
                            or "text-primary"
                        ),
                    }
                    for order in status_orders
                ],
            })

        return result

    # -------------------------------------------------------------------------
    # OPEN EXISTING ORDER IN POS
    # -------------------------------------------------------------------------

    @api.model
    def get_laundry_order_for_pos(self, order_id):
        if not order_id:
            raise ValidationError(
                _("Laundry order is required.")
            )

        order = self.browse(order_id).exists()

        if not order:
            raise ValidationError(
                _("Laundry order was not found.")
            )

        status_capabilities = (
            order.status_id.get_pos_capabilities()
            if order.status_id
            else {}
        )

        financial_values = (
            order._get_pos_financial_values()
        )

        data = {
            "id": order.id,
            "name": order.name,

            "partner_id": order.customer_id.id,
            "partner_name": (
                order.customer_id.display_name
            ),

            "order_type_id": order.order_type_id.id,
            "order_type_name": (
                order.order_type_id.display_name
            ),

            "order_type_prefix": (
                order.order_type_id.prefix or ""
            ),

            "allowed_category_ids": (
                order.order_type_id.pos_category_ids.ids
            ),
            "allow_pay": bool(
                order.order_type_id.allow_pay
            ),

            # Existing fields kept for compatibility
            "status_id": order.status_id.id,
            "status_name": (
                order.status_id.display_name
            ),

            # New structured status payload
            "status": status_capabilities,

            "payment_status_id": (
                order.payment_status_id.id
            ),

            "payment_status_name": (
                order.payment_status_id.display_name
            ),

            # Financial values
            "total_amount": (
                financial_values["total_amount"]
            ),

            "paid_amount": (
                financial_values["paid_amount"]
            ),

            "balance": (
                financial_values["balance"]
            ),

            "refundable_amount": (
                financial_values[
                    "refundable_amount"
                ]
            ),

            "order_datetime": (
                fields.Datetime.to_string(
                    order.order_datetime
                )
                if order.order_datetime
                else False
            ),

            "lines": [
                {
                    "id": line.id,

                    "product_id": (
                        line.product_id.id
                    ),

                    "product_name": (
                        line.product_id.display_name
                    ),

                    "qty": line.quantity,

                    "price_unit": line.price_unit,

                    "subtotal": (
                        line.price_subtotal
                    ),
                }
                for line in order.order_line_ids
            ],
        }

        _logger.info(
            "POS open order payload (core): "
            "order_id=%s type_id=%s "
            "allowed_categories=%s lines=%s "
            "total=%s paid=%s balance=%s "
            "refundable=%s",
            order.id,
            order.order_type_id.id,
            data.get("allowed_category_ids"),
            len(data.get("lines") or []),
            financial_values["total_amount"],
            financial_values["paid_amount"],
            financial_values["balance"],
            financial_values["refundable_amount"],
        )

        return (
            self._extend_laundry_order_for_pos_data(
                data,
                order,
            )
        )

    # -------------------------------------------------------------------------
    # PAYMENT DATA
    # -------------------------------------------------------------------------

    def get_payment_data(self):
        self.ensure_one()

        if not self.invoice_id:
            self.action_create_invoice()

        invoice = self.invoice_id

        if not invoice:
            raise ValidationError(
                _(
                    "No invoice found for this "
                    "laundry order."
                )
            )

        if invoice.state != "posted":
            invoice.action_post()

        financial_values = (
            self._get_pos_financial_values()
        )

        payment_methods = []

        for method in (
            self.pos_config_id.payment_method_ids
        ):
            if not method.journal_id:
                continue

            payment_methods.append({
                "id": method.id,
                "name": method.name,
                "journal_id": method.journal_id.id,
                "journal_name": (
                    method.journal_id.name
                ),
                "image": method.image or False,
            })

        return {
            "id": self.id,
            "order_name": self.name,

            "order_date": (
                fields.Datetime.to_string(
                    self.order_datetime
                )
            ),

            "order_type": (
                self.order_type_id.name
                if self.order_type_id
                else ""
            ),

            "customer_name": (
                self.customer_id.name or ""
            ),

            "customer_mobile": (
                self.customer_id.phone or ""
            ),

            "partner": {
                "id": self.customer_id.id,
                "name": self.customer_id.name,
            },

            "invoice_id": invoice.id,
            "invoice_name": invoice.name,
            "invoice_total": invoice.amount_total,

            "paid_amount": (
                financial_values["paid_amount"]
            ),

            "balance_due": (
                financial_values["balance"]
            ),

            "refundable_amount": (
                financial_values[
                    "refundable_amount"
                ]
            ),

            "invoice_payment_state": (
                invoice.payment_state
            ),

            "payment_status": (
                self.payment_status_id.name
                if self.payment_status_id
                else ""
            ),

            "currency_id": invoice.currency_id.id,
            "currency_name": (
                invoice.currency_id.name
            ),

            "payment_methods": payment_methods,
        }

    # -------------------------------------------------------------------------
    # PAID ORDER DETAILS
    # -------------------------------------------------------------------------

    def get_paid_order_details_for_pos(self):
        self.ensure_one()

        payments = self.env[
            "laundry.pos.payment"
        ].search(
            [
                (
                    "laundry_order_id",
                    "=",
                    self.id,
                ),
                ("state", "=", "posted"),
            ],
            order="payment_date desc, id desc",
        )

        financial_values = (
            self._get_pos_financial_values()
        )

        return {
            "order": {
                "id": self.id,
                "order_name": self.name or "",

                "customer_name": (
                    self.customer_id.name or ""
                ),

                "order_type": (
                    self.order_type_id.name
                    if self.order_type_id
                    else ""
                ),

                "order_date": (
                    fields.Datetime.to_string(
                        self.order_datetime
                    )
                    if self.order_datetime
                    else ""
                ),

                "invoice_name": (
                    self.invoice_id.name
                    if self.invoice_id
                    else ""
                ),

                "invoice_total": (
                    f"{financial_values['total_amount']:.3f}"
                ),

                "paid_amount": (
                    f"{financial_values['paid_amount']:.3f}"
                ),

                "balance": (
                    f"{financial_values['balance']:.3f}"
                ),

                "refundable_amount": (
                    f"{financial_values['refundable_amount']:.3f}"
                ),

                "payment_status": (
                    self.payment_status_id.name
                    if self.payment_status_id
                    else ""
                ),
            },

            "lines": [
                {
                    "id": line.id,

                    "product_name": (
                        line.product_id.display_name
                        if line.product_id
                        else ""
                    ),

                    "category": (
                        line.product_id
                        .pos_categ_ids[:1]
                        .name
                        if (
                            line.product_id
                            and line.product_id.pos_categ_ids
                        )
                        else ""
                    ),

                    "qty": (
                        f"{line.quantity or 0.0:.3f}"
                    ),

                    "price": (
                        f"{line.price_unit or 0.0:.3f}"
                    ),

                    "subtotal": (
                        f"{line.price_subtotal or 0.0:.3f}"
                    ),
                }
                for line in self.order_line_ids
            ],

            "payments": [
                {
                    "id": payment.id,

                    "amount": (
                        f"{payment.amount or 0.0:.3f}"
                    ),

                    "method": (
                        payment.payment_method_id.name
                        if payment.payment_method_id
                        else ""
                    ),

                    "date": (
                        fields.Datetime.to_string(
                            payment.payment_date
                        )
                        if payment.payment_date
                        else ""
                    ),

                    "reference": (
                        payment.name or ""
                    ),
                }
                for payment in payments
            ],
        }

    # -------------------------------------------------------------------------
    # FULL REFUND
    # -------------------------------------------------------------------------

    def action_refund_from_pos(self):
        self.ensure_one()

        if not self.invoice_id:
            raise UserError(
                _("No invoice found for this order.")
            )

        # Status capability validation.
        self.status_id.check_action_allowed(
            "refund"
        )

        config = self.pos_config_id

        if not config:
            raise UserError(
                _("POS configuration is missing.")
            )

        refund_payment_status = (
                config.refund_payment_id
            )

        refunded_order_status = (
            config.refunded_order_status_id
        )

        if not refund_payment_status:
            raise UserError(
                _(
                    "Refund payment status "
                    "is not configured."
                )
            )

        if not refunded_order_status:
            raise UserError(
                _(
                    "Refunded order status "
                    "is not configured."
                )
            )

        financial_values = (
            self._get_pos_financial_values()
        )

        amount_to_refund = financial_values[
            "refundable_amount"
        ]

        if amount_to_refund <= 0:
            raise UserError(
                _(
                    "This order has no refundable "
                    "amount."
                )
            )

        # 1. Create credit note.
        reversal = (
            self.env["account.move.reversal"]
            .with_context(
                active_model="account.move",
                active_ids=self.invoice_id.ids,
            )
            .create({
                "reason": _(
                    "POS laundry order refund"
                ),
                "journal_id": (
                    self.invoice_id.journal_id.id
                ),
                "date": (
                    fields.Date.context_today(self)
                ),
            })
        )

        reversal_result = reversal.reverse_moves()

        refund_move = self.env[
            "account.move"
        ].browse(
            reversal_result.get("res_id")
        )

        if (
            refund_move
            and refund_move.state == "draft"
        ):
            refund_move.action_post()

        # 2. Find posted original payments.
        posted_payments = self.env[
            "laundry.pos.payment"
        ].search([
            (
                "laundry_order_id",
                "=",
                self.id,
            ),
            ("state", "=", "posted"),
        ])

        if not posted_payments:
            raise UserError(
                _(
                    "No posted payment was found "
                    "for this order."
                )
            )

        payment_method = (
            posted_payments[:1].payment_method_id
        )

        if (
            not payment_method
            or not payment_method.journal_id
        ):
            raise UserError(
                _(
                    "The original payment method "
                    "does not have a journal."
                )
            )

        # 3. Create outbound refund payment.
        refund_payment = self.env[
            "account.payment"
        ].create({
            "payment_type": "outbound",
            "partner_type": "customer",
            "partner_id": self.customer_id.id,
            "amount": amount_to_refund,
            "currency_id": (
                self.invoice_id.currency_id.id
            ),
            "date": (
                fields.Date.context_today(self)
            ),
            "journal_id": (
                payment_method.journal_id.id
            ),
            "ref": _(
                "Refund for %s"
            ) % self.name,
        })

        refund_payment.action_post()

        # 4. Update laundry order.
        self.write({
            "payment_status_id": (
                refund_payment_status.id
            ),
            "status_id": (
                refunded_order_status.id
            ),
        })

        updated_financial_values = (
            self._get_pos_financial_values()
        )

        return {
            "success": True,

            "refund_payment_id": (
                refund_payment.id
            ),

            "refund_invoice_id": (
                refund_move.id
                if refund_move
                else False
            ),

            "refund_amount": amount_to_refund,

            "status_id": (
                self.status_id.id
                if self.status_id
                else False
            ),

            "status_name": (
                self.status_id.display_name
                if self.status_id
                else ""
            ),

            "status": (
                self.status_id.get_pos_capabilities()
                if self.status_id
                else {}
            ),

            "payment_status_id": (
                self.payment_status_id.id
                if self.payment_status_id
                else False
            ),

            "payment_status_name": (
                self.payment_status_id.display_name
                if self.payment_status_id
                else ""
            ),

            "total_amount": (
                updated_financial_values[
                    "total_amount"
                ]
            ),

            "paid_amount": (
                updated_financial_values[
                    "paid_amount"
                ]
            ),

            "balance": (
                updated_financial_values[
                    "balance"
                ]
            ),

            "refundable_amount": (
                updated_financial_values[
                    "refundable_amount"
                ]
            ),
        }
    
    def action_cancel_from_pos(self):
        self.ensure_one()

        if not self.status_id:
            raise UserError(
                _("The laundry order does not have an order status.")
            )

        # Validate that the current dynamic status allows cancellation.
        self.status_id.check_action_allowed("cancel")

        config = self.pos_config_id

        if not config:
            raise UserError(
                _("POS configuration is missing.")
            )

        cancelled_order_status = (
            config.cancelled_order_status_id
        )

        cancelled_payment_status = (
            config.cancelled_payment_id
        )

        if not cancelled_order_status:
            raise UserError(
                _("Cancelled order status is not configured.")
            )

        if not cancelled_payment_status:
            raise UserError(
                _("Cancelled payment status is not configured.")
            )

        financial_values = (
            self._get_pos_financial_values()
        )

        paid_amount = financial_values[
            "paid_amount"
        ]

        if paid_amount > 0:
            raise UserError(
                _(
                    "A paid or partially paid order cannot be cancelled. "
                    "Refund the order instead."
                )
            )

        self.write({
            "status_id": (
                cancelled_order_status.id
            ),
            "payment_status_id": (
                cancelled_payment_status.id
            ),
        })

        updated_financial_values = (
            self._get_pos_financial_values()
        )

        return {
            "success": True,

            "status_id": (
                self.status_id.id
                if self.status_id
                else False
            ),

            "status_name": (
                self.status_id.display_name
                if self.status_id
                else ""
            ),

            "status": (
                self.status_id.get_pos_capabilities()
                if self.status_id
                else {}
            ),

            "payment_status_id": (
                self.payment_status_id.id
                if self.payment_status_id
                else False
            ),

            "payment_status_name": (
                self.payment_status_id.display_name
                if self.payment_status_id
                else ""
            ),

            "total_amount": (
                updated_financial_values[
                    "total_amount"
                ]
            ),

            "paid_amount": (
                updated_financial_values[
                    "paid_amount"
                ]
            ),

            "balance": 0.0,

            "refundable_amount": (
                updated_financial_values[
                    "refundable_amount"
                ]
            ),
        }