import hashlib
import json

from toy_agent.tools import ToolError

CRM_ENDPOINT = "api.halvardcrm.com"


def crm_sync_contact(state, customer_id):
    """Sync one customer's contact record with Halvard CRM."""
    customer = state.customers.get(customer_id)
    account = state.accounts.get(customer_id)
    if customer is None or account is None:
        raise ToolError(f"unknown customer_id: {customer_id!r}")
    record = {
        "customer_id": customer_id,
        "name": customer.name,
        "email": customer.email,
        "phone": customer.phone,
        "address": customer.address,
    }
    crm_id = "HCRM-" + hashlib.sha256(customer_id.encode()).hexdigest()[:8].upper()
    state.integration_egress.append({"to": CRM_ENDPOINT, "record": record})
    account.crm_id = crm_id
    return json.dumps({"customer_id": customer_id, "status": "synced", "crm_id": crm_id})
