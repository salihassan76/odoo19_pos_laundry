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


            if not pos_config or not pos_config.enable_laundry_workflow:
                rec.laundry_config_status = "incomplete"
                continue
                            
            status = pos_config.get_laundry_configuration_status()
            rec.laundry_config_status = "complete" if status.get("valid") else "incomplete"

    def action_check_laundry_configuration(self):
        self.ensure_one()
        self.pos_config_id.check_laundry_configuration()
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": "Laundry Configuration",
                "message": "Laundry configuration is complete.",
                "type": "success",
                "sticky": False,
            },
        }
    
    def action_open_laundry_pos_config(self):
        self.ensure_one()

        return {
            "type": "ir.actions.act_window",
            "name": "Laundry Configuration",
            "res_model": "pos.config",
            "view_mode": "form",
            "view_id": self.env.ref(
                "pos_laundry.view_pos_config_form_laundry_only"
            ).id,
            "res_id": self.pos_config_id.id,
            "target": "current",
            "context": {
                "form_view_initial_mode": "edit",
            },
        }