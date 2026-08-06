from .public import redirect_root, scan_page
from .api import (
    api_events,
    api_event_candidates,
    api_validate_voter,
    api_results,
    api_vote,
)
from .organizer import organizer_events
from .registro import (
    api_tipos_documento,
    api_buscar_persona,
    api_registrar_votante,
    listado_votantes_view,
    api_listado_votantes,
)