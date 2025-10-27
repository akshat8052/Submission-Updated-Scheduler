import os
import logging
import requests
import base64
import pandas as pd
from bs4 import BeautifulSoup
from msal import ConfidentialClientApplication
from dotenv import load_dotenv
import re
from langchain_openai import AzureChatOpenAI, AzureOpenAIEmbeddings
from langchain.chains import create_retrieval_chain
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain_core.prompts import ChatPromptTemplate
from azure.storage.blob import BlobServiceClient
from langchain_community.vectorstores import DocArrayInMemorySearch
from datetime import datetime
import pytz

from azure.storage.blob import BlobServiceClient
import json
import os

# Load environment variables
load_dotenv()

# Azure App Credentials
CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")
# print("Client Secret:", CLIENT_SECRET)  # Debugging line to check if CLIENT_SECRET is loaded
logging.info(f"Client Secret: {CLIENT_SECRET}")  # Debugging line to check if CLIENT_SECRET is loaded

TENANT_ID = os.getenv("TENANT_ID")
USER_EMAIL = os.getenv("DEMAND_USER_EMAIL")

AUTHORITY = f"https://login.microsoftonline.com/{TENANT_ID}"
SCOPES = ["https://graph.microsoft.com/.default"]
MAIL_API_URL = f"https://graph.microsoft.com/v1.0/users/{USER_EMAIL}/mailFolders/inbox/messages"

# Directories and files
ATTACHMENT_DIR = os.getenv("TEMP_FOLDER_PATH", "/tmp/")+"attachments"
LATEST_ATTACHMENT_DIR = os.getenv("TEMP_FOLDER_PATH", "/tmp/")+"Attachments_Latest"
os.makedirs(ATTACHMENT_DIR, exist_ok=True)
os.makedirs(LATEST_ATTACHMENT_DIR, exist_ok=True)

EXCEL_FILE_PATH = os.getenv("TEMP_FOLDER_PATH", "/tmp/")+"attachments/Email_Data.xlsx"
CLASSIFIED_EXCEL_FILE = os.getenv("TEMP_FOLDER_PATH", "/tmp/")+"attachments/Classified_Email_Data.xlsx"
LATEST_METADATA_FILE = os.path.join(LATEST_ATTACHMENT_DIR, "Latest_Attachments_Metadata.xlsx")

# Logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Storage
email_records = []
latest_email_records = []

# Classification Rules
# RULES = [
#     {"to": "aditya.kumar@mycloudnas.online", "cc": "bankslob@mycloudnas.online", "keywords": {"banks"}, "team": "A"},
#     {"to": "aditya.kumar@mycloudnas.online", "cc": "energylob@mycloudnas.online", "keywords": {"energy"}, "team": "B"},
#     {"to": "aditya.kumar@mycloudnas.online", "cc": "specialitylines@mycloudnas.online", "keywords": {"speciality","lines"}, "team": "C"}
# ]
RULES = [
    {"to": "albert.roberto@mycloudnas.online", "cc": "specialitylines@mycloudnas.online", "keywords": {"speciality lines"}, "team": "A"},
    {"to": "albert.roberto@mycloudnas.online", "cc": "personallines@mycloudnas.online", "keywords": {"personal lines"}, "team": "B"},
    {"to": "albert.roberto@mycloudnas.online", "cc": "commerciallines@mycloudnas.online", "keywords": {"commercial lines"}, "team": "C"}
 
    # {"to": "albert.roberto@mycloudnas.online", "cc": "specialitylines@mycloudnas.online", "keywords": {"speciality lines"}, "team": "A"},
    # {"to": "albert.roberto@mycloudnas.online", "cc": "energylob@mycloudnas.online", "keywords": {"submission"}, "team": "B"},
    # {"to": "albert.roberto@mycloudnas.online", "cc": "specialitylines@mycloudnas.online", "keywords": {"speciality lines"}, "team": "C"}
]

# Reset latest attachments and metadata
def reset_latest_folder():
    for filename in os.listdir(LATEST_ATTACHMENT_DIR):
        file_path = os.path.join(LATEST_ATTACHMENT_DIR, filename)
        if os.path.isfile(file_path):
            os.remove(file_path)
    if os.path.exists(LATEST_METADATA_FILE):
        os.remove(LATEST_METADATA_FILE)
        logging.info("Cleared previous latest metadata and attachments.")

# Auth
def get_access_token():
    logging.info(f"Client Secret in get_access_token: {CLIENT_SECRET}")  # Debugging line to check if CLIENT_SECRET is passed correctly
    app = ConfidentialClientApplication(CLIENT_ID, authority=AUTHORITY, client_credential=CLIENT_SECRET)

    logging.info("Acquiring new access token...")
    token = app.acquire_token_for_client(scopes=SCOPES)
    logging.info(f"Access token acquired.: {token}")
    if "access_token" not in token:
        logging.error(f"Failed to acquire token: {token.get('error_description')}")
    return token.get("access_token", None)

# Download attachment
def download_attachment(attachment, email_index, also_copy_to_latest=True):
    if attachment.get("@odata.type") == "#microsoft.graph.fileAttachment":
        filename = attachment.get("name")
        content_bytes = attachment.get("contentBytes")
        if content_bytes:
            file_data = base64.b64decode(content_bytes)
            safe_filename = f"{email_index}_{filename}".replace(" ", "_")

            filepath = os.path.join(ATTACHMENT_DIR, safe_filename)
            with open(filepath, "wb") as f:
                f.write(file_data)

            latest_path = None
            if also_copy_to_latest:
                latest_path = os.path.join(LATEST_ATTACHMENT_DIR, safe_filename)
                with open(latest_path, "wb") as f:
                    f.write(file_data)

            return filepath, latest_path
    return None, None

# Get all attachments
def get_attachments(message_id, headers, email_index, also_copy_to_latest=False):
    attachment_url = f"https://graph.microsoft.com/v1.0/users/{USER_EMAIL}/messages/{message_id}/attachments"
    response = requests.get(attachment_url, headers=headers)
    attachment_paths = []
    latest_attachment_paths = []

    if response.status_code == 200:
        attachments = response.json().get("value", [])
        for att in attachments:
            filepath, latest_path = download_attachment(att, email_index, also_copy_to_latest)
            if filepath:
                # blob_service_client = BlobServiceClient.from_connection_string(os.getenv("AZURE_STORAGE_CONNECTION_STRING"))
                # push_attachment_to_blob(filepath, "attachments", blob_service_client, container_name=os.getenv("AZURE_BLOB_CONTAINER_NAME"))
                attachment_paths.append(filepath)
            if latest_path:
                latest_attachment_paths.append(latest_path)
    return ", ".join(attachment_paths), ", ".join(latest_attachment_paths)

# Get all attachments, with original filename mapping
def get_attachments_with_filenames(message_id, headers, email_index, also_copy_to_latest=False):
    attachment_url = f"https://graph.microsoft.com/v1.0/users/{USER_EMAIL}/messages/{message_id}/attachments"
    response = requests.get(attachment_url, headers=headers)
    attachment_paths = []
    latest_attachment_paths = []
    original_filenames = {}  # Dictionary to store original filename mapping

    if response.status_code == 200:
        attachments = response.json().get("value", [])
        for att in attachments:
            filepath, latest_path = download_attachment(att, email_index, also_copy_to_latest)
            if filepath:
                # Store the original filename for this path
                original_filenames[filepath] = att.get("name")
                attachment_paths.append(filepath)
            if latest_path:
                latest_attachment_paths.append(latest_path)
    
    # Return the paths and the original filename mapping
    return ", ".join(attachment_paths), ", ".join(latest_attachment_paths), original_filenames


# Strip HTML
def extract_plain_text(html_content):
    soup = BeautifulSoup(html_content, "html.parser")
    return soup.get_text(separator="\n", strip=True)

# Check for duplicates
def is_email_in_excel(email_id):
    if os.path.exists(EXCEL_FILE_PATH):
        df = pd.read_excel(EXCEL_FILE_PATH, engine="openpyxl")
        return email_id in df.get("Email ID", [])
    return False




# Upload attachments to Azure Blob Storage
def upload_attachments_to_blob(email_id, sender_email, timestamp, attachments_paths, original_filenames=None):
    """
    Upload email attachments to Azure Blob Storage in a folder named after the sender's email.
    
    Args:
        email_id (str): The unique ID of the email
        sender_email (str): The sender's email address to use as folder name
        attachments_paths (str): Comma-separated list of attachment file paths
        original_filenames (dict): Dictionary mapping local paths to original filenames
    
    Returns:
        list: List of URLs of the uploaded attachments
    """
    try:
        # Get Azure Blob Storage connection string from environment variables
        connection_string = os.getenv("AZURE_BLOB_CONNECTION_STRING")
        container_name = os.getenv("AZURE_CONTAINER_NAME")
        
        if not connection_string or not container_name:
            logging.error(f"Connection string: {connection_string}, Container name: {container_name}")
            logging.error("Azure Blob Storage connection string or container name not set")
            return []
        
        # Create folder name based on sender email
        folder_name = sender_email.split("@")[0] + "_" + timestamp.replace(" IST", "").replace(":", "-")
        
        # Initialize the BlobServiceClient
        blob_service_client = BlobServiceClient.from_connection_string(connection_string)
        container_client = blob_service_client.get_container_client(container_name)
        
        uploaded_urls = []
        
        # Process each attachment path
        if attachments_paths:
            for path in attachments_paths.split(", "):
                if os.path.exists(path):
                    # Use original filename if available, otherwise use the local filename
                    if original_filenames and path in original_filenames:
                        file_name = original_filenames[path]
                    else:
                        file_name = os.path.basename(path)
                    
                    # Create a blob name that includes the folder structure
                    blob_name = f"{folder_name}/{file_name}"
                    
                    # Create a blob client and upload the file
                    blob_client = container_client.get_blob_client(blob_name)
                    
                    with open(path, "rb") as data:
                        blob_client.upload_blob(data, overwrite=True)
                    
                    uploaded_urls.append(blob_client.url)
                    logging.info(f"Uploaded {file_name} to {folder_name} folder in blob storage")
                else:
                    logging.warning(f"File path does not exist: {path}")
        else:
            logging.info("No attachment paths provided")
        
        return uploaded_urls
    
    except Exception as e:
        logging.error(f"Error uploading attachments to blob: {str(e)}")
        import traceback
        logging.error(f"Traceback: {traceback.format_exc()}")
        return []



# Get and process emails
def get_outlook_emails():
    try:
        # Step 1: Reset latest folder
        reset_latest_folder()

        # Step 2: Get access token
        access_token = get_access_token()
        if not access_token:
            logging.error("Failed to get access token.")
            return

        # Step 3: Prepare headers and fetch emails
        headers = {"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"}
        params = {"$top": 50, "$orderby": "receivedDateTime DESC"}
        response = requests.get(MAIL_API_URL, headers=headers, params=params)

        if response.status_code != 200:
            logging.error(f"Error fetching emails: {response.status_code} {response.text}")
            return

        emails = response.json().get("value", [])
        if not emails:
            logging.info("No emails found.")
            return

        # Step 4: Load existing Email IDs from Email_Data.xlsx
        if os.path.exists(EXCEL_FILE_PATH):
            existing_df = pd.read_excel(EXCEL_FILE_PATH, engine="openpyxl")
            existing_email_ids = set(existing_df["Email ID"].astype(str))
        else:
            existing_df = pd.DataFrame()
            existing_email_ids = set()

        email_records = []
        classified_data = []
        latest_email_records = []

        # Step 5: Process new emails only
        for i, email in enumerate(emails, start=1):
            email_id = email.get("id")
            if email_id in existing_email_ids:
                continue  # Skip already processed emails

            # Basic metadata
            subject = email.get("subject", "")
            body_html = email.get("body", {}).get("content", "")
            body_text = extract_plain_text(body_html)
            sender = email.get("from", {}).get("emailAddress", {}).get("address", "")

            # Timestamp conversion
            received_dt = datetime.strptime(email.get("receivedDateTime", ""), "%Y-%m-%dT%H:%M:%S%z")
            ist_dt = received_dt.astimezone(pytz.timezone("Asia/Kolkata"))
            received_date = ist_dt.strftime("%Y-%m-%d")
            received_time = ist_dt.strftime("%H:%M:%S") + " IST"

            # Recipients
            to_recipients = ", ".join([r["emailAddress"]["address"] for r in email.get("toRecipients", [])])
            cc_recipients = ", ".join([r["emailAddress"]["address"] for r in email.get("ccRecipients", [])])
            bcc_recipients = ", ".join([r["emailAddress"]["address"] for r in email.get("bccRecipients", [])])

            # Classification
            # team = classify_email(to_recipients, cc_recipients, subject)
            # submission_result = classify_email_submission(body_text, subject, team)
            # logging.info(f"Classified email {email_id} from {sender} as {submission_result} for team {team}")
            # if "submission mail" in submission_result.lower():
            #     logging.info(f"Classified email {sender} as {submission_result} for team {team}")
            #     lob_result = classify_mail_type(body_text, subject)
            #     update_lob_mapping(lob_result, sender, os.getenv("AZURE_BLOB_CONNECTION_STRING"), os.getenv("AZURE_CONTAINER_NAME"))
            #     logging.info(f"Classified email {sender} as {submission_result} for team {team} with LOB {lob_result}")
            # else:
            #     # Delete user from lob
            #     update_lob_mapping(lob="", 
            #                        user=sender, 
            #                        connection_string=os.getenv("AZURE_BLOB_CONNECTION_STRING"), 
            #                        container_name=os.getenv("AZURE_CONTAINER_NAME"))
            




            # Download normal attachments (not yet latest)
            attachments, _, original_filenames = get_attachments_with_filenames(email_id, headers, email_index=i, also_copy_to_latest=False)
            if attachments:
                # Upload attachments to Azure Blob Storage
                timestamp=f"{received_date}_{received_time.replace(':', '-')}"
                attachment_urls = upload_attachments_to_blob(email_id, sender, timestamp, attachments, original_filenames)
                if attachment_urls:
                    logging.info(f"Uploaded attachments for email {email_id}: {attachment_urls}")
                else:
                    logging.warning(f"No attachments uploaded for email {email_id}")

            # Email Record for master log
            email_records.append({
                "Email ID": email_id,
                "From": sender,
                "To": to_recipients,
                "CC": cc_recipients,
                "BCC": bcc_recipients,
                "Subject": subject,
                "Body": body_text,
                "Received Date": received_date,
                "Received Time": received_time
            })

            # Classification Data
            classified_data.append({
                "Email ID": email_id,
                "To": to_recipients,
                "CC": cc_recipients,
                "BCC": bcc_recipients,
                "Subject": subject,
                "Body": body_text,
                # "Attachment Name": attachments,
                # "Team": team,
                # "Submission Result": submission_result,
                "DATE": received_date,
                "TIME": received_time
            })

            # Latest Submission Handling
            # if submission_result == "Submission Mail":
            _, latest_attachments = get_attachments(email_id, headers, email_index=i, also_copy_to_latest=True)

            latest_email_records.append({
                "From": sender,
                "To": to_recipients,
                "CC": cc_recipients,
                "BCC": bcc_recipients,
                "Subject": subject,
                "Body": body_text,
                "Received Date": received_date,
                "Received Time": received_time,
                # "Team": team,
                # "Submission Result": submission_result
            })

        # Step 6: Append to Email_Data.xlsx
        if email_records:
            new_email_df = pd.DataFrame(email_records)
            combined_email_df = pd.concat([existing_df, new_email_df], ignore_index=True)
            combined_email_df.to_excel(EXCEL_FILE_PATH, index=False, engine="openpyxl")
            logging.info("Updated Email_Data.xlsx")

        # Step 7: Append to Classified_Email_Data.xlsx
        if classified_data:
            classified_df = pd.DataFrame(classified_data)
            if os.path.exists(CLASSIFIED_EXCEL_FILE):
                existing_classified_df = pd.read_excel(CLASSIFIED_EXCEL_FILE, engine="openpyxl")
                combined_classified_df = pd.concat([existing_classified_df, classified_df], ignore_index=True)
            else:
                combined_classified_df = classified_df
            combined_classified_df.to_excel(CLASSIFIED_EXCEL_FILE, index=False, engine="openpyxl")
            logging.info("Updated Classified_Email_Data.xlsx")

        # Step 8: Save Latest_Submission_Metadata.xlsx
        if latest_email_records:
            pd.DataFrame(latest_email_records).to_excel(LATEST_METADATA_FILE, index=False, engine="openpyxl")
            logging.info("Saved latest submission emails.")
        else:
            logging.info("No new submission emails found.")
        logging.info("Email processing complete.")
    except Exception as e:
        logging.error(f"Error in get_outlook_emails: {e}")
        import traceback
        logging.error(f"Traceback: {traceback.format_exc()}")

# Team classification
def classify_email(to, cc, subject):
    to, cc, subject = to.lower(), cc.lower(), subject.lower()
    subject_keywords = set(re.findall(r'\w+', subject))
    for rule in RULES:
        if to == rule["to"] and cc == rule["cc"]:
            # and rule["keywords"] & subject_keywords:
            return rule["team"]
    return "Unknown Classification"

# Prompt setup
message = """
    You are an AI email classification assistant. Your job is to classify whether an email is a "Submission Mail" or "Non Submission Mail" using contextual understanding of the content.

    Use the following inputs:
    - Email Body: {body}
    - Subject: {Subject}
    - Team: {team}
    - Question: {input}

    Classification Objective:
    Determine whether this email represents a submission related to **insurance business activity** — such as initiating, requesting, or responding to:
    - **New policies** or policy endorsements
    - **Claims** (filing, updates, disputes, approvals)
    - **Coverage requests**, quotations, underwriting actions
    - **Client onboarding**, documentation, agreements, binders, or formal proposals

    Interpret the email **contextually**, not just by keyword matching. Look for phrases, intentions, or tone indicating that the sender or receiver is engaging in the **insurance submission process**.

    Classification Criteria:
    1. If the email involves **any actionable step** in the insurance domain — including but not limited to starting a process, requesting approvals, submitting documents, or referencing formal submissions related to **policies or claims**, classify it as **"Submission Mail"**.
    2. If the content is **informational, marketing-based, or administrative** and does **not reflect insurance submission intent**, classify as **"Non Submission Mail"**.

    Important Notes:
    - Focus only on the **email body** and the **subject** for signals.
    - Do not classify based solely on a single keyword. Understand the **intent and context**.
    - The output must strictly be either **"Submission Mail"** or **"Non Submission Mail"** — no other response is allowed. Don't give any reasoning.

    Now, based on the provided content and these rules, classify this email.

"""
prompt_new = ChatPromptTemplate.from_messages([
    ("system", message),
    ("human", "Context: {context}\nEmail Body: {body}\nSubject: {Subject}\nTeam: {team}\nQuestion: {input}"),
])


# AI classifier
def initialize_openai():
    try:
        embeddings = AzureOpenAIEmbeddings(
            model="text-embedding-ada-002",
            api_key=os.getenv("AZURE_OPENAI_API_KEY"),
            api_version="2023-05-15",
            azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT")
        )
        llm = AzureChatOpenAI(
            deployment_name="gpt-4o",
            api_key=os.getenv("AZURE_OPENAI_API_KEY"),
            api_version=os.getenv("AZURE_OPENAI_API_VERSION"),
            azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
            model_name="gpt-4o",
            temperature=0.1
        )
        retriever = DocArrayInMemorySearch.from_documents([], embeddings).as_retriever()
        question_answer_chain = create_stuff_documents_chain(llm, prompt_new)
        global chain
        chain = create_retrieval_chain(retriever, question_answer_chain)
    except Exception as e:
        logging.error(f"Error initializing OpenAI: {e}")
        

# Updated classify_email_submission function with context and debugging
def classify_email_submission(body, Subject, team, question="Is this a submission mail or non submission mail?"):
    try:
        print("Classifying email with body:", body[:100], "Subject:", Subject, "Team:", team, "Question:", question)
        
        # Prepare the input data with context
        input_data = {
            "context": "Insurance email classification context",
            "body": body, 
            "Subject": Subject, 
            "team": team, 
            "input": question
        }
        
        # Format and print the prompt with actual values for debugging
        formatted_prompt = prompt_new.format_prompt(**input_data)
        
        print("\n" + "="*80)
        print("FORMATTED PROMPT TO BE SENT TO LLM:")
        print("="*80)
        for message in formatted_prompt.to_messages():
            print(f"Role: {message.type}")
            # print(f"Content: {message.content}")
            print("-" * 40)
        print("="*80 + "\n")
        
        # Invoke the chain with the input data
        response = chain.invoke(input_data)
        
        print("Response received:", response.get("answer", "No response"))
        return response.get("answer", "No response")
        
    except Exception as e:
        logging.error(f"Error classifying email: {e}")
        import traceback
        logging.error(f"Traceback: {traceback.format_exc()}")
        return "Error in classification"

def main_func():
    try:
        initialize_openai()
        get_outlook_emails()
        logging.info("Run complete.")

        # Check if the latest metadata file exists
        if os.path.exists(LATEST_METADATA_FILE):
            # Read the metadata file
            latest_df = pd.read_excel(LATEST_METADATA_FILE, engine="openpyxl")

            # Check if the file has at least one row
            if not latest_df.empty:
                # Convert the first row to a dictionary
                first_row_dict = latest_df.iloc[0].to_dict()
                logging.info(f"First row of latest metadata: {first_row_dict}")
                return first_row_dict
            else:
                logging.info("No data found in the latest metadata file.")
                return {}
        else:
            logging.info("Latest metadata file does not exist.")
            return {}
    except Exception as e:
        logging.error(f"Unexpected error: {e}")
        return {}


def classify_mail_type(body_text, subject):
    """
    pass
    # Classify the email into Commercial Auto or Professional Liability based on content analysis.
    
    Args:
        body_text (str): The email body text
        subject (str): The email subject
    
    Returns:
        str: Classification result - "CommercialAuto", "ProfessionalLiability", or "Other"
    """
    # Convert to lowercase for case-insensitive matching
    text_to_analyze = (body_text.lower() + " " + subject.lower())
    
    # Commercial Auto keywords - comprehensive set
    commercial_auto_keywords = [
        # Vehicle identifiers
        "vin", "vehicle identification number", "license plate", 
        
        # Vehicle types
        "vehicle", "auto", "automobile", "car", "truck", "fleet", "trailer", 
        "commercial vehicle", "motor vehicle", "bus", "van", "pickup", "semi", 
        "tractor", "suv", "delivery vehicle", "rental vehicle",
        
        # Driver related
        "driver", "operator", "chauffeur", "cdl", "driving record", "mvr",
        "motor vehicle record", "driver's license",
        
        # Coverage terms
        "auto liability", "physical damage", "collision", "comprehensive", 
        "hired auto", "non-owned auto", "garagekeepers", "auto fleet",
        "commercial auto policy", "business auto", "trucking", "transportation",
        "motor carrier", "garage policy", "auto insurance",
        
        # Risk/claim terms
        "accident", "auto claim", "vehicle damage", "auto accident", 
        "traffic", "at-fault", "auto injury", "usdot", "dot number", 
        "fmcsa", "cargo", "vehicle schedule", "schedule of vehicles",
        
        # Business usage
        "delivery", "transport", "hauling", "freight", "logistics", 
        "last mile", "rideshare", "shuttle service", "taxi", "livery"
    ]
    
    # Professional Liability keywords - comprehensive set
    professional_liability_keywords = [
        # General PL terms
        "professional liability", "e&o", "errors and omissions", "malpractice", 
        "negligence", "services provided", "professional services", "consulting", 
        "advisor", "professional indemnity", "professional coverage",
        
        # Professions
        "accountant", "architect", "consultant", "attorney", "lawyer", 
        "physician", "doctor", "engineer", "designer", "real estate", 
        "broker", "agent", "financial advisor", "therapist", "counselor", 
        "it consultant", "software developer", "healthcare provider",
        
        # Coverage terms
        "claims made", "prior acts", "retroactive date", "tail coverage", 
        "extended reporting", "breach of duty", "fiduciary", "professional misconduct",
        "duty of care", "standard of care", "professional standards",
        
        # Risk/service terms 
        "professional advice", "client service", "failure to perform",
        "breach of contract", "representation", "expert", "consultation", 
        "misrepresentation", "certification", "license", "accreditation",
        
        # Claim scenarios
        "client complaint", "service failure", "professional error", 
        "missed deadline", "incorrect advice", "consulting error", 
        "service negligence", "failed service"
    ]
    
    # Count keyword matches for each category
    ca_matches = sum(1 for keyword in commercial_auto_keywords if keyword in text_to_analyze)
    pl_matches = sum(1 for keyword in professional_liability_keywords if keyword in text_to_analyze)
    
    # Determine classification based on keyword frequency
    if ca_matches > pl_matches and ca_matches > 0:
        return "Commercial Auto"
    elif pl_matches > ca_matches and pl_matches > 0:
        return "Professional Liability"
    else:
        return "Other"





def update_lob_mapping(lob, user, connection_string, container_name, blob_name="lob_mapping.json"):
    # Connect to Azure Blob Storage
    logging.info(f"Updating LOB mapping for {lob} with user {user}")
    if lob.lower() == "other":
        print("LOB is 'other'; no update performed.")
        return
    blob_service_client = BlobServiceClient.from_connection_string(connection_string)
    blob_client = blob_service_client.get_blob_client(container=container_name, blob=blob_name)

    try:
        blob_data = blob_client.download_blob().readall()
        lob_mapping = json.loads(blob_data.decode('utf-8'))
    except Exception:
        # File does not exist, create new mapping
        lob_mapping = {}
 
    # Remove user from any previous LOBs
    logging.info(f"Removing user {user} from previous LOBs if any.")
    for key in list(lob_mapping.keys()):
        if user in lob_mapping[key]:
            logging.info(f"Removing user {user} from LOB {key}.")
            lob_mapping[key].remove(user)
            # Remove LOB if empty after removal
            if not lob_mapping[key]:
                del lob_mapping[key]
 
    if lob != "":
        # Add user to the new LOB
        logging.info(f"Adding user {user} to LOB {lob}.")
        if lob in lob_mapping:
            if user not in lob_mapping[lob]:
                lob_mapping[lob].append(user)
        else:
            lob_mapping[lob] = [user]

    # Upload the updated JSON
    logging.info(f"Uploading updated LOB mapping to blob storage.")
    updated_json = json.dumps(lob_mapping, indent=2)
    blob_client.upload_blob(updated_json, overwrite=True)

    print(f"LOB mapping updated: {lob} -> {user}")
 




# if __name__ == "__main__":
#     main_func()
