from odoo import _, fields, models
from odoo.exceptions import UserError


class LaundryOrderStatus(models.Model):
    _name = "laundry.order.status"
    _description = "Laundry Order Status"
    _order = "sequence, id"

    ACTION_FIELD_MAP = {
        "edit": "can_edit",
        "cancel": "can_cancel",
        "payment": "can_receive_payment",
        "refund": "can_refund",
        "print": "can_print",
    }

    name = fields.Char(
        string="Status Name",
        required=True,
        translate=True,
    )

    active = fields.Boolean(
        default=True,
    )

    sequence = fields.Integer(
        default=10,
    )

    show_on_home = fields.Boolean(
        string="Show on POS Home",
        default=True,
        help=(
            "Display orders with this status as a section "
            "on the POS laundry home screen."
        ),
    )

    show_on_home_period = fields.Selection(
        selection=[
            ("0", "Always"),
            ("1", "1 Day"),
            ("3", "3 Days"),
            ("7", "1 Week"),
            ("14", "2 Weeks"),
            ("30", "1 Month"),
            ("90", "3 Months"),
        ],
        string="Show Orders For",
        default="0",
        required=True,
        help=(
            "Controls how far back orders with this status "
            "are shown on the POS home screen."
        ),
    )

    color = fields.Selection(
        selection=[
            ("text-primary", "Blue"),
            ("text-danger", "Red"),
            ("text-info", "Cyan"),
            ("text-warning", "Yellow"),
            ("text-dark", "Black"),
            ("text-success", "Green"),
        ],
        string="Color",
        default="text-primary",
        required=True,
        help=(
            "Select a color to visually distinguish this status "
            "in the POS interface."
        ),
    )

    # ---------------------------------------------------------
    # Action capabilities
    # ---------------------------------------------------------

    can_edit = fields.Boolean(
        string="Allow Editing",
        default=False,
        help=(
            "Allow products, quantities, customer, order type "
            "and other editable order details to be changed."
        ),
    )

    can_cancel = fields.Boolean(
        string="Allow Cancellation",
        default=False,
        help=(
            "Allow a saved laundry order in this status "
            "to be cancelled."
        ),
    )

    can_receive_payment = fields.Boolean(
        string="Allow Payment",
        default=False,
        help=(
            "Allow payments to be received while the laundry "
            "order is in this status."
        ),
    )

    can_refund = fields.Boolean(
        string="Allow Refund",
        default=False,
        help=(
            "Allow payments associated with an order in this "
            "status to be refunded."
        ),
    )

    can_print = fields.Boolean(
        string="Allow Printing",
        default=True,
        help=(
            "Allow the laundry order receipt or order document "
            "to be printed."
        ),
    )

    is_terminal = fields.Boolean(
        string="Terminal Status",
        default=False,
        help=(
            "Indicates that the normal operational workflow has ended, "
            "for example Completed, Cancelled or Refunded."
        ),
    )

    # ---------------------------------------------------------
    # POS helpers
    # ---------------------------------------------------------

    def get_pos_capabilities(self):
        """Return status details and capabilities for the POS."""
        self.ensure_one()

        return {
            "id": self.id,
            "name": self.display_name,
            "sequence": self.sequence,
            "active": bool(self.active),
            "show_on_home": bool(self.show_on_home),
            "show_on_home_period": self.show_on_home_period or "0",
            "color": self.color or "text-primary",
            "can_edit": bool(self.can_edit),
            "can_cancel": bool(self.can_cancel),
            "can_receive_payment": bool(
                self.can_receive_payment
            ),
            "can_refund": bool(self.can_refund),
            "can_print": bool(self.can_print),
            "is_terminal": bool(self.is_terminal),
        }

    def allows_action(self, action):
        """Return whether this status allows the requested action."""
        self.ensure_one()

        field_name = self.ACTION_FIELD_MAP.get(action)

        if not field_name:
            return False

        return bool(self[field_name])

    def check_action_allowed(self, action):
        """Raise a clear error when an action is not allowed."""
        self.ensure_one()

        action_labels = {
            "edit": _("editing"),
            "cancel": _("cancellation"),
            "payment": _("payment"),
            "refund": _("refund"),
            "print": _("printing"),
        }

        if action not in self.ACTION_FIELD_MAP:
            raise UserError(
                _("Unsupported laundry order action: %s")
                % action
            )

        if not self.allows_action(action):
            raise UserError(
                _(
                    "The order status '%(status)s' does not "
                    "allow %(action)s."
                )
                % {
                    "status": self.display_name,
                    "action": action_labels[action],
                }
            )

        return True