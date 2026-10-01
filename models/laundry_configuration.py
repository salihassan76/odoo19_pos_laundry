from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class LaundryConfiguration(models.Model):
    _name = "laundry.configuration"
    _description = "Laundry Configuration"
    _order = "name, id"

    _sql_constraints = [
        ("unique_pos_config", "unique(pos_config_id)", "Each POS can only have one Laundry Configuration."),
    ]

    name = fields.Char(string="Configuration Name", required=True)
    active = fields.Boolean(default=True)
    pos_config_id = fields.Many2one(
        "pos.config", string="Point of Sale", required=True, ondelete="cascade", index=True
    )
    company_id = fields.Many2one(related="pos_config_id.company_id", store=True, readonly=True)

    is_project = fields.Boolean(string="Enable Project", default=False)
    project_id = fields.Many2one(
        "project.project",
        string="Project",
        domain="[('company_id', 'in', [False, company_id])]",
    )

    unpaid_payment_id = fields.Many2one("laundry.order.payment.status", string="Unpaid Status", domain="[('laundry_configuration_id', '=', id)]")
    partial_payment_id = fields.Many2one("laundry.order.payment.status", string="Partial Paid Status", domain="[('laundry_configuration_id', '=', id)]")
    paid_payment_id = fields.Many2one("laundry.order.payment.status", string="Paid Status", domain="[('laundry_configuration_id', '=', id)]")
    cancelled_payment_id = fields.Many2one("laundry.order.payment.status", string="Cancelled Status", domain="[('laundry_configuration_id', '=', id)]")
    refund_payment_id = fields.Many2one("laundry.order.payment.status", string="Refund Status", domain="[('laundry_configuration_id', '=', id)]")

    order_status_id = fields.Many2one("laundry.order.status", string="Default Order Status", domain="[('laundry_configuration_id', '=', id)]")
    complete_order_status_id = fields.Many2one("laundry.order.status", string="Complete Order Status", domain="[('laundry_configuration_id', '=', id)]")
    refunded_order_status_id = fields.Many2one("laundry.order.status", string="Refunded Order Status", domain="[('laundry_configuration_id', '=', id)]")
    cancelled_order_status_id = fields.Many2one("laundry.order.status", string="Cancelled Order Status", domain="[('laundry_configuration_id', '=', id)]")
    confirmed_order_status_id = fields.Many2one("laundry.order.status", string="Confirmed Order Status", domain="[('laundry_configuration_id', '=', id)]")
    ready_order_status_id = fields.Many2one(
        "laundry.order.status", string="Ready Order Status", domain="[('active', '=', True), ('laundry_configuration_id', '=', id)]"
    )

    direct_print = fields.Boolean(string="Print After Save/Validate", default=False)
    show_receipt_preview = fields.Boolean(string="Show Receipt Preview", default=True)
    enable_laundry_barcode = fields.Boolean(string="Enable Laundry Barcode")
    continuous_barcode_scan = fields.Boolean(string="Continuous Scanning", default=True)
    barcode_order_access = fields.Selection(
        [("own_pos", "Orders Created by This POS"), ("same_company", "All Company Orders")],
        string="Barcode Order Access",
        default="own_pos",
        required=True,
    )
    duplicate_scan_delay = fields.Integer(string="Duplicate Scan Delay (Seconds)", default=2)

    @api.constrains("is_project", "project_id")
    def _check_project(self):
        for record in self:
            if record.is_project and not record.project_id:
                raise ValidationError(_("Select a project when project integration is enabled."))

    @api.constrains("duplicate_scan_delay")
    def _check_duplicate_scan_delay(self):
        for record in self:
            if record.duplicate_scan_delay < 0:
                raise ValidationError(_("Duplicate scan delay cannot be negative."))

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get("name") and vals.get("pos_config_id"):
                vals["name"] = self.env["pos.config"].browse(vals["pos_config_id"]).display_name
        return super().create(vals_list)

    @api.onchange("pos_config_id")
    def _onchange_pos_config_id(self):
        if self.pos_config_id and (not self.name or self.name == "Laundry Configuration"):
            self.name = self.pos_config_id.display_name

    @api.model
    def _get_pos_config_from_context(self):
        pos_config_id = self.env.context.get("default_pos_config_id") or self.env.context.get("pos_config_id")
        return self.env["pos.config"].browse(pos_config_id).exists() if pos_config_id else self.env["pos.config"]

    @api.model
    def action_open_laundry_configuration(self):
        pos_config = self._get_pos_config_from_context()
        if not pos_config:
            raise UserError(_("Please select a Point of Sale first."))
        config = self.search([("pos_config_id", "=", pos_config.id)], limit=1)
        if not config:
            config = self.create({"name": pos_config.display_name, "pos_config_id": pos_config.id})
        return {
            "type": "ir.actions.act_window",
            "name": _("Laundry Settings"),
            "res_model": "laundry.configuration",
            "view_mode": "form",
            "views": [(False, "form")],
            "res_id": config.id,
            "target": "current",
        }

    def get_configuration_status(self):
        self.ensure_one()
        items = []

        def add(name, value):
            items.append({"name": name, "ok": bool(value)})

        add(_("Default Order Status"), self.order_status_id)
        add(_("Complete Order Status"), self.complete_order_status_id)
        add(_("Refunded Order Status"), self.refunded_order_status_id)
        add(_("Cancelled Order Status"), self.cancelled_order_status_id)
        add(_("Confirmed Order Status"), self.confirmed_order_status_id)
        add(_("Ready Order Status"), self.ready_order_status_id)
        add(_("Unpaid Payment Status"), self.unpaid_payment_id)
        add(_("Partial Paid Payment Status"), self.partial_payment_id)
        add(_("Paid Payment Status"), self.paid_payment_id)
        add(_("Cancelled Payment Status"), self.cancelled_payment_id)
        add(_("Refunded Payment Status"), self.refund_payment_id)
        add(
            _("Laundry Order Types"),
            self.env["laundry.order.type"].search_count(
                [("active", "=", True), ("is_hidden", "=", False), ("laundry_configuration_id", "=", self.id)]
            ),
        )
        if self.is_project:
            add(_("Project"), self.project_id)
        return {"valid": all(item["ok"] for item in items), "items": items}

    def check_configuration(self):
        self.ensure_one()
        status = self.get_configuration_status()
        if status["valid"]:
            return True
        missing = [item["name"] for item in status["items"] if not item["ok"]]
        raise UserError(
            _("Laundry POS configuration is incomplete.\n\nPlease configure:\n- %s")
            % "\n- ".join(missing)
        )

    def as_pos_config_values(self):
        """Return primitive values injected into the POS config payload."""
        self.ensure_one()
        names = [
            "is_project", "project_id", "unpaid_payment_id", "partial_payment_id",
            "paid_payment_id", "cancelled_payment_id", "refund_payment_id", "order_status_id",
            "complete_order_status_id", "refunded_order_status_id", "cancelled_order_status_id",
            "confirmed_order_status_id", "ready_order_status_id", "direct_print",
            "show_receipt_preview", "enable_laundry_barcode", "continuous_barcode_scan",
            "barcode_order_access", "duplicate_scan_delay",
        ]
        values = {"laundry_configuration_id": self.id}
        for name in names:
            value = self[name]
            values[name] = value.id if isinstance(value, models.BaseModel) else value
        return values
