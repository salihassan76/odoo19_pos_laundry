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
            config = self.env["laundry.configuration"].search([], limit=1)

            if not config:
                rec.laundry_config_status = "incomplete"
                continue

            status = config.get_configuration_status()
            rec.laundry_config_status = "complete" if status.get("valid") else "incomplete"
            
    def action_open_laundry_configuration(self):
        config = self.env["laundry.configuration"].search([], limit=1)

        if not config:
            config = self.env["laundry.configuration"].create({})

        return {
            "type": "ir.actions.act_window",
            "name": "Laundry Settings",
            "res_model": "laundry.configuration",
            "view_mode": "form",
            "res_id": config.id,
            "target": "current",
        }
    

