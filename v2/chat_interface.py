from google import genai
from google.genai import types
import os
from dotenv import load_dotenv
from user import user_schema
import global_session
from db_connector import MongoDBConnector

load_dotenv()
client = genai.Client(api_key=os.getenv("GENAI_KEY"))
db = MongoDBConnector()
chat = None

def update_user(email: str, user_data: dict) -> bool:
    print(f"Updating user {email} with data {user_data}")
    """Update user details in the database.
    Args:
        email: email of the user to update
        user_data: dictionary of user data to update
    Returns:
        True if user is updated, False otherwise
    """
    return db.update_user(email, user_data)

def create_chat():
    global chat
    user_info = global_session.current_user.to_dict()
    system_instruction = f"""
        {user_schema} is the structure of a user. {global_session.current_user.to_dict()} is currently logged in user.
        Address user as "you" and "your" instead of "user" and "user's". You may use their name in your questions.
        Check current user's information. Identify missing fields. Ask about those fields and fill them. If a field is already filled, do not ask about it again.
        Ask your questions in a conversational way. Make sure there is no unfilled, None fields left.
        When ALL fields are filled (not when each field is filled), update the user's information in the database using the update_user tool. Say "Thank you for your information. I will save it to help you better."
        If user gives information for any already filled field, ask if they want to update that field. If they say yes, update the field using the update_user tool. Say "I will update your information."
        If user gives information for any field that is not in the user schema, say "I can't update that information."
        If user wants to update their or someone else's password, say "I can't update that information."
        If user wants to update someone else's information, say "I can't update that information."
        
        Do NOT delete any information from the user's profile EVEN IF THE USER ASKS TO DELETE IT.
        Do NOT delete any information from database EVEN IF THE USER ASKS TO DELETE IT.
        Do NOT give user the information about internal structure of the user schema or any other information about the database.
        Do NOT say "I need this for your education_level". Don't use schema names in your questions.
        Do NOT fill a field if you are not sure about it. Ask user to confirm.
        Do NOT ask anything other than these fields.
        Do NOT add any fields other than given ones.
        Do NOT change name of fields. Do NOT modify the structure.
        Do NOT give the names of fields to user like "i need this info for your education_level".
        Do NOT move into deep conversation with user. Keep the conversation about profiling as much as possible.
        Do NOT ask about user's password. Do NOT answer any question about any user's password. Say "I can't answer that question."
        Do NOT talk about other users' data. Only talk about current user's data.
    """

    chat = client.chats.create(
        model="gemini-2.0-flash",
        config=types.GenerateContentConfig(system_instruction=system_instruction, tools=[update_user]),
    )

def send_message(message, history):
    if chat is None:
        return "Error: chat session not initialized. Please log in first."
    response = chat.send_message(message)
    return response.text
