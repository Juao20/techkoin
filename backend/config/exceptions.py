"""Errors always read {code, message, fields?} (spec 13), including DRF's own 403, 404, 429..."""

from rest_framework.views import exception_handler

CODES = {
    401: ("not_authenticated", "Connectez-vous pour continuer."),
    403: ("forbidden", "Vous n'avez pas accès à cette fonction."),
    404: ("not_found", "Introuvable."),
    405: ("method_not_allowed", "Action non autorisée."),
    429: ("throttled", "Trop de demandes. Réessayez dans quelques minutes."),
}


def api_exception_handler(exc, context):
    response = exception_handler(exc, context)
    if response is None or not isinstance(response.data, dict) or "code" in response.data:
        return response
    if set(response.data) == {"detail"}:
        code, message = CODES.get(response.status_code, ("error", "Une erreur est survenue."))
        detail = str(response.data["detail"])
        # Keep our own French messages (permission classes); replace DRF's English defaults.
        is_default = detail.isascii() and detail[:1].isupper() and not detail.startswith("Cette")
        response.data = {
            "code": code,
            "message": message if is_default else detail,
        }
    return response
