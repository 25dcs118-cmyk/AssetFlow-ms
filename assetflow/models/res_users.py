from odoo import api, fields, models
from odoo.exceptions import AccessError


class ResUsers(models.Model):
    _inherit = 'res.users'

    department_id = fields.Many2one('asset.department', string='Department')
    employee_status = fields.Selection([
        ('active', 'Active'),
        ('inactive', 'Inactive'),
    ], string='Employee Status', default='active')
    assetflow_role = fields.Selection([
        ('employee', 'Employee'),
        ('department_head', 'Department Head'),
        ('asset_manager', 'Asset Manager'),
        ('admin', 'Admin'),
    ], string='AssetFlow Role', compute='_compute_assetflow_role', store=True)
    allocation_ids = fields.One2many('asset.allocation', 'employee_id', string='Allocations')
    booking_ids = fields.One2many('resource.booking', 'requester_id', string='Bookings')

    @api.depends('groups_id')
    def _compute_assetflow_role(self):
        group_admin = self.env.ref('assetflow.group_assetflow_admin', raise_if_not_found=False)
        group_manager = self.env.ref('assetflow.group_assetflow_asset_manager', raise_if_not_found=False)
        group_head = self.env.ref('assetflow.group_assetflow_department_head', raise_if_not_found=False)
        for user in self:
            if group_admin and group_admin in user.groups_id:
                user.assetflow_role = 'admin'
            elif group_manager and group_manager in user.groups_id:
                user.assetflow_role = 'asset_manager'
            elif group_head and group_head in user.groups_id:
                user.assetflow_role = 'department_head'
            else:
                user.assetflow_role = 'employee'

    @api.model_create_multi
    def create(self, vals_list):
        users = super().create(vals_list)
        group_employee = self.env.ref('assetflow.group_assetflow_employee', raise_if_not_found=False)
        if group_employee:
            group_employee.sudo().write({'users': [(4, user.id) for user in users]})
        return users

    def _check_assetflow_admin(self):
        if not self.env.user.has_group('assetflow.group_assetflow_admin'):
            raise AccessError("Only an Admin can change AssetFlow roles.")

    def action_promote_department_head(self):
        self._check_assetflow_admin()
        group = self.env.ref('assetflow.group_assetflow_department_head')
        group.sudo().write({'users': [(4, user.id) for user in self]})

    def action_promote_asset_manager(self):
        self._check_assetflow_admin()
        group = self.env.ref('assetflow.group_assetflow_asset_manager')
        group.sudo().write({'users': [(4, user.id) for user in self]})

    def action_demote_to_employee(self):
        self._check_assetflow_admin()
        group_head = self.env.ref('assetflow.group_assetflow_department_head')
        group_manager = self.env.ref('assetflow.group_assetflow_asset_manager')
        group_admin = self.env.ref('assetflow.group_assetflow_admin')
        for group in (group_head, group_manager, group_admin):
            group.sudo().write({'users': [(3, user.id) for user in self]})
