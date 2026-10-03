from odoo import api, fields, models


def _assign_selected_laundry_configuration(env, vals_list):
    """Assign records created from a Laundry workspace to its selected shop."""
    configuration_id = env.context.get("default_laundry_configuration_id")
    configuration_commands = env.context.get("default_laundry_configuration_ids")
    if not configuration_commands and configuration_id:
        configuration_commands = [(6, 0, [configuration_id])]
    if configuration_commands:
        for vals in vals_list:
            vals.setdefault("laundry_configuration_ids", configuration_commands)


class PosCategory(models.Model):
    _inherit = "pos.category"

    laundry_configuration_ids = fields.Many2many(
        "laundry.configuration",
        "pos_category_laundry_configuration_rel",
        "category_id",
        "configuration_id",
        string="Laundry Shops",
    )
    laundry_pos_config_ids = fields.Many2many(
        "pos.config",
        string="Assigned POS Shops",
        compute="_compute_laundry_pos_config_ids",
    )

    @api.depends("laundry_configuration_ids.pos_config_id")
    def _compute_laundry_pos_config_ids(self):
        for category in self:
            category.laundry_pos_config_ids = (
                category.laundry_configuration_ids.mapped("pos_config_id")
            )

    @api.model_create_multi
    def create(self, vals_list):
        _assign_selected_laundry_configuration(self.env, vals_list)
        return super().create(vals_list)


class ProductTemplate(models.Model):
    _inherit = "product.template"

    laundry_configuration_ids = fields.Many2many(
        "laundry.configuration",
        "product_template_laundry_configuration_rel",
        "product_tmpl_id",
        "configuration_id",
        string="Laundry Shops",
    )
    laundry_pos_config_ids = fields.Many2many(
        "pos.config",
        string="Assigned POS Shops",
        compute="_compute_laundry_pos_config_ids",
    )

    @api.depends("laundry_configuration_ids.pos_config_id")
    def _compute_laundry_pos_config_ids(self):
        for product in self:
            product.laundry_pos_config_ids = (
                product.laundry_configuration_ids.mapped("pos_config_id")
            )

    @api.model_create_multi
    def create(self, vals_list):
        _assign_selected_laundry_configuration(self.env, vals_list)
        return super().create(vals_list)
