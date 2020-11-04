from flask_inputs import Inputs
from flask_inputs.validators import JsonSchema

# https://pythonhosted.org/Flask-Inputs/#module-flask_inputs
# https://json-schema.org/understanding-json-schema/
# noinspection SpellCheckingInspection
checkout_session_schema = {
    'type': 'object',
    'properties': {
        'price': {
            'type': 'string',
        },
        'offer': {
            'type': 'integer'
        }
    },
    'required': ['price', 'offer']
}


class CheckoutSessionInputs(Inputs):
    json = [JsonSchema(schema=checkout_session_schema)]


def validate_checkout_session(request):
    inputs = CheckoutSessionInputs(request)
    if inputs.validate():
        return None
    else:
        return inputs.errors
