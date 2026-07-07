from django.urls import re_path

from .views import WaitingListSmsSettings

urlpatterns = [
    re_path(r'^control/event/(?P<organizer>[^/]+)/(?P<event>[^/]+)/waitinglistsms/settings$',
            WaitingListSmsSettings.as_view(), name='settings'),
]
