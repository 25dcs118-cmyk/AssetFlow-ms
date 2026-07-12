from datetime import timedelta

from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError


class ResourceBooking(models.Model):
    _name = 'resource.booking'
    _description = 'Resource Booking'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'start_datetime desc'

    asset_id = fields.Many2one(
        'asset.asset', required=True, tracking=True, ondelete='restrict',
        domain="[('is_shared', '=', True)]")
    requester_id = fields.Many2one('res.users', default=lambda self: self.env.user, required=True, tracking=True)
    start_datetime = fields.Datetime(required=True, tracking=True)
    end_datetime = fields.Datetime(required=True, tracking=True)
    purpose = fields.Char()
    state = fields.Selection([
        ('upcoming', 'Upcoming'),
        ('ongoing', 'Ongoing'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ], default='upcoming', required=True, tracking=True)
    reminder_sent = fields.Boolean(default=False, copy=False)
    duration_hours = fields.Float(compute='_compute_duration_hours', store=True, string='Duration (Hours)')

    @api.depends('start_datetime', 'end_datetime')
    def _compute_duration_hours(self):
        for booking in self:
            if booking.start_datetime and booking.end_datetime:
                booking.duration_hours = (booking.end_datetime - booking.start_datetime).total_seconds() / 3600.0
            else:
                booking.duration_hours = 0.0

    @api.constrains('asset_id', 'start_datetime', 'end_datetime', 'state')
    def _check_overlap(self):
        for booking in self:
            if booking.state == 'cancelled':
                continue
            if booking.start_datetime >= booking.end_datetime:
                raise ValidationError("Booking start time must be before end time.")
            overlapping = self.search([
                ('id', '!=', booking.id),
                ('asset_id', '=', booking.asset_id.id),
                ('state', 'not in', ('cancelled', 'completed')),
                ('start_datetime', '<', booking.end_datetime),
                ('end_datetime', '>', booking.start_datetime),
            ], limit=1)
            if overlapping:
                raise ValidationError(
                    f"{booking.asset_id.name} is already booked from "
                    f"{overlapping.start_datetime} to {overlapping.end_datetime}."
                )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            asset = self.env['asset.asset'].browse(vals.get('asset_id'))
            if not asset.is_shared:
                raise UserError(f"Asset {asset.name} is not marked as shared/bookable.")
        bookings = super().create(vals_list)
        for booking in bookings:
            self.env['asset.activity.log'].log(
                booking.asset_id, 'booked',
                f"{booking.asset_id.tag} booked by {booking.requester_id.name} "
                f"{booking.start_datetime} - {booking.end_datetime}."
            )
            booking.message_post(
                body=f"Booking Confirmed: {booking.asset_id.name} from {booking.start_datetime} to {booking.end_datetime}.",
                partner_ids=[booking.requester_id.partner_id.id],
            )
        return bookings

    def action_cancel(self):
        for booking in self:
            if booking.state not in ('upcoming', 'ongoing'):
                raise UserError("Only upcoming or ongoing bookings can be cancelled.")
            was_ongoing = booking.state == 'ongoing'
            booking.state = 'cancelled'
            if was_ongoing and booking.asset_id.state == 'reserved':
                booking.asset_id.write({'state': 'available'})
            booking.message_post(
                body=f"Booking Cancelled: {booking.asset_id.name} ({booking.start_datetime} - {booking.end_datetime}).",
                partner_ids=[booking.requester_id.partner_id.id],
            )
        return True

    @api.model
    def _cron_update_booking_states(self):
        now = fields.Datetime.now()
        starting = self.search([('state', '=', 'upcoming'), ('start_datetime', '<=', now), ('end_datetime', '>', now)])
        for booking in starting:
            booking.state = 'ongoing'
            if booking.asset_id.state == 'available':
                booking.asset_id.write({'state': 'reserved'})

        ending = self.search([('state', '=', 'ongoing'), ('end_datetime', '<=', now)])
        for booking in ending:
            booking.state = 'completed'
            if booking.asset_id.state == 'reserved':
                booking.asset_id.write({'state': 'available'})

        soon = self.search([
            ('state', '=', 'upcoming'),
            ('reminder_sent', '=', False),
            ('start_datetime', '>', now),
            ('start_datetime', '<=', now + timedelta(hours=1)),
        ])
        for booking in soon:
            booking.message_post(
                body=f"Reminder: your booking of {booking.asset_id.name} starts at {booking.start_datetime}.",
                partner_ids=[booking.requester_id.partner_id.id],
            )
            booking.reminder_sent = True
