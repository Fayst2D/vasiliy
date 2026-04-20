# Vasiliy 2.0

This project is an example of a chatbot based on agentic AI.

# Installation guide

1. Install ```uv```
2. Run ```uv sync``` in the repo root
3. Obtain Gemini API and Telegram API keys. Make a ```keys.yaml``` file with the following structure:

```
telegram: <TELEGRAM TOKEN>
gemini: <GEMINI TOKEN>
```
4. Run the bot: ```uv run main.py```

# Configuration files

All the configuration files (including prompt) are located in the [config](config/) directory. Feel free to experiment with prompts and parameters.