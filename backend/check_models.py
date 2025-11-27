import google.generativeai as genai

# Configure API
api_key = 'AIzaSyBHq5LxXtqENgENbDiU6O3b9_LmVQkt-bc'
genai.configure(api_key=api_key)

print('=== AVAILABLE TEXT GENERATION MODELS ===\n')
for model in genai.list_models():
    if 'generateContent' in model.supported_generation_methods:
        print(f'✅ Model: {model.name}')
        print(f'   Display Name: {model.display_name}')
        print(f'   Description: {model.description}')
        print()
