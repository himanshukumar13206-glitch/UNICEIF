from config import OWNER_ID, DEVS

AUTHORIZED_USERS = [OWNER_ID] + DEVS

def is_authorized(user_id: int) -> bool:
    """Only bot owner and devs can control."""
    if not AUTHORIZED_USERS:
        return True
    return user_id in AUTHORIZED_USERS

async def log_message(client, text: str):
    from config import LOGGER_ID
    if LOGGER_ID:
        try:
            await client.send_message(LOGGER_ID, text)
        except:
            pass
