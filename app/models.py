import enum

from sqlalchemy import (
    Column,
    Integer,
    BigInteger,
    String,
    Enum,
    ForeignKey,
    Float,
    Boolean
)
from sqlalchemy.orm import relationship
from .database import Base


class SubscriptionStatus(str, enum.Enum):
    active = "ACTIVE"
    inactive = "INACTIVE"


class Subscription(Base):
    __tablename__ = 'subscription'

    id = Column(Integer, primary_key=True)
    offer_id = Column(Integer, ForeignKey('offer.id'))
    user_id = Column(Integer, unique=True, nullable=False)
    stripe_subscription_id = Column(String(255), unique=True, nullable=False)
    stripe_customer_id = Column(String(255), unique=True, nullable=False)
    status = Column(Enum(SubscriptionStatus), default=SubscriptionStatus.inactive)

    def __init__(
        self,
        user_id,
        stripe_subscription_id,
        stripe_customer_id,
    ):
        self.user_id = user_id
        self.stripe_subscription_id = stripe_subscription_id
        self.stripe_customer_id = stripe_customer_id

    def __repr__(self):
        return '<Subscription user_id=%r, subscription_id=%r, status=%r>' % (
            self.user_id,
            self.stripe_subscription_id,
            self.status
        )


class Offer(Base):
    __tablename__ = 'offer'

    id = Column(Integer, primary_key=True)
    name = Column(String(255), unique=True)
    price = Column(Float, nullable=False)
    items = relationship("OfferItem", backref="offer", lazy="joined")
    stripe_price_id = Column(String(255))
    default = Column(Boolean, default=False)
    subscriptions = relationship("Subscription", backref="offer", lazy="joined")

    def __init__(
        self,
        name=None,
        price=None,
        stripe_price_id=None,
        items=None,
        default=None
    ):
        self.name = name
        self.price = price
        self.stripe_price_id = stripe_price_id
        if items:
            self.items = items
        self.default = default


class ResourceEnum(str, enum.Enum):
    workspace = "workspace",
    document = "document",
    file = "file"


class OfferItem(Base):
    __tablename__ = 'offerItem'

    id = Column(Integer, primary_key=True)
    offer_id = Column(Integer, ForeignKey('offer.id'), nullable=False)
    resource = Column(Enum(ResourceEnum), nullable=False)
    limit = Column(BigInteger, default=0)
    description = Column(String(255), nullable=True)

    def __init__(
        self,
        offer_id=None,
        resource=None,
        limit=None,
        description=None
    ):
        self.offer_id = offer_id
        self.resource = resource
        self.limit = limit
        self.description = description


class UserUsage(Base):
    __tablename__ = 'userUsage'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, nullable=False)
    workspace_count = Column(Integer, nullable=False, default=0)

    def __init__(
        self,
        user_id=None,
        workspace_count=None
    ):
        self.user_id = user_id,
        self.workspace_count = workspace_count

    def __repr__(self):
        return '<UserUsage user_id=%r, workspace_count=%r>' % (
            self.user_id,
            self.workspace_count
        )


class WorkspaceUsage(Base):
    __tablename__ = 'workspaceUsage'

    id = Column(Integer, primary_key=True)
    workspace_id = Column(Integer, nullable=False, unique=True)
    creator_user_id = Column(Integer, nullable=False)
    document_count = Column(Integer, nullable=False, default=0)
    storage_size_count = Column(Integer, nullable=False, default=0)

    def __init__(
        self,
        workspace_id=None,
        creator_user_id=None,
        document_count=None,
        storage_size_count=None
    ):
        self.workspace_id = workspace_id
        self.creator_user_id = creator_user_id
        self.document_count = document_count
        self.storage_size_count = storage_size_count

    def __repr__(self):
        return '<WorkspaceUsage workspace_id=%r, creator_user_id=%r, document_count=%r, storage_size_count=%r>' % (
            self.workspace_id,
            self.creator_user_id,
            self.document_count,
            self.storage_size_count
        )
