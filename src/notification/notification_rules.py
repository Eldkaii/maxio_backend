from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session

from src.models import Notification, Match, TelegramIdentity


"""
notification_rules.py

Este módulo centraliza todas las reglas de negocio que determinan
si una notificación PUEDE o NO ser enviada en un momento dado.

RESPONSABILIDAD PRINCIPAL
-------------------------
Evaluar condiciones y devolver un booleano indicando si una notificación
está habilitada para ser enviada, sin ejecutar ningún efecto colateral.

Este archivo NO envía notificaciones, NO modifica estados en la base
de datos y NO realiza commits. Su objetivo es únicamente decidir.

DISEÑO Y ALCANCE
----------------
- Contiene funciones puras de validación.
- Puede consultar la base de datos SOLO para leer información necesaria
  (ej: match, identidades de usuario, fechas).
- No depende de servicios externos (Telegram, email, etc.).
- Es totalmente testeable de forma aislada.

FUNCIÓN PRINCIPAL
-----------------
can_send_notification(db, notification, now=None) -> bool

Esta función actúa como punto de entrada único para evaluar cualquier
tipo de notificación. A partir del canal y del tipo de evento, delega
la validación a reglas específicas.

REGLAS IMPLEMENTADAS ACTUALMENTE
--------------------------------
Canal: "telegram"
Evento: "MATCH_EVALUATION"

Para que una notificación de evaluación post-match pueda enviarse:
1. La notificación debe estar en estado "pending".
2. El usuario debe existir.
3. El usuario debe tener una identidad de Telegram activa.
4. El match asociado debe existir.
5. El match se considera finalizado únicamente cuando transcurrió
   al menos 1 hora desde su fecha (match.date + 1 hora).
6. La hora actual debe ser mayor o igual al momento de finalización.

USO PREVISTO
------------
Este módulo está diseñado para ser utilizado por un daemon o dispatcher
de notificaciones, el cual:
- Consulta notificaciones pendientes.
- Evalúa si pueden enviarse usando este módulo.
- Ejecuta el envío.
- Actualiza el estado de la notificación según el resultado.

EXTENSIBILIDAD
--------------
Nuevos eventos y canales deben agregarse creando nuevas funciones
de validación específicas y delegando desde can_send_notification,
manteniendo este archivo como la única fuente de verdad de reglas.

IMPORTANTE
----------
Cualquier cambio en la lógica de cuándo se envía una notificación
debe realizarse exclusivamente en este módulo.
"""


def can_send_notification(
    db: Session,
    notification: Notification,
    now: datetime | None = None,
) -> bool:
    """
    Determina si una notificación puede enviarse ahora.
    """
    now = now or datetime.now(timezone.utc)

    if notification.status != "pending":
        return False

    if notification.channel == "telegram":
        return _can_send_telegram_notification(db, notification, now)

    # Canal no soportado
    return False


def _can_send_telegram_notification(
    db: Session,
    notification: Notification,
    now: datetime,
) -> bool:
    # El usuario debe existir
    user = notification.user
    if not user:
        return False

    # Debe tener identidad de Telegram activa
    telegram_identity = (
        db.query(TelegramIdentity)
        .filter(
            TelegramIdentity.user_id == user.id,
            TelegramIdentity.is_active.is_(True),
        )
        .first()
    )

    if not telegram_identity:
        return False

    # Reglas por tipo de evento
    if notification.event_type == "MATCH_EVALUATION":
        return _can_send_match_evaluation(db, notification, now)

    # Evento no soportado
    return False


def _can_send_match_evaluation(
    db: Session,
    notification: Notification,
    now: datetime,
) -> bool:
    payload = notification.payload or {}
    match_id = payload.get("match_id")

    if not match_id:
        return False

    match = db.query(Match).filter(Match.id == match_id).first()
    if not match or not match.date:
        return False

    match_end = match.date + timedelta(hours=1)

    return now >= match_end
