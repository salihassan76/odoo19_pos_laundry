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
    customer_id = fields.Many2one("res.partner", string="Customer", required=True)
    order_line_ids = fields.One2many("laundry.order.line", "order_id", string="Order Lines")
    total_amount = fields.Float(string="Total Amount", compute="_compute_total_amount", store=True)
    order_type_id = fields.Many2one("laundry.order.type", string="Order Type", required=True)
    payment_status_id = fields.Many2one(
        "laundry.order.payment.status",
        string="Payment Status",
        readonly=True,
        required=True,
        default=lambda self: self.env["laundry.order.payment.status"].search([],order="sequence", limit=1).id,
    )
    status_id = fields.Many2one(
        "laundry.order.status",
        string="Status",
        readonly=True,
        required=True,
        default=lambda self: self.env["laundry.order.status"].search([], limit=1).id,
    )
    project_id = fields.Many2one("project.project", string="Project", readonly=True)
    order_datetime = fields.Datetime(
        string="Order Received",
        default=fields.Datetime.now,
        required=True,
        readonly=True,
        copy=False,
    )
    order_date = fields.Date(string="Order Day", compute="_compute_order_datetime_parts", store=True, index=True)
    order_hour = fields.Integer(string="Order Hour", compute="_compute_order_datetime_parts", store=True, index=True)
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
    is_package = fields.Boolean(string="Package Usage")
    package_rule_id = fields.Many2one("package.rule", string="Package")
    currency_id = fields.Many2one(
        "res.currency",
        string="Currency",
        default=lambda self: self.env.company.currency_id,
    )
    pos_order_id = fields.Many2one("pos.order", string="POS Order", readonly=True, copy=False)
    order_note = fields.Text(string="Order Note")
    order_internal_note = fields.Text(string="Internal Note")

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
        """Save the laundry order from the POS without creating a pos.order.

        Latest flow:
        - Save Order creates laundry.order and laundry.order.line only.
        - If the order type is package sale, create partner.package and its balance rows.
        - If an active package is selected, record package usage history.
        - The real pos.order is created later by the normal POS payment/sync flow.
        """
        if not data.get("partner_id"):
            raise ValidationError("Customer is required.")

        if not data.get("laundry_order_type_id"):
            raise ValidationError("Laundry order type is required.")

        lines = data.get("lines") or []
        if not lines:
            raise ValidationError("Please add at least one product before saving the laundry order.")
        # Validate package products
        if data.get("is_package_usage"):
            partner_package = self.env["partner.package"].browse(
                data.get("partner_package_id")
            )

            if not partner_package.exists():
                raise ValidationError("Please select a valid package.")

            self._validate_package_products(
                partner_package,
                lines,
            )

        package_rule = self._get_package_rule_from_data(data)
        laundry_order = self._create_laundry_order(data, package_rule)
        self._create_laundry_order_lines(laundry_order, lines)

        partner_package = self._create_partner_package(data, laundry_order, package_rule)
        self._create_package_usage_lines(data, laundry_order)
        config = self.env["laundry.configuration"].search([], limit=1)

        return {
            "laundry_order_id": laundry_order.id,
            "partner_package_id": partner_package.id if partner_package else False,
            "pos_order_id": False,
            "direct_sale": laundry_order.order_type_id.direct_sale,
            "direct_print": bool(config.direct_print) if config else False,
            "receipt": laundry_order._get_receipt_data(),
            "show_receipt_preview":bool(config.show_receipt_preview) if config else False,
        }

    def _get_package_rule_from_data(self, data):
        package_rule_id = data.get("package_rule_id")
        if package_rule_id:
            package_rule = self.env["package.rule"].browse(package_rule_id)
            if package_rule.exists():
                return package_rule

        # For package sales, allow the POS line/package product to identify the rule.
        line_product_ids = [line.get("product_id") for line in data.get("lines", []) if line.get("product_id")]
        if line_product_ids:
            package_rule = self.env["package.rule"].search([("product_id", "in", line_product_ids)], limit=1)
            if package_rule:
                return package_rule

        return self.env["package.rule"]

    def _create_laundry_order(self, data, package_rule=False):
        vals = {
            "customer_id": data.get("partner_id"),
            "order_type_id": data.get("laundry_order_type_id"),
            "package_rule_id": package_rule.id if package_rule else False,
            "is_package": bool(data.get("is_package_usage")),
            "order_note": data.get("notes") or "",
        }

        if data.get("is_package_usage"):
            config = self.env["laundry.configuration"].search([], limit=1)
            if not config or not config.package_payment_id:
                raise ValidationError(_("Please configure Package Payment Status in Laundry Settings."))

            vals["payment_status_id"] = config.package_payment_id.id

        return self.create(vals)

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
            raise ValidationError("Package is required for package sale.")

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

            # Keep the balance by product. Each allowed product receives the detail quantity.
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
            raise ValidationError("Please select an active customer package.")

        partner_package = self.env["partner.package"].browse(partner_package_id)
        if not partner_package.exists():
            raise ValidationError("Selected customer package was not found.")

        if partner_package.partner_id.id != data.get("partner_id"):
            raise ValidationError("Selected package does not belong to this customer.")

        if partner_package.state != "active":
            raise ValidationError("Selected package is not active.")

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
                    "Product %s is not included in this package."
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
                    "Not enough package balance for %s. Remaining: %s, Requested: %s."
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
            # Change this if you want another grouping field
            service = (
                line.product_id.pos_categ_ids[:1].name
                if line.product_id.pos_categ_ids
                else "Other"
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
