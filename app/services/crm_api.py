def sync_client(params: dict) -> dict:
    client_id = params.get("client_id", "unknown")
    action = params.get("action", "upsert")
    return {
        "crm_sync": f"{action} client_id={client_id}",
        "status": "success"
    }
