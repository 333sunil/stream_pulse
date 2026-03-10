from ldap3 import Server, Connection, ALL, SUBTREE
from app.core.config import settings
from cachetools import TTLCache
import hashlib
from loguru import logger

# Create a cache for storing authentication results
auth_cache = TTLCache(maxsize=100, ttl=300)  # Cache up to 100 items for 5 minutes


def get_auth_cache_key(username, password):
    # Create a unique key based on both username and password
    # We hash the combination to avoid storing the raw password in the cache keys
    return hashlib.sha256(f"{username}:{password}".encode()).hexdigest()

def authenticate_user_cached(username, password):
    cache_key = get_auth_cache_key(username, password)
    
    # 2. Check if user is in cache
    if cache_key in auth_cache:
        logger.debug(f"Cache HIT for {username}")
        return auth_cache[cache_key]

    # 3. Cache MISS: Call your existing LDAP function
    logger.debug(f"Cache MISS for {username}. Calling LDAP...")
    user_data = authenticate_user_simple(username, password)

    if user_data:
        # 4. Store successful result in cache
        auth_cache[cache_key] = user_data
    
    return user_data

def authenticate_user_simple(username, password):
    # 1. Server Config (Matches your Docker-Compose)
    LDAP_SERVER = f"ldap://{settings.LDAP_SERVER}:{settings.LDAP_PORT}"

    server = Server(LDAP_SERVER, get_info=ALL)
    
    # 2. Connect as Admin to find the user
    with Connection(server, user=settings.LDAP_USER, password=settings.LDAP_PASSWORD, auto_bind=True) as conn:
        search_filter = f"(|(uid={username})(cn={username}))"
        
        conn.search(
            search_base=settings.LDAP_BASE_DN, 
            search_filter=search_filter, 
            search_scope=SUBTREE
        )

        if not conn.entries:
            logger.debug(f"User {username} not found in LDAP")
            return None

        # Grab the exact path (DN) of the user we found
        user_dn = conn.entries[0].entry_dn
        logger.debug(f"Found User DN: {user_dn}")

    # 3. Now try to log in (Bind) as that specific user
    try:
        with Connection(server, user=user_dn, password=password, auto_bind=True) as user_conn:
            logger.debug("Authentication Successful!")
            return {"dn": user_dn, "username": username}
    except Exception as e:
        logger.debug(f"Login failed for {user_dn}: {e}")
        return None
