from odoo import api, fields, models
from odoo.exceptions import AccessError, UserError


class AssetTransfer(models.Model):
    _name = 'asset.transfer'
    _description = 'Asset Transfer Request'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'request_date desc'

    asset_id = fields.Many2one('asset.asset', required=True, tracking=True, ondelete='restrict')
    old_allocation_id = fields.Many2one('asset.allocation', string='Current Allocation', tracking=True)
    new_holder_type = fields.Selection([
        ('employee', 'Employee'),
        ('department', 'Department'),
    ], required=True, default='employee', tracking=True)
    new_employee_id = fields.Many2one('res.users', string='New Employee', tracking=True)
    new_department_id = fields.Many2one('asset.department', string='New Department', tracking=True)
    expected_return_date = fields.Date()
    requested_by = fields.Many2one('res.users', default=lambda self: self.env.user, required=True, tracking=True)
    approved_by = fields.Many2one('res.users', tracking=True)
    request_date = fields.Datetime(default=fields.Datetime.now, required=True)
    approval_date = fields.Datetime()
    state = fields.Selection([
        ('requested', 'Requested'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('completed', 'Completed'),
    ], default='requested', required=True, tracking=True)
    new_allocation_id = fields.Many2one('asset.allocation', string='New Allocation', readonly=True)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('old_allocation_id'):
                asset = self.env['asset.asset'].browse(vals.get('asset_id'))
                vals['old_allocation_id'] = asset.current_allocation_id.id
        transfers = super().create(vals_list)
        managers = self.env['res.users'].search([
            ('groups_id', 'in', self.env.ref('assetflow.group_assetflow_asset_manager').id),
        ])
        for transfer in transfers:
            self.env['asset.activity.log'].log(
                transfer.asset_id, 'transfer_requested',
                f"Transfer requested for asset {transfer.asset_id.tag}."
            )
            approvers = managers
            dept_head = transfer.asset_id.department_id.department_head_id
            if dept_head:
                approvers |= dept_head
            if approvers:
                transfer.message_post(
                    body=f"New transfer request for {transfer.asset_id.tag} awaiting your approval.",
                    partner_ids=approvers.mapped('partner_id.id'),
                )
        return transfers

    def _check_can_approve(self):
        user = self.env.user
        for transfer in self:
            is_manager = user.has_group('assetflow.group_assetflow_asset_manager')
            is_dept_head = (
                user.has_group('assetflow.group_assetflow_department_head')
                and transfer.asset_id.department_id
                and transfer.asset_id.department_id.department_head_id == user
            )
            if not (is_manager or is_dept_head):
                raise AccessError("Only the Asset Manager or the asset's own Department Head can approve this transfer.")

    def action_approve(self):
        self._check_can_approve()
        for transfer in self:
            if transfer.state != 'requested':
                raise UserError("Only requested transfers can be approved.")
            if transfer.old_allocation_id and transfer.old_allocation_id.state == 'active':
                transfer.old_allocation_id.write({
                    'state': 'transferred',
                    'actual_return_date': fields.Date.context_today(self),
                })
            new_allocation = self.env['asset.allocation'].with_context(from_transfer=True).create({
                'asset_id': transfer.asset_id.id,
                'holder_type': transfer.new_holder_type,
                'employee_id': transfer.new_employee_id.id,
                'department_id': transfer.new_department_id.id,
                'expected_return_date': transfer.expected_return_date,
            })
            transfer.write({
                'state': 'completed',
                'approved_by': self.env.user.id,
                'approval_date': fields.Datetime.now(),
                'new_allocation_id': new_allocation.id,
            })
            self.env['asset.activity.log'].log(
                transfer.asset_id, 'transfer_approved',
                f"Transfer approved for asset {transfer.asset_id.tag}, now held by {new_allocation.holder_name}."
            )
        return True

    def action_reject(self):
        self._check_can_approve()
        self.write({
            'state': 'rejected',
            'approved_by': self.env.user.id,
            'approval_date': fields.Datetime.now(),
        })
        return True
