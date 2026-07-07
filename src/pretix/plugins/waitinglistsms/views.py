from django import forms
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from pretix.base.forms import SettingsForm
from pretix.base.models import Event
from pretix.control.views.event import EventSettingsFormView, EventSettingsViewMixin


class WaitingListSmsSettingsForm(SettingsForm):
    waitinglistsms_enabled = forms.BooleanField(
        label=_('Enable SMS notifications'),
        required=False,
        help_text=_('Send an SMS in addition to the regular waiting list email when a voucher is assigned.'),
    )
    waitinglistsms_provider = forms.ChoiceField(
        label=_('SMS gateway'),
        choices=(
            ('pingram', 'Pingram'),
            ('twilio', 'Twilio'),
            ('webhook', _('Generic HTTP gateway')),
        ),
        required=False,
    )
    waitinglistsms_from = forms.CharField(
        label=_('Sender number'),
        required=False,
        help_text=_(
            'For Twilio, enter the Twilio phone number or messaging service sender. '
            'For Pingram, this is optional and must be configured in your Pingram account.'
        ),
    )
    waitinglistsms_pingram_api_key = forms.CharField(
        label=_('Pingram API key'), required=False, widget=forms.PasswordInput(render_value=True),
        help_text=_(
            'Use an API key starting with pingram_sk_ from the Environments section of the Pingram dashboard.'
        ),
    )
    waitinglistsms_pingram_type = forms.CharField(
        label=_('Pingram notification type'), required=False, initial='waiting_list_sms',
        help_text=_('Create an SMS notification in Pingram and enter its Type, e.g. welcome_sms.'),
    )
    waitinglistsms_pingram_base_url = forms.URLField(
        label=_('Pingram API base URL'), required=False, initial='https://api.pingram.io',
        help_text=_('Use https://api.ca.pingram.io or https://api.eu.pingram.io for regional Pingram environments.'),
    )
    waitinglistsms_twilio_account_sid = forms.CharField(label=_('Twilio Account SID'), required=False)
    waitinglistsms_twilio_auth_token = forms.CharField(
        label=_('Twilio Auth Token'), required=False, widget=forms.PasswordInput(render_value=True)
    )
    waitinglistsms_webhook_url = forms.URLField(
        label=_('Generic gateway URL'), required=False,
        help_text=_('The plugin will POST JSON containing to, from, body, event, item, and voucher_code.'),
    )
    waitinglistsms_message = forms.CharField(
        label=_('Message text'), required=False, widget=forms.Textarea,
        help_text=_(
            'Available placeholders: {event}, {item}, {variation}, {voucher_code}, {voucher_valid_until}, {url}.'
        ),
    )

    def clean(self):
        data = super().clean()
        if data.get('waitinglistsms_enabled'):
            provider = data.get('waitinglistsms_provider') or 'pingram'
            if provider in ('twilio', 'webhook') and not data.get('waitinglistsms_from'):
                self.add_error('waitinglistsms_from', _('Please enter a sender number.'))
            if provider == 'pingram':
                if not data.get('waitinglistsms_pingram_api_key'):
                    self.add_error('waitinglistsms_pingram_api_key', _('Please enter your Pingram API key.'))
                if not data.get('waitinglistsms_pingram_type'):
                    self.add_error('waitinglistsms_pingram_type', _('Please enter your Pingram notification type.'))
            elif provider == 'twilio':
                if not data.get('waitinglistsms_twilio_account_sid'):
                    self.add_error('waitinglistsms_twilio_account_sid', _('Please enter your Twilio Account SID.'))
                if not data.get('waitinglistsms_twilio_auth_token'):
                    self.add_error('waitinglistsms_twilio_auth_token', _('Please enter your Twilio Auth Token.'))
            elif data.get('waitinglistsms_provider') == 'webhook' and not data.get('waitinglistsms_webhook_url'):
                self.add_error('waitinglistsms_webhook_url', _('Please enter the gateway URL.'))
        return data


class WaitingListSmsSettings(EventSettingsViewMixin, EventSettingsFormView):
    model = Event
    form_class = WaitingListSmsSettingsForm
    template_name = 'waitinglistsms/settings.html'
    permission = 'event.settings.general:write'

    def get_success_url(self):
        return reverse('plugins:waitinglistsms:settings', kwargs={
            'organizer': self.request.event.organizer.slug,
            'event': self.request.event.slug,
        })
