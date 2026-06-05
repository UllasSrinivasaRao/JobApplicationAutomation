import os
from dotenv import load_dotenv
from cerebras.cloud.sdk import Cerebras

# 1. Load the "Locker" (.env file)
load_dotenv()
api_key = os.getenv("CEREBRAS_API_KEY")

# 2. Initialize the Cerebras Client
client = Cerebras(api_key=api_key)

# 3. Ask a simple question to test the brain
try:
    completion = client.chat.completions.create(
        model="llama3.1-8b",# This is a fast, efficient model
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