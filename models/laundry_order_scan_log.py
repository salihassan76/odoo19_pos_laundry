from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class LaundryOrderScanLog(models.Model):
    _name = "laundry.order.scan.log"
    _description = "Laundry Order Barcode Scan Log"
    _order = "scan_datetime desc, id desc"
    _rec_name = "display_name"

    # -------------------------------------------------------------------------
    # Main information
    # -------------------------------------------------------------------------

    order_id = fields.Many2one(
        comodel_name="laundry.order",
        string="Laundry Order",
        required=True,
        index=True,
        ondelete="cascade",
    )

    display_name = fields.Char(
        string="Description",
        compute="_compute_display_name",
        store=True,
    )

    barcode = fields.Char(
        string="Scanned Barcode",
        required=True,
        index=True,
    )

    action_code = fields.Char(
        string="Action Code",
        index=True,
        help="Action code extracted from the scanned barcode, when applicable.",
    )

    scan_datetime = fields.Datetime(
        string="Scan Date and Time",
        required=True,
        default=fields.Datetime.now,
        index=True,
    )

    # -------------------------------------------------------------------------
    # Scan source
    # -------------------------------------------------------------------------

    source = fields.Selection(
        selection=[
            ("pos", "Point of Sale"),
            ("backend", "Backend"),
            ("delivery_portal", "Delivery Portal"),
            ("logistics", "Logistics"),
            ("portal", "Portal"),
        ],
        string="Scan Source",
        required=True,
        default="pos",
        index=True,
    )

    user_id = fields.Many2one(
        comodel_name="res.users",
        string="Scanned By",
        required=True,
        default=lambda self: self.env.user,
        index=True,
        ondelete="restrict",
    )

    # -------------------------------------------------------------------------
    # POS information
    # -------------------------------------------------------------------------

    origin_pos_config_id = fields.Many2one(
        comodel_name="pos.config",
        string="Origin POS",
        index=True,
        ondelete="set null",
        help="POS configuration that originally created the laundry order.",
    )

    scanning_pos_config_id = fields.Many2one(
        comodel_name="pos.config",
        string="Scanning POS",
        index=True,
        ondelete="set null",
        help=(
            "POS configuration where the barcode was scanned. "
            "This is empty for backend and delivery portal scans."
        ),
    )

    company_id = fields.Many2one(
        comodel_name="res.company",
        string="Company",
        related="order_id.company_id",
        store=True,
        readonly=True,
        index=True,
    )

    # -------------------------------------------------------------------------
    # Status information
    # -------------------------------------------------------------------------

    old_status_id = fields.Many2one(
        comodel_name="laundry.order.status",
        string="Previous Status",
        index=True,
        ondelete="set null",
    )

    new_status_id = fields.Many2one(
        comodel_name="laundry.order.status",
        string="New Status",
        index=True,
        ondelete="set null",
    )

    status_changed = fields.Boolean(
        string="Status Changed",
        compute="_compute_status_changed",
        store=True,
    )

    # -------------------------------------------------------------------------
    # Result
    # -------------------------------------------------------------------------

    result = fields.Selection(
        selection=[
            ("popup_opened", "Status Popup Opened"),
            ("order_opened", "Order Opened"),
            ("status_updated", "Status Updated"),
            ("status_unchanged", "Status Unchanged"),
            ("duplicate_ignored", "Duplicate Ignored"),
            ("print_requested", "Print Requested"),
            ("access_denied", "Access Denied"),
            ("order_not_found", "Order Not Found"),
            ("failed", "Failed"),
        ],
        string="Result",
        required=True,
        default="popup_opened",
        index=True,
    )

    success = fields.Boolean(
        string="Successful",
        compute="_compute_success",
        store=True,
    )

    message = fields.Text(
        string="Result Message",
        help="Additional information about the scan result or error.",
    )

    # -------------------------------------------------------------------------
    # Technical information
    # -------------------------------------------------------------------------

    raw_payload = fields.Text(
        string="Raw Payload",
        help=(
            "Optional technical payload received from the POS, backend, "
            "delivery portal, or logistics interface."
        ),
    )

    device_reference = fields.Char(
        string="Device Reference",
        index=True,
        help=(
            "Optional reference identifying the scanner, delivery device, "
            "browser session, or workstation."
        ),
    )

    ip_address = fields.Char(
        string="IP Address",
    )

    # -------------------------------------------------------------------------
    # Computed fields
    # -------------------------------------------------------------------------

    @api.depends(
        "order_id",
        "scan_datetime",
        "source",
        "result",
    )
    def _compute_display_name(self):
        source_labels = dict(
            self._fields["source"].selection
        )

        result_labels = dict(
            self._fields["result"].selection
        )

        for record in self:
            order_name = (
                record.order_id.display_name
                if record.order_id
                else _("Unknown Order")
            )

            source_name = source_labels.get(
                record.source,
                record.source or "",
            )

            result_name = result_labels.get(
                record.result,
                record.result or "",
            )

            record.display_name = "%s - %s - %s" % (
                order_name,
                source_name,
                result_name,
            )

    @api.depends(
        "old_status_id",
        "new_status_id",
    )
    def _compute_status_changed(self):
        for record in self:
            record.status_changed = bool(
                record.old_status_id
                and record.new_status_id
                and record.old_status_id != record.new_status_id
            )

    @api.depends("result")
    def _compute_success(self):
        successful_results = {
            "popup_opened",
            "order_opened",
            "status_updated",
            "status_unchanged",
            "duplicate_ignored",
            "print_requested",
        }

        for record in self:
            record.success = record.result in successful_results

    # -------------------------------------------------------------------------
    # Validation
    # -------------------------------------------------------------------------

    @api.constrains(
        "source",
        "scanning_pos_config_id",
    )
    def _check_scanning_pos(self):
        for record in self:
            if (
                record.source == "pos"
                and not record.scanning_pos_config_id
            ):
                raise ValidationError(
                    _(
                        "A scanning POS configuration is required "
                        "for Point of Sale barcode scans."
                    )
                )

    @api.constrains(
        "order_id",
        "origin_pos_config_id",
    )
    def _check_origin_pos(self):
        for record in self:
            if (
                record.order_id
                and record.origin_pos_config_id
                and record.order_id.pos_config_id
                != record.origin_pos_config_id
            ):
                raise ValidationError(
                    _(
                        "The scan log origin POS must match the "
                        "laundry order origin POS."
                    )
                )

    # -------------------------------------------------------------------------
    # Create
    # -------------------------------------------------------------------------

    @api.model_create_multi
    def create(self, vals_list):
        LaundryOrder = self.env["laundry.order"]

        for vals in vals_list:
            order_id = vals.get("order_id")

            if order_id:
                order = LaundryOrder.browse(order_id).exists()

                if order:
                    vals.setdefault(
                        "origin_pos_config_id",
                        order.pos_config_id.id
                        if order.pos_config_id
                        else False,
                    )

            vals.setdefault(
                "user_id",
                self.env.user.id,
            )

            vals.setdefault(
                "scan_datetime",
                fields.Datetime.now(),
            )

        return super().create(vals_list)

    # -------------------------------------------------------------------------
    # Restrictions
    # -------------------------------------------------------------------------

    def write(self, vals):
        protected_fields = {
            "order_id",
            "barcode",
            "source",
            "user_id",
            "scan_datetime",
            "origin_pos_config_id",
            "scanning_pos_config_id",
            "old_status_id",
            "new_status_id",
            "result",
        }

        if (
            protected_fields.intersection(vals)
            and not self.env.context.get("allow_scan_log_edit")
        ):
            raise ValidationError(
                _(
                    "Barcode scan log records cannot be modified "
                    "after they are created."
                )
            )

        return super().write(vals)

    def unlink(self):
        if not self.env.user.has_group(
            "base.group_system"
        ):
            raise ValidationError(
                _(
                    "Only administrators can delete barcode scan logs."
                )
            )

        return super().unlink()