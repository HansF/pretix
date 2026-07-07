import logging

import requests
from django.utils.timezone import localtime
from django.utils.translation import gettext as _
from django_scopes import scopes_disabled

from pretix.base.models import WaitingListEntry
from pretix.celery_app import app
from pretix.multidomain.urlreverse import build_absolute_uri

logger = logging.getLogger(__name__)

DEFAULT_MESSAGE = _('Good news! A spot opened for {event}. Use voucher {voucher_code} to book: {url}')


def _message(entry):
    voucher = entry.voucher
    event = entry.event
    url = build_absolute_uri(event, 'presale:event.index')
    valid_until = localtime(voucher.valid_until).strftime('%Y-%m-%d %H:%M') if voucher.valid_until else ''
    template = event.settings.waitinglistsms_message or DEFAULT_MESSAGE
    return str(template).format(
        event=event.name,
        item=entry.item.name,
        variation=entry.variation.value if entry.variation else '',
        voucher_code=voucher.code,
        voucher_valid_until=valid_until,
        url=url,
    )


def _send_twilio(entry, body):
    event = entry.event
    sid = event.settings.waitinglistsms_twilio_account_sid
    token = event.settings.waitinglistsms_twilio_auth_token
    response = requests.post(
        f'https://api.twilio.com/2010-04-01/Accounts/{sid}/Messages.json',
        data={
            'To': str(entry.phone),
            'From': event.settings.waitinglistsms_from,
            'Body': body,
        },
        auth=(sid, token),
        timeout=10,
    )
    response.raise_for_status()
    return response.json().get('sid')


def _send_pingram(entry, body):
    event = entry.event
    sms = {'message': body}
    if event.settings.waitinglistsms_from:
        sms['from'] = event.settings.waitinglistsms_from
    response = requests.post(
        (event.settings.waitinglistsms_pingram_base_url or 'https://api.pingram.io').rstrip('/') + '/sender',
        json={
            'type': event.settings.waitinglistsms_pingram_type or 'waiting_list_sms',
            'to': {
                'id': f'pretix-waitinglist-{entry.pk}',
                'number': str(entry.phone),
            },
            'sms': sms,
        },
        headers={
            'Authorization': f'Bearer {event.settings.waitinglistsms_pingram_api_key}',
            'Content-Type': 'application/json',
        },
        timeout=10,
    )
    response.raise_for_status()
    data = response.json()
    return data.get('trackingId') or data.get('id')


def _send_webhook(entry, body):
    event = entry.event
    response = requests.post(
        event.settings.waitinglistsms_webhook_url,
        json={
            'to': str(entry.phone),
            'from': event.settings.waitinglistsms_from,
            'body': body,
            'event': event.slug,
            'item': entry.item_id,
            'variation': entry.variation_id,
            'voucher_code': entry.voucher.code,
        },
        timeout=10,
    )
    response.raise_for_status()
    return str(response.status_code)


@app.task(throws=(WaitingListEntry.DoesNotExist,))
@scopes_disabled()
def send_waitinglist_sms(entry_id):
    entry = WaitingListEntry.objects.select_related(
        'event', 'event__organizer', 'item', 'variation', 'voucher'
    ).get(pk=entry_id)
    if not entry.voucher_id or not entry.phone or not entry.event.settings.waitinglistsms_enabled:
        return False
    if entry.all_logentries().filter(action_type='pretix.plugins.waitinglistsms.sent').exists():
        return False

    body = _message(entry)
    try:
        provider = entry.event.settings.waitinglistsms_provider or 'pingram'
        if provider == 'webhook':
            provider_id = _send_webhook(entry, body)
        elif provider == 'twilio':
            provider_id = _send_twilio(entry, body)
        else:
            provider_id = _send_pingram(entry, body)
    except Exception as e:
        logger.exception('Could not send waiting list SMS for entry %s', entry.pk)
        entry.log_action('pretix.plugins.waitinglistsms.failed', {'error': str(e)[:500]})
        raise

    entry.log_action('pretix.plugins.waitinglistsms.sent', {'provider_id': provider_id, 'body': body})
    return True
