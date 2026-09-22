# My agent: Culpeper Herbalist Agent
One-liner: A conversational herbalist and domain agent that consults Culpeper's Complete Herbal book to provide medicinal plant remedies, manage plant/food items in Firestore, geocode plant locations, and generate plant imagery.

Tool coverage:
- Memory: User allergies, herbal preferences, and past consultation history
- Tools: consult_herbal_corpus (RAG on Culpeper's Herbal), read_items / write_item (Firestore database), geocode_address / search_nearby_places / get_live_weather_and_aqi (Google Maps & Weather), get_wikipedia_summary
- Catalog/UI: A2UI v0.8 card catalog for herbs, plants, and remedies
- Image gen: generate_item_image (gemini-3.1-flash-lite-image model)
- Sandbox: AgentEngineSandboxCodeExecutor for Python code calculations
