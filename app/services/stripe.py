import stripe

from flask import Response

from app.database import db_session
from app.models import Subscription, SubscriptionStatus


STRIPE_CHECKOUT_COMPLETE_EVENT = "checkout.session.completed"
STRIPE_INVOICE_PAID_EVENT = "invoice.paid"
STRIPE_INVOICE_FAILED_EVENT = "invoice.payment_failed"
STRIPE_SUBSCRIPTION_UPDATED_EVENT = "customer.subscription.updated"
STRIPE_SUBSCRIPTION_DELETED_EVENT = "customer.subscription.deleted"


def create_stripe_session(user_id, price_id, offer_id, success_url, cancel_url):
    return stripe.checkout.Session.create(
        payment_method_types=['card'],
        line_items=[{
            'price': price_id,
            'quantity': 1,
        }],
        mode='subscription',
        success_url=success_url,
        cancel_url=cancel_url,
        metadata={
            "user_id": user_id,
            "offer_id": offer_id
        }
    )


def handle_stripe_webhook(request, stripe_endpoint_secret):
    event = parse_stripe_event(request, stripe_endpoint_secret)

    if event is None:
        return Response(status=400)

    # Handle events
    if event['type'] == STRIPE_CHECKOUT_COMPLETE_EVENT:
        complete_stripe_session(event)
    elif event['type'] == STRIPE_INVOICE_PAID_EVENT:
        stripe_invoice_paid(event)
    elif event['type'] == STRIPE_INVOICE_FAILED_EVENT:
        stripe_invoice_failed(event)
    elif event['type'] == STRIPE_SUBSCRIPTION_UPDATED_EVENT:
        stripe_update_subscription(event)
    elif event['type'] == STRIPE_SUBSCRIPTION_DELETED_EVENT:
        stripe_delete_subscription(event)

    # Passed signature verification
    return Response(status=200)


def parse_stripe_event(request, stripe_endpoint_secret):
    payload = request.data.decode("utf-8")
    received_sig = request.headers.get("Stripe-Signature", None)

    try:
        return stripe.Webhook.construct_event(
            payload, received_sig, stripe_endpoint_secret
        )
    except ValueError as e:
        # Invalid payload
        print(e)
        return None
    except stripe.error.SignatureVerificationError as e:
        # Invalid signature
        print(e)
        return None
    return None


def complete_stripe_session(event):
    checkout_session = event['data']['object']
    subscription_id = checkout_session.subscription
    customer_id = checkout_session.customer
    user_id = checkout_session.metadata["user_id"]
    offer_id = checkout_session.metadata["offer_id"]

    # Create a new subscription and mark it as paid this month.
    subscription = sign_up_customer(user_id, offer_id, customer_id, subscription_id)
    mark_paid(subscription)
    db_session.add(subscription)
    db_session.commit()


def stripe_invoice_paid(event):
    invoice = event['data']['object']
    subscription_id = invoice.subscription

    subscription = find_customer_signup(subscription_id)

    # Check if this is the first invoice or a later invoice in the
    # subscription lifecycle.
    first_invoice = invoice.billing_reason == 'subscription_create'

    # You already handle marking the first invoice as paid in the
    # `checkout.session.completed` handler.
    #
    # Only use this for the 2nd invoice and later, so it doesn't conflict.
    if not first_invoice:
        # Mark the subscription as paid.
        mark_paid(subscription)
        db_session.commit()


def stripe_invoice_failed(event):
    invoice = event['data']['object']
    subscription_id = invoice.subscription

    subscription = find_customer_signup(subscription_id)
    mark_past_due(subscription)


def stripe_update_subscription(event):
    print("event : " + str(event))
    customer_id = event['data']['object']['customer']

    subscription = Subscription.query.filter(
        Subscription.stripe_customer_id == customer_id
    ).first()
    if not subscription:
        return None

    subscription.stripe_subscription_id = event['id']
    if event['data']['object']['status'] == 'active':
        subscription.status = SubscriptionStatus.active
    else:
        subscription.status = SubscriptionStatus.inactive
    db_session.commit()


def stripe_delete_subscription(event):
    print("event : " + str(event))
    customer_id = event['data']['object']['customer']

    subscription = Subscription.query.filter(
        Subscription.stripe_customer_id == customer_id
    ).first()
    if not subscription:
        return None

    subscription.status = SubscriptionStatus.inactive
    db_session.commit()


def mark_past_due(subscription):
    subscription.status = SubscriptionStatus.inactive


def mark_paid(subscription):
    subscription.status = SubscriptionStatus.active


def find_customer_signup(subscription_id):
    return Subscription.query.filter(
        Subscription.id == subscription_id
    )


def sign_up_customer(user_id, offer_id, customer_id, subscription_id):
    subscription = Subscription(
        user_id=user_id,
        stripe_subscription_id=subscription_id,
        stripe_customer_id=customer_id
    )
    subscription.offer_id = offer_id
    return subscription
