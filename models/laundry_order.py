from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from collections import OrderedDict


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
        readonly=True,
        required=True,
    )

    status_id = fields.Many2one(
        "laundry.order.status",
        string="Status",
        readonly=True,
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

    is_package = fields.Boolean(
        string="Package Usage",
    )

    package_rule_id = fields.Many2one(
        "package.rule",
        string="Package",
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

    @api.model
    def process_pos_laundry_order(self, data):
        """Create or update a laundry order from POS.

        Existing orders are editable only while their current status is New.
        Package usage is recalculated by removing this order's previous usage
        lines first, then validating/creating the new usage lines. This keeps
        remaining package quantities correct during edits.
        """
        if not data.get("partner_id"):
            raise ValidationError(_("Customer is required."))

        if not data.get("laundry_order_type_id"):
            raise ValidationError(_("Laundry order type is required."))

        if not data.get("pos_config_id"):
            raise ValidationError(_("POS Configuration is missing."))

        pos_config = self.env["pos.config"].browse(data.get("pos_config_id"))
        if not pos_config.exists():
            raise ValidationError(_("Selected POS Configuration was not found."))

        pos_config.check_laundry_configuration()

        lines = data.get("lines") or []
        if not lines:
            raise ValidationError(_("Please add at least one product before saving the laundry order."))

        package_rule = self._get_package_rule_from_data(data)
        laundry_order_id = data.get("laundry_order_id")
        partner_package = False

        if data.get("is_package_usage"):
            partner_package = self.env["partner.package"].browse(data.get("partner_package_id"))
            if not partner_package.exists():
                raise ValidationError(_("Please select a valid package."))
            self._validate_package_products(partner_package, lines)

        if laundry_order_id:
            laundry_order = self.browse(laundry_order_id)
            if not laundry_order.exists():
                raise ValidationError(_("Laundry order was not found."))

            self._check_laundry_order_editable(laundry_order)
            self._update_laundry_order(laundry_order, data, package_rule)
            self._replace_laundry_order_lines(laundry_order, lines)
            self._recreate_package_usage_lines_for_edit(data, laundry_order)
        else:
            laundry_order = self._create_laundry_order(
                data=data,
                package_rule=package_rule,
                pos_config=pos_config,
            )
            self._create_laundry_order_lines(laundry_order, lines)
            partner_package = self._create_partner_package(data, laundry_order, package_rule)
            self._create_package_usage_lines(data, laundry_order)

        return {
            "laundry_order_id": laundry_order.id,
            "laundry_order_name": laundry_order.name,
            "partner_package_id": partner_package.id if partner_package else False,
            "pos_order_id": False,
            "direct_sale": laundry_order.order_type_id.direct_sale,
            "direct_print": bool(pos_config.direct_print),
            "receipt": laundry_order._get_receipt_data(),
            "show_receipt_preview": bool(pos_config.show_receipt_preview),
        }

    def _get_package_rule_from_data(self, data):
        package_rule_id = data.get("package_rule_id")
        if package_rule_id:
            package_rule = self.env["package.rule"].browse(package_rule_id)
            if package_rule.exists():
                return package_rule

        line_product_ids = [
            line.get("product_id")
            for line in data.get("lines", [])
            if line.get("product_id")
        ]

        if line_product_ids:
            package_rule = self.env["package.rule"].search([
                ("product_id", "in", line_product_ids)
            ], limit=1)
            if package_rule:
                return package_rule

        return self.env["package.rule"]

    def _create_laundry_order(self, data, package_rule=False, pos_config=False):
        if not pos_config:
            pos_config = self.env["pos.config"].browse(data.get("pos_config_id"))

        if not pos_config.exists():
            raise ValidationError(_("Selected POS Configuration was not found."))

        pos_config.check_laundry_configuration()

        vals = {
            "customer_id": data.get("partner_id"),
            "order_type_id": data.get("laundry_order_type_id"),
            "package_rule_id": package_rule.id if package_rule else False,
            "is_package": bool(data.get("is_package_usage")),
            "order_note": data.get("notes") or "",
            "status_id": pos_config.order_status_id.id,
            "pos_config_id": pos_config.id,
        }

        if pos_config.is_project and pos_config.project_id:
            vals["project_id"] = pos_config.project_id.id

        if data.get("is_package_usage"):
            vals["payment_status_id"] = pos_config.package_payment_id.id
        else:
            vals["payment_status_id"] = pos_config.unpaid_payment_id.id

        return self.create(vals)

    def _is_new_status(self, status):
        if not status:
            return False
        return (status.name or "").strip().lower() == "new"

    def _check_laundry_order_editable(self, laundry_order):
        laundry_order.ensure_one()
        if not self._is_new_status(laundry_order.status_id):
            raise ValidationError(_("Only laundry orders with status New can be edited from POS."))

    def _update_laundry_order(self, laundry_order, data, package_rule=False):
        laundry_order.ensure_one()
        vals = {
            "customer_id": data.get("partner_id"),
            "order_type_id": data.get("laundry_order_type_id"),
            "package_rule_id": package_rule.id if package_rule else False,
            "is_package": bool(data.get("is_package_usage")),
            "order_note": data.get("notes") or "",
        }
        laundry_order.write(vals)
        return laundry_order

    def _replace_laundry_order_lines(self, laundry_order, lines):
        laundry_order.ensure_one()
        laundry_order.order_line_ids.unlink()
        self._create_laundry_order_lines(laundry_order, lines)

    def _recreate_package_usage_lines_for_edit(self, data, laundry_order):
        laundry_order.ensure_one()
        UsageLine = self.env["partner.package.usage.line"]
        UsageLine.search([
            ("laundry_order_id", "=", laundry_order.id),
        ]).unlink()
        self._create_package_usage_lines(data, laundry_order)


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

    def _create_partner_package(self, data, laundry_order, package_rule=False):
        if not data.get("is_package_sale"):
            return False

        if not package_rule:
            raise ValidationError(_("Package is required for package sale."))

        partner_package = self.env["partner.package"].create({
            "partner_id": data.get("partner_id"),
            "package_rule_id": package_rule.id,
            "laundry_order_id": laundry_order.id,
        })

        self._create_partner_package_balances(partner_package)

        return partner_package

    def _create_partner_package_balances(self, partner_package):
        UsageBalance = self.env["partner.package.usage"]

        for detail in partner_package.package_rule_id.detail_ids:
            products = detail.product_ids
            if not products:
                continue

            for product in products:
                UsageBalance.create({
                    "partner_package_id": partner_package.id,
                    "package_rule_detail_id": detail.id,
                    "product_id": product.id,
                    "allowed_qty": detail.qty,
                })

    def _create_package_usage_lines(self, data, laundry_order):
        if not data.get("is_package_usage"):
            return

        partner_package_id = data.get("partner_package_id")
        if not partner_package_id:
            raise ValidationError(_("Please select an active customer package."))

        partner_package = self.env["partner.package"].browse(partner_package_id)
        if not partner_package.exists():
            raise ValidationError(_("Selected customer package was not found."))

        if partner_package.partner_id.id != data.get("partner_id"):
            raise ValidationError(_("Selected package does not belong to this customer."))

        if partner_package.state != "active":
            raise ValidationError(_("Selected package is not active."))

        UsageLine = self.env["partner.package.usage.line"]

        for line in data.get("lines", []):
            product_id = line.get("product_id")
            if not product_id:
                continue

            qty = line.get("qty") or 1.0

            detail = self._get_package_detail_for_product(
                partner_package,
                product_id,
            )

            if not detail:
                product = self.env["product.product"].browse(product_id)
                raise ValidationError(
                    _("Product %s is not included in this package.")
                    % product.display_name
                )

            used_qty = sum(
                UsageLine.search([
                    ("partner_package_id", "=", partner_package.id),
                    ("package_rule_detail_id", "=", detail.id),
                ]).mapped("qty")
            )

            remaining_qty = detail.qty - used_qty

            if qty > remaining_qty:
                raise ValidationError(
                    _("Not enough package balance for %s. Remaining: %s, Requested: %s.")
                    % (detail.pos_category_id.name, remaining_qty, qty)
                )

            UsageLine.create({
                "partner_package_id": partner_package.id,
                "package_rule_detail_id": detail.id,
                "laundry_order_id": laundry_order.id,
                "product_id": product_id,
                "qty": qty,
            })

    def _validate_package_products(self, partner_package, lines):
        allowed_products = partner_package.package_rule_id.detail_ids.mapped("product_ids").ids

        for line in lines:
            product_id = line.get("product_id")

            if product_id not in allowed_products:
                product = self.env["product.product"].browse(product_id)
                raise ValidationError(
                    _("Product %s is not included in this package.")
                    % product.display_name
                )

    def _get_package_detail_for_product(self, partner_package, product_id):
        for detail in partner_package.package_rule_id.detail_ids:
            if product_id in detail.product_ids.ids:
                return detail

        return False

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

        return {
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
            "is_package_sale": self.order_type_id.is_package_sale,
            "is_package_use": self.order_type_id.is_package_use,
            "services": list(services.values()),
        }

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

        orders = self.search([
            ("customer_id", "=", partner_id),
            ("status_id", "in", statuses.ids),
        ], order="order_datetime desc, id desc")

        result = []

        for status in statuses:
            status_orders = orders.filtered(lambda o: o.status_id.id == status.id)

            result.append({
                "status_id": status.id,
                "status_name": status.name,
                "status_color": status.color,
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

        allowed_category_ids = order.order_type_id.pos_category_ids.ids

        return {
            "id": order.id,
            "name": order.name,

            "partner_id": order.customer_id.id,
            "partner_name": order.customer_id.name,

            "order_type_id": order.order_type_id.id,
            "order_type_name": order.order_type_id.name,
            "order_type_prefix": order.order_type_id.prefix or "",
            "allowed_category_ids": allowed_category_ids,

            "status_id": order.status_id.id,
            "status_name": order.status_id.name,

            "payment_status_id": order.payment_status_id.id,
            "payment_status_name": order.payment_status_id.name,

            "is_package": bool(order.is_package),
            "package_rule_id": order.package_rule_id.id if order.package_rule_id else False,
            "package_rule_name": order.package_rule_id.name if order.package_rule_id else "",
            "partner_package_id": self.env["partner.package.usage.line"].search([
                ("laundry_order_id", "=", order.id),
            ], limit=1).partner_package_id.id or False,

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
    def get_payment_data(self):
        self.ensure_one()

        # Create/post invoice automatically if missing
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
                "icon": method.laundry_icon or False,
            })

        return {
            "id": self.id,
            "order_name": self.name,
            "order_date": fields.Datetime.to_string(self.order_datetime),
            "order_type": self.order_type_id.name if self.order_type_id else "",

            "customer_name": self.customer_id.name or "",
            "customer_mobile": self.customer_id.mobile or self.customer_id.phone or "",

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

