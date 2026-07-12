from odoo import api, fields, models


class AssetCategory(models.Model):
    _name = 'asset.category'
    _description = 'Asset Category'
    _order = 'name'

    name = fields.Char(required=True)
    code = fields.Char()
    parent_id = fields.Many2one('asset.category', string='Parent Category', ondelete='restrict')
    child_ids = fields.One2many('asset.category', 'parent_id', string='Sub-Categories')
    warranty_period = fields.Integer(string='Warranty Period (months)')
    default_bookable = fields.Boolean(string='Default Bookable', default=False)
    asset_ids = fields.One2many('asset.asset', 'category_id', string='Assets')
    asset_count = fields.Integer(compute='_compute_asset_count')
    active = fields.Boolean(default=True)

    _sql_constraints = [
        ('code_uniq', 'unique(code)', 'Category code must be unique.'),
    ]

    def _compute_asset_count(self):
        for category in self:
            category.asset_count = len(category.asset_ids)
