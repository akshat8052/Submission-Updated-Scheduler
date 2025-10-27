# """
# Document Processing Pipeline for Azure Function App
# Adapted from the Submission from images/extraction_v1.py
# """

# import os
# import re
# import json
# import time
# import logging
# import pandas as pd
# from datetime import datetime
# from typing import Dict, Any, List

# # Try importing the necessary packages, handle missing dependencies gracefully
# try:
#     import tiktoken
# except ImportError:
#     logging.warning("tiktoken not installed. Token counting will not be accurate.")
    
#     # Simple fallback for token counting
#     def simple_token_count(text):
#         return len(text.split())
        
#     class DummyTikToken:
#         @staticmethod
#         def encoding_for_model(model):
#             return DummyTikToken()
            
#         @staticmethod
#         def get_encoding(name):
#             return DummyTikToken()
            
#         @staticmethod
#         def encode(text):
#             return [1] * simple_token_count(text)
            
#     tiktoken = DummyTikToken()

# try:
#     from openai import AzureOpenAI
# except ImportError:
#     logging.error("openai package not installed. AI processing will not work.")

# try:
#     from azure.core.credentials import AzureKeyCredential
# except ImportError:
#     logging.error("Azure Core package not installed. Azure services will not work properly.")

# # Local modules
# import constants
# import prompts
# import helper
# # Import specific function from utils
# from utils import upload_json_to_blob

# # Azure OpenAI client setup
# def get_openai_client():
#     """
#     Gets an Azure OpenAI client, with fallbacks
#     """
#     try:
#         from openai import AzureOpenAI
#         return AzureOpenAI(
#             azure_endpoint=constants.AZURE_OPENAI_ENDPOINT,
#             api_key=constants.AZURE_OPENAI_KEY,
#             api_version=constants.AZURE_OPENAI_API_VERSION,
#         )
#     except ImportError:
#         logging.error("OpenAI SDK not installed or not compatible")
        
#         # Create a mock client that logs errors
#         class MockOpenAIClient:
#             def __getattr__(self, name):
#                 def method(*args, **kwargs):
#                     logging.error(f"OpenAI {name} method called but OpenAI SDK not available")
#                     return None
#                 return method
                
#         return MockOpenAIClient()

# # ---------------------------------------------------------------------------
# # OpenAI helpers
# # ---------------------------------------------------------------------------

# def generate_response(prompt_text: str, system_prompt: str, max_tokens: int = 3048) -> str:
#     """Generate a response using Azure OpenAI"""
#     client = get_openai_client()
#     message_text = [
#         {"role": "system", "content": system_prompt},
#         {"role": "user", "content": prompt_text},
#     ]
#     completion = client.chat.completions.create(
#         model="gpt-4o",  # Using the available model in your environment
#         messages=message_text,
#         max_tokens=max_tokens,
#         temperature=0.2,
#         seed=38,
#         top_p=0.9,
#         response_format={"type": "json_object"},
#     )
#     return completion.choices[0].message.content


# def count_tokens(prompt_text: str, model: str = "gpt-4") -> int:
#     """
#     Counts tokens for a given model, with fallbacks for missing dependencies
#     """
#     # First try using tiktoken if available
#     try:
#         if hasattr(tiktoken, "encoding_for_model"):
#             try:
#                 encoding = tiktoken.encoding_for_model(model)
#                 return len(encoding.encode(prompt_text))
#             except (KeyError, AttributeError):
#                 try:
#                     encoding = tiktoken.get_encoding("cl100k_base")  # fallback
#                     return len(encoding.encode(prompt_text))
#                 except (KeyError, AttributeError):
#                     pass
#     except Exception:
#         pass
        
#     # Fallback: simple approximation (4 chars ~= 1 token)
#     return len(prompt_text) // 4

# # ---------------------------------------------------------------------------
# # Email content extraction
# # ---------------------------------------------------------------------------

# def prepare_email_content(metadata: Dict[str, Any]) -> str:
#     """
#     Prepares email content from metadata
#     """
#     from_email = metadata.get("From", "")
#     to_email = metadata.get("To", "")
#     cc_email = metadata.get("CC", "")
#     subject = metadata.get("Subject", "")
#     body = metadata.get("Body", "")
    
#     email_content = f"From: {from_email}\nTo: {to_email}\nCC: {cc_email}\nSubject: {subject}\n\n{body}"
    
#     return email_content

# # ---------------------------------------------------------------------------
# # Classification (Submission vs Non)
# # ---------------------------------------------------------------------------

# def submission_classifier(email_content: str) -> str:
#     """Classify if the email is a submission and determine the line of business"""
#     classification_system_prompt = prompts.submission_classification_system_prompt
#     classification_prompt = prompts.submission_classification_prompt_template.format(
#         email_content=email_content
#     )
#     num_tokens = count_tokens(classification_prompt)
#     print(f"Submission Prompt Token Count: {num_tokens}")
#     response = generate_response(classification_prompt, classification_system_prompt)
#     try:
#         parsed = json.loads(response)
#         return parsed.get("Classification", "Non-Submission")
#     except json.JSONDecodeError:
#         return "Non-Submission"

# # ---------------------------------------------------------------------------
# # Azure Document Intelligence OCR
# # ---------------------------------------------------------------------------

# def extract_ocr_markdown(data: bytes) -> dict:
#     """Extract text from document using Azure Document Intelligence"""
#     try:
#         # Try to use Azure Document Intelligence if available
#         try:
#             from azure.core.credentials import AzureKeyCredential
#             from azure.ai.documentintelligence import DocumentIntelligenceClient
            
#             # Define helper class if the models aren't available
#             class AnalyzeDocumentRequest:
#                 def __init__(self, bytes_source=None):
#                     self.bytes_source = bytes_source
                    
#             class DocumentContentFormat:
#                 MARKDOWN = "markdown"
                
#             # Try to import the proper models if available    
#             try:
#                 from azure.ai.documentintelligence.models import (
#                     AnalyzeDocumentRequest,
#                     DocumentContentFormat,
#                 )
#             except ImportError:
#                 pass
                
#             with DocumentIntelligenceClient(
#                 endpoint=constants.DOCAI_ENDPOINT,
#                 credential=AzureKeyCredential(constants.DOCAI_KEY),
#             ) as client_di:
#                 poller = client_di.begin_analyze_document(
#                     "prebuilt-layout",
#                     AnalyzeDocumentRequest(bytes_source=data),
#                     output_content_format=DocumentContentFormat.MARKDOWN,
#                 )
#                 return poller.result().as_dict()
#         except (ImportError, Exception) as e:
#             logging.warning(f"Azure Document Intelligence failed: {e}. Trying Form Recognizer.")
            
#             # Try to use Form Recognizer (older version) if available
#             try:
#                 from azure.ai.formrecognizer import DocumentAnalysisClient
                
#                 with DocumentAnalysisClient(
#                     endpoint=constants.DOCAI_ENDPOINT,
#                     credential=AzureKeyCredential(constants.DOCAI_KEY),
#                 ) as client_fr:
#                     poller = client_fr.begin_analyze_document(
#                         "prebuilt-read",
#                         data
#                     )
#                     result = poller.result()
                    
#                     # Convert to a format similar to Document Intelligence
#                     text_content = ""
#                     pages = []
                    
#                     for page in result.pages:
#                         page_text = ""
#                         for line in page.lines:
#                             page_text += line.content + "\n"
                            
#                         text_content += page_text
#                         pages.append({
#                             "pageNumber": page.page_number,
#                             "spans": [{"offset": len(text_content) - len(page_text), "length": len(page_text)}]
#                         })
                    
#                     return {
#                         "content": text_content,
#                         "pages": pages
#                     }
#             except (ImportError, Exception) as e:
#                 logging.warning(f"Form Recognizer failed: {e}. Falling back to utils.py extract_text_from_document.")
                
#                 # Use the existing utility from utils.py if available
#                 try:
#                     from utils import extract_text_from_document
#                     import tempfile
                    
#                     # Save bytes to a temporary file
#                     with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
#                         tmp.write(data)
#                         tmp_path = tmp.name
                        
#                     # Use the existing utility
#                     extracted_text = extract_text_from_document(tmp_path, ".pdf")
                    
#                     # Clean up the temporary file
#                     try:
#                         os.remove(tmp_path)
#                     except:
#                         pass
                        
#                     # Return in a format similar to Document Intelligence
#                     return {
#                         "content": extracted_text,
#                         "pages": [{"pageNumber": 1, "spans": [{"offset": 0, "length": len(extracted_text)}]}]
#                     }
#                 except Exception as e:
#                     logging.error(f"All OCR methods failed: {e}")
                    
#     except Exception as e:
#         logging.error(f"OCR extraction error: {e}")
        
#     # Return empty result if all methods fail
#     return {"content": "", "pages": []}


# def get_page_wise_content(content_json: dict) -> List[Dict[str, Any]]:
#     """Extract page-wise content from OCR results"""
#     page_wise_content = []
#     for page in content_json.get("pages", []):
#         content = ""
#         spans = page.get("spans", [])
#         if spans:
#             span = spans[0]
#             content = content_json["content"][span["offset"]: span["offset"] + span["length"]]
#         page_wise_content.append(
#             {
#                 "page_number": page.get("pageNumber"),
#                 "content": content,
#             }
#         )
#     return page_wise_content

# # ---------------------------------------------------------------------------
# # File text extraction helpers
# # ---------------------------------------------------------------------------

# def excel_to_string(file_path: str, max_rows: int = 100) -> str:
#     """Convert Excel file to a string representation"""
#     try:
#         all_sheets = pd.read_excel(file_path, sheet_name=None)
#         excel_text = ""
#         for sheet_name, df in all_sheets.items():
#             # Limit rows
#             df = df.head(max_rows)
#             excel_text += f"### Sheet Name: {sheet_name}\n"
#             # Pipe-separated, fill NaNs
#             sheet_txt = (
#                 df.fillna("")
#                   .astype(str)
#                   .apply(lambda row: "|".join(row), axis=1)
#                   .str.cat(sep="\n")
#             )
#             excel_text += sheet_txt + "\n\n"
#         return excel_text.strip()
#     except Exception as e:
#         return f"Error reading Excel file: {e}"


# def pdf_to_string(content_json: dict, max_pages: int) -> str:
#     """Convert PDF OCR results to a string representation"""
#     page_wise = get_page_wise_content(content_json)
#     result_string = ""
#     for page in page_wise[:max_pages]:
#         result_string += f"### Page Number: {page['page_number']}\n{page['content']}\n\n"
#     return result_string.strip()

# # ---------------------------------------------------------------------------
# # Doctype classification
# # ---------------------------------------------------------------------------

# def doctype_classifier(document_content: str) -> str:
#     """Classify the document type (Skeleton Risk, Slip Risk, SOV, Others)"""
#     system_prompt = prompts.doctype_classification_system_prompt
#     doctype_prompt = prompts.doctype_classification_prompt_template.format(
#         document_content=document_content
#     )
#     num_tokens = count_tokens(doctype_prompt)
#     print(f"Doctype Classification Prompt Token Count: {num_tokens}")
#     response = generate_response(doctype_prompt, system_prompt)
#     try:
#         parsed = json.loads(response)
#         return parsed.get("Classification", "Others")
#     except json.JSONDecodeError:
#         return "Others"

# # ---------------------------------------------------------------------------
# # Document classification
# # ---------------------------------------------------------------------------

# def get_ocr_json(file_path: str, ocr_folder: str) -> dict:
#     """Get OCR JSON for a document, with caching"""
#     filename = os.path.basename(file_path)
#     json_path = os.path.join(ocr_folder, f"{os.path.splitext(filename)[0]}.json")
    
#     if os.path.exists(json_path):
#         with open(json_path, "r", encoding="utf-8") as jf:
#             return json.load(jf)

#     with open(file_path, "rb") as f:
#         pdf_bytes = f.read()

#     print(f"[INFO] Performing Azure OCR for: {filename}")
#     content_json = extract_ocr_markdown(pdf_bytes)

#     # Save OCR results for future use
#     os.makedirs(os.path.dirname(json_path), exist_ok=True)
#     with open(json_path, "w", encoding="utf-8") as jf:
#         json.dump(content_json, jf, indent=2)

#     return content_json


# def classify_file(file_path: str, ocr_folder: str, max_pages: int) -> str:
#     """Classify a file by its content"""
#     filename = os.path.basename(file_path)
#     file_lower = filename.lower()

#     if file_lower.endswith((".pdf", ".docx", ".doc")):
#         ocr_json = get_ocr_json(file_path, ocr_folder)
#         text = pdf_to_string(ocr_json, max_pages)
#         return doctype_classifier(text)

#     if file_lower.endswith((".xlsx", ".xls")) and not filename.startswith("~$"):
#         text = excel_to_string(file_path)
#         return doctype_classifier(text)

#     return "Others"


# def save_classification_results(results: dict, output_folder: str):
#     """Save document classification results to a JSON file"""
#     if not results:
#         return
        
#     os.makedirs(output_folder, exist_ok=True)
#     results_path = os.path.join(output_folder, "doctype_classification.json")
    
#     with open(results_path, "w", encoding="utf-8") as f:
#         json.dump(results, f, indent=4, ensure_ascii=False)
        
#     print("[INFO] Doctype Classification Results saved to:", results_path)


# def get_attachment_wise_classification(attachment_folder: str, ocr_folder: str, max_pages: int = 10) -> Dict[str, str]:
#     """Classify all attachments in a folder"""
#     os.makedirs(ocr_folder, exist_ok=True)
    
#     results = {}
#     for filename in os.listdir(attachment_folder):
#         print(f"[INFO] Processing file: {filename}")
#         file_path = os.path.join(attachment_folder, filename)
        
#         if not os.path.isfile(file_path):
#             continue
            
#         try:
#             result = classify_file(file_path, ocr_folder, max_pages)
#             if result:
#                 results[filename] = result
#         except Exception as e:
#             print(f"[ERROR] Failed to classify {filename}: {e}")
#             continue

#     return results

# # ---------------------------------------------------------------------------
# # Content extraction by file type
# # ---------------------------------------------------------------------------

# def extract_content_by_type(
#     file_path: str,
#     filename: str,
#     ocr_folder: str,
#     max_pages: int,
# ) -> str:
#     """Extract content from a file based on its type"""
#     file_lower = filename.lower()
    
#     if file_lower.endswith((".pdf", ".docx", ".doc")):
#         ocr_json = get_ocr_json(file_path, ocr_folder)
#         return pdf_to_string(ocr_json, max_pages)
        
#     elif file_lower.endswith((".xlsx", ".xls")) and not filename.startswith("~$"):
#         return excel_to_string(file_path)
        
#     print(f"[INFO] Unsupported file format for: {filename}")
#     return ""


# def get_doctype_wise_attachment_content(
#     attachment_folder: str,
#     ocr_folder: str,
#     classification_dict: dict,
#     max_pages: int,
# ) -> dict:
#     """Group attachment content by document type"""
#     categorized_content = {
#         "Skeleton Risk": "",
#         "Slip Risk": "",
#         "SOV": "",
#     }

#     for filename, doc_type in classification_dict.items():
#         file_path = os.path.join(attachment_folder, filename)
        
#         if not os.path.isfile(file_path):
#             print(f"[WARNING] File not found: {file_path}")
#             continue

#         try:
#             content = extract_content_by_type(file_path, filename, ocr_folder, max_pages)
#             if content:
#                 formatted = f"## FileName: {filename}\n{content}\n\n"
#                 if doc_type in categorized_content:
#                     categorized_content[doc_type] += formatted
#         except Exception as e:
#             print(f"[ERROR] Failed to read {filename}: {e}")
#             continue

#     return {k: v.strip() for k, v in categorized_content.items()}

# # ---------------------------------------------------------------------------
# # Single-document extraction (Slip / Skeleton / SOV)
# # ---------------------------------------------------------------------------

# def extract_single(doc_type: str, email_content: str, attachment_content: str) -> dict:
#     """Extract fields from a single document type"""
#     fields_description_map = {
#         "Skeleton Risk": prompts.skeleton_fields_description,
#         "Slip Risk": prompts.slip_fields_description,
#         "SOV": prompts.sov_fields_description,
#     }
    
#     if doc_type not in fields_description_map:
#         return {}

#     filled_prompt = prompts.extraction_prompt_template.format(
#         fields_description=fields_description_map[doc_type],
#         email_content=email_content,
#         attachment_content=attachment_content,
#     )
    
#     print(f"[INFO] Token count for {doc_type} extraction prompt: {count_tokens(filled_prompt)}")
#     response = generate_response(filled_prompt, prompts.extraction_system_prompt)
    
#     try:
#         return json.loads(response)
#     except Exception as e:
#         print(f"[ERROR] Failed to parse {doc_type} JSON: {e}")
#         return {}


# def get_extraction(email_content: str, doctype_content_dict: dict) -> dict:
#     """Extract fields from all document types"""
#     result = {doc: {} for doc in ["Skeleton Risk", "Slip Risk", "SOV"]}

#     # Skeleton Risk: if empty, still run with 'Not Present'
#     skeleton_content = doctype_content_dict.get("Skeleton Risk", "").strip()
#     if not skeleton_content:
#         print("[INFO] Skeleton Risk content missing; running extraction with attachment content 'Not Present'.")
#         result["Skeleton Risk"] = extract_single("Skeleton Risk", email_content, "Not Present")
#     else:
#         result["Skeleton Risk"] = extract_single("Skeleton Risk", email_content, skeleton_content)

#     # Other doc types only if content exists
#     for doc_type in ["Slip Risk", "SOV"]:
#         content = doctype_content_dict.get(doc_type, "").strip()
#         if content:
#             result[doc_type] = extract_single(doc_type, email_content, content)

#     return result

# # ---------------------------------------------------------------------------
# # Mail content upload with enhanced thread parsing
# # ---------------------------------------------------------------------------

# def upload_mail_content(metadata: Dict[str, Any], unique_id: str = None) -> str:
#     """
#     Upload the complete mail content as main_content.json to blob storage
    
#     Enhanced version that includes complete email thread parsing as a list format
#     to ensure proper data population into blob storage.
    
#     Args:
#         metadata: Email metadata including From, To, Subject, etc.
#         unique_id: Unique identifier for the email. If None, one will be generated.
        
#     Returns:
#         str: Blob URL if upload was successful, None otherwise
#     """
#     try:
#         # Create a unique identifier for this email if not provided
#         if not unique_id:
#             sender = metadata.get("From", "unknown")
#             timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
#             unique_id = f"{sender}"
        
#         # Prepare the email content
#         email_content = prepare_email_content(metadata)
        
#         # Try to parse the email thread if email_thread_parser is available
#         email_thread_data = None
#         parsed_thread_list = []
#         thread_summary = {}
        
#         try:
#             from email_thread_parser import EmailThreadParser
#             parser = EmailThreadParser()
#             email_body = metadata.get("Body", "")
#             if email_body:
#                 parsed_thread_list = parser.parse_email_thread(email_body)
#                 thread_summary = parser.extract_thread_summary(email_body)
                
#                 # Ensure each email in the thread has proper structure for blob storage
#                 for idx, email in enumerate(parsed_thread_list):
#                     if 'email_id' not in email:
#                         email['email_id'] = idx + 1
#                     if 'timestamp' not in email:
#                         email['timestamp'] = datetime.now().isoformat()
#                     # Ensure content is properly formatted
#                     if isinstance(email.get('content'), list):
#                         email['content'] = '\n'.join(email['content'])
                
#                 email_thread_data = {
#                     "parsedThread": parsed_thread_list,
#                     "threadSummary": thread_summary,
#                     "totalEmailsInThread": len(parsed_thread_list)
#                 }
                
#                 print(f"[INFO] Parsed email thread with {len(parsed_thread_list)} emails")
#         except ImportError:
#             print("[INFO] email_thread_parser module not available, skipping thread parsing")
#             # Create a basic thread structure with just the current email
#             parsed_thread_list = [{
#                 "email_id": 1,
#                 "headers": {
#                     "from": metadata.get("From", ""),
#                     "to": metadata.get("To", ""),
#                     "cc": metadata.get("CC", ""),
#                     "subject": metadata.get("Subject", "")
#                 },
#                 "content": metadata.get("Body", ""),
#                 "type": "current",
#                 "quote_level": 0,
#                 "timestamp": datetime.now().isoformat()
#             }]
#             thread_summary = {
#                 "total_emails": 1,
#                 "participants": [metadata.get("From", "")],
#                 "subjects": [metadata.get("Subject", "")],
#                 "total_word_count": len(metadata.get("Body", "").split()) if metadata.get("Body") else 0,
#                 "email_types": {"current": 1, "reply": 0, "quoted": 0}
#             }
#         except Exception as e:
#             print(f"[WARNING] Error parsing email thread: {e}")
#             # Create a basic thread structure with just the current email
#             parsed_thread_list = [{
#                 "email_id": 1,
#                 "headers": {
#                     "from": metadata.get("From", ""),
#                     "to": metadata.get("To", ""),
#                     "cc": metadata.get("CC", ""),
#                     "subject": metadata.get("Subject", "")
#                 },
#                 "content": metadata.get("Body", ""),
#                 "type": "current",
#                 "quote_level": 0,
#                 "timestamp": datetime.now().isoformat()
#             }]
#             thread_summary = {
#                 "total_emails": 1,
#                 "participants": [metadata.get("From", "")],
#                 "subjects": [metadata.get("Subject", "")],
#                 "total_word_count": len(metadata.get("Body", "").split()) if metadata.get("Body") else 0,
#                 "email_types": {"current": 1, "reply": 0, "quoted": 0}
#             }
        
#         # Create a JSON object with the email content, metadata and complete thread info
#         mail_content_json = {
#             "uniqueIdentifier": unique_id,
#             "metadata": metadata,
#             "emailContent": email_content,
#             "emailThreadList": parsed_thread_list,  # Complete thread as a list
#             "threadSummary": thread_summary,
#             "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
#         }
        
#         # Add thread data if available (backwards compatibility)
#         if email_thread_data:
#             mail_content_json["emailThread"] = email_thread_data
        
#         # Validate thread list structure before upload
#         if parsed_thread_list:
#             print(f"[INFO] Email thread structure validated: {len(parsed_thread_list)} emails in thread")
#             for idx, email in enumerate(parsed_thread_list):
#                 if not email.get('email_id'):
#                     email['email_id'] = idx + 1
#                 if not email.get('timestamp'):
#                     email['timestamp'] = datetime.now().isoformat()
#                 if not email.get('type'):
#                     email['type'] = 'current' if idx == 0 else 'quoted'
#         else:
#             print("[WARNING] Empty email thread list, using fallback structure")
#             mail_content_json["emailThreadList"] = [{
#                 "email_id": 1,
#                 "headers": {
#                     "from": metadata.get("From", ""),
#                     "to": metadata.get("To", ""),
#                     "cc": metadata.get("CC", ""),
#                     "subject": metadata.get("Subject", "")
#                 },
#                 "content": metadata.get("Body", ""),
#                 "type": "current",
#                 "quote_level": 0,
#                 "timestamp": datetime.now().isoformat()
#             }]
        
#         # Create blob name using the unique identifier
#         blob_name = f"{unique_id}/main_content.json"
        
#         # Upload to blob storage
#         blob_url = upload_json_to_blob(mail_content_json, blob_name)
        
#         if blob_url:
#             print(f"\n[INFO] Mail content uploaded to blob storage: {blob_url}")
#             return blob_url
#         else:
#             print("\n[WARNING] Failed to upload mail content to blob storage")
#             return None
#     except Exception as e:
#         print(f"\n[ERROR] Error uploading mail content to blob: {e}")
#         return None

# # ---------------------------------------------------------------------------
# # Main processing pipeline
# # ---------------------------------------------------------------------------

# def process_email_attachments(metadata: Dict[str, Any], attachment_paths: List[str]) -> dict:
#     """
#     Main processing pipeline for email attachments
    
#     Args:
#         metadata: Email metadata including From, To, Subject, etc.
#         attachment_paths: List of paths to attachments
    
#     Returns:
#         dict: Extraction results
#     """
#     # Setup processing folders
#     temp_folder = constants.TEMP_FOLDER_PATH
#     extraction_folder = constants.EXTRACTIONOUTPUT_PATH
    
#     # Create a unique identifier for this email
#     sender = metadata.get("From", "unknown")
#     timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
#     unique_id = f"{sender}"
    
#     # Setup paths
#     processing_folder = os.path.join(extraction_folder, unique_id)
#     attachment_folder = os.path.join(processing_folder, "attachments")
#     ocr_folder = os.path.join(processing_folder, "OCR")
#     output_folder = os.path.join(processing_folder, "output")
    
#     os.makedirs(attachment_folder, exist_ok=True)
#     os.makedirs(ocr_folder, exist_ok=True)
#     os.makedirs(output_folder, exist_ok=True)
    
#     # Upload mail content to blob storage regardless of attachment status
#     upload_mail_content(metadata, unique_id)
    
#     # Prepare the email content for further processing
#     email_content = prepare_email_content(metadata)
    
#     # Step 1: LOB classification
#     print("\n---------------- RUNNING LOB CLASSIFICATION ----------------")
#     submission_classification = submission_classifier(email_content)
#     print(f"[INFO] Submission Classification: {submission_classification}")
    
#     if submission_classification == "Non-Submission":
#         print("\n---------------- NON-SUBMISSION EMAIL. NO EXTRACTION PERFORMED ----------------")
#         return {}
    
#     # Copy attachments to processing folder
#     for path in attachment_paths:
#         if os.path.exists(path):
#             filename = os.path.basename(path)
#             dest_path = os.path.join(attachment_folder, filename)
#             with open(path, "rb") as src, open(dest_path, "wb") as dst:
#                 dst.write(src.read())
    
#     # Step 2: Attachment-wise classification
#     print("\n---------------- RUNNING ATTACHMENT-WISE CLASSIFICATION ----------------")
#     attachment_classification_result = get_attachment_wise_classification(
#         attachment_folder, 
#         ocr_folder, 
#         max_pages=constants.CLASSIFICATION_MAX_PAGES
#     )
    
#     print("\n---------------- ATTACHMENT CLASSIFICATION RESULT ----------------")
#     print(json.dumps(attachment_classification_result, indent=4))
    
#     # Save classification results
#     save_classification_results(attachment_classification_result, output_folder)
    
#     # Step 3: Extract content by document type
#     print("\n---------------- EXTRACTING DOCTYPE-WISE ATTACHMENT CONTENT ----------------")
#     doctype_wise_attachment_content = get_doctype_wise_attachment_content(
#         attachment_folder,
#         ocr_folder,
#         attachment_classification_result,
#         max_pages=constants.CLASSIFICATION_MAX_PAGES,
#     )
    
#     non_empty_keys = [k for k, v in doctype_wise_attachment_content.items() if v]
#     if non_empty_keys:
#         print(f"[INFO] Attachment content found in: {non_empty_keys}")
#     else:
#         print("[INFO] No attachment content found.")
    
#     # Step 4: Perform field extraction
#     print("\n---------------- PERFORMING FIELD EXTRACTION ----------------")
#     extracted_fields = get_extraction(email_content, doctype_wise_attachment_content)
    
#     # Prepare final result
#     final_result = {
#         "uniqueIdentifier": unique_id,
#         "sender": metadata.get("From", ""),
#         "recipient": metadata.get("To", ""),
#         "subject": metadata.get("Subject", ""),
#         "totalAttachments": len(attachment_paths),
#         "attachmentDocTypeClassification": attachment_classification_result if attachment_classification_result else None,
#         "lineOfBusiness": submission_classification,
#         "extractedFields": extracted_fields,
#         "processedDate": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
#     }
    
#     # Save result
#     result_file_path = os.path.join(output_folder, "extraction.json")
    
#     with open(result_file_path, "w", encoding="utf-8") as f:
#         json.dump(final_result, f, indent=4, ensure_ascii=False)
    
#     print(f"\n[INFO] Extraction results saved to: {result_file_path}")
    
#     # Upload extraction.json to blob storage
#     try:
#         # Create blob name using the unique identifier
#         blob_name = f"{unique_id}/extraction.json"
        
#         # Upload to blob storage
#         blob_url = upload_json_to_blob(final_result, blob_name)
        
#         if blob_url:
#             print(f"\n[INFO] Extraction results uploaded to blob storage: {blob_url}")
#         else:
#             print("\n[WARNING] Failed to upload extraction results to blob storage")
#     except Exception as e:
#         print(f"\n[ERROR] Error uploading extraction results to blob: {e}")
    
#     return final_result



# """
# Document Processing Pipeline for Azure Function App
# Adapted from the Submission from images/extraction_v1.py
# """

# import os
# import re
# import json
# import time
# import logging
# import pandas as pd
# from datetime import datetime
# from typing import Dict, Any, List

# # Try importing the necessary packages, handle missing dependencies gracefully
# try:
#     import tiktoken
# except ImportError:
#     logging.warning("tiktoken not installed. Token counting will not be accurate.")
    
#     # Simple fallback for token counting
#     def simple_token_count(text):
#         return len(text.split())
        
#     class DummyTikToken:
#         @staticmethod
#         def encoding_for_model(model):
#             return DummyTikToken()
            
#         @staticmethod
#         def get_encoding(name):
#             return DummyTikToken()
            
#         @staticmethod
#         def encode(text):
#             return [1] * simple_token_count(text)
            
#     tiktoken = DummyTikToken()

# try:
#     from openai import AzureOpenAI
# except ImportError:
#     logging.error("openai package not installed. AI processing will not work.")

# try:
#     from azure.core.credentials import AzureKeyCredential
# except ImportError:
#     logging.error("Azure Core package not installed. Azure services will not work properly.")

# # Local modules
# import constants
# import prompts
# import helper
# # Import specific function from utils
# from utils import upload_json_to_blob

# # Azure OpenAI client setup
# def get_openai_client():
#     """
#     Gets an Azure OpenAI client, with fallbacks
#     """
#     try:
#         from openai import AzureOpenAI
#         return AzureOpenAI(
#             azure_endpoint=constants.AZURE_OPENAI_ENDPOINT,
#             api_key=constants.AZURE_OPENAI_KEY,
#             api_version=constants.AZURE_OPENAI_API_VERSION,
#         )
#     except ImportError:
#         logging.error("OpenAI SDK not installed or not compatible")
        
#         # Create a mock client that logs errors
#         class MockOpenAIClient:
#             def __getattr__(self, name):
#                 def method(*args, **kwargs):
#                     logging.error(f"OpenAI {name} method called but OpenAI SDK not available")
#                     return None
#                 return method
                
#         return MockOpenAIClient()

# # ---------------------------------------------------------------------------
# # OpenAI helpers
# # ---------------------------------------------------------------------------

# def generate_response(prompt_text: str, system_prompt: str, max_tokens: int = 3048) -> str:
#     """Generate a response using Azure OpenAI"""
#     client = get_openai_client()
#     message_text = [
#         {"role": "system", "content": system_prompt},
#         {"role": "user", "content": prompt_text},
#     ]
#     completion = client.chat.completions.create(
#         model="gpt-4o",  # Using the available model in your environment
#         messages=message_text,
#         max_tokens=max_tokens,
#         temperature=0.2,
#         seed=38,
#         top_p=0.9,
#         response_format={"type": "json_object"},
#     )
#     return completion.choices[0].message.content


# def count_tokens(prompt_text: str, model: str = "gpt-4") -> int:
#     """
#     Counts tokens for a given model, with fallbacks for missing dependencies
#     """
#     # First try using tiktoken if available
#     try:
#         if hasattr(tiktoken, "encoding_for_model"):
#             try:
#                 encoding = tiktoken.encoding_for_model(model)
#                 return len(encoding.encode(prompt_text))
#             except (KeyError, AttributeError):
#                 try:
#                     encoding = tiktoken.get_encoding("cl100k_base")  # fallback
#                     return len(encoding.encode(prompt_text))
#                 except (KeyError, AttributeError):
#                     pass
#     except Exception:
#         pass
        
#     # Fallback: simple approximation (4 chars ~= 1 token)
#     return len(prompt_text) // 4

# # ---------------------------------------------------------------------------
# # Email content extraction
# # ---------------------------------------------------------------------------

# def validate_json_structure(json_data: dict) -> dict:
#     """
#     Validate the structured JSON format for main_content.json
    
#     Args:
#         json_data: The JSON data to validate
        
#     Returns:
#         dict: Validation results with status and details
#     """
#     validation_results = {
#         "isValid": True,
#         "errors": [],
#         "warnings": [],
#         "sectionValidation": {}
#     }
    
#     required_sections = [
#         "documentInfo", "emailHeaders", "emailContent", 
#         "emailThread", "attachments", "processing", "legacy"
#     ]
    
#     # Check for required top-level sections
#     for section in required_sections:
#         if section not in json_data:
#             validation_results["errors"].append(f"Missing required section: {section}")
#             validation_results["isValid"] = False
#             validation_results["sectionValidation"][section] = False
#         else:
#             validation_results["sectionValidation"][section] = True
    
#     # Validate documentInfo section
#     if "documentInfo" in json_data:
#         doc_info = json_data["documentInfo"]
#         required_fields = ["uniqueIdentifier", "version", "documentType", "createdAt"]
#         for field in required_fields:
#             if field not in doc_info:
#                 validation_results["warnings"].append(f"Missing documentInfo field: {field}")
    
#     # Validate emailHeaders section
#     if "emailHeaders" in json_data:
#         headers = json_data["emailHeaders"]
#         if not headers.get("from"):
#             validation_results["warnings"].append("Missing 'from' email address")
#         if not headers.get("subject"):
#             validation_results["warnings"].append("Missing email subject")
    
#     # Validate emailThread section
#     if "emailThread" in json_data:
#         thread = json_data["emailThread"]
#         if "threadList" not in thread or not isinstance(thread["threadList"], list):
#             validation_results["errors"].append("Invalid or missing threadList")
#             validation_results["isValid"] = False
#         elif len(thread["threadList"]) == 0:
#             validation_results["warnings"].append("Empty thread list")
    
#     return validation_results

# def prepare_email_content(metadata: Dict[str, Any]) -> str:
#     """
#     Prepares email content from metadata
#     """
#     from_email = metadata.get("From", "")
#     to_email = metadata.get("To", "")
#     cc_email = metadata.get("CC", "")
#     subject = metadata.get("Subject", "")
#     body = metadata.get("Body", "")
    
#     email_content = f"From: {from_email}\nTo: {to_email}\nCC: {cc_email}\nSubject: {subject}\n\n{body}"
    
#     return email_content

# # ---------------------------------------------------------------------------
# # Classification (Submission vs Non)
# # ---------------------------------------------------------------------------

# def submission_classifier(email_content: str) -> str:
#     """Classify if the email is a submission and determine the line of business"""
#     classification_system_prompt = prompts.submission_classification_system_prompt
#     classification_prompt = prompts.submission_classification_prompt_template.format(
#         email_content=email_content
#     )
#     num_tokens = count_tokens(classification_prompt)
#     print(f"Submission Prompt Token Count: {num_tokens}")
#     response = generate_response(classification_prompt, classification_system_prompt)
#     try:
#         parsed = json.loads(response)
#         return parsed.get("Classification", "Non-Submission")
#     except json.JSONDecodeError:
#         return "Non-Submission"

# # ---------------------------------------------------------------------------
# # Azure Document Intelligence OCR
# # ---------------------------------------------------------------------------

# def extract_ocr_markdown(data: bytes) -> dict:
#     """Extract text from document using Azure Document Intelligence"""
#     try:
#         # Try to use Azure Document Intelligence if available
#         try:
#             from azure.core.credentials import AzureKeyCredential
#             from azure.ai.documentintelligence import DocumentIntelligenceClient
            
#             # Define helper class if the models aren't available
#             class AnalyzeDocumentRequest:
#                 def __init__(self, bytes_source=None):
#                     self.bytes_source = bytes_source
                    
#             class DocumentContentFormat:
#                 MARKDOWN = "markdown"
                
#             # Try to import the proper models if available    
#             try:
#                 from azure.ai.documentintelligence.models import (
#                     AnalyzeDocumentRequest,
#                     DocumentContentFormat,
#                 )
#             except ImportError:
#                 pass
                
#             with DocumentIntelligenceClient(
#                 endpoint=constants.DOCAI_ENDPOINT,
#                 credential=AzureKeyCredential(constants.DOCAI_KEY),
#             ) as client_di:
#                 poller = client_di.begin_analyze_document(
#                     "prebuilt-layout",
#                     AnalyzeDocumentRequest(bytes_source=data),
#                     output_content_format=DocumentContentFormat.MARKDOWN,
#                 )
#                 return poller.result().as_dict()
#         except (ImportError, Exception) as e:
#             logging.warning(f"Azure Document Intelligence failed: {e}. Trying Form Recognizer.")
            
#             # Try to use Form Recognizer (older version) if available
#             try:
#                 from azure.ai.formrecognizer import DocumentAnalysisClient
                
#                 with DocumentAnalysisClient(
#                     endpoint=constants.DOCAI_ENDPOINT,
#                     credential=AzureKeyCredential(constants.DOCAI_KEY),
#                 ) as client_fr:
#                     poller = client_fr.begin_analyze_document(
#                         "prebuilt-read",
#                         data
#                     )
#                     result = poller.result()
                    
#                     # Convert to a format similar to Document Intelligence
#                     text_content = ""
#                     pages = []
                    
#                     for page in result.pages:
#                         page_text = ""
#                         for line in page.lines:
#                             page_text += line.content + "\n"
                            
#                         text_content += page_text
#                         pages.append({
#                             "pageNumber": page.page_number,
#                             "spans": [{"offset": len(text_content) - len(page_text), "length": len(page_text)}]
#                         })
                    
#                     return {
#                         "content": text_content,
#                         "pages": pages
#                     }
#             except (ImportError, Exception) as e:
#                 logging.warning(f"Form Recognizer failed: {e}. Falling back to utils.py extract_text_from_document.")
                
#                 # Use the existing utility from utils.py if available
#                 try:
#                     from utils import extract_text_from_document
#                     import tempfile
                    
#                     # Save bytes to a temporary file
#                     with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
#                         tmp.write(data)
#                         tmp_path = tmp.name
                        
#                     # Use the existing utility
#                     extracted_text = extract_text_from_document(tmp_path, ".pdf")
                    
#                     # Clean up the temporary file
#                     try:
#                         os.remove(tmp_path)
#                     except:
#                         pass
                        
#                     # Return in a format similar to Document Intelligence
#                     return {
#                         "content": extracted_text,
#                         "pages": [{"pageNumber": 1, "spans": [{"offset": 0, "length": len(extracted_text)}]}]
#                     }
#                 except Exception as e:
#                     logging.error(f"All OCR methods failed: {e}")
                    
#     except Exception as e:
#         logging.error(f"OCR extraction error: {e}")
        
#     # Return empty result if all methods fail
#     return {"content": "", "pages": []}


# def get_page_wise_content(content_json: dict) -> List[Dict[str, Any]]:
#     """Extract page-wise content from OCR results"""
#     page_wise_content = []
#     for page in content_json.get("pages", []):
#         content = ""
#         spans = page.get("spans", [])
#         if spans:
#             span = spans[0]
#             content = content_json["content"][span["offset"]: span["offset"] + span["length"]]
#         page_wise_content.append(
#             {
#                 "page_number": page.get("pageNumber"),
#                 "content": content,
#             }
#         )
#     return page_wise_content

# # ---------------------------------------------------------------------------
# # File text extraction helpers
# # ---------------------------------------------------------------------------

# def excel_to_string(file_path: str, max_rows: int = 100) -> str:
#     """Convert Excel file to a string representation"""
#     try:
#         all_sheets = pd.read_excel(file_path, sheet_name=None)
#         excel_text = ""
#         for sheet_name, df in all_sheets.items():
#             # Limit rows
#             df = df.head(max_rows)
#             excel_text += f"### Sheet Name: {sheet_name}\n"
#             # Pipe-separated, fill NaNs
#             sheet_txt = (
#                 df.fillna("")
#                   .astype(str)
#                   .apply(lambda row: "|".join(row), axis=1)
#                   .str.cat(sep="\n")
#             )
#             excel_text += sheet_txt + "\n\n"
#         return excel_text.strip()
#     except Exception as e:
#         return f"Error reading Excel file: {e}"


# def pdf_to_string(content_json: dict, max_pages: int) -> str:
#     """Convert PDF OCR results to a string representation"""
#     page_wise = get_page_wise_content(content_json)
#     result_string = ""
#     for page in page_wise[:max_pages]:
#         result_string += f"### Page Number: {page['page_number']}\n{page['content']}\n\n"
#     return result_string.strip()

# # ---------------------------------------------------------------------------
# # Doctype classification
# # ---------------------------------------------------------------------------

# def doctype_classifier(document_content: str) -> str:
#     """Classify the document type (Skeleton Risk, Slip Risk, SOV, Others)"""
#     system_prompt = prompts.doctype_classification_system_prompt
#     doctype_prompt = prompts.doctype_classification_prompt_template.format(
#         document_content=document_content
#     )
#     num_tokens = count_tokens(doctype_prompt)
#     print(f"Doctype Classification Prompt Token Count: {num_tokens}")
#     response = generate_response(doctype_prompt, system_prompt)
#     try:
#         parsed = json.loads(response)
#         return parsed.get("Classification", "Others")
#     except json.JSONDecodeError:
#         return "Others"

# # ---------------------------------------------------------------------------
# # Document classification
# # ---------------------------------------------------------------------------

# def get_ocr_json(file_path: str, ocr_folder: str) -> dict:
#     """Get OCR JSON for a document, with caching"""
#     filename = os.path.basename(file_path)
#     json_path = os.path.join(ocr_folder, f"{os.path.splitext(filename)[0]}.json")
    
#     if os.path.exists(json_path):
#         with open(json_path, "r", encoding="utf-8") as jf:
#             return json.load(jf)

#     with open(file_path, "rb") as f:
#         pdf_bytes = f.read()

#     print(f"[INFO] Performing Azure OCR for: {filename}")
#     content_json = extract_ocr_markdown(pdf_bytes)

#     # Save OCR results for future use
#     os.makedirs(os.path.dirname(json_path), exist_ok=True)
#     with open(json_path, "w", encoding="utf-8") as jf:
#         json.dump(content_json, jf, indent=2)

#     return content_json


# def classify_file(file_path: str, ocr_folder: str, max_pages: int) -> str:
#     """Classify a file by its content"""
#     filename = os.path.basename(file_path)
#     file_lower = filename.lower()

#     if file_lower.endswith((".pdf", ".docx", ".doc")):
#         ocr_json = get_ocr_json(file_path, ocr_folder)
#         text = pdf_to_string(ocr_json, max_pages)
#         return doctype_classifier(text)

#     if file_lower.endswith((".xlsx", ".xls")) and not filename.startswith("~$"):
#         text = excel_to_string(file_path)
#         return doctype_classifier(text)

#     return "Others"


# def save_classification_results(results: dict, output_folder: str):
#     """Save document classification results to a JSON file"""
#     if not results:
#         return
        
#     os.makedirs(output_folder, exist_ok=True)
#     results_path = os.path.join(output_folder, "doctype_classification.json")
    
#     with open(results_path, "w", encoding="utf-8") as f:
#         json.dump(results, f, indent=4, ensure_ascii=False)
        
#     print("[INFO] Doctype Classification Results saved to:", results_path)


# def get_attachment_wise_classification(attachment_folder: str, ocr_folder: str, max_pages: int = 10) -> Dict[str, str]:
#     """Classify all attachments in a folder"""
#     os.makedirs(ocr_folder, exist_ok=True)
    
#     results = {}
#     for filename in os.listdir(attachment_folder):
#         print(f"[INFO] Processing file: {filename}")
#         file_path = os.path.join(attachment_folder, filename)
        
#         if not os.path.isfile(file_path):
#             continue
            
#         try:
#             result = classify_file(file_path, ocr_folder, max_pages)
#             if result:
#                 results[filename] = result
#         except Exception as e:
#             print(f"[ERROR] Failed to classify {filename}: {e}")
#             continue

#     return results

# # ---------------------------------------------------------------------------
# # Content extraction by file type
# # ---------------------------------------------------------------------------

# def extract_content_by_type(
#     file_path: str,
#     filename: str,
#     ocr_folder: str,
#     max_pages: int,
# ) -> str:
#     """Extract content from a file based on its type"""
#     file_lower = filename.lower()
    
#     if file_lower.endswith((".pdf", ".docx", ".doc")):
#         ocr_json = get_ocr_json(file_path, ocr_folder)
#         return pdf_to_string(ocr_json, max_pages)
        
#     elif file_lower.endswith((".xlsx", ".xls")) and not filename.startswith("~$"):
#         return excel_to_string(file_path)
        
#     print(f"[INFO] Unsupported file format for: {filename}")
#     return ""


# def get_doctype_wise_attachment_content(
#     attachment_folder: str,
#     ocr_folder: str,
#     classification_dict: dict,
#     max_pages: int,
# ) -> dict:
#     """Group attachment content by document type"""
#     categorized_content = {
#         "Skeleton Risk": "",
#         "Slip Risk": "",
#         "SOV": "",
#     }

#     for filename, doc_type in classification_dict.items():
#         file_path = os.path.join(attachment_folder, filename)
        
#         if not os.path.isfile(file_path):
#             print(f"[WARNING] File not found: {file_path}")
#             continue

#         try:
#             content = extract_content_by_type(file_path, filename, ocr_folder, max_pages)
#             if content:
#                 formatted = f"## FileName: {filename}\n{content}\n\n"
#                 if doc_type in categorized_content:
#                     categorized_content[doc_type] += formatted
#         except Exception as e:
#             print(f"[ERROR] Failed to read {filename}: {e}")
#             continue

#     return {k: v.strip() for k, v in categorized_content.items()}

# # ---------------------------------------------------------------------------
# # Single-document extraction (Slip / Skeleton / SOV)
# # ---------------------------------------------------------------------------

# def extract_single(doc_type: str, email_content: str, attachment_content: str) -> dict:
#     """Extract fields from a single document type"""
#     fields_description_map = {
#         "Skeleton Risk": prompts.skeleton_fields_description,
#         "Slip Risk": prompts.slip_fields_description,
#         "SOV": prompts.sov_fields_description,
#     }
    
#     if doc_type not in fields_description_map:
#         return {}

#     filled_prompt = prompts.extraction_prompt_template.format(
#         fields_description=fields_description_map[doc_type],
#         email_content=email_content,
#         attachment_content=attachment_content,
#     )
    
#     print(f"[INFO] Token count for {doc_type} extraction prompt: {count_tokens(filled_prompt)}")
#     response = generate_response(filled_prompt, prompts.extraction_system_prompt)
    
#     try:
#         return json.loads(response)
#     except Exception as e:
#         print(f"[ERROR] Failed to parse {doc_type} JSON: {e}")
#         return {}


# def get_extraction(email_content: str, doctype_content_dict: dict) -> dict:
#     """Extract fields from all document types"""
#     result = {doc: {} for doc in ["Skeleton Risk", "Slip Risk", "SOV"]}

#     # Skeleton Risk: if empty, still run with 'Not Present'
#     skeleton_content = doctype_content_dict.get("Skeleton Risk", "").strip()
#     if not skeleton_content:
#         print("[INFO] Skeleton Risk content missing; running extraction with attachment content 'Not Present'.")
#         result["Skeleton Risk"] = extract_single("Skeleton Risk", email_content, "Not Present")
#     else:
#         result["Skeleton Risk"] = extract_single("Skeleton Risk", email_content, skeleton_content)

#     # Other doc types only if content exists
#     for doc_type in ["Slip Risk", "SOV"]:
#         content = doctype_content_dict.get(doc_type, "").strip()
#         if content:
#             result[doc_type] = extract_single(doc_type, email_content, content)

#     return result

# # ---------------------------------------------------------------------------
# # Mail content upload with enhanced thread parsing
# # ---------------------------------------------------------------------------

# def upload_mail_content(metadata: Dict[str, Any], unique_id: str = None) -> str:
#     """
#     Upload the complete mail content as main_content.json to blob storage
    
#     Enhanced version that includes complete email thread parsing as a list format
#     to ensure proper data population into blob storage.
    
#     Args:
#         metadata: Email metadata including From, To, Subject, etc.
#         unique_id: Unique identifier for the email. If None, one will be generated.
        
#     Returns:
#         str: Blob URL if upload was successful, None otherwise
#     """
#     try:
#         # Create a unique identifier for this email if not provided
#         if not unique_id:
#             sender = metadata.get("From", "unknown")
#             timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
#             unique_id = f"{sender}"
        
#         # Prepare the email content
#         email_content = prepare_email_content(metadata)
        
#         # Try to parse the email thread if email_thread_parser is available
#         email_thread_data = None
#         parsed_thread_list = []
#         thread_summary = {}
        
#         try:
#             from email_thread_parser import EmailThreadParser
#             parser = EmailThreadParser()
#             email_body = metadata.get("Body", "")
#             if email_body:
#                 parsed_thread_list = parser.parse_email_thread(email_body)
#                 thread_summary = parser.extract_thread_summary(email_body)
                
#                 # Ensure each email in the thread has proper structure for blob storage
#                 for idx, email in enumerate(parsed_thread_list):
#                     if 'email_id' not in email:
#                         email['email_id'] = idx + 1
#                     if 'timestamp' not in email:
#                         email['timestamp'] = datetime.now().isoformat()
#                     # Ensure content is properly formatted
#                     if isinstance(email.get('content'), list):
#                         email['content'] = '\n'.join(email['content'])
                
#                 email_thread_data = {
#                     "parsedThread": parsed_thread_list,
#                     "threadSummary": thread_summary,
#                     "totalEmailsInThread": len(parsed_thread_list)
#                 }
                
#                 print(f"[INFO] Parsed email thread with {len(parsed_thread_list)} emails")
#         except ImportError:
#             print("[INFO] email_thread_parser module not available, skipping thread parsing")
#             # Create a basic thread structure with just the current email
#             parsed_thread_list = [{
#                 "email_id": 1,
#                 "headers": {
#                     "from": metadata.get("From", ""),
#                     "to": metadata.get("To", ""),
#                     "cc": metadata.get("CC", ""),
#                     "subject": metadata.get("Subject", "")
#                 },
#                 "content": metadata.get("Body", ""),
#                 "type": "current",
#                 "quote_level": 0,
#                 "timestamp": datetime.now().isoformat()
#             }]
#             thread_summary = {
#                 "total_emails": 1,
#                 "participants": [metadata.get("From", "")],
#                 "subjects": [metadata.get("Subject", "")],
#                 "total_word_count": len(metadata.get("Body", "").split()) if metadata.get("Body") else 0,
#                 "email_types": {"current": 1, "reply": 0, "quoted": 0}
#             }
#         except Exception as e:
#             print(f"[WARNING] Error parsing email thread: {e}")
#             # Create a basic thread structure with just the current email
#             parsed_thread_list = [{
#                 "email_id": 1,
#                 "headers": {
#                     "from": metadata.get("From", ""),
#                     "to": metadata.get("To", ""),
#                     "cc": metadata.get("CC", ""),
#                     "subject": metadata.get("Subject", "")
#                 },
#                 "content": metadata.get("Body", ""),
#                 "type": "current",
#                 "quote_level": 0,
#                 "timestamp": datetime.now().isoformat()
#             }]
#             thread_summary = {
#                 "total_emails": 1,
#                 "participants": [metadata.get("From", "")],
#                 "subjects": [metadata.get("Subject", "")],
#                 "total_word_count": len(metadata.get("Body", "").split()) if metadata.get("Body") else 0,
#                 "email_types": {"current": 1, "reply": 0, "quoted": 0}
#             }
        
#         # Create a structured JSON object with organized sections
#         mail_content_json = {
#             # Document identification and metadata
#             "documentInfo": {
#                 "uniqueIdentifier": unique_id,
#                 "version": "2.0",
#                 "documentType": "email_content",
#                 "createdAt": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
#                 "processedAt": datetime.now().isoformat(),
#                 "dataSource": "email_processor"
#             },
            
#             # Email header information
#             "emailHeaders": {
#                 "from": metadata.get("From", ""),
#                 "to": metadata.get("To", ""),
#                 "cc": metadata.get("CC", ""),
#                 "bcc": metadata.get("BCC", ""),
#                 "subject": metadata.get("Subject", ""),
#                 "date": metadata.get("Date", ""),
#                 "messageId": metadata.get("Message-ID", ""),
#                 "replyTo": metadata.get("Reply-To", ""),
#                 "importance": metadata.get("Importance", ""),
#                 "priority": metadata.get("Priority", "")
#             },
            
#             # Email content structure
#             "emailContent": {
#                 "formattedContent": email_content,
#                 "originalBody": metadata.get("Body", ""),
#                 "bodyFormat": metadata.get("BodyFormat", "text"),
#                 "encoding": metadata.get("Encoding", "utf-8"),
#                 "size": len(metadata.get("Body", "")),
#                 "wordCount": len(metadata.get("Body", "").split()) if metadata.get("Body") else 0
#             },
            
#             # Email thread analysis
#             "emailThread": {
#                 "threadList": parsed_thread_list,
#                 "threadSummary": thread_summary,
#                 "threadMetrics": {
#                     "totalEmails": len(parsed_thread_list),
#                     "uniqueParticipants": len(set(thread_summary.get("participants", []))),
#                     "conversationDepth": max([email.get("quote_level", 0) for email in parsed_thread_list]) if parsed_thread_list else 0,
#                     "hasReplies": len(parsed_thread_list) > 1,
#                     "threadStartDate": parsed_thread_list[-1].get("timestamp") if parsed_thread_list else None,
#                     "threadEndDate": parsed_thread_list[0].get("timestamp") if parsed_thread_list else None
#                 }
#             },
            
#             # Attachment information (if any)
#             "attachments": {
#                 "hasAttachments": bool(metadata.get("Attachments", [])),
#                 "attachmentCount": len(metadata.get("Attachments", [])),
#                 "attachmentList": metadata.get("Attachments", []),
#                 "totalAttachmentSize": metadata.get("TotalAttachmentSize", 0)
#             },
            
#             # Processing metadata
#             "processing": {
#                 "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
#                 "processingVersion": "2.0",
#                 "threadParsingEnabled": True,
#                 "threadParsingStatus": "success" if parsed_thread_list else "fallback",
#                 "dataValidation": {
#                     "hasValidHeaders": bool(metadata.get("From") and metadata.get("Subject")),
#                     "hasContent": bool(metadata.get("Body")),
#                     "threadParsed": len(parsed_thread_list) > 0,
#                     "structureValid": True
#                 }
#             },
            
#             # Legacy compatibility section
#             "legacy": {
#                 "originalMetadata": metadata,
#                 "legacyEmailContent": email_content
#             }
#         }
        
#         # Add backwards compatible thread data if available
#         if email_thread_data:
#             mail_content_json["legacy"]["emailThread"] = email_thread_data
        
#         # Validate thread list structure before upload
#         if parsed_thread_list:
#             print(f"[INFO] Email thread structure validated: {len(parsed_thread_list)} emails in thread")
#             for idx, email in enumerate(parsed_thread_list):
#                 if not email.get('email_id'):
#                     email['email_id'] = idx + 1
#                 if not email.get('timestamp'):
#                     email['timestamp'] = datetime.now().isoformat()
#                 if not email.get('type'):
#                     email['type'] = 'current' if idx == 0 else 'quoted'
            
#             # Update the structured JSON with validated data
#             mail_content_json["emailThread"]["threadList"] = parsed_thread_list
#             mail_content_json["emailThread"]["threadMetrics"]["totalEmails"] = len(parsed_thread_list)
#             mail_content_json["processing"]["threadParsingStatus"] = "success"
#         else:
#             print("[WARNING] Empty email thread list, using fallback structure")
#             fallback_thread = [{
#                 "email_id": 1,
#                 "headers": {
#                     "from": metadata.get("From", ""),
#                     "to": metadata.get("To", ""),
#                     "cc": metadata.get("CC", ""),
#                     "subject": metadata.get("Subject", "")
#                 },
#                 "content": metadata.get("Body", ""),
#                 "type": "current",
#                 "quote_level": 0,
#                 "timestamp": datetime.now().isoformat()
#             }]
#             mail_content_json["emailThread"]["threadList"] = fallback_thread
#             mail_content_json["emailThread"]["threadMetrics"]["totalEmails"] = 1
#             mail_content_json["processing"]["threadParsingStatus"] = "fallback"
        
#         # Final validation of the complete structure
#         validation_results = {
#             "documentStructure": bool(mail_content_json.get("documentInfo")),
#             "emailHeaders": bool(mail_content_json.get("emailHeaders", {}).get("from")),
#             "emailContent": bool(mail_content_json.get("emailContent", {}).get("originalBody")),
#             "threadData": bool(mail_content_json.get("emailThread", {}).get("threadList")),
#             "processingInfo": bool(mail_content_json.get("processing"))
#         }
        
#         mail_content_json["processing"]["dataValidation"].update(validation_results)
        
#         print(f"[INFO] Structured JSON validation: {validation_results}")
#         print(f"[INFO] Document structure created with {len(mail_content_json)} main sections")
        
#         # Perform comprehensive structure validation
#         structure_validation = validate_json_structure(mail_content_json)
#         if not structure_validation["isValid"]:
#             print(f"[WARNING] JSON structure validation failed: {structure_validation['errors']}")
#         if structure_validation["warnings"]:
#             print(f"[INFO] JSON structure warnings: {structure_validation['warnings']}")
        
#         mail_content_json["processing"]["structureValidation"] = structure_validation
        
#         # Create blob name using the unique identifier
#         blob_name = f"{unique_id}/main_content.json"
        
#         # Upload to blob storage
#         blob_url = upload_json_to_blob(mail_content_json, blob_name)
        
#         if blob_url:
#             print(f"\n[INFO] Mail content uploaded to blob storage: {blob_url}")
#             return blob_url
#         else:
#             print("\n[WARNING] Failed to upload mail content to blob storage")
#             return None
#     except Exception as e:
#         print(f"\n[ERROR] Error uploading mail content to blob: {e}")
#         return None

# # ---------------------------------------------------------------------------
# # Main processing pipeline
# # ---------------------------------------------------------------------------

# def process_email_attachments(metadata: Dict[str, Any], attachment_paths: List[str]) -> dict:
#     """
#     Main processing pipeline for email attachments
    
#     Args:
#         metadata: Email metadata including From, To, Subject, etc.
#         attachment_paths: List of paths to attachments
    
#     Returns:
#         dict: Extraction results
#     """
#     # Setup processing folders
#     temp_folder = constants.TEMP_FOLDER_PATH
#     extraction_folder = constants.EXTRACTIONOUTPUT_PATH
    
#     # Create a unique identifier for this email
#     sender = metadata.get("From", "unknown")
#     timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
#     unique_id = f"{sender}"
    
#     # Setup paths
#     processing_folder = os.path.join(extraction_folder, unique_id)
#     attachment_folder = os.path.join(processing_folder, "attachments")
#     ocr_folder = os.path.join(processing_folder, "OCR")
#     output_folder = os.path.join(processing_folder, "output")
    
#     os.makedirs(attachment_folder, exist_ok=True)
#     os.makedirs(ocr_folder, exist_ok=True)
#     os.makedirs(output_folder, exist_ok=True)
    
#     # Upload mail content to blob storage regardless of attachment status
#     upload_mail_content(metadata, unique_id)
    
#     # Prepare the email content for further processing
#     email_content = prepare_email_content(metadata)
    
#     # Step 1: LOB classification
#     print("\n---------------- RUNNING LOB CLASSIFICATION ----------------")
#     submission_classification = submission_classifier(email_content)
#     print(f"[INFO] Submission Classification: {submission_classification}")
    
#     if submission_classification == "Non-Submission":
#         print("\n---------------- NON-SUBMISSION EMAIL. NO EXTRACTION PERFORMED ----------------")
#         return {}
    
#     # Copy attachments to processing folder
#     for path in attachment_paths:
#         if os.path.exists(path):
#             filename = os.path.basename(path)
#             dest_path = os.path.join(attachment_folder, filename)
#             with open(path, "rb") as src, open(dest_path, "wb") as dst:
#                 dst.write(src.read())
    
#     # Step 2: Attachment-wise classification
#     print("\n---------------- RUNNING ATTACHMENT-WISE CLASSIFICATION ----------------")
#     attachment_classification_result = get_attachment_wise_classification(
#         attachment_folder, 
#         ocr_folder, 
#         max_pages=constants.CLASSIFICATION_MAX_PAGES
#     )
    
#     print("\n---------------- ATTACHMENT CLASSIFICATION RESULT ----------------")
#     print(json.dumps(attachment_classification_result, indent=4))
    
#     # Save classification results
#     save_classification_results(attachment_classification_result, output_folder)
    
#     # Step 3: Extract content by document type
#     print("\n---------------- EXTRACTING DOCTYPE-WISE ATTACHMENT CONTENT ----------------")
#     doctype_wise_attachment_content = get_doctype_wise_attachment_content(
#         attachment_folder,
#         ocr_folder,
#         attachment_classification_result,
#         max_pages=constants.CLASSIFICATION_MAX_PAGES,
#     )
    
#     non_empty_keys = [k for k, v in doctype_wise_attachment_content.items() if v]
#     if non_empty_keys:
#         print(f"[INFO] Attachment content found in: {non_empty_keys}")
#     else:
#         print("[INFO] No attachment content found.")
    
#     # Step 4: Perform field extraction
#     print("\n---------------- PERFORMING FIELD EXTRACTION ----------------")
#     extracted_fields = get_extraction(email_content, doctype_wise_attachment_content)
    
#     # Prepare final result
#     final_result = {
#         "uniqueIdentifier": unique_id,
#         "sender": metadata.get("From", ""),
#         "recipient": metadata.get("To", ""),
#         "subject": metadata.get("Subject", ""),
#         "totalAttachments": len(attachment_paths),
#         "attachmentDocTypeClassification": attachment_classification_result if attachment_classification_result else None,
#         "lineOfBusiness": submission_classification,
#         "extractedFields": extracted_fields,
#         "processedDate": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
#     }
    
#     # Save result
#     result_file_path = os.path.join(output_folder, "extraction.json")
    
#     with open(result_file_path, "w", encoding="utf-8") as f:
#         json.dump(final_result, f, indent=4, ensure_ascii=False)
    
#     print(f"\n[INFO] Extraction results saved to: {result_file_path}")
    
#     # Upload extraction.json to blob storage
#     try:
#         # Create blob name using the unique identifier
#         blob_name = f"{unique_id}/extraction.json"
        
#         # Upload to blob storage
#         blob_url = upload_json_to_blob(final_result, blob_name)
        
#         if blob_url:
#             print(f"\n[INFO] Extraction results uploaded to blob storage: {blob_url}")
#         else:
#             print("\n[WARNING] Failed to upload extraction results to blob storage")
#     except Exception as e:
#         print(f"\n[ERROR] Error uploading extraction results to blob: {e}")
    
#     return final_result






"""
Document Processing Pipeline for Azure Function App
Adapted from the Submission from images/extraction_v1.py
"""

import os
import re
import json
import time
import logging
import pandas as pd
from datetime import datetime
from typing import Dict, Any, List

# Try importing the necessary packages, handle missing dependencies gracefully
try:
    import tiktoken
except ImportError:
    logging.warning("tiktoken not installed. Token counting will not be accurate.")
    
    # Simple fallback for token counting
    def simple_token_count(text):
        return len(text.split())
        
    class DummyTikToken:
        @staticmethod
        def encoding_for_model(model):
            return DummyTikToken()
            
        @staticmethod
        def get_encoding(name):
            return DummyTikToken()
            
        @staticmethod
        def encode(text):
            return [1] * simple_token_count(text)
            
    tiktoken = DummyTikToken()

try:
    from openai import AzureOpenAI
except ImportError:
    logging.error("openai package not installed. AI processing will not work.")

try:
    from azure.core.credentials import AzureKeyCredential
except ImportError:
    logging.error("Azure Core package not installed. Azure services will not work properly.")

# Local modules
import constants
import prompts
import helper
# Import specific function from utils
from utils import upload_json_to_blob

# Azure OpenAI client setup
def get_openai_client():
    """
    Gets an Azure OpenAI client, with fallbacks
    """
    try:
        from openai import AzureOpenAI
        return AzureOpenAI(
            azure_endpoint=constants.AZURE_OPENAI_ENDPOINT,
            api_key=constants.AZURE_OPENAI_KEY,
            api_version=constants.AZURE_OPENAI_API_VERSION,
        )
    except ImportError:
        logging.error("OpenAI SDK not installed or not compatible")
        
        # Create a mock client that logs errors
        class MockOpenAIClient:
            def __getattr__(self, name):
                def method(*args, **kwargs):
                    logging.error(f"OpenAI {name} method called but OpenAI SDK not available")
                    return None
                return method
                
        return MockOpenAIClient()

# ---------------------------------------------------------------------------
# OpenAI helpers
# ---------------------------------------------------------------------------

def generate_response(prompt_text: str, system_prompt: str, max_tokens: int = 3048) -> str:
    """Generate a response using Azure OpenAI"""
    client = get_openai_client()
    message_text = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": prompt_text},
    ]
    completion = client.chat.completions.create(
        model="gpt-4o",  # Using the available model in your environment
        messages=message_text,
        max_tokens=max_tokens,
        temperature=0.2,
        seed=38,
        top_p=0.9,
        response_format={"type": "json_object"},
    )
    return completion.choices[0].message.content


def count_tokens(prompt_text: str, model: str = "gpt-4") -> int:
    """
    Counts tokens for a given model, with fallbacks for missing dependencies
    """
    # First try using tiktoken if available
    try:
        if hasattr(tiktoken, "encoding_for_model"):
            try:
                encoding = tiktoken.encoding_for_model(model)
                return len(encoding.encode(prompt_text))
            except (KeyError, AttributeError):
                try:
                    encoding = tiktoken.get_encoding("cl100k_base")  # fallback
                    return len(encoding.encode(prompt_text))
                except (KeyError, AttributeError):
                    pass
    except Exception:
        pass
        
    # Fallback: simple approximation (4 chars ~= 1 token)
    return len(prompt_text) // 4

# ---------------------------------------------------------------------------
# Email content extraction
# ---------------------------------------------------------------------------

def validate_json_structure(json_data: dict) -> dict:
    """
    Validate the structured JSON format for main_content.json
    
    Args:
        json_data: The JSON data to validate
        
    Returns:
        dict: Validation results with status and details
    """
    validation_results = {
        "isValid": True,
        "errors": [],
        "warnings": [],
        "sectionValidation": {}
    }
    
    required_sections = [
        "documentInfo", "emailHeaders", "emailContent", 
        "emailThread", "attachments", "processing", "legacy"
    ]
    
    # Check for required top-level sections
    for section in required_sections:
        if section not in json_data:
            validation_results["errors"].append(f"Missing required section: {section}")
            validation_results["isValid"] = False
            validation_results["sectionValidation"][section] = False
        else:
            validation_results["sectionValidation"][section] = True
    
    # Validate documentInfo section
    if "documentInfo" in json_data:
        doc_info = json_data["documentInfo"]
        required_fields = ["uniqueIdentifier", "version", "documentType", "createdAt"]
        for field in required_fields:
            if field not in doc_info:
                validation_results["warnings"].append(f"Missing documentInfo field: {field}")
    
    # Validate emailHeaders section
    if "emailHeaders" in json_data:
        headers = json_data["emailHeaders"]
        if not headers.get("from"):
            validation_results["warnings"].append("Missing 'from' email address")
        if not headers.get("subject"):
            validation_results["warnings"].append("Missing email subject")
    
    # Validate emailThread section
    if "emailThread" in json_data:
        thread = json_data["emailThread"]
        if "threadList" not in thread or not isinstance(thread["threadList"], list):
            validation_results["errors"].append("Invalid or missing threadList")
            validation_results["isValid"] = False
        elif len(thread["threadList"]) == 0:
            validation_results["warnings"].append("Empty thread list")
    
    return validation_results

def prepare_email_content(metadata: Dict[str, Any]) -> str:
    """
    Prepares email content from metadata
    """
    from_email = metadata.get("From", "")
    to_email = metadata.get("To", "")
    cc_email = metadata.get("CC", "")
    subject = metadata.get("Subject", "")
    body = metadata.get("Body", "")
    
    email_content = f"From: {from_email}\nTo: {to_email}\nCC: {cc_email}\nSubject: {subject}\n\n{body}"
    
    return email_content

# ---------------------------------------------------------------------------
# Classification (Submission vs Non)
# ---------------------------------------------------------------------------

def submission_classifier(email_content: str) -> str:
    """Classify if the email is a submission and determine the line of business"""
    classification_system_prompt = prompts.submission_classification_system_prompt
    classification_prompt = prompts.submission_classification_prompt_template.format(
        email_content=email_content
    )
    num_tokens = count_tokens(classification_prompt)
    print(f"Submission Prompt Token Count: {num_tokens}")
    response = generate_response(classification_prompt, classification_system_prompt)
    try:
        parsed = json.loads(response)
        return parsed.get("Classification", "Non-Submission")
    except json.JSONDecodeError:
        return "Non-Submission"

# ---------------------------------------------------------------------------
# Azure Document Intelligence OCR
# ---------------------------------------------------------------------------

def extract_ocr_markdown(data: bytes) -> dict:
    """Extract text from document using Azure Document Intelligence"""
    try:
        # Try to use Azure Document Intelligence if available
        try:
            from azure.core.credentials import AzureKeyCredential
            from azure.ai.documentintelligence import DocumentIntelligenceClient
            
            # Define helper class if the models aren't available
            class AnalyzeDocumentRequest:
                def __init__(self, bytes_source=None):
                    self.bytes_source = bytes_source
                    
            class DocumentContentFormat:
                MARKDOWN = "markdown"
                
            # Try to import the proper models if available    
            try:
                from azure.ai.documentintelligence.models import (
                    AnalyzeDocumentRequest,
                    DocumentContentFormat,
                )
            except ImportError:
                pass
                
            with DocumentIntelligenceClient(
                endpoint=constants.DOCAI_ENDPOINT,
                credential=AzureKeyCredential(constants.DOCAI_KEY),
            ) as client_di:
                poller = client_di.begin_analyze_document(
                    "prebuilt-layout",
                    AnalyzeDocumentRequest(bytes_source=data),
                    output_content_format=DocumentContentFormat.MARKDOWN,
                )
                return poller.result().as_dict()
        except (ImportError, Exception) as e:
            logging.warning(f"Azure Document Intelligence failed: {e}. Trying Form Recognizer.")
            
            # Try to use Form Recognizer (older version) if available
            try:
                from azure.ai.formrecognizer import DocumentAnalysisClient
                
                with DocumentAnalysisClient(
                    endpoint=constants.DOCAI_ENDPOINT,
                    credential=AzureKeyCredential(constants.DOCAI_KEY),
                ) as client_fr:
                    poller = client_fr.begin_analyze_document(
                        "prebuilt-read",
                        data
                    )
                    result = poller.result()
                    
                    # Convert to a format similar to Document Intelligence
                    text_content = ""
                    pages = []
                    
                    for page in result.pages:
                        page_text = ""
                        for line in page.lines:
                            page_text += line.content + "\n"
                            
                        text_content += page_text
                        pages.append({
                            "pageNumber": page.page_number,
                            "spans": [{"offset": len(text_content) - len(page_text), "length": len(page_text)}]
                        })
                    
                    return {
                        "content": text_content,
                        "pages": pages
                    }
            except (ImportError, Exception) as e:
                logging.warning(f"Form Recognizer failed: {e}. Falling back to utils.py extract_text_from_document.")
                
                # Use the existing utility from utils.py if available
                try:
                    from utils import extract_text_from_document
                    import tempfile
                    
                    # Save bytes to a temporary file
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                        tmp.write(data)
                        tmp_path = tmp.name
                        
                    # Use the existing utility
                    extracted_text = extract_text_from_document(tmp_path, ".pdf")
                    
                    # Clean up the temporary file
                    try:
                        os.remove(tmp_path)
                    except:
                        pass
                        
                    # Return in a format similar to Document Intelligence
                    return {
                        "content": extracted_text,
                        "pages": [{"pageNumber": 1, "spans": [{"offset": 0, "length": len(extracted_text)}]}]
                    }
                except Exception as e:
                    logging.error(f"All OCR methods failed: {e}")
                    
    except Exception as e:
        logging.error(f"OCR extraction error: {e}")
        
    # Return empty result if all methods fail
    return {"content": "", "pages": []}


def get_page_wise_content(content_json: dict) -> List[Dict[str, Any]]:
    """Extract page-wise content from OCR results"""
    page_wise_content = []
    for page in content_json.get("pages", []):
        content = ""
        spans = page.get("spans", [])
        if spans:
            span = spans[0]
            content = content_json["content"][span["offset"]: span["offset"] + span["length"]]
        page_wise_content.append(
            {
                "page_number": page.get("pageNumber"),
                "content": content,
            }
        )
    return page_wise_content

# ---------------------------------------------------------------------------
# File text extraction helpers
# ---------------------------------------------------------------------------

def excel_to_string(file_path: str, max_rows: int = 100) -> str:
    """Convert Excel file to a string representation"""
    try:
        all_sheets = pd.read_excel(file_path, sheet_name=None)
        excel_text = ""
        for sheet_name, df in all_sheets.items():
            # Limit rows
            df = df.head(max_rows)
            excel_text += f"### Sheet Name: {sheet_name}\n"
            # Pipe-separated, fill NaNs
            sheet_txt = (
                df.fillna("")
                  .astype(str)
                  .apply(lambda row: "|".join(row), axis=1)
                  .str.cat(sep="\n")
            )
            excel_text += sheet_txt + "\n\n"
        return excel_text.strip()
    except Exception as e:
        return f"Error reading Excel file: {e}"


def pdf_to_string(content_json: dict, max_pages: int) -> str:
    """Convert PDF OCR results to a string representation"""
    page_wise = get_page_wise_content(content_json)
    result_string = ""
    for page in page_wise[:max_pages]:
        result_string += f"### Page Number: {page['page_number']}\n{page['content']}\n\n"
    return result_string.strip()

# ---------------------------------------------------------------------------
# Doctype classification
# ---------------------------------------------------------------------------

def doctype_classifier(document_content: str) -> str:
    """Classify the document type (Skeleton Risk, Slip Risk, SOV, Others)"""
    system_prompt = prompts.doctype_classification_system_prompt
    doctype_prompt = prompts.doctype_classification_prompt_template.format(
        document_content=document_content
    )
    num_tokens = count_tokens(doctype_prompt)
    print(f"Doctype Classification Prompt Token Count: {num_tokens}")
    response = generate_response(doctype_prompt, system_prompt)
    try:
        parsed = json.loads(response)
        return parsed.get("Classification", "Others")
    except json.JSONDecodeError:
        return "Others"

# ---------------------------------------------------------------------------
# Document classification
# ---------------------------------------------------------------------------

def get_ocr_json(file_path: str, ocr_folder: str) -> dict:
    """Get OCR JSON for a document, with caching"""
    filename = os.path.basename(file_path)
    json_path = os.path.join(ocr_folder, f"{os.path.splitext(filename)[0]}.json")
    
    if os.path.exists(json_path):
        with open(json_path, "r", encoding="utf-8") as jf:
            return json.load(jf)

    with open(file_path, "rb") as f:
        pdf_bytes = f.read()

    print(f"[INFO] Performing Azure OCR for: {filename}")
    content_json = extract_ocr_markdown(pdf_bytes)

    # Save OCR results for future use
    os.makedirs(os.path.dirname(json_path), exist_ok=True)
    with open(json_path, "w", encoding="utf-8") as jf:
        json.dump(content_json, jf, indent=2)

    return content_json


def classify_file(file_path: str, ocr_folder: str, max_pages: int) -> str:
    """Classify a file by its content"""
    filename = os.path.basename(file_path)
    file_lower = filename.lower()

    if file_lower.endswith((".pdf", ".docx", ".doc")):
        ocr_json = get_ocr_json(file_path, ocr_folder)
        text = pdf_to_string(ocr_json, max_pages)
        return doctype_classifier(text)

    if file_lower.endswith((".xlsx", ".xls")) and not filename.startswith("~$"):
        text = excel_to_string(file_path)
        return doctype_classifier(text)

    return "Others"


def save_classification_results(results: dict, output_folder: str):
    """Save document classification results to a JSON file"""
    if not results:
        return
        
    os.makedirs(output_folder, exist_ok=True)
    results_path = os.path.join(output_folder, "doctype_classification.json")
    
    with open(results_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=4, ensure_ascii=False)
        
    print("[INFO] Doctype Classification Results saved to:", results_path)


def get_attachment_wise_classification(attachment_folder: str, ocr_folder: str, max_pages: int = 10) -> Dict[str, str]:
    """Classify all attachments in a folder"""
    os.makedirs(ocr_folder, exist_ok=True)
    
    results = {}
    for filename in os.listdir(attachment_folder):
        print(f"[INFO] Processing file: {filename}")
        file_path = os.path.join(attachment_folder, filename)
        
        if not os.path.isfile(file_path):
            continue
            
        try:
            result = classify_file(file_path, ocr_folder, max_pages)
            if result:
                results[filename] = result
        except Exception as e:
            print(f"[ERROR] Failed to classify {filename}: {e}")
            continue

    return results

# ---------------------------------------------------------------------------
# Content extraction by file type
# ---------------------------------------------------------------------------

def extract_content_by_type(
    file_path: str,
    filename: str,
    ocr_folder: str,
    max_pages: int,
) -> str:
    """Extract content from a file based on its type"""
    file_lower = filename.lower()
    
    if file_lower.endswith((".pdf", ".docx", ".doc")):
        ocr_json = get_ocr_json(file_path, ocr_folder)
        return pdf_to_string(ocr_json, max_pages)
        
    elif file_lower.endswith((".xlsx", ".xls")) and not filename.startswith("~$"):
        return excel_to_string(file_path)
        
    print(f"[INFO] Unsupported file format for: {filename}")
    return ""


def get_doctype_wise_attachment_content(
    attachment_folder: str,
    ocr_folder: str,
    classification_dict: dict,
    max_pages: int,
) -> dict:
    """Group attachment content by document type"""
    categorized_content = {
        "Skeleton Risk": "",
        "Slip Risk": "",
        "SOV": "",
    }

    for filename, doc_type in classification_dict.items():
        file_path = os.path.join(attachment_folder, filename)
        
        if not os.path.isfile(file_path):
            print(f"[WARNING] File not found: {file_path}")
            continue

        try:
            content = extract_content_by_type(file_path, filename, ocr_folder, max_pages)
            if content:
                # Clean the filename - remove numeric prefixes like "1_", "2_" etc.
                clean_filename = filename
                if re.match(r'^\d+_', clean_filename):
                    clean_filename = re.sub(r'^\d+_', '', clean_filename)
                    
                formatted = f"## FileName: {clean_filename}\n{content}\n\n"
                if doc_type in categorized_content:
                    categorized_content[doc_type] += formatted
        except Exception as e:
            print(f"[ERROR] Failed to read {filename}: {e}")
            continue

    return {k: v.strip() for k, v in categorized_content.items()}

# ---------------------------------------------------------------------------
# Single-document extraction (Slip / Skeleton / SOV)
# ---------------------------------------------------------------------------

def extract_single(submission_classification,doc_type: str, email_content: str, attachment_content: str) -> dict:
    """Extract fields from a single document type"""
    if submission_classification =="Auto Liability":
            fields_description_map = {
            "Skeleton Risk": prompts.auto_skeleton_fields_description,
            "Slip Risk": prompts.auto_slip_fields_description,
            "SOV": prompts.auto_sov_fields_description,
        }
    else:
        fields_description_map = {
            "Skeleton Risk": prompts.skeleton_fields_description,
            "Slip Risk": prompts.slip_fields_description,
            "SOV": prompts.sov_fields_description,
        }
    
    if doc_type not in fields_description_map:
        return {}

    # Clean attachment content to ensure filename references don't have numeric prefixes
    cleaned_attachment_content = attachment_content
    for match in re.finditer(r'## FileName: \d+_(.*?)\n', attachment_content):
        original = match.group(0)
        cleaned = f"## FileName: {match.group(1)}\n"
        cleaned_attachment_content = cleaned_attachment_content.replace(original, cleaned)

    filled_prompt = prompts.extraction_prompt_template.format(
        fields_description=fields_description_map[doc_type],
        email_content=email_content,
        attachment_content=cleaned_attachment_content,
    )
    
    print(f"[INFO] Token count for {doc_type} extraction prompt: {count_tokens(filled_prompt)}")
    response = generate_response(filled_prompt, prompts.extraction_system_prompt)
    
    try:
        return json.loads(response)
    except Exception as e:
        print(f"[ERROR] Failed to parse {doc_type} JSON: {e}")
        return {}


def get_extraction(submission_classification,email_content: str, doctype_content_dict: dict) -> dict:
    """Extract fields from all document types"""
    result = {doc: {} for doc in ["Skeleton Risk", "Slip Risk", "SOV"]}

    # Skeleton Risk: if empty, still run with 'Not Present'
    skeleton_content = doctype_content_dict.get("Skeleton Risk", "").strip()
    if not skeleton_content:
        print("[INFO] Skeleton Risk content missing; running extraction with attachment content 'Not Present'.")
        result["Skeleton Risk"] = extract_single(submission_classification,"Skeleton Risk", email_content, "Not Present")
    else:
        result["Skeleton Risk"] = extract_single(submission_classification,"Skeleton Risk", email_content, skeleton_content)

    # Other doc types only if content exists
    for doc_type in ["Slip Risk", "SOV"]:
        content = doctype_content_dict.get(doc_type, "").strip()
        if content:
            result[doc_type] = extract_single(submission_classification,doc_type, email_content, content)

    return result

# ---------------------------------------------------------------------------
# Mail content upload with enhanced thread parsing
# ---------------------------------------------------------------------------

def upload_mail_content(metadata: Dict[str, Any], unique_id: str = None) -> str:
    """
    Upload the complete mail content as main_content.json to blob storage
    
    Enhanced version that includes complete email thread parsing as a list format
    to ensure proper data population into blob storage.
    
    Args:
        metadata: Email metadata including From, To, Subject, etc.
        unique_id: Unique identifier for the email. If None, one will be generated.
        
    Returns:
        str: Blob URL if upload was successful, None otherwise
    """
    try:
        # Create a unique identifier for this email if not provided
        if not unique_id:
            sender = metadata.get("From", "unknown").split("@")[0]

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            date = metadata["Received Date"]
            time = metadata["Received Time"].replace(" IST", "").replace(":", "-")

        # Build folder name
            folder_name = f"{sender}_{date}_{time}"
            unique_id = f"{folder_name}"
        
        # Prepare the email content
        email_content = prepare_email_content(metadata)
        
        # Try to parse the email thread if email_thread_parser is available
        email_thread_data = None
        parsed_thread_list = []
        thread_summary = {}
        
        try:
            from email_thread_parser import EmailThreadParser
            parser = EmailThreadParser()
            email_body = metadata.get("Body", "")
            if email_body:
                parsed_thread_list = parser.parse_email_thread(email_body)
                thread_summary = parser.extract_thread_summary(email_body)
                
                # Ensure each email in the thread has proper structure for blob storage
                for idx, email in enumerate(parsed_thread_list):
                    if 'email_id' not in email:
                        email['email_id'] = idx + 1
                    if 'timestamp' not in email:
                        email['timestamp'] = datetime.now().isoformat()
                    # Ensure content is properly formatted
                    if isinstance(email.get('content'), list):
                        email['content'] = '\n'.join(email['content'])
                
                email_thread_data = {
                    "parsedThread": parsed_thread_list,
                    "threadSummary": thread_summary,
                    "totalEmailsInThread": len(parsed_thread_list)
                }
                
                print(f"[INFO] Parsed email thread with {len(parsed_thread_list)} emails")
        except ImportError:
            print("[INFO] email_thread_parser module not available, skipping thread parsing")
            # Create a basic thread structure with just the current email
            parsed_thread_list = [{
                "email_id": 1,
                "headers": {
                    "from": metadata.get("From", ""),
                    "to": metadata.get("To", ""),
                    "cc": metadata.get("CC", ""),
                    "subject": metadata.get("Subject", "")
                },
                "content": metadata.get("Body", ""),
                "type": "current",
                "quote_level": 0,
                "timestamp": datetime.now().isoformat()
            }]
            thread_summary = {
                "total_emails": 1,
                "participants": [metadata.get("From", "")],
                "subjects": [metadata.get("Subject", "")],
                "total_word_count": len(metadata.get("Body", "").split()) if metadata.get("Body") else 0,
                "email_types": {"current": 1, "reply": 0, "quoted": 0}
            }
        except Exception as e:
            print(f"[WARNING] Error parsing email thread: {e}")
            # Create a basic thread structure with just the current email
            parsed_thread_list = [{
                "email_id": 1,
                "headers": {
                    "from": metadata.get("From", ""),
                    "to": metadata.get("To", ""),
                    "cc": metadata.get("CC", ""),
                    "subject": metadata.get("Subject", "")
                },
                "content": metadata.get("Body", ""),
                "type": "current",
                "quote_level": 0,
                "timestamp": datetime.now().isoformat()
            }]
            thread_summary = {
                "total_emails": 1,
                "participants": [metadata.get("From", "")],
                "subjects": [metadata.get("Subject", "")],
                "total_word_count": len(metadata.get("Body", "").split()) if metadata.get("Body") else 0,
                "email_types": {"current": 1, "reply": 0, "quoted": 0}
            }
        
        # Create a structured JSON object with organized sections
        mail_content_json = {
            # Document identification and metadata
            "documentInfo": {
                "uniqueIdentifier": unique_id,
                "version": "2.0",
                "documentType": "email_content",
                "createdAt": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "processedAt": datetime.now().isoformat(),
                "dataSource": "email_processor"
            },
            
            # Email header information
            "emailHeaders": {
                "from": metadata.get("From", ""),
                "to": metadata.get("To", ""),
                "cc": metadata.get("CC", ""),
                "bcc": metadata.get("BCC", ""),
                "subject": metadata.get("Subject", ""),
                "date": metadata.get("Date", ""),
                "messageId": metadata.get("Message-ID", ""),
                "replyTo": metadata.get("Reply-To", ""),
                "importance": metadata.get("Importance", ""),
                "priority": metadata.get("Priority", "")
            },
            
            # Email content structure
            "emailContent": {
                "formattedContent": email_content,
                "originalBody": metadata.get("Body", ""),
                "bodyFormat": metadata.get("BodyFormat", "text"),
                "encoding": metadata.get("Encoding", "utf-8"),
                "size": len(metadata.get("Body", "")),
                "wordCount": len(metadata.get("Body", "").split()) if metadata.get("Body") else 0
            },
            
            # Email thread analysis
            "emailThread": {
                "threadList": parsed_thread_list,
                "threadSummary": thread_summary,
                "threadMetrics": {
                    "totalEmails": len(parsed_thread_list),
                    "uniqueParticipants": len(set(thread_summary.get("participants", []))),
                    "conversationDepth": max([email.get("quote_level", 0) for email in parsed_thread_list]) if parsed_thread_list else 0,
                    "hasReplies": len(parsed_thread_list) > 1,
                    "threadStartDate": parsed_thread_list[-1].get("timestamp") if parsed_thread_list else None,
                    "threadEndDate": parsed_thread_list[0].get("timestamp") if parsed_thread_list else None
                }
            },
            
            # Attachment information (if any)
            "attachments": {
                "hasAttachments": bool(metadata.get("Attachments", [])),
                "attachmentCount": len(metadata.get("Attachments", [])),
                "attachmentList": metadata.get("Attachments", []),
                "totalAttachmentSize": metadata.get("TotalAttachmentSize", 0)
            },
            
            # Processing metadata
            "processing": {
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "processingVersion": "2.0",
                "threadParsingEnabled": True,
                "threadParsingStatus": "success" if parsed_thread_list else "fallback",
                "dataValidation": {
                    "hasValidHeaders": bool(metadata.get("From") and metadata.get("Subject")),
                    "hasContent": bool(metadata.get("Body")),
                    "threadParsed": len(parsed_thread_list) > 0,
                    "structureValid": True
                }
            },
            
            # Legacy compatibility section
            "legacy": {
                "originalMetadata": metadata,
                "legacyEmailContent": email_content
            }
        }
        
        # Add backwards compatible thread data if available
        if email_thread_data:
            mail_content_json["legacy"]["emailThread"] = email_thread_data
        
        # Validate thread list structure before upload
        if parsed_thread_list:
            print(f"[INFO] Email thread structure validated: {len(parsed_thread_list)} emails in thread")
            for idx, email in enumerate(parsed_thread_list):
                if not email.get('email_id'):
                    email['email_id'] = idx + 1
                if not email.get('timestamp'):
                    email['timestamp'] = datetime.now().isoformat()
                if not email.get('type'):
                    email['type'] = 'current' if idx == 0 else 'quoted'
            
            # Update the structured JSON with validated data
            mail_content_json["emailThread"]["threadList"] = parsed_thread_list
            mail_content_json["emailThread"]["threadMetrics"]["totalEmails"] = len(parsed_thread_list)
            mail_content_json["processing"]["threadParsingStatus"] = "success"
        else:
            print("[WARNING] Empty email thread list, using fallback structure")
            fallback_thread = [{
                "email_id": 1,
                "headers": {
                    "from": metadata.get("From", ""),
                    "to": metadata.get("To", ""),
                    "cc": metadata.get("CC", ""),
                    "subject": metadata.get("Subject", "")
                },
                "content": metadata.get("Body", ""),
                "type": "current",
                "quote_level": 0,
                "timestamp": datetime.now().isoformat()
            }]
            mail_content_json["emailThread"]["threadList"] = fallback_thread
            mail_content_json["emailThread"]["threadMetrics"]["totalEmails"] = 1
            mail_content_json["processing"]["threadParsingStatus"] = "fallback"
        
        # Final validation of the complete structure
        validation_results = {
            "documentStructure": bool(mail_content_json.get("documentInfo")),
            "emailHeaders": bool(mail_content_json.get("emailHeaders", {}).get("from")),
            "emailContent": bool(mail_content_json.get("emailContent", {}).get("originalBody")),
            "threadData": bool(mail_content_json.get("emailThread", {}).get("threadList")),
            "processingInfo": bool(mail_content_json.get("processing"))
        }
        
        mail_content_json["processing"]["dataValidation"].update(validation_results)
        
        print(f"[INFO] Structured JSON validation: {validation_results}")
        print(f"[INFO] Document structure created with {len(mail_content_json)} main sections")
        
        # Perform comprehensive structure validation
        structure_validation = validate_json_structure(mail_content_json)
        if not structure_validation["isValid"]:
            print(f"[WARNING] JSON structure validation failed: {structure_validation['errors']}")
        if structure_validation["warnings"]:
            print(f"[INFO] JSON structure warnings: {structure_validation['warnings']}")
        
        mail_content_json["processing"]["structureValidation"] = structure_validation
        
        # Create blob name using the unique identifier
        blob_name = f"{unique_id}/main_content.json"
        
        # Upload to blob storage
        blob_url = upload_json_to_blob(mail_content_json, blob_name)
        
        if blob_url:
            print(f"\n[INFO] Mail content uploaded to blob storage: {blob_url}")
            return blob_url
        else:
            print("\n[WARNING] Failed to upload mail content to blob storage")
            return None
    except Exception as e:
        print(f"\n[ERROR] Error uploading mail content to blob: {e}")
        return None

# ---------------------------------------------------------------------------
# Main processing pipeline
# ---------------------------------------------------------------------------

def process_email_attachments(metadata: Dict[str, Any], attachment_paths: List[str]) -> dict:
    """
    Main processing pipeline for email attachments
    
    Args:
        metadata: Email metadata including From, To, Subject, etc.
        attachment_paths: List of paths to attachments
    
    Returns:
        dict: Extraction results
    """
    # Setup processing folders
    temp_folder = constants.TEMP_FOLDER_PATH
    extraction_folder = constants.EXTRACTIONOUTPUT_PATH
    
    # Create a unique identifier for this email
    username = metadata.get("From", "unknown").split("@")[0]
    date = metadata["Received Date"]
    time = metadata["Received Time"].replace(" IST", "").replace(":", "-")

# Build folder name
    folder_name = f"{username}_{date}_{time}"

    # unique_id = f"{sender}"
    unique_id = folder_name
    
    # Setup paths
    processing_folder = os.path.join(extraction_folder, unique_id)
    attachment_folder = os.path.join(processing_folder, "attachments")
    ocr_folder = os.path.join(processing_folder, "OCR")
    output_folder = os.path.join(processing_folder, "output")
    
    os.makedirs(attachment_folder, exist_ok=True)
    os.makedirs(ocr_folder, exist_ok=True)
    os.makedirs(output_folder, exist_ok=True)
    
    # Upload mail content to blob storage regardless of attachment status
    upload_mail_content(metadata, unique_id)
    
    # Prepare the email content for further processing
    email_content = prepare_email_content(metadata)
    
    # Step 1: LOB classification
    print("\n---------------- RUNNING LOB CLASSIFICATION ----------------")
    submission_classification = submission_classifier(email_content)
    print(f"[INFO] Submission Classification: {submission_classification}")
    
    if submission_classification == "Non-Submission":
        print("\n---------------- NON-SUBMISSION EMAIL. NO EXTRACTION PERFORMED ----------------")
        return {}
    
    # Copy attachments to processing folder
    for path in attachment_paths:
        if os.path.exists(path):
            filename = os.path.basename(path)
            dest_path = os.path.join(attachment_folder, filename)
            with open(path, "rb") as src, open(dest_path, "wb") as dst:
                dst.write(src.read())
    
    # Step 2: Attachment-wise classification
    print("\n---------------- RUNNING ATTACHMENT-WISE CLASSIFICATION ----------------")
    attachment_classification_result = get_attachment_wise_classification(
        attachment_folder, 
        ocr_folder, 
        max_pages=constants.CLASSIFICATION_MAX_PAGES
    )
    
    print("\n---------------- ATTACHMENT CLASSIFICATION RESULT ----------------")
    print(json.dumps(attachment_classification_result, indent=4))
    
    # Save classification results
    save_classification_results(attachment_classification_result, output_folder)
    
    # Step 3: Extract content by document type
    print("\n---------------- EXTRACTING DOCTYPE-WISE ATTACHMENT CONTENT ----------------")
    doctype_wise_attachment_content = get_doctype_wise_attachment_content(
        attachment_folder,
        ocr_folder,
        attachment_classification_result,
        max_pages=constants.CLASSIFICATION_MAX_PAGES,
    )
    
    non_empty_keys = [k for k, v in doctype_wise_attachment_content.items() if v]
    if non_empty_keys:
        print(f"[INFO] Attachment content found in: {non_empty_keys}")
    else:
        print("[INFO] No attachment content found.")
    
    # Step 4: Perform field extraction
    print("\n---------------- PERFORMING FIELD EXTRACTION ----------------")
    extracted_fields = get_extraction(submission_classification,email_content, doctype_wise_attachment_content)
    
    # Prepare final result with clean attachment names
    # Extract just the filename without any prefixes
    clean_attachment_classification = {}
    clean_name_mapping = {}  # To store mapping between original and clean names
    
    if attachment_classification_result:
        for attachment_name, doc_type in attachment_classification_result.items():
            # Extract just the filename without any "!_attachment_name" prefix
            clean_name = attachment_name
            if "!_attachment_name" in attachment_name:
                clean_name = attachment_name.split("!_attachment_name")[1]
                
            # Remove numeric prefixes like "1_", "2_", etc.
            if re.match(r'^\d+_', clean_name):
                base_name = re.sub(r'^\d+_', '', clean_name)
                clean_name_mapping[clean_name] = base_name
                clean_name = base_name
                
            clean_attachment_classification[clean_name] = doc_type
    
    # Clean up the filenames in the extracted fields to match the clean attachment names
    cleaned_extracted_fields = {}
    for doc_type, fields in extracted_fields.items():
        cleaned_extracted_fields[doc_type] = {}
        for field_name, field_data in fields.items():
            # Create a copy of the field data
            cleaned_field_data = field_data.copy()
            
            # Clean the filename in the field data if it's in our mapping
            if "filename" in cleaned_field_data:
                filename = cleaned_field_data["filename"]
                # Check if this filename has a numeric prefix
                if filename in clean_name_mapping:
                    cleaned_field_data["filename"] = clean_name_mapping[filename]
                elif re.match(r'^\d+_', filename):
                    # Handle cases where the mapping wasn't created but filename still has prefix
                    cleaned_field_data["filename"] = re.sub(r'^\d+_', '', filename)
            
            cleaned_extracted_fields[doc_type][field_name] = cleaned_field_data

    risk_details = {}
    if submission_classification =="Auto Liability":
        risk_details = calculate_risk_for_Auto_Liability(cleaned_extracted_fields)
    
    final_result = {
        "uniqueIdentifier": unique_id,
        "sender": metadata.get("From", ""),
        "recipient": metadata.get("To", ""),
        "subject": metadata.get("Subject", ""),
        "totalAttachments": len(attachment_paths),
        "attachmentDocTypeClassification": clean_attachment_classification if attachment_classification_result else None,
        "lineOfBusiness": submission_classification,
        "extractedFields": cleaned_extracted_fields,
        "riskDetails": risk_details,
        "processedDate": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }
    
    # Save result
    result_file_path = os.path.join(output_folder, "extraction.json")
    
    with open(result_file_path, "w", encoding="utf-8") as f:
        json.dump(final_result, f, indent=4, ensure_ascii=False)
    
    print(f"\n[INFO] Extraction results saved to: {result_file_path}")
    
    # Upload extraction.json to blob storage
    try:
        # Create blob name using the unique identifier
        blob_name = f"{unique_id}/extraction.json"
        
        # Upload to blob storage
        blob_url = upload_json_to_blob(final_result, blob_name)
        
        if blob_url:
            print(f"\n[INFO] Extraction results uploaded to blob storage: {blob_url}")
        else:
            print("\n[WARNING] Failed to upload extraction results to blob storage")
    except Exception as e:
        print(f"\n[ERROR] Error uploading extraction results to blob: {e}")
    
    return final_result




def calculate_risk_for_Auto_Liability(data: dict):
    scores = {}
    reasons = []

    def get_value(section, field):
        return data.get(section, {}).get(field, {}).get("value", "Not Present")

    # ---- Scoring Rule Functions ----
    def accidents_score(val):
        if val == "Not Present": return 5
        try:
            n = int(val)
        except:
            return 5
        if n <= 2: return 1
        elif n <= 5: return 2
        elif n <= 10: return 3
        elif n <= 15: return 4
        else: return 5

    def violations_score(val):
        if val == "Not Present": return 5
        try:
            n = int(val)
        except:
            return 5
        if n <= 1: return 1
        elif n <= 3: return 2
        elif n <= 6: return 3
        elif n <= 10: return 4
        else: return 5

    def experience_score(val):
        if val == "Not Present": return 5
        import re
        match = re.search(r"(\d+)", val)
        years = int(match.group(1)) if match else 0
        if years >= 10: return 1
        elif years >= 5: return 2
        elif years >= 3: return 3
        elif years >= 1: return 4
        else: return 5

    def age_score(val):
        if val == "Not Present": return 5
        if "Over" in val or "above" in val:
            num = int(val.split("Over")[1].split()[0])
            if num > 70: return 4
            if 30 <= num <= 60: return 1
            return 2
        return 5

    def named_drivers_score(val):
        if val == "Not Present": return 5
        try:
            n = int(val)
        except:
            return 5
        if n <= 50: return 1
        elif n <= 200: return 2
        elif n <= 500: return 3
        elif n <= 1000: return 4
        else: return 5

    def mileage_score(val):
        if val == "Not Present": return 5
        import re
        match = re.search(r"(\d+)", val.replace(",", ""))
        miles = int(match.group(1)) if match else 0
        if miles <= 20000: return 1
        elif miles <= 50000: return 2
        elif miles <= 80000: return 3
        elif miles <= 120000: return 4
        else: return 5

    def legal_score(val):
        if val == "Not Present": return 5
        try:
            n = int(val)
        except:
            return 5
        if n == 0: return 1
        elif n <= 2: return 2
        elif n <= 5: return 3
        elif n <= 10: return 4
        else: return 5

    def vehicle_value_score(val):
        if val == "Not Present": return 5
        try:
            v = float(val)
        except:
            return 5
        if v <= 25000: return 1
        elif v <= 75000: return 2
        elif v <= 150000: return 3
        elif v <= 300000: return 4
        else: return 5

    def weather_score(val):
        if val == "Not Present": return 5
        levels = {"None": 1, "Mild": 2, "Moderate": 3, "Severe": 4, "Extreme": 5}
        return levels.get(val, 5)

    # ---- Calculate scores ----
    params = {
        "Number of Accidents": accidents_score(get_value("Slip Risk", "NumberofAccidents")),
        "Number of Violations": violations_score(get_value("Slip Risk", "NumberofViolations")),
        "Driver Experience": experience_score(get_value("Slip Risk", "DriversExperienceYears")),
        "Driver Age": age_score(get_value("Slip Risk", "DriversAge")),
        "Named Drivers": named_drivers_score(get_value("Slip Risk", "NumberOfNamedDrivers")),
        "Annual Mileage": mileage_score(get_value("Slip Risk", "AnnualMileage")),
        "Pending Legal Issues": legal_score(get_value("Slip Risk", "PendingChallansOrLegalIssues")),
        "Vehicle Value": vehicle_value_score(get_value("SOV", "VehicleValue")),
        "Weather Risk": weather_score(get_value("Slip Risk", "RegionalWeatherRisks")),
    }

    # ---- Collect reasons and total ----
    total_score = 0
    for k, v in params.items():
        total_score += v
        if v == 1:
            reasons.append(f"{k}: Low risk (score {v})")
        elif v == 2:
            reasons.append(f"{k}: Moderate risk (score {v})")
        elif v == 3:
            reasons.append(f"{k}: Elevated risk (score {v})")
        elif v == 4:
            reasons.append(f"{k}: High risk (score {v})")
        else:
            reasons.append(f"{k}: Extreme risk or data missing (score {v})")

    # ---- Categorize based on total ----
    if total_score <= 15:
        category = "Low Risk"
    elif total_score <= 25:
        category = "Moderate Risk"
    elif total_score <= 30:
        category = "High Risk"
    elif total_score <= 35:
        category = "Very High Risk"
    else:
        category = "Extreme Risk"

    return {
        "risk_score": total_score,
        "risk_category": category,
        "risk_reasons": reasons
    }
