from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _

from pretix import __version__ as version


class WaitingListSmsApp(AppConfig):
    name = 'pretix.plugins.waitinglistsms'
    verbose_name = _('Waiting list SMS notifications')

    class PretixPluginMeta:
        name = _('Waiting list SMS notifications')
        author = _('the pretix team')
        version = version
        category = 'FEATURE'
        description = _(
            'Send SMS notifications through Pingram, Twilio, or a generic SMS gateway when waiting list '
            'vouchers are assigned.'
        )
        settings_links = [
            ((_('Communication'), _('Waiting list SMS')), 'plugins:waitinglistsms:settings', {}),
        ]

    def ready(self):
        from . import signals  # NOQA
