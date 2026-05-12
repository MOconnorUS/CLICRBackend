import os

from supabase import create_client, Client
from dotenv import load_dotenv
from datetime import datetime, timezone

supabase: Client | None = None

def establish_connection() -> Client:
    """
    Establish the connection with our Supabase DataBase.

    ::return the Supabase Client
    """

    global supabase

    load_dotenv()

    url: str = os.getenv("SUPABASE_URL")
    key: str = os.getenv("SUPABASE_SECRET_KEY")
    supabase = create_client(url, key)

    return supabase

def fetch(venue: str, column: str) -> int | str:
    """
    Fetch the integer values from supabase.

    ::param venue the venue name
    ::param column the column string name
    ::return int the int value returned or a string error response if empty
    """

    try:
        response = supabase.table("testIncrement").select(column).eq("venue", venue).execute()
    except Exception as e:
        return f'Error Fetching Data: {e}'
        
    data = response.data

    if len(data) == 0:
        return f'No Values Returned'

    return data[0][column]

def update(venue: str, column: str) -> bool:
    """
    Updates either the entered or exited data.

    ::param venue the venue string
    ::param column the string to specify people_entered or people_exited
    ::return either True if the execution was successful or false if it failed
    """

    col_val = fetch(venue, column)

    if type(col_val) is str:
        print(col_val)
        return False

    col_val += 1

    try:
        supabase.table("testIncrement").update({column:col_val}).eq("venue", venue).execute()
    except Exception as e:
        print(f'Error Updating Data: {e}')
        return False
    
    return True

def update_live_count(venue: str) -> bool:
    """
    Updates the live count at the venue by fetching the people entered and exited and doing a subtraction update

    ::param venue the venue name
    ::return True upon success and False otherwise
    """

    # Note: this may get expensive for scaling if we continue doing a double query every time we update
    # Instead we may want to group it into one single query, not sure how much more efficient it will be
    # But probably better in the long run
    entered_val = fetch(venue, "people_entered")
    exited_val = fetch(venue, "people_exited")

    if type(entered_val) is str:
        print(entered_val)
        return False
    
    if type(exited_val) is str:
        print(exited_val)
        return False
    
    # May want future error handling for negatives, for now we will do 0
    live_count = entered_val - exited_val

    if live_count < 0:
        live_count = 0

    try:
        supabase.table("testIncrement").update({"live_count": live_count}).eq("venue", venue).execute()
    except Exception as e:
        print(f'Error Updating Live Count: {e}')
        return False
    
    return True

# Note: we would use this function below to create a new venue in our table to store their data, eventually we may want the venue name to be a 
# Primary key to another table to store their historicals so we can draw on it for the insights.
def insert() -> bool:
    """
    Inserts a new record for the column based on the id.

    ::return true upon success and false otherwise
    """

    # This will have to be modified along with the params to ensure we can create a new venue probably based on a form entry via the app or webapp
    # or both
    # Also Note: this is more for the SQL, we want venue names to NOT be unique since there can be venues with the same name BUT we want to make a 
    # unique ID associated with each venue - this ID will allow connections when we have different websockets for different venues
    test_data = {
        "id": 3,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "people_entered": 1,
        "people_exited": 0,
        "live_count": 0,
        "venue": "test venue3"
    }

    try:
        supabase.table("testIncrement").insert(test_data).execute()
    except Exception as e:
        print(f'Error Creating New Venue: {e}')
        return False

    return True

# For Testing Purposes Only
if __name__ == "__main__":
    load_dotenv()

    supabase = establish_connection()

    update("test venue", "people_entered", supabase)
    update_live_count("test venue", supabase)
    # insert(supabase)

    # fetch("test venue", "people_entered", supabase)

