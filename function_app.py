# import logging
# import azure.functions as func
# import os
# import json
# from DemandClassifier import main_func
# from utils import process_attachments
# from extraction import process_email_attachments, submission_classifier, prepare_email_content

# app = func.FunctionApp()

# # Timer trigger: fetch emails via Graph API, process attachments/images, no blob/db logic
# @app.timer_trigger(schedule="0,30 * * * * *", arg_name="myTimer", run_on_startup=False, use_monitor=False)
# def timer_trigger(myTimer: func.TimerRequest) -> None:
#     logging.info('Azure Function timer trigger started.')
    
#     # Fetch latest email metadata using Graph API
#     metadata = main_func()
#     logging.info(f"Fetched metadata: {metadata}")
    
#     if metadata and isinstance(metadata, dict):
#         # Step 1: Prepare email content for classification
#         email_content = prepare_email_content(metadata)
        
#         # Step 2: Perform submission (LOB) classification
#         logging.info("Performing submission classification...")
#         submission_type = submission_classifier(email_content)
#         logging.info(f"Submission classification result: {submission_type}")
        
#         # Step 3: If Non-Submission, reject and skip further processing
#         if submission_type == "Non-Submission":
#             logging.info("Email classified as Non-Submission. Skipping processing.")
#             # Here you could implement any notification or rejection handling
#             # For example, moving the email to a different folder or sending a notification
#             return
        
#         # Continue processing if it's a valid submission
#         logging.info(f"Processing valid submission of type: {submission_type}")
        
#         # Get attachment folder paths from the metadata
#         attachment_folder = os.getenv("TEMP_FOLDER_PATH", "/tmp/") + "Attachments_Latest"
#         logging.info(f"Attachment folder path: {attachment_folder}")
#         attachment_paths = []
        
#         # Collect all attachment file paths
#         if os.path.exists(attachment_folder):
#             for filename in os.listdir(attachment_folder):
#                 file_path = os.path.join(attachment_folder, filename)
#                 if os.path.isfile(file_path):
#                     attachment_paths.append(file_path)
            
#             logging.info(f"Found {len(attachment_paths)} attachments to process")
            
#             # Process attachments using the integrated extraction pipeline
#             if attachment_paths:
#                 try:
#                     # Process attachments with the extraction pipeline from "Submission from images"
#                     extraction_results = process_email_attachments(metadata, attachment_paths)
#                     logging.info(f"Extraction results: {json.dumps(extraction_results, indent=2)}")
                    
#                 except Exception as e:
#                     logging.error(f"Error processing attachments with extraction pipeline: {str(e)}")
#                     import traceback
#                     logging.error(f"Traceback: {traceback.format_exc()}")
            
#             # Also run the original attachment processing for compatibility
#             try:
#                 process_attachments(metadata)
#             except Exception as e:
#                 logging.error(f"Error in original process_attachments: {str(e)}")
#         else:
#             logging.warning(f"Attachment folder not found: {attachment_folder}")
#     else:
#         logging.warning('No valid metadata found. Skipping attachment processing.')
    
#     logging.info('Azure Function timer trigger completed.')




# import logging
# import azure.functions as func
# import os
# import json
# from DemandClassifier import main_func
# from utils import process_attachments
# from extraction import process_email_attachments, submission_classifier, prepare_email_content, upload_mail_content

# app = func.FunctionApp()

# # Timer trigger: fetch emails via Graph API, process attachments/images, no blob/db logic
# @app.timer_trigger(schedule="0,30 * * * * *", arg_name="myTimer", run_on_startup=False, use_monitor=False)
# def timer_trigger(myTimer: func.TimerRequest) -> None:
#     logging.info('Azure Function timer trigger started.')
    
#     # Fetch latest email metadata using Graph API
#     metadata = main_func()
#     logging.info(f"Fetched metadata: {metadata}")
    
#     if metadata and isinstance(metadata, dict):
#         # Step 1: Always upload mail content regardless of submission type or attachments
#         try:
#             # Upload mail content
#             blob_url = upload_mail_content(metadata)
#             logging.info(f"Mail content uploaded to blob: {blob_url}")
#         except Exception as e:
#             logging.error(f"Error uploading mail content: {e}")
#             import traceback
#             logging.error(f"Traceback: {traceback.format_exc()}")
        
#         # Step 2: Prepare email content for classification
#         email_content = prepare_email_content(metadata)
        
#         # Step 3: Perform submission (LOB) classification
#         logging.info("Performing submission classification...")
#         submission_type = submission_classifier(email_content)
#         logging.info(f"Submission classification result: {submission_type}")
        
#         # Step 4: If Non-Submission, reject and skip further processing
#         if submission_type == "Non-Submission":
#             logging.info("Email classified as Non-Submission. Skipping further processing.")
#             # Here you could implement any notification or rejection handling
#             # For example, moving the email to a different folder or sending a notification
#             return
        
#         # Continue processing if it's a valid submission
#         logging.info(f"Processing valid submission of type: {submission_type}")
        
#         # Get attachment folder paths from the metadata
#         attachment_folder = os.getenv("TEMP_FOLDER_PATH", "/tmp/") + "Attachments_Latest"
#         attachment_paths = []
        
#         # Collect all attachment file paths
#         if os.path.exists(attachment_folder):
#             for filename in os.listdir(attachment_folder):
#                 file_path = os.path.join(attachment_folder, filename)
#                 if os.path.isfile(file_path):
#                     attachment_paths.append(file_path)
            
#             logging.info(f"Found {len(attachment_paths)} attachments to process")
            
#             # Process attachments using the integrated extraction pipeline
#             if attachment_paths:
#                 try:
#                     # Process attachments with the extraction pipeline from "Submission from images"
#                     extraction_results = process_email_attachments(metadata, attachment_paths)
#                     logging.info(f"Extraction results: {json.dumps(extraction_results, indent=2)}")
                    
#                 except Exception as e:
#                     logging.error(f"Error processing attachments with extraction pipeline: {str(e)}")
#                     import traceback
#                     logging.error(f"Traceback: {traceback.format_exc()}")
            
#             # Also run the original attachment processing for compatibility
#             try:
#                 process_attachments(metadata)
#             except Exception as e:
#                 logging.error(f"Error in original process_attachments: {str(e)}")
#         else:
#             logging.warning(f"Attachment folder not found: {attachment_folder}")
#     else:
#         logging.warning('No valid metadata found. Skipping attachment processing.')
    
#     logging.info('Azure Function timer trigger completed.')





import logging
import azure.functions as func
import os
import json
from DemandClassifier import main_func
from utils import process_attachments, upload_json_to_blob
from extraction import process_email_attachments, submission_classifier, prepare_email_content, upload_mail_content

# Function to upload metadata.json to blob storage
def upload_metadata_json(metadata):
    """Upload metadata.json to blob storage regardless of attachment status"""
    if "From" in metadata:
        folder_name = metadata["From"].split("@")[0] 
        date = metadata["Received Date"]
        time = metadata["Received Time"].replace(" IST", "").replace(":", "-")

    # Build folder name
        folder_name = f"{folder_name}_{date}_{time}"
        metadata_blob_name = f"{folder_name}/metadata.json"
        blob_url = upload_json_to_blob(metadata, metadata_blob_name)
        if blob_url:
            logging.info(f"Metadata uploaded to blob storage: {blob_url}")
        else:
            logging.warning("Failed to upload metadata to blob storage")
    else:
        logging.error("The 'From' field is missing in metadata. Cannot create folder in blob.")

app = func.FunctionApp()

# Timer trigger: fetch emails via Graph API, process attachments/images, no blob/db logic
@app.timer_trigger(schedule="0,30 * * * * *", arg_name="myTimer", run_on_startup=False, use_monitor=False)
def timer_trigger(myTimer: func.TimerRequest) -> None:
    logging.info('Azure Function timer trigger started.')
    
    # Fetch latest email metadata using Graph API
    metadata = main_func()
    logging.info(f"Fetched metadata: {metadata}")
    
    if metadata and isinstance(metadata, dict):
        # Step 1: Always upload mail content and metadata regardless of submission type or attachments
        try:
            # Upload mail content
            blob_url = upload_mail_content(metadata)
            logging.info(f"Mail content uploaded to blob: {blob_url}")
            
            # Upload metadata
            upload_metadata_json(metadata)
        except Exception as e:
            logging.error(f"Error uploading mail content or metadata: {e}")
            import traceback
            logging.error(f"Traceback: {traceback.format_exc()}")
        
        # Step 2: Prepare email content for classification
        email_content = prepare_email_content(metadata)
        
        # Step 3: Perform submission (LOB) classification
        logging.info("Performing submission classification...")
        submission_type = submission_classifier(email_content)
        logging.info(f"Submission classification result: {submission_type}")
        
        # Step 4: If Non-Submission, reject and skip further processing
        if submission_type == "Non-Submission":
            logging.info("Email classified as Non-Submission. Skipping further processing.")
            # Here you could implement any notification or rejection handling
            # For example, moving the email to a different folder or sending a notification
            return
        
        # Continue processing if it's a valid submission
        logging.info(f"Processing valid submission of type: {submission_type}")
        
        # Get attachment folder paths from the metadata
        attachment_folder = os.getenv("TEMP_FOLDER_PATH", "/tmp/") + "Attachments_Latest"
        attachment_paths = []
        
        # Collect all attachment file paths
        if os.path.exists(attachment_folder):
            for filename in os.listdir(attachment_folder):
                file_path = os.path.join(attachment_folder, filename)
                if os.path.isfile(file_path):
                    attachment_paths.append(file_path)
            
            logging.info(f"Found {len(attachment_paths)} attachments to process")
            
            # Process attachments using the integrated extraction pipeline
            if attachment_paths:
                try:
                    # Process attachments with the extraction pipeline from "Submission from images"
                    extraction_results = process_email_attachments(metadata, attachment_paths)
                    logging.info(f"Extraction results: {json.dumps(extraction_results, indent=2)}")
                    
                except Exception as e:
                    logging.error(f"Error processing attachments with extraction pipeline: {str(e)}")
                    import traceback
                    logging.error(f"Traceback: {traceback.format_exc()}")
            
            # Also run the original attachment processing for compatibility
            try:
                process_attachments(metadata)
            except Exception as e:
                logging.error(f"Error in original process_attachments: {str(e)}")
        else:
            logging.warning(f"Attachment folder not found: {attachment_folder}")
            
            # Even if no attachment folder, still upload metadata.json
            try:
                # Create a separate function to just upload the metadata.json without needing attachments
                upload_metadata_json(metadata)
            except Exception as e:
                logging.error(f"Error uploading metadata.json: {str(e)}")
    else:
        logging.warning('No valid metadata found. Skipping attachment processing.')
    
    logging.info('Azure Function timer trigger completed.')