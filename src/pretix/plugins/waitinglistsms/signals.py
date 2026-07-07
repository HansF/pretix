from django.db import transaction
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.urls import resolve, reverse
from django.utils.translation import gettext_lazy as _

from pretix.base.logentrytypes import WaitingListEntryLogEntryType, log_entry_types
from pretix.base.models import WaitingListEntry
from pretix.control.signals import nav_event_settings

from .tasks import send_waitinglist_sms


@log_entry_types.new('pretix.plugins.waitinglistsms.sent', _('A waiting list SMS notification was sent.'))
@log_entry_types.new('pretix.plugins.waitinglistsms.failed', _('A waiting list SMS notification could not be sent.'))
class WaitingListSmsLogEntryType(WaitingListEntryLogEntryType):
    pass


@receiver(post_save, sender=WaitingListEntry, dispatch_uid='waitinglistsms_wle_post_save')
def waitinglist_entry_saved(sender, instance, created, **kwargs):
    if not instance.voucher_id or not instance.phone:
        return
    if not instance.event.settings.waitinglistsms_enabled:
        return
    if instance.all_logentries().filter(action_type='pretix.plugins.waitinglistsms.sent').exists():
        return
    transaction.on_commit(lambda: send_waitinglist_sms.apply_async(args=(instance.pk,)))


@receiver(nav_event_settings, dispatch_uid='waitinglistsms_nav')
def navbar_info(sender, request, **kwargs):
    url = resolve(request.path_info)
    if not request.user.has_event_permission(request.organizer, request.event, 'event.settings.general:write',
                                             request=request):
        return []
    return [{
        'label': _('Waiting list SMS'),
        'url': reverse('plugins:waitinglistsms:settings', kwargs={
            'event': request.event.slug,
            'organizer': request.organizer.slug,
        }),
        'active': url.namespace == 'plugins:waitinglistsms',
    }]
