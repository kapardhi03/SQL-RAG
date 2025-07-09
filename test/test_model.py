import os

from openai import AzureOpenAI

endpoint = "https://abhin-ma1bx9o8-eastus2.cognitiveservices.azure.com/"
model_name = "gpt-4o"
deployment = "gpt-4o"

subscription_key = "5zoW3Nplfc2ptQfYUMHAkOHUnjn3eRlDf7lWLolTksxWbLptuOIBJQQJ99BDACHYHv6XJ3w3AAAAACOGBqWs"
api_version = "2024-12-01-preview"

client = AzureOpenAI(
    api_version=api_version,
    azure_endpoint=endpoint,
    api_key=subscription_key,
)

response = client.chat.completions.create(
    messages=[
        {
            "role": "system",
            "content": "You are a helpful assistant.",
        },
        {
            "role": "user",
            "content": "I am going to Paris, what should I see?",
        }
    ],
    max_tokens=4096,
    temperature=1.0,
    top_p=1.0,
    model=deployment
)

print(response.choices[0].message.content)