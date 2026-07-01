from odoo import models, fields


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    pos_enable_laundry_workflow = fields.Boolean(
        related="pos_config_id.enable_laundry_workflow",
        readonly=False,
        string="Laundry Workflow",
    )

    laundry_config_status = fields.Selection(
        [
            ("complete", "Complete"),
            ("incomplete", "Incomplete"),
        ],
        string="Laundry Configuration Status",
        compute="_compute_laundry_config_status",
    )

    def _compute_laundry_config_status(self):
        for rec in self:
            pos_config = rec.pos_config_id

            if not pos_config:
                rec.laundry_config_status = "incomplete"
                continue

            status = self.env["laundry.configuration"].get_configuration_status(pos_config)
            rec.laundry_config_status = "complete" if status.get("valid") else "incomplete"

    def action_open_laundry_configuration(self):
        self.ensure_one()

        return self.env["laundry.configuration"].with_context(
            pos_config_id=self.pos_config_id.id,
            default_pos_config_id=self.pos_config_id.id,
        ).action_open_laundry_configuration()