import stripe
import os
import jwt
from flask import Flask, jsonify, request, Response, redirect
from flask_jsontools import DynamicJSONEncoder
from sqlalchemy.orm import joinedload

from app.database import db_session, init_db
from app.invalid_usage import InvalidUsage
from app.validation import validate_checkout_session
from app.services.stripe import (
    create_stripe_session,
    complete_stripe_session,
    stripe_invoice_paid,
    stripe_invoice_failed,
    handle_stripe_webhook,
)
from app.services.usage import (
    get_workspace_usage_and_limits,
    get_user_usage_and_limits
)
from app.services.log import (
    handle_billing_event
)
from app.models import Offer, Subscription, OfferItem


app = Flask(__name__)
app.json_encoder = DynamicJSONEncoder

stripe.api_key = os.getenv('STRIPE_API_KEY')
stripe_publishable_key = os.getenv('STRIPE_PUBLISHABLE_KEY')
stripe_success_url = os.getenv('STRIPE_CHECKOUT_SUCCESS_URL')
stripe_cancel_url = os.getenv('STRIPE_CHECKOUT_CANCEL_URL')
stripe_endpoint_secret = os.getenv('STRIPE_ENDPOINT_SECRET')
stripe_portal_return_url = os.getenv('STRIPE_PORTAL_RETURN_URL')


@app.teardown_appcontext
def shutdown_session(exception=None):
    db_session.remove()

@app.errorhandler(InvalidUsage)
def handle_invalid_usage(error):
    response = jsonify(error.to_dict())
    response.status_code = error.status_code
    return response


@app.route('/offer', methods=['GET'])
def offer():
    return jsonify({
        'publishableKey': stripe_publishable_key,
        'offers': Offer.query.all()
    })


@app.route('/create-checkout-session', methods=['POST'])
def create_checkout_session():
    errors = validate_checkout_session(request)
    if errors is not None:
        print(errors)
        raise InvalidUsage(errors)

    encoded_jwt = request.headers.get('Authorization')
    if not encoded_jwt:
        return Response("No authorization header found", status=401)

    _, raw_jwt = encoded_jwt.split() # Remove "Bearer"
    decoded = jwt.decode(raw_jwt, algorithms=['HS256'], verify=False)

    price_id = request.json.get('price')
    offer_id = request.json.get('offer')
    session = create_stripe_session(
        decoded["userId"],
        price_id,
        offer_id,
        stripe_success_url,
        stripe_cancel_url
    )
    return jsonify(id=session.id)


@app.route('/create-portal-session', methods=['GET'])
def stripe_portal():
    encoded_jwt = request.headers.get('Authorization')
    if not encoded_jwt:
        return Response("No authorization header found", status=401)

    _, raw_jwt = encoded_jwt.split() # Remove "Bearer"
    decoded = jwt.decode(raw_jwt, algorithms=['HS256'], verify=False)

    subscription = Subscription.query.filter(Subscription.user_id == decoded["userId"]).first()
    if not subscription:
        return Response(status=404)

    session = stripe.billing_portal.Session.create(
        customer=subscription.stripe_customer_id,
        return_url=stripe_portal_return_url,
    )
    return jsonify(url=session.url)


@app.route('/stripe-webhook', methods=['POST'])
def stripe_webhook():
    return handle_stripe_webhook(request, stripe_endpoint_secret)


@app.route('/subscription', methods=['GET'])
def subscription():
    encoded_jwt = request.headers.get('Authorization')
    if not encoded_jwt:
        return Response("No authorization header found", status=401)

    _, raw_jwt = encoded_jwt.split() # Remove "Bearer"
    decoded = jwt.decode(raw_jwt, algorithms=['HS256'], verify=False)

    subscription = Subscription.query.filter(Subscription.user_id == decoded["userId"]).first()
    if not subscription:
        return Response(status=404)
    return jsonify(subscription)


@app.route("/billing/event", methods=["POST"])
def log() -> str:
    encoded_jwt = request.headers.get('Authorization')
    if not encoded_jwt:
        return Response("No authorization header found", status=401)

    _, raw_jwt = encoded_jwt.split() # Remove "Bearer"
    decoded = jwt.decode(raw_jwt, algorithms=['HS256'], verify=False)

    print("GOT BILLING EVENT ", request.json)

    handle_billing_event(request.json, decoded["userId"])
    return Response(status=200)


@app.route("/usage/workspace", methods=["POST"])
def workspace_usage():
    workspace_id = request.json.get("workspaceId")
    if not workspace_id:
        return Response(status=400)

    print("workspace_id : ", str(workspace_id))
    usage_and_limits = get_workspace_usage_and_limits(workspace_id)
    print(usage_and_limits)
    if not usage_and_limits:
        return jsonify({})

    return jsonify({
        'offer': {
            'items': usage_and_limits[1].items
        },
        'usage': usage_and_limits[0]
    })


@app.route("/usage/user", methods=["POST"])
def user_usage():
    encoded_jwt = request.headers.get('Authorization')
    if not encoded_jwt:
        return Response("No authorization header found", status=401)

    print("JWT : " + str(encoded_jwt))
    _, raw_jwt = encoded_jwt.split() # Remove "Bearer"
    decoded = jwt.decode(raw_jwt, algorithms=['HS256'], verify=False)
    user_id = decoded["userId"]

    usage_and_limits = get_user_usage_and_limits(user_id)
    if not usage_and_limits:
        return jsonify({})

    return jsonify({
        'offer': {
            'items': usage_and_limits[1].items
        },
        'usage': usage_and_limits[0]
    })


# These two lines are used only while developing.
# In production this code will be run as a module.
if __name__ == "__main__":
    app.run(host='0.0.0.0', port=int(os.getenv("PORT")))
    init_db()


