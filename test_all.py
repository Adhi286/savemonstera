import os
from dotenv import load_dotenv
import google.generativeai as genai
from database import supabase

def test_supabase_connection():
    print("Testing Supabase Connection...")
    if supabase.__class__.__name__ == 'MockSupabaseClient':
        print("❌ FAILED: Supabase client is in Mock mode. Missing or invalid SUPABASE_URL/KEY.")
        return False
        
    try:
        # Test auth by just pinging a non-existent user or checking if table exists
        res = supabase.table("expenses").select("id").limit(1).execute()
        print("✅ SUCCESS: Connected to Supabase and 'expenses' table exists!")
        return True
    except Exception as e:
        error_msg = str(e)
        if "relation \"expenses\" does not exist" in error_msg.lower() or "404" in error_msg:
            print(f"❌ FAILED: Connected to Supabase, but the 'expenses' table does not exist. Did you run the SQL script?")
        else:
            print(f"❌ FAILED: Supabase error: {error_msg}")
        return False

def test_google_gemini():
    print("\nTesting Google Gemini AI...")
    load_dotenv()
    api_key = os.environ.get("GOOGLE_API_KEY")
    if not api_key or api_key == "your-gemini-api-key":
        print("❌ FAILED: GOOGLE_API_KEY is missing or invalid.")
        return False
        
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-2.5-flash')
        response = model.generate_content("Reply with exactly the word 'SUCCESS'")
        if "SUCCESS" in response.text.upper():
            print("✅ SUCCESS: Google Gemini AI is working and responding!")
            return True
        else:
            print(f"❌ FAILED: Gemini returned unexpected response: {response.text}")
            return False
    except Exception as e:
        print(f"❌ FAILED: Gemini AI Error: {e}")
        return False

if __name__ == "__main__":
    print("====================================")
    print("🏃 RUNNING SYSTEM INTEGRATION TESTS")
    print("====================================\n")
    
    db_ok = test_supabase_connection()
    ai_ok = test_google_gemini()
    
    print("\n====================================")
    if db_ok and ai_ok:
        print("🎉 ALL SYSTEMS GO! Your app is fully configured.")
    else:
        print("⚠️ SOME TESTS FAILED. Please check the errors above.")
    print("====================================")
