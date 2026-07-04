import os
import uuid
import datetime
from supabase import create_client, Client
from dotenv import load_dotenv
import threading

load_dotenv()

url: str = os.environ.get("SUPABASE_URL", "")
key: str = os.environ.get("SUPABASE_KEY", "")

class MockResponse:
    def __init__(self, data=None):
        self.data = data if data is not None else []

class MockAuthUser:
    def __init__(self, uid, email, name):
        self.id = uid
        self.email = email
        self.user_metadata = {"name": name}

class MockAuthSession:
    def __init__(self, token):
        self.access_token = token

class MockAuthResponse:
    def __init__(self, user, session=None):
        self.user = user
        self.session = session

class MockQueryBuilder:
    def __init__(self, table_name, db):
        self.table_name = table_name
        self.db = db
        self._action = None
        self._payload = None
        self._filters = []
        self._order = None
        self._limit = None

    def select(self, columns):
        self._action = "select"
        return self

    def insert(self, data):
        self._action = "insert"
        self._payload = data if isinstance(data, list) else [data]
        return self

    def update(self, data):
        self._action = "update"
        self._payload = data
        return self

    def eq(self, column, value):
        self._filters.append(("eq", column, value))
        return self

    def like(self, column, value):
        self._filters.append(("like", column, value.replace('%', '')))
        return self
        
    def gte(self, column, value):
        self._filters.append(("gte", column, value))
        return self
        
    def lte(self, column, value):
        self._filters.append(("lte", column, value))
        return self

    def order(self, column, desc=False):
        self._order = (column, desc)
        return self

    def limit(self, count):
        self._limit = count
        return self

    def execute(self):
        records = self.db.get(self.table_name, [])
        result = []
        
        if self._action == "insert":
            for item in self._payload:
                new_item = item.copy()
                if "id" not in new_item:
                    new_item["id"] = str(uuid.uuid4())
                if "created_at" not in new_item:
                    new_item["created_at"] = datetime.datetime.now().isoformat()
                records.append(new_item)
                result.append(new_item)
            self.db[self.table_name] = records
            return MockResponse(result)

        elif self._action == "update":
            for item in records:
                match = True
                for f_type, col, val in self._filters:
                    if f_type == "eq" and item.get(col) != val:
                        match = False
                if match:
                    item.update(self._payload)
                    result.append(item)
            return MockResponse(result)

        elif self._action == "select":
            for item in records:
                match = True
                for f_type, col, val in self._filters:
                    if f_type == "eq" and item.get(col) != val:
                        match = False
                    elif f_type == "like" and val not in str(item.get(col)):
                        match = False
                    elif f_type == "gte" and str(item.get(col)) < str(val):
                        match = False
                    elif f_type == "lte" and str(item.get(col)) > str(val):
                        match = False
                if match:
                    result.append(item)
                    
            if self._order:
                col, desc = self._order
                result.sort(key=lambda x: x.get(col, ""), reverse=desc)
                
            if self._limit:
                result = result[:self._limit]
                
            return MockResponse(result)
            
        return MockResponse([])

class MockAuth:
    def __init__(self, db):
        self.db = db
        
    def sign_up(self, credentials):
        email = credentials.get("email")
        password = credentials.get("password")
        name = credentials.get("options", {}).get("data", {}).get("name", "")
        
        if any(u.get("email") == email for u in self.db["users"]):
            raise Exception("User already exists")
            
        uid = str(uuid.uuid4())
        user = {"id": uid, "email": email, "password": password, "name": name}
        self.db["users"].append(user)
        
        return MockAuthResponse(MockAuthUser(uid, email, name))
        
    def sign_in_with_password(self, credentials):
        email = credentials.get("email")
        password = credentials.get("password")
        
        for u in self.db["users"]:
            if u["email"] == email and u["password"] == password:
                token = f"mock-token-{u['id']}"
                return MockAuthResponse(
                    MockAuthUser(u["id"], u["email"], u["name"]),
                    MockAuthSession(token)
                )
        raise Exception("Invalid credentials")
        
    def get_user(self, token):
        uid = token.replace("mock-token-", "")
        for u in self.db["users"]:
            if u["id"] == uid:
                return MockAuthResponse(MockAuthUser(u["id"], u["email"], u["name"]))
        raise Exception("Invalid token")

class MockSupabaseClient:
    def __init__(self):
        self._db = {"expenses": [], "budgets": [], "users": []}
        self.auth = MockAuth(self._db)
        
    def table(self, table_name):
        return MockQueryBuilder(table_name, self._db)

# Don't try to create client if it's the placeholder
if url == "your-supabase-url" or not url or not key:
    print("Using In-Memory Mock Supabase Client")
    supabase = MockSupabaseClient()
else:
    try:
        supabase = create_client(url, key)
    except Exception as e:
        print(f"Failed to init Supabase client: {e}")
        supabase = MockSupabaseClient()

def init_db():
    db_url = os.environ.get("DATABASE_URL")
    if not db_url or db_url == "your-postgres-connection-string":
        print("DATABASE_URL not set or placeholder, skipping actual table auto-creation.")
        return

    try:
        import psycopg2
        conn = psycopg2.connect(db_url)
        conn.autocommit = True
        cur = conn.cursor()
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS expenses (
              id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
              user_id UUID NOT NULL,
              date DATE NOT NULL,
              description TEXT,
              amount FLOAT NOT NULL DEFAULT 0,
              category TEXT DEFAULT 'Other',
              type TEXT DEFAULT 'debit',
              mode TEXT DEFAULT 'manual',
              status TEXT DEFAULT 'approved',
              ref_no TEXT,
              created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
            );
        """)
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS budgets (
              id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
              user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
              weekly_limit FLOAT DEFAULT 500,
              monthly_limit FLOAT DEFAULT 2000,
              agent_threshold FLOAT DEFAULT 100,
              updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
            );
        """)
        
        cur.close()
        conn.close()
        print("Tables initialized successfully.")
    except Exception as e:
        print(f"Error initializing tables: {e}")

