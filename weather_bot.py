import os
from dotenv import load_dotenv
from openai import OpenAI
import random
import json

# Load environment variables
load_dotenv()

# Initialize OpenAI client
client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY"),
    base_url=os.getenv("OPENAI_API_BASE")
)

def get_current_temperature(location: str, unit: str) -> float:
    """Simulate getting temperature for a location"""
    base_temp = random.uniform(15, 30)
    if unit == "Fahrenheit":
        return (base_temp * 9/5) + 32
    return base_temp

def get_rain_probability(location: str) -> int:
    """Simulate getting rain probability for a location"""
    return random.randint(0, 100)

def process_weather_query(query: str):
    functions = [
        {
            "type": "function",
            "function": {
                "name": "get_current_temperature",
                "description": "Get the current temperature for a specific location",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "location": {
                            "type": "string",
                            "description": "The city and state, e.g., San Francisco, CA"
                        },
                        "unit": {
                            "type": "string",
                            "enum": ["Celsius", "Fahrenheit"],
                            "description": "The temperature unit to use"
                        }
                    },
                    "required": ["location", "unit"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "get_knowledge_base",
                "description": " Company Administrative Knowledge Base (shuttle bus, travel, parking space management, welfare meals, express delivery, item collection, etc. and other common problems)",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                             "description": "a group of search query keys. some keys tag are related with 公司行政知识库（班车类、差旅、车位办理、福利餐类、快递、物品领用类……等其他 常见问题）(required)"
                                
                        }
                    },
                    "required": [
                        "query"
                    ]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "get_rain_probability",
                "description": "Get the probability of rain for a specific location",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "location": {
                            "type": "string",
                            "description": "The city and state, e.g., San Francisco, CA"
                        }
                    },
                    "required": ["location"]
                }
            }
        }
    ]

    messages = [
        {"role": "system", "content": "You are a tool bot. Use the provided functions to answer tool-related questions. For Chinese users, default to Celsius."},
        {"role": "user", "content": query}
    ]

    try:
        response = client.chat.completions.create(
            model=os.getenv("OPENAI_MODEL"),
            messages=messages,
            tools=functions,
            tool_choice="auto"
        )

        assistant_message = response.choices[0].message
        print(assistant_message)
        if hasattr(assistant_message, 'tool_calls') and assistant_message.tool_calls:
            # Add the assistant message with tool calls
            messages.append(assistant_message)
            
            # Process each tool call and add tool messages
            for tool_call in assistant_message.tool_calls:
               
                function_name = tool_call.function.name
                function_args = json.loads(tool_call.function.arguments)
                
                if function_name == "get_current_temperature":
                    result = get_current_temperature(
                        function_args["location"],
                        function_args["unit"]
                    )
                elif function_name == "get_rain_probability":
                    result = get_rain_probability(function_args["location"])
                else:
                    raise ValueError(f"Unknown function: {function_name}")
                # Add individual tool message for each tool call
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "name": function_name,
                    "content": str(result)
                })
            
            # Get the final response
            final_response = client.chat.completions.create(
                model=os.getenv("OPENAI_MODEL"),
                messages=messages
            )
            return final_response.choices[0].message.content
        
        return assistant_message.content
    except Exception as e:
        print(f"Detailed error: {str(e)}")
        raise

if __name__ == "__main__":
    print("Weather Bot initialized! Ask me about the weather (type 'quit' to exit)")
    while True:
        user_query = input("\nYour question: ")
        if user_query.lower() == 'quit':
            break
        
        try:
            response = process_weather_query(user_query)
            print(f"Assistant: {response}\n")
        except Exception as e:
            print(f"Error processing query: {e}")
    
    print("Goodbye!")