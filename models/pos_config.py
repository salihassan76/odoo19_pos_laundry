from odoo import api, models, fields


class PosConfig(models.Model):
    _inherit = "pos.config"

    enable_laundry_workflow = fields.Boolean(
        string="Enable Laundry Workflow",
        default=False,
    )

    @api.model
    def _load_pos_data_read(self, records, config):
        data = super()._load_pos_data_read(records, config)

        for record in data:
            if "enable_laundry_workflow" not in record:
                pos_config = self.browse(record["id"])
                record["enable_laundry_workflow"] = pos_config.enable_laundry_workflow

        return data