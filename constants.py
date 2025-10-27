"""
Constants for the Azure Function App
"""
import os

# Azure OpenAI settings
AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
AZURE_OPENAI_KEY = os.getenv("AZURE_OPENAI_KEY")
AZURE_OPENAI_API_VERSION = os.getenv("AZURE_OPENAI_API_VERSION", "2023-05-15")

# Azure Document Intelligence settings
DOCAI_ENDPOINT = os.getenv("FORM_RECOGNIZER_ENDPOINT")
DOCAI_KEY = os.getenv("FORM_RECOGNIZER_KEY")

# Processing parameters
CLASSIFICATION_MAX_PAGES = 10
EXTRACTION_MAX_PAGES = 20
EXTRACTION_MAX_CHUNKS = 10
MAX_FILENAME_LENGTH = 100

# Folders
TEMP_FOLDER_PATH = os.getenv("TEMP_FOLDER_PATH", "/tmp/")
EXTRACTIONOUTPUT_PATH = os.path.join(TEMP_FOLDER_PATH, "Extraction_Results")