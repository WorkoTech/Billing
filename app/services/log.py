import enum

from app.database import get_or_create, db_session
from app.models import UserUsage, WorkspaceUsage


class BillingEventType(str, enum.Enum):
    WORKSPACE_DOCUMENT_CREATED = 'WORKSPACE_DOCUMENT_CREATED',
    WORKSPACE_DOCUMENT_DELETED = 'WORKSPACE_DOCUMENT_DELETED',
    WORKSPACE_STORAGE_CREATED = 'WORKSPACE_STORAGE_CREATED',
    WORKSPACE_STORAGE_DELETED = 'WORKSPACE_STORAGE_DELETED',
    WORKSPACE_CREATED = 'WORKSPACE_CREATED',
    WORKSPACE_DELETED = 'WORKSPACE_DELETED',


class BillingEvent:
    def __init__(
        self,
        type,
        user_id=None,
        workspace_id=None,
        storage_size=None
    ):
        self.type = type
        self.user_id = user_id
        self.workspace_id = workspace_id
        self.storage_size = storage_size


def handle_billing_event(payload, user_id):
    event = BillingEvent(
        user_id=user_id,
        type=payload.get('type'),
        workspace_id=payload.get('workspaceId'),
        storage_size=payload.get('storageSize')
    )

    if event.type == BillingEventType.WORKSPACE_CREATED:
        return workspace_created_handler(event)
    elif event.type == BillingEventType.WORKSPACE_DELETED:
        return workspace_deleted_handler(event)
    elif event.type == BillingEventType.WORKSPACE_DOCUMENT_CREATED:
        return document_created_handler(event)
    elif event.type == BillingEventType.WORKSPACE_DOCUMENT_DELETED:
        return document_deleted_handler(event)
    elif event.type == BillingEventType.WORKSPACE_STORAGE_CREATED:
        return storage_created_handler(event)
    elif event.type == BillingEventType.WORKSPACE_STORAGE_DELETED:
        return storage_deleted_handler(event)


def workspace_created_handler(event):
    generic_user_event_handler(event, 1)

    workspace_usage = WorkspaceUsage(
        workspace_id=event.workspace_id,
        creator_user_id=event.user_id
    )
    db_session.add(workspace_usage)
    db_session.commit()


def workspace_deleted_handler(event):
    generic_user_event_handler(event, -1)

    workspace_usage = WorkspaceUsage.query.filter(
        WorkspaceUsage.workspace_id==event.workspace_id,
    ).first()
    db_session.delete(workspace_usage)
    db_session.commit()


def document_created_handler(event):
    return generic_workspace_event_handler(
        event,
        'document_count',
        1
    )


def document_deleted_handler(event):
    return generic_workspace_event_handler(
        event,
        'document_count',
        -1
    )


def storage_created_handler(event):
    return generic_workspace_event_handler(
        event,
        'storage_size_count',
        event.storage_size
    )


def storage_deleted_handler(event):
    return generic_workspace_event_handler(
        event,
        'storage_size_count',
        -event.storage_size
    )


def generic_user_event_handler(event, add):
    user_usage, created = get_or_create(
        db_session,
        UserUsage,
        user_id=event.user_id
    )

    print("user_usage workspace_count before : %r", user_usage)
    user_usage.workspace_count = user_usage.workspace_count + add
    print("user_usage worksapce_count after : %r", user_usage)

    if created:
        db_session.add(user_usage)


def generic_workspace_event_handler(event, field, add):
    workspace_usage = WorkspaceUsage.query.filter(
        WorkspaceUsage.workspace_id==event.workspace_id,
    ).first()

    if not workspace_usage:
        raise Exception("Workspace Usage not found")

    print("Workspace usage before event: %r", workspace_usage)
    current = getattr(workspace_usage, field)
    if current + add >= 0:
        setattr(workspace_usage, field, current + add)
    else:
        print("Unable to set event value to less than 0")
    print("Workspace usage after event: %r", workspace_usage)
    db_session.commit()
