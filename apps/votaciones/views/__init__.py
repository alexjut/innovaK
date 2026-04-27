from .public import redirect_root, scan_page, dashboard_page
from .api import (
    api_events,
    api_event_candidates,
    api_validate_voter,
    api_results,
    api_vote,
)
from .qr import qr_event_png, qr_candidate_png
from .organizer import (
    organizer_events,
    organizer_event_create,
    organizer_event_edit,
    organizer_event_toggle,
    organizer_event_delete,
    organizer_artists,
    organizer_artist_edit,
    organizer_artist_toggle,
    organizer_artist_delete,
)
from .registro import (
    registro_votante_view,
    api_tipos_documento,
    api_buscar_persona,
    api_registrar_votante,
    listado_votantes_view,       # ← nuevo
    api_listado_votantes,  
)