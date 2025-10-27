import os
import logging
# from PIL import Image
# import pytesseract
# import fitz
# import io
from azure.storage.blob import BlobServiceClient
import re
import json
from openai import AzureOpenAI
from azure.ai.documentintelligence import DocumentIntelligenceClient
from azure.core.credentials import AzureKeyCredential

# pytesseract.pytesseract.tesseract_cmd = "/home/site/wwwroot/tesseract"
# pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

def azurePrebuildReadOCR(file_path):
    with open(file_path, "rb") as file:
        doc_intelli_client = DocumentIntelligenceClient(
            endpoint=os.getenv("FORM_RECOGNIZER_ENDPOINT"), 
            credential=AzureKeyCredential(os.getenv("FORM_RECOGNIZER_KEY"))
        )
        poller = doc_intelli_client.begin_analyze_document(
            "prebuilt-read", 
            file
        )
        _data = poller.result()
    
    extracted_text = []
    
    for page in _data.pages:
        for line in page.lines:
            extracted_text.append(line.content)
            
    return " ".join(extracted_text)

# def extract_text_from_image(uploaded_file, lang: str = "eng") -> str:
#     """
#     Extracts text from an image using Tesseract OCR.

#     Parameters:
#     - image_path (str): Path to the image file.
#     - lang (str): Language for OCR (default is English: "eng").

#     Returns:
#     - str: Extracted text from the image.
#     """
#     try:
#         # Open the image
#         image = Image.open(uploaded_file)

#         # Extract text
#         text = pytesseract.image_to_string(image, lang=lang)

#         return text.strip()  # Remove leading/trailing spaces
#     except Exception as e:
#         return f"Error: {str(e)}"

# def extract_text_from_pdf(pdf_file):
#     doc = fitz.open(stream=pdf_file.read(), filetype="pdf")
#     extracted_text = ""

#     for page_num in range(len(doc)):
#         page = doc[page_num]

#         # Extract text directly from the page
#         extracted_text += page.get_text("text") + "\n"

#         # Extract images from the page
#         for img_index, img in enumerate(page.get_images(full=True)):
#             xref = img[0]  # Image reference
#             base_image = doc.extract_image(xref)
#             image_data = base_image["image"]

#             # Convert image data to PIL Image
#             img = Image.open(io.BytesIO(image_data))

#             # Apply OCR
#             text_from_image = pytesseract.image_to_string(img)
#             extracted_text += f"\n[Image {img_index} OCR Text]:\n{text_from_image}\n"

#     return extracted_text


def extract_entities(text):
    try:
        """Extract entities from text using Azure OpenAI."""
        endpoint = os.getenv("AZURE_OPENAI_ENDPOINT", "")  
        deployment = os.getenv("DEPLOYMENT_NAME", "")
        subscription_key = os.getenv("AZURE_OPENAI_KEY", "")  

        # Initialize Azure OpenAI Service client with key-based authentication    
        client = AzureOpenAI(  
            azure_endpoint=endpoint,  
            api_key=subscription_key,  
            api_version=os.getenv("AZURE_OPENAI_API_VERSION")    
            )

        chat_prompt = [
        {
            "role": "system",
            "content": [
            {
                    "type": "text",
                    "text": "You are an advanced AI specializing in extracting key entities from demand letters." 
                            "Your task is to extract the following details from the attached document:\n\n"
                            "Entities are in single quotes. In json output that caption should be."
                            "\n\nEntities to Extract:"
                            "- 'Policy Number', 'Name of the claimant', 'Claim Amount', 'Claim Number'," 
                            " 'Letter Adressed To', 'Name of the Insurer Designated person', 'Name of the insurance company'," 
                            "- 'Dates' : All types of dates (along with their respective captions)\n"
                            "- 'Summary' : (must include as a top-level key)\n\n"
                            " \n \n\n "
                            "Output Format:"
                            "- The extracted data should be structured in JSON format.\n"
                            "- If any value is not available, do not add that key.\n" 
                            "- The summary is in bullet points, containing the complete letter summary.\n" 
                            "- In summary, do not add word more then 30 characters.\n"
                            "- Ensure accuracy, proper formatting, and completeness in your response."
                }
                    ]
                },
                {
                    "role": "user",
                    "content": text
                }
            ]

            
        # Include speech result if speech is enabled  
        messages = chat_prompt 

        completion = client.chat.completions.create(  
            model=deployment,  
            messages=messages,
            # max_tokens=800,  
            temperature=0.7,  
            top_p=0.95,  
            stop=None,  
            stream=False  
        )  
        
        match = re.search(r'```json\n(.*?)\n```', completion.choices[0].message.content, re.DOTALL)
        json_data = {}
        if match:
            clean_json = match.group(1)
            json_data = json.loads(clean_json)

        return json_data
    except Exception as e:
        logging.error(f"Error extracting entities: {str(e)}")
        import traceback
        logging.error(f"Traceback: {traceback.format_exc()}")




def upload_pdf_file_to_blob(uploaded_file):
    try:
        AZURE_BLOB_CONNECTION_STRING = os.getenv("AZURE_BLOB_CONNECTION_STRING")
        AZURE_CONTAINER_NAME = os.getenv("AZURE_CONTAINER_NAME")

        # Initialize Azure Blob Client
        if not AZURE_BLOB_CONNECTION_STRING:
            raise ValueError("AZURE_BLOB_CONNECTION_STRING environment variable is not set")
        
        blob_service_client = BlobServiceClient.from_connection_string(AZURE_BLOB_CONNECTION_STRING)

        container_client = blob_service_client.get_container_client(AZURE_CONTAINER_NAME)
        
        blob_name = uploaded_file.name

        blob_client = container_client.get_blob_client(blob_name)
        blob_client.upload_blob(uploaded_file.getvalue(), overwrite=True)

        return blob_client.url

    except Exception as e:
        print(f"Error uploading PDF file to Azure Blob Storage: {str(e)}")
        return None

def upload_json_to_blob(
        json_data: dict,
        blob_name: str):
    try:
        AZURE_BLOB_CONNECTION_STRING = os.getenv("AZURE_BLOB_CONNECTION_STRING")
        AZURE_CONTAINER_NAME = os.getenv("AZURE_CONTAINER_NAME")

        # Initialize Azure Blob Client
        if not AZURE_BLOB_CONNECTION_STRING:
            raise ValueError("AZURE_BLOB_CONNECTION_STRING environment variable is not set")
        
        blob_service_client = BlobServiceClient.from_connection_string(AZURE_BLOB_CONNECTION_STRING)

        container_client = blob_service_client.get_container_client(AZURE_CONTAINER_NAME)
        
        blob_client = container_client.get_blob_client(blob_name)

        json_string = json.dumps(json_data, indent=4)
        blob_client.upload_blob(json_string, overwrite=True)

        return blob_client.url

    except Exception as e:
        print(f"Error uploading JSON data to Azure Blob Storage: {str(e)}")
        return None
    
def extract_text_from_document(file_path, file_extension):
    AZURE_ENDPOINT = os.getenv("FORM_RECOGNIZER_ENDPOINT")
    AZURE_KEY = os.getenv("FORM_RECOGNIZER_KEY")
    client = DocumentIntelligenceClient(AZURE_ENDPOINT, AzureKeyCredential(AZURE_KEY))
    with open(file_path, "rb") as file:
        poller = client.begin_analyze_document("prebuilt-read", file)
        result = poller.result()
    if result is not None:
        if file_extension in [".docx", ".xlsx"]:
            extracted_text = result.content
        elif result.pages:
            extracted_text = "\n".join([line.content for page in result.pages if page.lines for line in page.lines])
        else:
            extracted_text = "No text found in the document."
    else:
        extracted_text = "No text found in the document."
    return extracted_text

import tempfile
import zipfile

def process_uploaded_file(file_path: str):
    file_extension = os.path.splitext(file_path)[1].lower()

    if file_extension in [".png", ".jpg", ".jpeg", ".pdf", ".docx", ".xlsx"]:
        return extract_text_from_document(file_path, file_extension)
    elif file_extension == ".zip":
        extracted_text = {}
        with tempfile.TemporaryDirectory() as temp_dir:
            with zipfile.ZipFile(file_path, 'r') as zip_ref:
                zip_ref.extractall(temp_dir)
            for root, _, files in os.walk(temp_dir):
                for file_name in files:
                    file_path = os.path.join(root, file_name)
                    file_ext = os.path.splitext(file_name)[1].lower()
                    extracted_text[file_name] = extract_text_from_document(file_path, file_ext)
        return extracted_text
    else:
        return f"Unsupported file format: {file_path}"

def process_attachments(metadata: dict):
    
    folder_path = os.getenv("TEMP_FOLDER_PATH", "/tmp/")+"Attachments_Latest"
    if not os.path.exists(folder_path):
        logging.error(f"Folder {folder_path} does not exist.")
        return

    extracted_data = {}
    for file_name in os.listdir(folder_path):
        file_path = os.path.join(folder_path, file_name)
        logging.warning(f"Processing file: {file_path}")

        if os.path.isfile(file_path):
            extracted_text = process_uploaded_file(file_path)
            extracted_data[file_name] = extracted_text

    logging.warning(f"Extracted data: {extracted_data}")
    json_data = json.dumps(extracted_data, indent=4)
    
    # In metadata, use the 'From' field to create a folder in the blob and upload the JSON file in that folder
    if "From" in metadata:
        username = metadata["From"].split("@")[0]
        date = metadata["Received Date"]
        time = metadata["Received Time"].replace(" IST", "").replace(":", "-")

        # Build folder name
        folder_name = f"{username}_{date}_{time}"

        blob_name = f"{folder_name}/extracted_data.json"
        upload_json_to_blob(json_data, blob_name)
        # Save metadata.json in the same folder in the blob
        metadata_blob_name = f"{folder_name}/metadata.json"
        upload_json_to_blob(metadata, metadata_blob_name)
    else:
        logging.error("The 'From' field is missing in metadata. Cannot create folder in blob.")

        # if _text:
        #     entities = extract_entities(_text)
        #     # logging.error(f"Extracted entities: {entities}")
        #     Policy_Number = entities.get("Policy Number", "")
        #     if not Policy_Number:
        #         logging.warning("Policy Number not found in the extracted entities."
        #                         "Skipping uploading to Azure Blob Storage.")
        #     else:
        #         # Policy_Number = file_name.split('.')[0]
        #         upload_pdf_file_to_blob(file_path)
        #         upload_json_to_blob(entities, f"{Policy_Number}.json")