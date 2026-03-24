# pretix_ticketing_portal

This plugin provides:

- `/portal/` as a working installation-wide ticketing portal page
- `root_urlpatterns` in `pretix_ticketing_portal.urls` for clean `/` interception
- an event settings page at `/control/event/<organizer>/<event>/settings/ticketing-portal/`

## Remaining `/` integration step

This repository does not track the runtime Pretix project URL configuration, so `/` cannot be made to win over the stock Pretix root view from the plugin alone here.

In the runtime Pretix project `urls.py`, prepend the plugin root patterns before the stock root route:

```python
from pretix_ticketing_portal.urls import root_urlpatterns as ticketing_portal_root_urlpatterns

urlpatterns = [
    *ticketing_portal_root_urlpatterns,
    # existing pretix URL patterns continue below
]
```

Keep the plugin `urlpatterns` loaded as usual so `/portal/` remains available for direct testing.
