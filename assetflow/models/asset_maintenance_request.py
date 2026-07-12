from odoo import api, fields, models
from odoo.exceptions import AccessError, UserError


class AssetMaintenanceRequest(models.Model):
    _name = 'asset.maintenance.request'
    _description = 'Asset Maintenance Request'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'request_date desc'

    asset_id = fields.Many2one('asset.asset', required=True, tracking=True, ondelete='restrict')
    category_id = fields.Many2one(related='asset_id.category_id', string='Category', store=True)
    requester_id = fields.Many2one('res.users', default=lambda self: self.env.user, required=True, tracking=True)
    technician_id = fields.Many2one('res.users', string='Assigned Technician', tracking=True)
    priority = fields.Selection([
        ('0', 'Low'),
        ('1', 'Normal'),
        ('2', 'High'),
        ('3', 'Urgent'),
    ], default='1', required=True, tracking=True)
    description = fields.Text(required=True)
    request_date = fields.Datetime(default=fields.Datetime.now, required=True)
    approval_date = fields.Datetime()
    resolution_date = fields.Datetime()
    resolution_notes = fields.Text()
    state = fields.Selection([
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('in_progress', 'In Progress'),
        ('resolved', 'Resolved'),
    ], default='pending', required=True, tracking=True)

    @api.model_create_multi
    def create(self, vals_list):
        requests = super().create(vals_list)
        managers = self.env['res.users'].search([
            ('groups_id', 'in', self.env.ref('assetflow.group_assetflow_asset_manager').id),
        ])
        for request in requests:
            self.env['asset.activity.log'].log(
                request.asset_id, 'maintenance_requested',
                f"Maintenance requested for asset {request.asset_id.tag}."
            )
            if managers:
                request.message_post(
                    body=f"New maintenance request raised for {request.asset_id.tag} by {request.requester_id.name}.",
                    partner_ids=managers.mapped('partner_id.id'),
                )
        return requests

    def _check_can_manage(self):
        if not self.env.user.has_group('assetflow.group_assetflow_asset_manager'):
            raise AccessError("Only an Asset Manager can approve, reject or resolve maintenance requests.")

    def action_approve(self):
        self._check_can_manage()
        for request in self:
            if request.state != 'pending':
                raise UserError("Only pending requests can be approved.")
            request.write({'state': 'approved', 'approval_date': fields.Datetime.now()})
            request.asset_id.write({'state': 'maintenance'})
            self.env['asset.activity.log'].log(
                request.asset_id, 'maintenance_approved',
                f"Maintenance approved for asset {request.asset_id.tag}."
            )
        return True

    def action_reject(self):
        self._check_can_manage()
        self.filtered(lambda r: r.state == 'pending').write({'state': 'rejected'})
        return True

    def action_start(self):
        self._check_can_manage()
        for request in self:
            if request.state != 'approved':
                raise UserError("Only approved requests can move to In Progress.")
        self.write({'state': 'in_progress'})
        return True

    def action_resolve(self):
        self._check_can_manage()
        for request in self:
            if request.state not in ('approved', 'in_progress'):
                raise UserError("Only approved or in-progress requests can be resolved.")
            request.write({'state': 'resolved', 'resolution_date': fields.Datetime.now()})
            request.asset_id.write({'state': 'available'})
            self.env['asset.activity.log'].log(
                request.asset_id, 'maintenance_resolved',
                f"Maintenance resolved for asset {request.asset_id.tag}, asset available again."
            )
        return True
