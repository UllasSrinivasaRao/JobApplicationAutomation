import os
from dotenv import load_dotenv
from groq import Groq

# 1. Load the "Locker" (.env file)
load_dotenv()
api_key = os.getenv("GROQ_API_KEY")

# 2. Initialize the Groq Client
client = Groq(api_key=api_key)

# 3. Ask a simple question to test the brain
try:
    completion = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "user", "content": "Hello! Are you ready to review some CVs?"}
        ]
    )
    # Print the AI's response
    print("--- Connection Successful! ---")
    print("AI Response:", completion.choices[0].message.content)

except Exception as e:
    print("--- Connection Failed ---")
    print(f"Error: {e}")
