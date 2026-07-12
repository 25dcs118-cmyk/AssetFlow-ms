from odoo import api, fields, models
from odoo.exceptions import UserError


class AssetAllocation(models.Model):
    _name = 'asset.allocation'
    _description = 'Asset Allocation'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'allocation_date desc'

    asset_id = fields.Many2one('asset.asset', required=True, tracking=True, ondelete='restrict')
    holder_type = fields.Selection([
        ('employee', 'Employee'),
        ('department', 'Department'),
    ], required=True, default='employee', tracking=True)
    employee_id = fields.Many2one('res.users', tracking=True)
    department_id = fields.Many2one('asset.department', tracking=True)
    holder_name = fields.Char(compute='_compute_holder_name', store=True)
    allocation_date = fields.Date(required=True, default=fields.Date.context_today, tracking=True)
    expected_return_date = fields.Date(tracking=True)
    actual_return_date = fields.Date(tracking=True)
    condition_out = fields.Selection([
        ('new', 'New'), ('good', 'Good'), ('fair', 'Fair'), ('poor', 'Poor'), ('damaged', 'Damaged'),
    ], string='Condition (Handover)')
    condition_in = fields.Selection([
        ('new', 'New'), ('good', 'Good'), ('fair', 'Fair'), ('poor', 'Poor'), ('damaged', 'Damaged'),
    ], string='Condition (Check-in)')
    return_notes = fields.Text(string='Condition Check-in Notes')
    state = fields.Selection([
        ('active', 'Active'),
        ('returned', 'Returned'),
        ('transferred', 'Transferred'),
    ], default='active', required=True, tracking=True)
    is_overdue = fields.Boolean(compute='_compute_is_overdue', search='_search_is_overdue')
    category_id = fields.Many2one(related='asset_id.category_id', string='Category', store=True)
    asset_department_id = fields.Many2one(related='asset_id.department_id', string='Asset Department', store=True)
    duration_days = fields.Float(compute='_compute_duration_days', store=True, string='Duration (Days)')

    @api.depends('allocation_date', 'actual_return_date')
    def _compute_duration_days(self):
        today = fields.Date.context_today(self)
        for allocation in self:
            if not allocation.allocation_date:
                allocation.duration_days = 0.0
                continue
            end = allocation.actual_return_date or today
            allocation.duration_days = max((end - allocation.allocation_date).days, 0)

    @api.depends('holder_type', 'employee_id.name', 'department_id.name')
    def _compute_holder_name(self):
        for allocation in self:
            if allocation.holder_type == 'employee':
                allocation.holder_name = allocation.employee_id.name
            else:
                allocation.holder_name = allocation.department_id.name

    @api.depends('state', 'expected_return_date')
    def _compute_is_overdue(self):
        today = fields.Date.context_today(self)
        for allocation in self:
            allocation.is_overdue = bool(
                allocation.state == 'active'
                and allocation.expected_return_date
                and allocation.expected_return_date < today
            )

    def _search_is_overdue(self, operator, value):
        today = fields.Date.context_today(self)
        domain = [('state', '=', 'active'), ('expected_return_date', '<', today)]
        if (operator == '=' and value) or (operator == '!=' and not value):
            return domain
        return ['!'] + domain

    @api.model_create_multi
    def create(self, vals_list):
        if not self.env.context.get('from_transfer'):
            for vals in vals_list:
                asset = self.env['asset.asset'].browse(vals.get('asset_id'))
                asset._check_available()
        allocations = super().create(vals_list)
        for allocation in allocations:
            allocation.asset_id.write({'state': 'allocated'})
            self.env['asset.activity.log'].log(
                allocation.asset_id, 'allocated',
                f"Asset {allocation.asset_id.tag} allocated to {allocation.holder_name}."
            )
        return allocations

    @api.model
    def _cron_flag_overdue(self):
        overdue = self.search([('is_overdue', '=', True)])
        for allocation in overdue:
            self.env['asset.activity.log'].log(
                allocation.asset_id, 'overdue',
                f"Allocation of {allocation.asset_id.tag} to {allocation.holder_name} is overdue "
                f"(expected return {allocation.expected_return_date})."
            )
            allocation.message_post(
                body=f"This allocation is overdue. Expected return date was {allocation.expected_return_date}."
            )

    def action_return(self):
        for allocation in self:
            if allocation.state != 'active':
                raise UserError("Only active allocations can be returned.")
            allocation.write({
                'state': 'returned',
                'actual_return_date': fields.Date.context_today(self),
            })
            allocation.asset_id.write({'state': 'available'})
            self.env['asset.activity.log'].log(
                allocation.asset_id, 'returned',
                f"Asset {allocation.asset_id.tag} returned by {allocation.holder_name}."
            )
        return True
