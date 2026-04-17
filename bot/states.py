import json
import redis


redis_client = redis.StrictRedis(host='redis', port=6379, db=0)


class States:
    WAITING_FOR_ADMIN_MESSAGE = "waiting_for_admin_message"
    WAITING_FOR_CLIENT_MESSAGE = "waiting_for_client_message"
    ADMIN_BROADCAST_WAITING = "admin_broadcast_waiting"


def set_user_state(user_id, state):
    redis_client.set(f"user_state:{user_id}", json.dumps(state))

def get_user_state(user_id):
    try:
        return json.loads(redis_client.get(f"user_state:{user_id}"))
    except:
        return {}

def reset_user_state(user_id):
    redis_client.delete(f"user_state:{user_id}")
