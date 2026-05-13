import os

from supabase import create_client, Client
from dotenv import load_dotenv
from datetime import datetime, timezone

supabase: Client | None = None

class DB:
    def __init__(self):
        self.supabase: Client | None = None

    def establish_connection(self) -> None:
        """
        Establish the connection with our Supabase DataBase.
        """

        load_dotenv()

        url: str = os.getenv("SUPABASE_URL")
        key: str = os.getenv("SUPABASE_SECRET_KEY")
        self.supabase = create_client(url, key)

        return None

    def fetch(self, venue: str, column: str) -> int | str:
        """
        Fetch the integer values from supabase.

        ::param venue the venue name
        ::param column the column string name
        ::return int the int value returned or a string error response if empty
        """

        try:
            response = self.supabase.table("testIncrement").select(column).eq("venue", venue).execute()
        except Exception as e:
            return f'Error Fetching Data: {e}'
            
        data = response.data

        if len(data) == 0:
            return f'No Values Returned'

        return data[0][column]

    def update(self, venue: str, value: int, column: str = "") -> bool:
        """
        Updates either the entered or exited data if a column is provided otherwise it updates the live count.

        ::param venue the venue string
        ::param column the string to specify people_entered or people_exited
        ::param value the int value to replace the current value with
        ::return either True if the execution was successful or false if it failed
        """

        if column == "":
            column = "live_count"

        try:
            self.supabase.table("testIncrement").update({column:value}).eq("venue", venue).execute()
        except Exception as e:
            print(f'Error Updating Data: {e}')
            return False
        
        return True

    # Note: we would use this function below to create a new venue in our table to store their data, eventually we may want the venue name to be a 
    # Primary key to another table to store their historicals so we can draw on it for the insights.
    def insert(self) -> bool:
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
            "people_entered": 0,
            "people_exited": 0,
            "live_count": 0,
            "venue": "test venue3"
        }

        try:
            self.supabase.table("testIncrement").insert(test_data).execute()
        except Exception as e:
            print(f'Error Creating New Venue: {e}')
            return False

        return True

# For Testing Purposes Only
if __name__ == "__main__":
    load_dotenv()

    # supabase = establish_connection()

    # update("test venue", "people_entered", supabase)
    # update_live_count("test venue", supabase)
    # insert()

    # fetch("test venue", "people_entered", supabase)

