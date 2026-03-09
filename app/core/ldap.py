from ldap3 import Server, Connection, ALL, SUBTREE
from app.core.config import settings

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
            print(f"User {username} not found in LDAP")
            return None

        # Grab the exact path (DN) of the user we found
        user_dn = conn.entries[0].entry_dn
        print(f"Found User DN: {user_dn}")

    # 3. Now try to log in (Bind) as that specific user
    try:
        with Connection(server, user=user_dn, password=password, auto_bind=True) as user_conn:
            print("Authentication Successful!")
            return {"dn": user_dn, "username": username}
    except Exception as e:
        print(f"Login failed for {user_dn}: {e}")
        return None
