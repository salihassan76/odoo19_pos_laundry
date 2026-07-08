from odoo import models, fields, api

class LaundryOrderStatus(models.Model):
    _name = "laundry.order.status"
    _description = "Laundry Order Status"
    _order = "sequence,id"

    name = fields.Char(required=True)
    active = fields.Boolean(default=True)
    sequence = fields.Integer(default=10)
    show_on_home = fields.Boolean(
        string="Show on POS Home",
        default=True,
        help="Display this status as a section on the POS customer home screen."
    )
    show_on_home_period = fields.Selection([
            ("0", "Always"),
            ("1", "1 Day"),
            ("3", "3 Days"),
            ("7", "1 Week"),
            ("14", "2 Weeks"),
            ("30", "1 Month"),
            ("90", "3 Months"),
        ], default="0")
        
    color = fields.Selection([
    ("text-primary", "Blue"),
    ("text-danger", "Red"),
    ("text-info", "Cyan"),
    ("text-warning", "Yellow"),
    ("text-dark", "Black"),
    ("text-success", "Green"),
    ], default="text-primary",string="Color", help="Select a color for this status to visually distinguish it in the POS interface.")