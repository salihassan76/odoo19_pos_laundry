from odoo import api, fields, models, _
from odoo.exceptions import AccessError, UserError, ValidationError


class LaundryOrderBarcode(models.Model):
    _inherit = "laundry.order"

    barcode = fields.Char(
        string="Order Barcode",
        copy=False,
        readonly=True,
        index=True,
    )

    barcode_last_scan_datetime = fields.Datetime(
        string="Last Barcode Scan",
        copy=False,
        readonly=True,
    )

    barcode_last_action = fields.Char(
        string="Last Barcode Action",
        copy=False,
        readonly=True,
    )

    barcode_last_source = fields.Selection(
        [
            ("pos", "Point of Sale"),
            ("backend", "Backend"),
            ("logistics", "Logistics"),
            ("portal", "Portal"),
        ],
        copy=False,
        readonly=True,
    )

    barcode_last_user_id = fields.Many2one(
        "res.users",
        string="Last Scanned By",
        copy=False,
        readonly=True,
    )

    barcode_last_pos_config_id = fields.Many2one(
        "pos.config",
        string="Last Scanning POS",
        copy=False,
        readonly=True,
    )

    _sql_constraints = [
        (
            "laundry_order_barcode_unique",
            "unique(barcode)",
            "The laundry order barcode must be unique.",
        ),
    ]

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get("barcode"):
                vals["barcode"] = self.env[
                    "ir.sequence"
                ].next_by_code(
                    "laundry.order.barcode"
                )

        return super().create(vals_list)

    @api.model
    def process_laundry_barcode(
        self,
        scanned_barcode,
        source="pos",
        pos_config_id=False,
        requested_status_id=False,
    ):
        """
        Process a laundry-order barcode.

        Initial scan:
            Find the order and return the status-change popup.

        Status confirmation:
            Validate and update the selected order status.
        """

        allowed_sources = {
            "pos",
            "backend",
            "logistics",
            "portal",
            "delivery_portal",
        }

        if source not in allowed_sources:
            raise ValidationError(
                _(
                    "Unsupported barcode scan source: %(source)s"
                )
                % {
                    "source": source,
                }
            )

        parsed = self._parse_laundry_barcode(
            scanned_barcode
        )

        order = self._find_order_by_barcode(
            parsed["order_barcode"]
        )

        scanning_pos = self.env["pos.config"]

        if source == "pos":
            scanning_pos = self._get_scanning_pos(
                pos_config_id=pos_config_id,
            )

        order._check_barcode_access(
            source=source,
            scanning_pos=scanning_pos,
        )

        if requested_status_id:
            return order._barcode_update_status(
                new_status_id=requested_status_id,
                scanned_barcode=parsed["raw_barcode"],
                source=source,
                scanning_pos=scanning_pos,
            )

        order._record_barcode_activity(
            action="status_popup",
            source=source,
            scanning_pos=scanning_pos,
        )

        return order._prepare_barcode_popup_data(
            source=source,
            scanning_pos=scanning_pos,
        )

    @api.model
    def _parse_laundry_barcode(
        self,
        scanned_barcode,
    ):
        """
        Validate and normalize a laundry-order barcode.

        Supported format:
            LND0000000123
        """
        barcode = (
            scanned_barcode or ""
        ).strip().upper()

        if not barcode:
            raise UserError(
                _("The scanned barcode is empty.")
            )

        if not barcode.startswith("LND"):
            raise UserError(
                _(
                    "This is not a valid laundry "
                    "order barcode."
                )
            )

        return {
            "raw_barcode": barcode,
            "order_barcode": barcode,
        }

    @api.model
    def _find_order_by_barcode(
        self,
        order_barcode,
    ):
        order = self.search(
            [
                (
                    "barcode",
                    "=",
                    order_barcode,
                )
            ],
            limit=1,
        )

        if not order:
            raise UserError(
                _(
                    "No laundry order was found "
                    "for this barcode."
                )
            )

        return order

    @api.model
    def _get_scanning_pos(
        self,
        pos_config_id=False,
    ):
        if not pos_config_id:
            raise UserError(
                _(
                    "The scanning POS configuration "
                    "is required."
                )
            )

        try:
            config_id = int(pos_config_id)
        except (TypeError, ValueError):
            raise UserError(
                _(
                    "The scanning POS configuration "
                    "is invalid."
                )
            )

        pos_config = self.env[
            "pos.config"
        ].browse(config_id).exists()

        if not pos_config:
            raise UserError(
                _(
                    "The scanning POS configuration "
                    "was not found."
                )
            )

        return pos_config

    def _check_barcode_access(
        self,
        source,
        scanning_pos=False,
    ):
        self.ensure_one()

        if source != "pos":
            return True

        if not scanning_pos:
            raise AccessError(
                _(
                    "The scanning POS configuration "
                    "is required."
                )
            )

        if not scanning_pos.enable_laundry_barcode:
            raise AccessError(
                _(
                    "Barcode scanning is disabled "
                    "for this POS."
                )
            )

        access_mode = (
            scanning_pos.barcode_order_access
        )

        if (
            access_mode == "own_pos"
            and self.pos_config_id != scanning_pos
        ):
            raise AccessError(
                _(
                    "This order belongs to another POS."
                )
            )

        if (
            access_mode == "same_company"
            and self.company_id
            != scanning_pos.company_id
        ):
            raise AccessError(
                _(
                    "This order belongs to another "
                    "company."
                )
            )

        return True

    def _barcode_update_status(
        self,
        new_status_id,
        scanned_barcode,
        source="pos",
        scanning_pos=False,
    ):
        self.ensure_one()

        try:
            status_id = int(new_status_id)
        except (TypeError, ValueError):
            raise UserError(
                _("The selected status is invalid.")
            )

        new_status = self.env[
            "laundry.order.status"
        ].browse(status_id).exists()

        if not new_status:
            raise UserError(
                _(
                    "The selected status was not found."
                )
            )

        if not new_status.active:
            raise UserError(
                _("The selected status is inactive.")
            )

        if not new_status.allow_barcode_update:
            raise UserError(
                _(
                    "The selected status cannot be "
                    "assigned using barcode scanning."
                )
            )

        old_status = self.status_id

        if old_status == new_status:
            self._record_barcode_activity(
                action="status_unchanged",
                source=source,
                scanning_pos=scanning_pos,
            )

            return {
                "success": True,
                "action": "status_unchanged",
                "close_popup": False,
                "message": _(
                    "The order already has the "
                    "selected status."
                ),
            }

        if (
            old_status
            and old_status.is_terminal
        ):
            raise UserError(
                _(
                    "A terminal order cannot be "
                    "updated using barcode scanning."
                )
            )

        self.write(
            {
                "status_id": new_status.id,
            }
        )

        self._record_barcode_activity(
            action="status_updated",
            source=source,
            scanning_pos=scanning_pos,
        )

        self._barcode_status_changed_hook(
            old_status=old_status,
            new_status=new_status,
            source=source,
            scanning_pos=scanning_pos,
        )

        return {
            "success": True,
            "action": "status_updated",
            "close_popup": True,
            "order_id": self.id,
            "barcode": (
                scanned_barcode or self.barcode or ""
            ),
            "old_status_id": (
                old_status.id
                if old_status
                else False
            ),
            "old_status_name": (
                old_status.display_name
                if old_status
                else ""
            ),
            "new_status_id": new_status.id,
            "new_status_name":
                new_status.display_name,
            "message": _(
                "The laundry order status "
                "was updated."
            ),
        }

    def _prepare_barcode_popup_data(
        self,
        source="pos",
        scanning_pos=False,
    ):
        """
        Prepare the response used by the barcode
        status-change popup.

        This method only prepares data. It does not
        change the order status.
        """
        self.ensure_one()

        available_statuses = self.env[
            "laundry.order.status"
        ].search(
            [
                ("active", "=", True),
                (
                    "allow_barcode_update",
                    "=",
                    True,
                ),
            ],
            order="sequence, id",
        )

        currency = (
            self.currency_id
            if (
                "currency_id" in self._fields
                and self.currency_id
            )
            else self.company_id.currency_id
        )

        current_status_id = (
            self.status_id.id
            if self.status_id
            else False
        )

        return {
            "success": True,
            "action": "status_popup",
            "message": _("Laundry order found."),
            "popup_data": {
                "title": _(
                    "Update Laundry Order Status"
                ),
                "order": {
                    "id": self.id,
                    "name": self.display_name,
                    "barcode": self.barcode or "",
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
                    "order_type_id": (
                        self.order_type_id.id
                        if self.order_type_id
                        else False
                    ),
                    "order_type_name": (
                        self.order_type_id.display_name
                        if self.order_type_id
                        else ""
                    ),
                    "status_id":
                        current_status_id,
                    "status_name": (
                        self.status_id.display_name
                        if self.status_id
                        else ""
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
                        self.total_amount or 0.0
                    ),
                    "currency": {
                        "id": currency.id,
                        "name": currency.name,
                        "symbol": currency.symbol,
                        "position": currency.position,
                        "decimal_places":
                            currency.decimal_places,
                    },
                    "origin_pos_id": (
                        self.pos_config_id.id
                        if self.pos_config_id
                        else False
                    ),
                    "origin_pos_name": (
                        self.pos_config_id.display_name
                        if self.pos_config_id
                        else ""
                    ),
                    "scanning_pos_id": (
                        scanning_pos.id
                        if scanning_pos
                        else False
                    ),
                    "scanning_pos_name": (
                        scanning_pos.display_name
                        if scanning_pos
                        else ""
                    ),
                    "source": source,
                },
                "current_status_id":
                    current_status_id,
                "available_statuses": [
                    {
                        "id": status.id,
                        "name":
                            status.display_name,
                        "color": (
                            status.color
                            or "text-primary"
                        ),
                        "sequence":
                            status.sequence,
                        "is_current": (
                            status.id
                            == current_status_id
                        ),
                    }
                    for status
                    in available_statuses
                ],
            },
        }

    def _record_barcode_activity(
        self,
        action,
        source,
        scanning_pos=False,
    ):
        self.ensure_one()

        self.write(
            {
                "barcode_last_scan_datetime":
                    fields.Datetime.now(),
                "barcode_last_action":
                    action,
                "barcode_last_source":
                    self._normalize_barcode_source(
                        source
                    ),
                "barcode_last_user_id":
                    self.env.user.id,
                "barcode_last_pos_config_id": (
                    scanning_pos.id
                    if scanning_pos
                    else False
                ),
            }
        )

        return True

    @api.model
    def _normalize_barcode_source(
        self,
        source,
    ):
        source_map = {
            "pos": "pos",
            "backend": "backend",
            "logistics": "logistics",
            "portal": "portal",
            "delivery_portal": "portal",
        }

        return source_map.get(
            source,
            "backend",
        )

    def _barcode_status_changed_hook(
        self,
        old_status,
        new_status,
        source,
        scanning_pos=False,
    ):
        """
        Central extension hook for other modules.

        Future modules such as WhatsApp notifications
        and logistics integrations can override this
        method without adding their logic directly to
        the barcode workflow.
        """
        return True
