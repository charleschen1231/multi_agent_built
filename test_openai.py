#!/usr/bin/env python3
import os
from dotenv import load_dotenv
load_dotenv()

api_key = os.getenv('OPENAI_API_KEY') or os.getenv('openai-apikey')
print(f'API Key found: {bool(api_key)}')
print(f'API Key length: {len(api_key) if api_key else 0}')

if api_key:
    from openai import OpenAI
    client = OpenAI(api_key=api_key)
    try:
        response = client.chat.completions.create(
            model='gpt-4o',
            messages=[
                {'role': 'system', 'content': 'You are a helpful assistant.'},
                {'role': 'user', 'content': 'Say "OpenAI API is working!"'}
            ],
            max_tokens=50
        )
        print(f'Response: {response.choices[0].message.content}')
    except Exception as e:
        print(f'Error: {e}')
