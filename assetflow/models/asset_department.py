from odoo import api, fields, models
from odoo.exceptions import ValidationError


class AssetDepartment(models.Model):
    _name = 'asset.department'
    _description = 'Department'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'complete_name'

    name = fields.Char(required=True, tracking=True)
    code = fields.Char(tracking=True)
    parent_id = fields.Many2one('asset.department', string='Parent Department', ondelete='restrict')
    child_ids = fields.One2many('asset.department', 'parent_id', string='Sub-Departments')
    complete_name = fields.Char(compute='_compute_complete_name', store=True, recursive=True)
    department_head_id = fields.Many2one(
        'res.users', string='Department Head',
        domain="[('assetflow_role', 'in', ('department_head', 'admin'))]", tracking=True)
    employee_ids = fields.One2many('res.users', 'department_id', string='Employees')
    employee_count = fields.Integer(compute='_compute_employee_count')
    asset_ids = fields.One2many('asset.asset', 'department_id', string='Assets')
    asset_count = fields.Integer(compute='_compute_asset_count')
    active = fields.Boolean(default=True)
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)

    _sql_constraints = [
        ('code_uniq', 'unique(code, company_id)', 'Department code must be unique.'),
    ]

    @api.depends('name', 'parent_id.complete_name')
    def _compute_complete_name(self):
        for dept in self:
            if dept.parent_id:
                dept.complete_name = f"{dept.parent_id.complete_name} / {dept.name}"
            else:
                dept.complete_name = dept.name

    def _compute_employee_count(self):
        for dept in self:
            dept.employee_count = len(dept.employee_ids)

    def _compute_asset_count(self):
        for dept in self:
            dept.asset_count = len(dept.asset_ids)

    @api.constrains('parent_id')
    def _check_parent_recursion(self):
        if not self._check_recursion():
            raise ValidationError("A department cannot be its own ancestor.")

    def action_view_assets(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Assets',
            'res_model': 'asset.asset',
            'view_mode': 'list,form',
            'domain': [('department_id', '=', self.id)],
            'context': {'default_department_id': self.id},
        }
