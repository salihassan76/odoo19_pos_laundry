from odoo import api, fields, models, _
from odoo.exceptions import AccessError, UserError


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

    # -------------------------------------------------------------------------
    # ORM
    # -------------------------------------------------------------------------

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

    # -------------------------------------------------------------------------
    # Public barcode entry points
    # -------------------------------------------------------------------------

    @api.model
    def process_pos_barcode(
        self,
        scanned_barcode,
        pos_config_id,
        requested_status_id=False,
    ):
        """
        Process a barcode scan originating from the POS.

        The source is determined by this method and cannot be supplied or
        changed by the RPC caller.
        """
        scanning_pos = self._get_authorized_scanning_pos(
            pos_config_id=pos_config_id,
        )

        return self._process_barcode_internal(
            scanned_barcode=scanned_barcode,
            source="pos",
            scanning_pos=scanning_pos,
            requested_status_id=requested_status_id,
        )

    @api.model
    def process_backend_barcode(
        self,
        scanned_barcode,
        requested_status_id=False,
    ):
        """
        Process a barcode scan originating from the Odoo backend.

        Only authenticated internal users may use this entry point. Normal
        model ACLs, record rules, and company restrictions still apply.
        """
        if not self.env.user._is_internal():
            raise AccessError(
                _(
                    "Only internal users can use "
                    "backend barcode scanning."
                )
            )

        return self._process_barcode_internal(
            scanned_barcode=scanned_barcode,
            source="backend",
            scanning_pos=self.env["pos.config"],
            requested_status_id=requested_status_id,
        )

    # -------------------------------------------------------------------------
    # Shared internal processor
    # -------------------------------------------------------------------------

    @api.model
    def _process_barcode_internal(
        self,
        scanned_barcode,
        source,
        scanning_pos=False,
        requested_status_id=False,
    ):
        """
        Shared internal barcode processor.

        This method is private and must only be called by trusted public entry
        points that set the source themselves.
        """
        if source not in {"pos", "backend"}:
            raise AccessError(
                _("Unsupported barcode processing channel.")
            )

        parsed = self._parse_laundry_barcode(
            scanned_barcode
        )

        order = self._find_order_by_barcode(
            parsed["order_barcode"]
        )

        order._check_barcode_access(
            source=source,
            scanning_pos=scanning_pos,
            operation=(
                "write"
                if requested_status_id
                else "read"
            ),
        )

        if requested_status_id:
            return order._barcode_update_status(
                new_status_id=requested_status_id,
                scanned_barcode=parsed["raw_barcode"],
                source=source,
                scanning_pos=scanning_pos,
            )

        popup_data = order._prepare_barcode_popup_data(
            source=source,
            scanning_pos=scanning_pos,
        )

        order._record_barcode_activity(
            action="status_popup",
            source=source,
            scanning_pos=scanning_pos,
        )

        return popup_data

    # -------------------------------------------------------------------------
    # Barcode parsing and order lookup
    # -------------------------------------------------------------------------

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

    # -------------------------------------------------------------------------
    # POS authorization
    # -------------------------------------------------------------------------

    @api.model
    def _get_authorized_scanning_pos(
        self,
        pos_config_id=False,
    ):
        """
        Return a validated POS configuration for a POS barcode request.
        """
        if not pos_config_id:
            raise AccessError(
                _(
                    "The scanning POS configuration "
                    "is required."
                )
            )

        try:
            config_id = int(pos_config_id)
        except (TypeError, ValueError):
            raise AccessError(
                _(
                    "The scanning POS configuration "
                    "is invalid."
                )
            )

        pos_config = self.env[
            "pos.config"
        ].browse(config_id).exists()

        if not pos_config:
            raise AccessError(
                _(
                    "The scanning POS configuration "
                    "was not found."
                )
            )

        self._check_record_access(
            pos_config,
            operation="read",
        )

        if (
            "active" in pos_config._fields
            and not pos_config.active
        ):
            raise AccessError(
                _("The POS configuration is inactive.")
            )

        if (
            "enable_laundry_workflow"
            in pos_config._fields
            and not pos_config.enable_laundry_workflow
        ):
            raise AccessError(
                _(
                    "The laundry workflow is disabled "
                    "for this POS."
                )
            )

        laundry_config = pos_config._get_laundry_configuration()
        if not laundry_config or not laundry_config.enable_laundry_barcode:
            raise AccessError(
                _(
                    "Barcode scanning is disabled "
                    "for this POS."
                )
            )

        if (
            pos_config.company_id
            not in self.env.user.company_ids
        ):
            raise AccessError(
                _(
                    "You are not authorized to use "
                    "this POS configuration."
                )
            )

        return pos_config

    def _check_barcode_access(
        self,
        source,
        scanning_pos=False,
        operation="read",
    ):
        """
        Enforce channel-specific order authorization.

        The method fails closed for unknown sources, invalid access modes,
        unavailable companies, and missing POS configurations.
        """
        self.ensure_one()

        if operation not in {"read", "write"}:
            raise AccessError(
                _("Unsupported barcode operation.")
            )

        self._check_record_access(
            self,
            operation=operation,
        )

        if (
            self.company_id
            and self.company_id
            not in self.env.user.company_ids
        ):
            raise AccessError(
                _(
                    "You are not authorized to access "
                    "orders from this company."
                )
            )

        if source == "backend":
            if not self.env.user._is_internal():
                raise AccessError(
                    _(
                        "Only internal users can use "
                        "backend barcode scanning."
                    )
                )

            return True

        if source != "pos":
            raise AccessError(
                _("Unauthorized barcode source.")
            )

        if not scanning_pos or len(scanning_pos) != 1:
            raise AccessError(
                _(
                    "A valid scanning POS configuration "
                    "is required."
                )
            )

        self._check_record_access(
            scanning_pos,
            operation="read",
        )

        if (
            "active" in scanning_pos._fields
            and not scanning_pos.active
        ):
            raise AccessError(
                _("The POS configuration is inactive.")
            )

        if (
            "enable_laundry_workflow"
            in scanning_pos._fields
            and not scanning_pos.enable_laundry_workflow
        ):
            raise AccessError(
                _(
                    "The laundry workflow is disabled "
                    "for this POS."
                )
            )

        laundry_config = scanning_pos._get_laundry_configuration()
        if not laundry_config or not laundry_config.enable_laundry_barcode:
            raise AccessError(
                _(
                    "Barcode scanning is disabled "
                    "for this POS."
                )
            )

        if (
            scanning_pos.company_id
            not in self.env.user.company_ids
        ):
            raise AccessError(
                _(
                    "You are not authorized to use "
                    "this POS configuration."
                )
            )

        if self.company_id != scanning_pos.company_id:
            raise AccessError(
                _(
                    "The order and scanning POS belong "
                    "to different companies."
                )
            )

        access_mode = (
            laundry_config.barcode_order_access
            or ""
        )

        if access_mode == "own_pos":
            if not self.pos_config_id:
                raise AccessError(
                    _(
                        "This order is not assigned "
                        "to a POS configuration."
                    )
                )

            if self.pos_config_id != scanning_pos:
                raise AccessError(
                    _(
                        "This order belongs to another POS."
                    )
                )

        elif access_mode == "same_company":
            # Company equality was already checked above.
            pass

        else:
            raise AccessError(
                _(
                    "The POS barcode access policy "
                    "is invalid."
                )
            )

        return True

    @api.model
    def _check_record_access(
        self,
        record,
        operation="read",
    ):
        """
        Apply standard Odoo ACLs and record rules.

        Kept in one helper for compatibility and to avoid accidentally using
        sudo in barcode processing.
        """
        record.check_access_rights(
            operation,
            raise_exception=True,
        )
        record.check_access_rule(
            operation,
        )

        return True

    # -------------------------------------------------------------------------
    # Status transition validation
    # -------------------------------------------------------------------------

    def _get_allowed_barcode_next_status(
        self,
    ):
        """
        Return the single configured next status after validating the existing
        PR-1 workflow rules.

        PR 2 can replace this method with channel-specific transition records
        without changing the popup or status-update methods.
        """
        self.ensure_one()

        current_status = self.status_id

        if not current_status:
            raise UserError(
                _("The order does not have a current status.")
            )

        if current_status.is_terminal:
            raise UserError(
                _(
                    "A terminal order cannot be updated "
                    "using barcode scanning."
                )
            )

        next_status = current_status.next_status_id

        if not next_status:
            raise UserError(
                _(
                    "No next status is configured for '%s'."
                )
                % current_status.display_name
            )

        if not next_status.active:
            raise UserError(
                _(
                    "The configured next status '%s' "
                    "is inactive."
                )
                % next_status.display_name
            )

        if not next_status.allow_barcode_update:
            raise UserError(
                _(
                    "The next status '%s' does not allow "
                    "barcode updates."
                )
                % next_status.display_name
            )

        return next_status

    # -------------------------------------------------------------------------
    # Status update
    # -------------------------------------------------------------------------

    def _barcode_update_status(
        self,
        new_status_id,
        scanned_barcode,
        source="pos",
        scanning_pos=False,
    ):
        self.ensure_one()

        # Defence in depth: never rely only on the popup-load authorization.
        self._check_barcode_access(
            source=source,
            scanning_pos=scanning_pos,
            operation="write",
        )

        old_status = self.status_id
        expected_status = (
            self._get_allowed_barcode_next_status()
        )

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
                _("The selected status was not found.")
            )

        if new_status != expected_status:
            raise UserError(
                _(
                    "The selected status is not the "
                    "configured next status."
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
            "old_status_id": old_status.id,
            "old_status_name": old_status.display_name,
            "new_status_id": new_status.id,
            "new_status_name": new_status.display_name,
            "message": _(
                "The laundry order status was updated "
                "from '%(old_status)s' to '%(new_status)s'."
            )
            % {
                "old_status": old_status.display_name,
                "new_status": new_status.display_name,
            },
        }

    # -------------------------------------------------------------------------
    # Popup data
    # -------------------------------------------------------------------------

    def _prepare_barcode_popup_data(
        self,
        source="pos",
        scanning_pos=False,
    ):
        """
        Prepare the barcode confirmation popup.

        Only the configured next status is returned, provided it is active and
        allows barcode updates.
        """
        self.ensure_one()

        current_status = self.status_id
        next_status = (
            self._get_allowed_barcode_next_status()
        )

        currency = (
            self.currency_id
            if (
                "currency_id" in self._fields
                and self.currency_id
            )
            else self.company_id.currency_id
        )

        return {
            "success": True,
            "action": "status_popup",
            "message": _("Laundry order found."),
            "popup_data": {
                "title": _("Confirm Status Update"),
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
                    "total_amount": self.total_amount or 0.0,
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
                "current_status": {
                    "id": current_status.id,
                    "name": current_status.display_name,
                    "color": (
                        current_status.color
                        or "text-primary"
                    ),
                },
                "next_status": {
                    "id": next_status.id,
                    "name": next_status.display_name,
                    "color": (
                        next_status.color
                        or "text-primary"
                    ),
                },
            },
        }

    # -------------------------------------------------------------------------
    # Activity tracking
    # -------------------------------------------------------------------------

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
        }

        normalized_source = source_map.get(source)

        if not normalized_source:
            raise AccessError(
                _("Unsupported barcode source.")
            )

        return normalized_source

    # -------------------------------------------------------------------------
    # Extension hook
    # -------------------------------------------------------------------------

    def _barcode_status_changed_hook(
        self,
        old_status,
        new_status,
        source,
        scanning_pos=False,
    ):
        """
        Central extension hook for future modules.

        WhatsApp, logistics, and portal modules can override this method
        without putting integration-specific logic inside the core barcode
        workflow.
        """
        return True
