from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from collections import OrderedDict
from datetime import timedelta

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

    order_note = fields.Text(string="Order Note")
    order_internal_note = fields.Text(string="Internal Note")

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

    @api.depends("order_datetime")
    def _compute_order_datetime_parts(self):
        for rec in self:
            if rec.order_datetime:
                dt = fields.Datetime.context_timestamp(rec, rec.order_datetime)
                rec.order_date = dt.date()
                rec.order_hour = dt.hour
                rec.order_weekday = str(dt.weekday())
            else:
                rec.order_date = False
                rec.order_hour = 0
                rec.order_weekday = False

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", "New") == "New":
                order_type = self.env["laundry.order.type"].browse(vals.get("order_type_id"))
                sequence_code = f"laundry.order.{order_type.id}" if order_type else "laundry.order"
                vals["name"] = self.env["ir.sequence"].next_by_code(sequence_code) or "New"
        return super().create(vals_list)

    @api.depends("order_line_ids.price_subtotal")
    def _compute_total_amount(self):
        for order in self:
            order.total_amount = sum(order.order_line_ids.mapped("price_subtotal"))

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

        pos_config = self.env["pos.config"].browse(data.get("pos_config_id"))
        if not pos_config.exists():
            raise ValidationError(_("Selected POS Configuration was not found."))

        pos_config.check_laundry_configuration()

        lines = data.get("lines") or []
        if not lines:
            raise ValidationError(_("Please add at least one product before saving the laundry order."))

        context = self._prepare_pos_laundry_order_context(data, pos_config)
        self._validate_pos_laundry_order_data(data, pos_config, context)

        laundry_order_id = data.get("laundry_order_id")

        if laundry_order_id:
            laundry_order = self.browse(laundry_order_id)
            if not laundry_order.exists():
                raise ValidationError(_("Laundry order was not found."))

            self._check_laundry_order_editable(laundry_order)
            self._update_laundry_order(laundry_order, data, pos_config, context)
            self._replace_laundry_order_lines(laundry_order, lines)
            self._after_update_laundry_order_from_pos(laundry_order, data, pos_config, context)
        else:
            laundry_order = self._create_laundry_order(data, pos_config, context)
            self._create_laundry_order_lines(laundry_order, lines)
            self._after_create_laundry_order_from_pos(laundry_order, data, pos_config, context)

        response = {
            "laundry_order_id": laundry_order.id,
            "laundry_order_name": laundry_order.name,
            "pos_order_id": False,
            "direct_sale": laundry_order.order_type_id.direct_sale,
            "direct_print": bool(pos_config.direct_print),
            "receipt": laundry_order._get_receipt_data(),
            "show_receipt_preview": bool(pos_config.show_receipt_preview),
        }
        return self._extend_pos_laundry_order_response(response, laundry_order, data, pos_config, context)

    def _validate_required_pos_data(self, data):
        if not data.get("partner_id"):
            raise ValidationError(_("Customer is required."))
        if not data.get("laundry_order_type_id"):
            raise ValidationError(_("Laundry order type is required."))
        if not data.get("pos_config_id"):
            raise ValidationError(_("POS Configuration is missing."))

    def _prepare_pos_laundry_order_context(self, data, pos_config):
        return {}

    def _validate_pos_laundry_order_data(self, data, pos_config, context):
        return True

    def _prepare_laundry_order_vals(self, data, pos_config, context):
        vals = {
            "customer_id": data.get("partner_id"),
            "order_type_id": data.get("laundry_order_type_id"),
            "order_note": data.get("notes") or "",
            "status_id": pos_config.order_status_id.id,
            "payment_status_id": pos_config.unpaid_payment_id.id,
            "pos_config_id": pos_config.id,
        }

        if pos_config.is_project and pos_config.project_id:
            vals["project_id"] = pos_config.project_id.id

        return vals

    def _prepare_laundry_order_update_vals(self, data, pos_config, context):
        return {
            "customer_id": data.get("partner_id"),
            "order_type_id": data.get("laundry_order_type_id"),
            "order_note": data.get("notes") or "",
        }

    def _create_laundry_order(self, data, pos_config=False, context=False):
        if not pos_config:
            pos_config = self.env["pos.config"].browse(data.get("pos_config_id"))
        if not pos_config.exists():
            raise ValidationError(_("Selected POS Configuration was not found."))
        pos_config.check_laundry_configuration()
        return self.create(self._prepare_laundry_order_vals(data, pos_config, context or {}))

    def _is_new_status(self, status):
        if not status:
            return False
        return (status.name or "").strip().lower() == "new"

    def _check_laundry_order_editable(self, laundry_order):
        laundry_order.ensure_one()
        if not self._is_new_status(laundry_order.status_id):
            raise ValidationError(_("Only laundry orders with status New can be edited from POS."))

    def _update_laundry_order(self, laundry_order, data, pos_config=False, context=False):
        laundry_order.ensure_one()
        if not pos_config:
            pos_config = laundry_order.pos_config_id
        vals = self._prepare_laundry_order_update_vals(data, pos_config, context or {})
        laundry_order.write(vals)
        return laundry_order

    def _replace_laundry_order_lines(self, laundry_order, lines):
        laundry_order.ensure_one()
        laundry_order.order_line_ids.unlink()
        self._create_laundry_order_lines(laundry_order, lines)

    def _create_laundry_order_lines(self, laundry_order, lines):
        LaundryOrderLine = self.env["laundry.order.line"]

        for line in lines:
            product_id = line.get("product_id")
            if not product_id:
                continue

            product = self.env["product.product"].browse(product_id)
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

    def _after_create_laundry_order_from_pos(self, laundry_order, data, pos_config, context):
        return True

    def _after_update_laundry_order_from_pos(self, laundry_order, data, pos_config, context):
        return True

    def _extend_pos_laundry_order_response(self, response, laundry_order, data, pos_config, context):
        return response

    def _extend_receipt_data(self, receipt):
        return receipt

    def _extend_laundry_order_for_pos_data(self, data, order):
        return data

    # -------------------------------------------------------------------------
    # RECEIPTS / ORDER LOADING / PAYMENT DATA
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
                "product_name": line.product_id.display_name,
                "qty": line.quantity,
                "price_unit": line.price_unit,
                "subtotal": line.price_subtotal,
            })

        receipt = {
            "company_name": company.name,
            "company_phone": company.phone or "",
            "company_email": company.email or "",
            "order_name": self.name,
            "date": fields.Datetime.to_string(self.order_datetime),
            "customer_name": self.customer_id.name,
            "customer_mobile": self.customer_id.phone or "",
            "order_type": self.order_type_id.name,
            "payment_status": self.payment_status_id.name,
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
            "direct_print": bool(config.direct_print),
            "show_receipt_preview": bool(config.show_receipt_preview),
        }

    @api.model
    def get_customer_orders_by_status_for_pos(self, partner_id):
        if not partner_id:
            return []

        statuses = self.env["laundry.order.status"].search([
            ("active", "=", True),
            ("show_on_home", "=", True),
        ], order="sequence, id")

        result = []
        now = fields.Datetime.now()

        for status in statuses:
            domain = [
                ("customer_id", "=", partner_id),
                ("status_id", "=", status.id),
            ]

            period_days = int(status.show_on_home_period or 0)

            if period_days > 0:
                cutoff_date = now - timedelta(days=period_days)
                domain.append(("order_datetime", ">=", cutoff_date))

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
                "orders": [{
                    "id": order.id,
                    "name": order.name,
                    "total_amount": order.total_amount,
                    "order_datetime": fields.Datetime.to_string(order.order_datetime),
                    "payment_status": order.payment_status_id.name if order.payment_status_id else "",
                    "order_type": order.order_type_id.name if order.order_type_id else "",
                    "order_type_id": order.order_type_id.id,
                    "order_type_icon": order.order_type_id.icon_class or "fa-file-text-o",
                    "order_type_color": order.order_type_id.icon_color or "text-primary",
                } for order in status_orders],
            })

        return result

    @api.model
    def get_laundry_order_for_pos(self, order_id):
        if not order_id:
            raise ValidationError(_("Laundry order is required."))

        order = self.browse(order_id)
        if not order.exists():
            raise ValidationError(_("Laundry order was not found."))

        data = {
            "id": order.id,
            "name": order.name,
            "partner_id": order.customer_id.id,
            "partner_name": order.customer_id.name,
            "order_type_id": order.order_type_id.id,
            "order_type_name": order.order_type_id.name,
            "order_type_prefix": order.order_type_id.prefix or "",
            "allowed_category_ids": order.order_type_id.pos_category_ids.ids,
            "status_id": order.status_id.id,
            "status_name": order.status_id.name,
            "payment_status_id": order.payment_status_id.id,
            "payment_status_name": order.payment_status_id.name,
            "total_amount": order.total_amount,
            "order_datetime": fields.Datetime.to_string(order.order_datetime),
            "lines": [{
                "id": line.id,
                "product_id": line.product_id.id,
                "product_name": line.product_id.display_name,
                "qty": line.quantity,
                "price_unit": line.price_unit,
                "subtotal": line.price_subtotal,
            } for line in order.order_line_ids],
        }
        return self._extend_laundry_order_for_pos_data(data, order)

    def get_payment_data(self):
        self.ensure_one()

        if not self.invoice_id:
            self.action_create_invoice()

        invoice = self.invoice_id

        if not invoice:
            raise ValidationError(_("No invoice found for this laundry order."))

        if invoice.state != "posted":
            invoice.action_post()

        paid_amount = invoice.amount_total - invoice.amount_residual
        payment_methods = []

        for method in self.pos_config_id.payment_method_ids:
            if not method.journal_id:
                continue

            payment_methods.append({
                "id": method.id,
                "name": method.name,
                "journal_id": method.journal_id.id,
                "journal_name": method.journal_id.name,
                "icon": method.image or False,
            })

        return {
            "id": self.id,
            "order_name": self.name,
            "order_date": fields.Datetime.to_string(self.order_datetime),
            "order_type": self.order_type_id.name if self.order_type_id else "",
            "customer_name": self.customer_id.name or "",
            "customer_mobile": self.customer_id.phone or "",
            "partner": {
                "id": self.customer_id.id,
                "name": self.customer_id.name,
            },
            "invoice_id": invoice.id,
            "invoice_name": invoice.name,
            "invoice_total": invoice.amount_total,
            "paid_amount": paid_amount,
            "balance_due": invoice.amount_residual,
            "invoice_payment_state": invoice.payment_state,
            "payment_status": self.payment_status_id.name if self.payment_status_id else "",
            "currency_id": invoice.currency_id.id,
            "currency_name": invoice.currency_id.name,
            "payment_methods": payment_methods,
        }
