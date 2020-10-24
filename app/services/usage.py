from app.models import (
    WorkspaceUsage,
    UserUsage,
    Subscription,
    Offer,
    OfferItem
)

from app.database import db_session, get_or_create


def get_workspace_usage_and_limits(workspace_id):
    print("here workspace_id :", str(workspace_id))
    workspace_usage = WorkspaceUsage.query.filter(
        WorkspaceUsage.workspace_id==workspace_id
    ).join(
        Subscription, WorkspaceUsage.creator_user_id==Subscription.user_id
    ).join(
        Subscription.offer
    ).add_entity(
        Offer
    ).first()

    print(workspace_usage)
    return workspace_usage


def get_user_usage_and_limits(user_id):
    user_usage, created = get_or_create(
        db_session,
        UserUsage,
        user_id=user_id
    )
    if created:
        db_session.add(user_usage)
        db_session.commit()

    usage = UserUsage.query.filter(
        UserUsage.id == user_usage.id
    ).join(
        Subscription, UserUsage.user_id==Subscription.user_id
    ).join(
        Subscription.offer
    ).add_entity(
        Offer
    ).first()

    print("usage", usage)

    return usage
