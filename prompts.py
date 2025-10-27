# """
# Prompts for the document classification and extraction pipeline
# """

# # ---- High‑level system prompts ----
# submission_classification_system_prompt = (
#     "You are a highly experienced insurance underwriter and document analyst specializing in analyzing "
#     "submission emails (terrorism, war & hull, general liability) in the London Market."
# )

# doctype_classification_system_prompt = (
#     "You are a highly experienced insurance document analyst specializing in analyzing insurance documents "
#     "and schedules in the London Market."
# )

# extraction_system_prompt = (
#     "You are a highly experienced insurance underwriter and document analyst specializing in analyzing "
#     "insurance submissions, slips, skeleton risks, and SOV schedules. Extract only explicitly stated data."
# )

# # ---- Queries used for RAG or targeted retrieval ----
# skeleton_query = """Assured Name, Risk Location, Inception Date, Expiry Date, Broker Name, Broker Email, Underwriter,
# Line of Business Group, Trade Sector, Internal Risk Reference, Submission Status, New/Renewal Indicator"""

# slip_query = """Arch Policy Reference EEA NON-EEA
# UMR Unique Market Reference Master Reference
# Written Date PERIOD Written AAL
# Written Line % section-wise participation
# Legal Entity Syndicate Participant Role
# Risk Code Split Risk Code ALLOCATION OF PREMIUM TO CODING premium allocation TO, GT, RS, WL SETTLEMENT INFORMATION
# Slip Leader Lead Underwriter Section Leader BUREAU(X) LEADER(S)
# Business Activities insured operations interest summary INTEREST(S)
# Section Names coverage headings TRADING EEA Non EEA HULL & MACHINERY BUILDER'S RISK
# GWP 100% Gross Written Premium BLENDED PREMIUM
# Limit 100% SUM (RE)INSURED/LIMIT EXCESS LIMIT EXCESS LIMIT HERON
# Attachment Point Excess Point
# Deductibles SIR Self-Insured Retention Coverage deductible Moral Damages Material Damage (Actual) or Constructive Total Loss
# Cyber Clause LMA5402 cyber exclusion inclusion
# Sanctions Clause JH2010/009 LMA3100 Sanction Limitation and Exclusion Sanction Limitation Clause
# ---"""

# # ---------------------------------------------------------------------------
# # Submission (Line of Business) Classification Prompt
# # Categories inferred from screenshots: Terrorism, Hull and War, General Liability, Non-Submission
# # ---------------------------------------------------------------------------
# submission_classification_prompt_template = """
# ## Categories for Classification:

# **Category 1: Terrorism**
# - Typically covers risks related to terrorism, sabotage, political violence, strikes, riots, civil commotion, or looting.
# - You might see references to terrorism-related organizations or clauses, or any coverage related to terrorism risks.
# - **Coverage details:** Covers physical damage and business interruption from terrorist acts, sabotage, political violence, strikes, riots.

# **Category 2: Hull and War**
# - Usually involves marine or aviation hull risks and war perils like piracy, military actions, or hostile acts.
# - Watch for mentions of vessels, aircraft, hull values, or marine/aviation war clauses.
# - Look for indications of physical loss or damage caused by war or hostile events impacting marine or aviation assets.
# - **Coverage details:** Protects marine and aviation hulls against war perils including hostile military actions, piracy, capture, and war risks.

# **Category 3: General Liability**
# - Generally covers third-party liability risks such as bodily injury, property damage, public/products liability, or employer's liability.
# - Might include references to legal defense, indemnity, lawsuits, or settlements linked to third-party claims.
# - Look for limits of liability or aggregate/per occurrence limits specific to liability insurance.
# - **Coverage details:** Provides third-party liability coverage for bodily injury, property damage, personal and advertising injury, including products.

# **Category 4: Non-Submission**
# - Use this category if the email or document doesn't appear to contain insurance submissions, policy wording, coverage details, clause titles.
# - This might include meeting invites, calendar notifications, personal or unrelated correspondence, or emails with only attachments but no obvious submission text.
# - Be aware most emails will likely contain some form of submission, so apply this category only if there's genuinely no insurance-related submission content.

# ## Instructions
# 1. Analyze the entire email thread carefully, including To, From, CC, Subject, and body fields in detail.
# 2. Additionally, analyze attachment names along with the email content for classification clues.
# 3. Pay close attention to policy wording, clause titles, section headers, and coverage details.
# 4. Identify explicit and implicit references, keywords, synonyms, and typical market terminology related to each category (Terrorism, War & Hull, Liability).
# 5. You can also check coverage details mentioned within the email content to support your classification.
# 6. Classify the email strictly into the single most appropriate category based on your detailed analysis.

# ## Format Your Response
# Return your answer in strict JSON format only as shown below:
# {{ "Classification": "[Terrorism/War and Hull/General Liability/Non-Submission]" }}

# Do not add any extra text or explanation.

# ## Examples
# Terrorism: "Coverage against acts of terrorism, sabotage, or political violence."
# War and Hull: "War Risks Clause, hull coverage for marine vessels, piracy, or war perils."
# General Liability: "Public liability for bodily injury, property damage, or employer's liability section."
# Non-Submission: "Meeting invite for project discussion.", "No insurance content found.", "Personal greeting email."

# ## Final Output Template
# {{ "Classification": "[Terrorism/War and Hull/General Liability/Non-Submission]" }}

# ---
# Below is the email content to be used for classification:

# {email_content}
# """

# # ---------------------------------------------------------------------------
# # Doctype Classification Prompt Template (attachments / documents)
# # ---------------------------------------------------------------------------
# doctype_classification_prompt_template = """
# You are an expert insurance document analyst and your role is to classify the document or email below into one of the following categories:

# **Skeleton Risk**:
# - A preliminary submission used for early-stage underwriting. It captures essential, high-level coverage details for initial quoting.
# - Look for fields and keywords: Assured Name, Risk Location, Inception/Expiry Date, Broker Details, Underwriter, Line of Business, Trade Sector.

# **Slip Risk**:
# - A formal, market-standard insurance or **reinsurance** contract document used to bind coverage with detailed terms, conditions, limits.
# - There might be one or multiple insurers.
# - Look for fields and keywords: Written Date/Line %, Legal Entity, Risk Code, Slip Leader, Business Description, Currency, Sections, Limits.

# **SOV (Statement of Values)**:
# - A structured schedule listing insured properties or assets, mostly in Excel. Used for valuation, modeling, and exposure analysis.
# - Look for fields and keywords: Location Addresses, TIV or Replacement Value, Construction Type, Occupancy, Year Built, Number of Stories.

# **Others**:
# - Content that does not fit any of the above types. Examples: internal communications, general queries, marketing materials, drafts, or non‑insurance documents.

# # Instructions:
# 1. Analyze the document content carefully. Look for explicit definitions, structural clues, and contextual phrases.
# 2. The input data might be a submission email, excel data in pipe-separated format with sheet names or text content is in page-wise markdown.
# 3. Evaluate the input structure, terminology, and layout. Use clues from tables, headers, key phrases, and even the filename.
# 4. Only classify as **"Others"** if:
#    - None of the definitions, fields, or coverage details clearly match any category.
#    - The document is off-topic, not insurance-related, or is incomplete/irrelevant.

# # Input Content:
# {document_content}

# # Classification Output
# Respond in **strict JSON only**:
# {{ "Classification": "[Slip Risk/Skeleton Risk/SOV/Others]" }}
# """

# # ---------------------------------------------------------------------------
# # Extraction Prompt Template
# # ---------------------------------------------------------------------------
# extraction_prompt_template = """
# You are an expert at extracting key fields from submission emails and insurance-related documents.
# You will be provided with the email content and the attachment content for a submission of an insurance related documents.

# The **email content** contains metadata such as CC, To, From, Subject, Body, and a list of attachments.
# The **attachment content** may be in one of the following formats:
# - **Textual content**: page-wise markdown format (as extracted from PDF or Word).
# - **Tabular content**: pipe-separated values with sheet names (as extracted from Excel).
# The attachment content may or may not be present but email content will always be present.

# You must extract data only from the provided content. **Do not infer or fabricate values.**

# ## Below are the list of fields to be extracted with their description details:
# {fields_description}

# ## Instructions for Extraction
# - **Extract data only from the provided email and attachment content. Do not guess or make assumptions.**
# - If a field is **explicitly stated or clearly referenced**, extract the exact value.
# - If a field is **not present or cannot be confidently determined**, return:
#   - `"value": "Not Present"`
#   - `"confidence": "0%"`
# - For all extracted fields, assign a **confidence level** based on clarity and directness of match (e.g., exact match: 95–100%, inferred but clear: 70–85%, ambiguous: 40–60%, weak: 10–25%, not present: 0%).

# ## Self-Assessment of Extracted Fields:
# After extracting the value, self-assess the accuracy and reliability of the extraction. Provide a confidence score on a scale of 0 to 100:
# - 85–99: The extracted value matches exactly with the clear context provided.
# - 70–84: The extracted value appears correct, but there are minor ambiguities or the context is somewhat unclear.
# - 50–69: The extracted value is plausible, but the context is vague or partially missing, leading to moderate confidence.
# - 25–49: The extracted value is highly uncertain due to poor context, conflicting information, or significant ambiguity.
# - 1–24: The extracted value is likely incorrect, and the context provides little to no support for the extraction.
# - 0: The value is not present or cannot be determined from the context.

# AVOID OVERESTIMATION: Be cautious not to overestimate your confidence. If there is any doubt or ambiguity, reflect it in the score.
# **Note: The confidence score is critical for deciding on manual reviews. Ensure the scores accurately reflect your certainty.**

# ## Response Format
# Return a **strict JSON object**, where each field key maps to a nested object with:
# {{
#   "Field Name": {{
#     "value": "Extracted content or 'Not Present'",
#     "confidence": "Percentage string e.g., '85%'"
#   }}
# }}

# # Email Content:
# {email_content}

# # Attachment Content:
# {attachment_content}
# """

# # ---------------------------------------------------------------------------
# # Field Description Blocks (used depending on document type)
# # ---------------------------------------------------------------------------

# skeleton_fields_description = """
# 1. **Assured Name**: Full legal name of the insured entity (also referred to as "Assured" or "Insured").
# 2. **Risk Location / Territory**: Geographic area or country where the risk is situated or covered.
#    - Check for keyword like 'situation' or 'address' to extract this field
# 3. **Inception Date**: Start date of the policy or effective coverage (format: DD/MM/YYYY).
#    - Check for 'Period' or Date keyword for Inception Date.
# 4. **Expiry Date**: End date of the policy or termination of coverage (format: DD/MM/YYYY).
#    - For this refer to period of the policy and then decide the expiry date.
#    - Example: If start date or inception date is 12/03/2020 and period is 12 months then Expiry date would be 11/03/2021.
#    - Note: The period might be any number of months or a (start and end Date both together). Accordingly you have calculate Expiry Date.
# 5. **Internal Risk Reference**: Unique internal reference code used by the insurer or broker.
# 6. **Broker**: Name of the brokerage firm placing the risk.
#    - Analyze the email content carefully to get broker information. The broker name and details might present in signature of a email body.
# 7. **Broker Name**: Full name of the individual broker or main point of contact.
# 8. **Broker Email Address**: Email address of the broker or placing contact.
# 9. **Underwriter**: Name of the underwriter or underwriting team responsible.
#    - Check for keyword like "Underwriter" or refer to Recipient Name ("To:" in email body)
# 10. **Line of Business Group**: High-level insurance category (e.g., Terrorism, Property, Marine, Casualty).
# 11. **Trade Sector**: The business or industry classification of the insured (e.g., Construction, Retail, Hotels, Parks).
# 12. **Status**: The current stage of the email, The value for this field will be either **SUBMISSION** or **RESUBMISSION**.
#    - Refer to the email subject and look for keywords like 'RE:' indicating a resubmission.
#    - If the email content has previous mails or threads, it is a resubmission.
#    - If there is no clue for Resubmission identification return SUBMISSION
# 13. **New/Renewal Indicator**: Indicates whether the risk is a "New" submission or a "Renewal".
#    - If the email body has a reference to 'Renewal' keyword, then indicate as 'Renewal' else 'New'
# """

# slip_fields_description = """
# 1. **Arch Policy Reference**: Unique identifier from Arch Insurance used internally.
#    - Often alphanumeric with year/section references (e.g., 010669/01/2025).
#    - Capture all sections if multiple exist.
# 2. **Unique Market Reference (UMR)**: Global slip reference (e.g., "B1234XYZ56789").
#    - Appears near header or slip reference line.
# 3. **Written Date**: Date the policy was finalized (DD/MM/YYYY or MM/DD/YYYY).
#    - Check for the word "written" or "Written Date" nearby.
#    - Prefer the date associated with policy finalization.
# 4. **Written Line %**: Percentage of risk written by insurer (e.g., 25%).
#    - Often appears section-wise like "Section A - 10%".
#    - Capture all section allocations if present.
# 5. **Legal Entity**: Underwriting legal entity or syndicate responsible.
#    - Capture exact legal entity or syndicate name/number.
#    - Example: "2012/1955", "A3603" etc.
# 6. **Risk Code Split**: Categories such as Property, Liability, Marine.
#    - Includes section-wise allocation or premium split.
#    - Look for Allocation of Premium to Coding title to code the codes for Risk.
#    - Look for codes like T, B, W etc. with percentage or section labels like "TS at 100%", "W-100%"
# 7. **Slip Leader**: Lead underwriter or syndicate coordinating the risk.
#    - Capture exactly as shown (e.g., "Chubb Global Markets").
#    - Usually labeled "Slip Leader" or "Lead Underwriter".
# 8. **Business Activities / Description / Interest**: Description of insured's operations or covered interest.
#    - Summarize into one line if multiple lines provided.
#    - Look for terms like "Business", "Interest", "INTEREST(S)" or insured operations.
# 9. **Currency**: Financial terms currency (e.g., GBP, USD) - return in 3-letter ISO format.
#    - Detect currency near premiums, limits, or payment terms.
#    - Convert symbols ($, £) to ISO codes.
# 10. **Section Name(s)**: Section titles or headings related to coverages.
#     - Extract full section headings (e.g., "Section A - Hull and Machinery").
#     - Include all sections in order.
# 11. **GWP 100%**: Gross Written Premium for 100% of risk.
#     - Often appears section-wise with numeric values.
#     - Check for "Premium" or "GWP" keywords in document or email body.
# 12. **Limit 100%**: Maximum payout under the policy (100% basis). Return in numeric format.
#     - Capture section-wise if listed separately.
#     - Ignore sub-limits unless explicitly marked as total.
# 13. **Attachment 100% Point**: Point at which insurance applies (check excess or attachment point).
#     - Capture monetary value, Keywords: "Attachment Point", "Excess Point".
# 14. **Deductibles / SIRs**: Deductible or self-insured retention amounts.
#     - Capture numeric values with any qualifiers (per occurrence, aggregate).
#     - Look for "Deductible" or "SIR" in schedules or tables.
# 15. **Cyber Clause**: Terms or clause names related to cyber risk inclusion or exclusion.
#     - Keyword: "Cyber", "Cyber Exclusion Clause", "Cyber Clause (e.g., LMA5402)".
#     - Return clause reference or "Not Present".
# 16. **Sanctions Clause**: Terms or clause names referencing international sanctions compliance.
#     - Keyword: "Sanction", "Sanction Clause", "Sanction Limitation and Exclusion" (e.g., JH2010/009, LMA3100).
#     - Return exact clause reference or "Not Present".
# """

# sov_fields_description = """
# 1. **Assured Name**: Full legal name of the insured entity.
# 2. **Internal Risk Reference**: Internal reference or identifier from the broker/insurer system.
# 3. **Broker**: Name of the brokerage firm submitting the risk.
# 4. **Broker Name**: Name of the submitting individual broker or main contact.
# 5. **Broker Email Address**: Email of the submitting broker or main contact.
# 6. **Status**: The current submission status (e.g., Bound, Quoted, Declined, Pending).
# 7. **New/Renewal Indicator**: Whether the submission is for a new risk or a renewal.
# 8. **Location Identifier**: Unique ID or name for the insured location or asset.
# 9. **Address / Site Details**: Full physical address or geographic description of the insured property.
# 10. **TIV (Total Insured Value)**: Total declared value of property at the location. Return in numeric format.
# 11. **Occupancy / Use**: Description of how the property is used (e.g., Office, Manufacturing, Warehouse).
# 12. **Construction Type**: Details on building materials and structure (e.g., Masonry, Frame, Fire Resistive).
# 13. **Risk Location / Territory**: Country, region, or zone where the insured property is located.
# """

# # Convenience mapping (if needed by code)
# FIELDS_MAP = {
#     "Skeleton Risk": skeleton_fields_description,
#     "Slip Risk": slip_fields_description,
#     "SOV": sov_fields_description
# }



"""
Prompts for the document classification and extraction pipeline
"""

# ---- High‑level system prompts ----
# submission_classification_system_prompt = (
#     "You are a highly experienced insurance underwriter and document analyst specializing in analyzing "
#     "submission emails (terrorism, war & hull, general liability) in the London Market."
# )

submission_classification_system_prompt = (
    "You are a highly experienced insurance underwriter and document analyst specializing in analyzing "
    "submission emails (terrorism, war & hull, general liability, auto liability) in the London Market."
)

doctype_classification_system_prompt = (
    "You are a highly experienced insurance document analyst specializing in analyzing insurance documents "
    "and schedules in the London Market."
)

extraction_system_prompt = (
    "You are a highly experienced insurance underwriter and document analyst specializing in analyzing "
    "insurance submissions, slips, skeleton risks, and SOV schedules. Extract only explicitly stated data."
)

# ---- Queries used for RAG or targeted retrieval ----
skeleton_query = """Assured Name, Risk Location, Inception Date, Expiry Date, Broker Name, Broker Email, Underwriter,
Line of Business Group, Trade Sector, Internal Risk Reference, Submission Status, New/Renewal Indicator"""

slip_query = """Arch Policy Reference EEA NON-EEA
UMR Unique Market Reference Master Reference
Written Date PERIOD Written AAL
Written Line % section-wise participation
Legal Entity Syndicate Participant Role
Risk Code Split Risk Code ALLOCATION OF PREMIUM TO CODING premium allocation TO, GT, RS, WL SETTLEMENT INFORMATION
Slip Leader Lead Underwriter Section Leader BUREAU(X) LEADER(S)
Business Activities insured operations interest summary INTEREST(S)
Section Names coverage headings TRADING EEA Non EEA HULL & MACHINERY BUILDER'S RISK
GWP 100% Gross Written Premium BLENDED PREMIUM
Limit 100% SUM (RE)INSURED/LIMIT EXCESS LIMIT EXCESS LIMIT HERON
Attachment Point Excess Point
Deductibles SIR Self-Insured Retention Coverage deductible Moral Damages Material Damage (Actual) or Constructive Total Loss
Cyber Clause LMA5402 cyber exclusion inclusion
Sanctions Clause JH2010/009 LMA3100 Sanction Limitation and Exclusion Sanction Limitation Clause
---"""

# ---------------------------------------------------------------------------
# Submission (Line of Business) Classification Prompt
# Categories inferred from screenshots: Terrorism, Hull and War, General Liability, Non-Submission
# ---------------------------------------------------------------------------
# submission_classification_prompt_template = """
# ## Categories for Classification:

# **Category 1: Terrorism**
# - Typically covers risks related to terrorism, sabotage, political violence, strikes, riots, civil commotion, or looting.
# - You might see references to terrorism-related organizations or clauses, or any coverage related to terrorism risks.
# - **Coverage details:** Covers physical damage and business interruption from terrorist acts, sabotage, political violence, strikes, riots.

# **Category 2: Hull and War**
# - Usually involves marine or aviation hull risks and war perils like piracy, military actions, or hostile acts.
# - Watch for mentions of vessels, aircraft, hull values, or marine/aviation war clauses.
# - Look for indications of physical loss or damage caused by war or hostile events impacting marine or aviation assets.
# - **Coverage details:** Protects marine and aviation hulls against war perils including hostile military actions, piracy, capture, and war risks.

# **Category 3: General Liability**
# - Generally covers third-party liability risks such as bodily injury, property damage, public/products liability, or employer's liability.
# - Might include references to legal defense, indemnity, lawsuits, or settlements linked to third-party claims.
# - Look for limits of liability or aggregate/per occurrence limits specific to liability insurance.
# - **Coverage details:** Provides third-party liability coverage for bodily injury, property damage, personal and advertising injury, including products.

# **Category 4: Auto Liability**
# - Pertains to risks associated with automobiles, including commercial vehicle fleets, individual cars, trucks, and trailers.
# - Look for terms like "Commercial Auto," "Fleet Schedule," "Hired and Non-Owned," "Vehicle Identification Number (VIN)," "driver information," or auto-specific liability limits.
# - **Coverage details:** Covers liability for Bodily Injury (BI) and Property Damage (PD) arising from the ownership, maintenance, or use of insured vehicles.


# **Category 5: Non-Submission**
# - Use this category if the email or document doesn't appear to contain insurance submissions, policy wording, coverage details, clause titles.
# - This might include meeting invites, calendar notifications, personal or unrelated correspondence, or emails with only attachments but no obvious submission text.
# - Be aware most emails will likely contain some form of submission, so apply this category only if there's genuinely no insurance-related submission content.

# ## Instructions
# 1. Analyze the entire email thread carefully, including To, From, CC, Subject, and body fields in detail.
# 2. Additionally, analyze attachment names along with the email content for classification clues.
# 3. Pay close attention to policy wording, clause titles, section headers, and coverage details.
# 4. Identify explicit and implicit references, keywords, synonyms, and typical market terminology related to each category (Terrorism, War & Hull, Liability).
# 5. You can also check coverage details mentioned within the email content to support your classification.
# 6. Classify the email strictly into the single most appropriate category based on your detailed analysis.

# ## Format Your Response
# Return your answer in strict JSON format only as shown below:
# {{ "Classification": "[Terrorism/War and Hull/General Liability/Non-Submission]" }}

# Do not add any extra text or explanation.

# ## Examples
# Terrorism: "Coverage against acts of terrorism, sabotage, or political violence."
# War and Hull: "War Risks Clause, hull coverage for marine vessels, piracy, or war perils."
# General Liability: "Public liability for bodily injury, property damage, or employer's liability section."
# Non-Submission: "Meeting invite for project discussion.", "No insurance content found.", "Personal greeting email."

# ## Final Output Template
# {{ "Classification": "[Terrorism/War and Hull/General Liability/Non-Submission]" }}

# ---
# Below is the email content to be used for classification:

# {email_content}
# """


submission_classification_prompt_template = """
## Categories for Classification:

**Category 1: Terrorism**
- Typically covers risks related to terrorism, sabotage, political violence, strikes, riots, civil commotion, or looting.
- You might see references to terrorism-related organizations or clauses, or any coverage related to terrorism risks.
- **Coverage details:** Covers physical damage and business interruption from terrorist acts, sabotage, political violence, strikes, riots.

**Category 2: Hull and War**
- Usually involves marine or aviation hull risks and war perils like piracy, military actions, or hostile acts.
- Watch for mentions of vessels, aircraft, hull values, or marine/aviation war clauses.
- **Coverage details:** Protects marine and aviation hulls against war perils including hostile military actions, piracy, capture, and war risks.

**Category 3: General Liability**
- Generally covers third-party liability risks such as bodily injury, property damage, public/products liability, or employer's liability.
- Might include references to legal defense, indemnity, lawsuits, or settlements linked to third-party claims.
- **Coverage details:** Provides third-party liability coverage for bodily injury, property damage, personal and advertising injury, including products.

**Category 4: Auto Liability**
- Pertains to risks associated with automobiles, including commercial vehicle fleets, individual cars, trucks, and trailers.
- Look for terms like "Commercial Auto," "Fleet Schedule," "Hired and Non-Owned," "Vehicle Identification Number (VIN)," "driver information," or auto-specific liability limits.
- **Coverage details:** Covers liability for Bodily Injury (BI) and Property Damage (PD) arising from the ownership, maintenance, or use of insured vehicles.

**Category 5: Non-Submission**
- Use this category if the email or document doesn't appear to contain insurance submissions, policy wording, or coverage details.
- This might include meeting invites, calendar notifications, personal correspondence, or emails with only attachments but no obvious submission text.

## Instructions
1. Analyze the entire email thread carefully, including To, From, CC, Subject, and body fields in detail.
2. Additionally, analyze attachment names along with the email content for classification clues.
3. Pay close attention to policy wording, clause titles, section headers, and coverage details.
4. Classify the email strictly into the single most appropriate category based on your detailed analysis.

## Format Your Response
Return your answer in strict JSON format only as shown below:
{{ "Classification": "[Terrorism/War and Hull/General Liability/Auto Liability/Non-Submission]" }}

Do not add any extra text or explanation.

## Final Output Template
{{ "Classification": "[Terrorism/Hull & war/General Liability/Auto Liability/Non-Submission]" }}

---
Below is the email content to be used for classification:

{email_content}
"""

# ---------------------------------------------------------------------------
# Doctype Classification Prompt Template (attachments / documents)
# ---------------------------------------------------------------------------
doctype_classification_prompt_template = """
You are an expert insurance document analyst and your role is to classify the document or email below into one of the following categories:

**Skeleton Risk**:
- A preliminary submission used for early-stage underwriting. It captures essential, high-level coverage details for initial quoting.
- Look for fields and keywords: Assured Name, Risk Location, Inception/Expiry Date, Broker Details, Underwriter, Line of Business, Trade Sector.
+ For Auto Liability: Look for fields such as Account Number, Name, City, State, Country, Effective Date, Expiration Date, Industry, Subtype, Primary Use.

**Slip Risk**:
- A formal, market-standard insurance or reinsurance contract document used to bind coverage with detailed terms, conditions, limits.
- There might be one or multiple insurers.
- Look for fields and keywords: Written Date/Line %, Legal Entity, Risk Code, Slip Leader, Business Description, Currency, Sections, Limits.
+ For Auto Liability: Look for Total Premium, Driver info (age, license type, experience), Number of Accidents/Violations, Annual Mileage, Ownership Type, Safety Features, Usage Pattern, Certificates, Weather Risks.

**SOV (Statement of Values)**:
- A structured schedule listing insured properties or assets, mostly in Excel. Used for valuation, modeling, and exposure analysis.
- Look for fields and keywords: Location Addresses, TIV or Replacement Value, Construction Type, Occupancy, Year Built, Number of Stories.
+ For Auto Liability: Look for detailed per-vehicle records with Make, Model, Year, and Vehicle Value.

**Others**:
- Content that does not fit any of the above types. Examples: internal communications, general queries, marketing materials, drafts, or non‑insurance documents.

# Instructions:
1. Analyze the document content carefully. Look for explicit definitions, structural clues, and contextual phrases.
2. The input data might be a submission email, excel data in pipe-separated format with sheet names or text content is in page-wise markdown.
3. Evaluate the input structure, terminology, and layout. Use clues from tables, headers, key phrases, and even the filename.
4. Only classify as **"Others"** if:
   - None of the definitions, fields, or coverage details clearly match any category.
   - The document is off-topic, not insurance-related, or is incomplete/irrelevant.

# Input Content:
{document_content}

# Classification Output
Respond in **strict JSON only**:
{{ "Classification": "[Slip Risk/Skeleton Risk/SOV/Others]" }}
"""

# ---------------------------------------------------------------------------
# Extraction Prompt Template
# ---------------------------------------------------------------------------
extraction_prompt_template = """
You are an expert at extracting key fields from submission emails and insurance-related documents.
You will be provided with the email content and the attachment content for a submission of an insurance related documents.

The **email content** contains metadata such as CC, To, From, Subject, Body, and a list of attachments.
The **attachment content** may be in one of the following formats:
- **Textual content**: page-wise markdown format (as extracted from PDF or Word).
- **Tabular content**: pipe-separated values with sheet names (as extracted from Excel).
The attachment content may or may not be present but email content will always be present.

You must extract data only from the provided content. **Do not infer or fabricate values.**

## Below are the list of fields to be extracted with their description details:
{fields_description}

## Instructions for Extraction
- **Extract data only from the provided email and attachment content. Do not guess or make assumptions.**
- If a field is **explicitly stated or clearly referenced**, extract the exact value.
- If a field is **not present or cannot be confidently determined**, return:
  - `"value": "Not Present"`
  - `"confidence": "0%"`
- For all extracted fields, assign a **confidence level** based on clarity and directness of match (e.g., exact match: 95–100%, inferred but clear: 70–85%, ambiguous: 40–60%, weak: 10–25%, not present: 0%).
- **Document Source Tracking**: For each extracted field, identify which document (email or specific attachment) contains the value.
- **Location Information**: If extracting from attachment content, note the approximate location (page number, section, table) where the value was found.

## Self-Assessment of Extracted Fields:
After extracting the value, self-assess the accuracy and reliability of the extraction. Provide a confidence score on a scale of 0 to 100:
- 85–99: The extracted value matches exactly with the clear context provided.
- 70–84: The extracted value appears correct, but there are minor ambiguities or the context is somewhat unclear.
- 50–69: The extracted value is plausible, but the context is vague or partially missing, leading to moderate confidence.
- 25–49: The extracted value is highly uncertain due to poor context, conflicting information, or significant ambiguity.
- 1–24: The extracted value is likely incorrect, and the context provides little to no support for the extraction.
- 0: The value is not present or cannot be determined from the context.

AVOID OVERESTIMATION: Be cautious not to overestimate your confidence. If there is any doubt or ambiguity, reflect it in the score.
**Note: The confidence score is critical for deciding on manual reviews. Ensure the scores accurately reflect your certainty.**

## Response Format
Return a **strict JSON object**, where each field key maps to a nested object with:
{{
  "Field Name": {{
    "value": "Extracted content or 'Not Present'",
    "confidence": "Percentage string e.g., '85%'",
    "filename": "Source document name or 'Email'",
  }}
}}

# Email Content:
{email_content}

# Attachment Content:
{attachment_content}
"""

# ---------------------------------------------------------------------------
# Field Description Blocks (used depending on document type)
# ---------------------------------------------------------------------------

skeleton_fields_description = """
1. **Assured Name**: Full legal name of the insured entity (also referred to as "Assured" or "Insured").
2. **Risk Location / Territory**: Geographic area or country where the risk is situated or covered.
   - Check for keyword like 'situation' or 'address' to extract this field
3. **Inception Date**: Start date of the policy or effective coverage (format: DD/MM/YYYY).
   - Check for 'Period' or Date keyword for Inception Date.
4. **Expiry Date**: End date of the policy or termination of coverage (format: DD/MM/YYYY).
   - For this refer to period of the policy and then decide the expiry date.
   - Example: If start date or inception date is 12/03/2020 and period is 12 months then Expiry date would be 11/03/2021.
   - Note: The period might be any number of months or a (start and end Date both together). Accordingly you have calculate Expiry Date.
5. **Internal Risk Reference**: Unique internal reference code used by the insurer or broker.
6. **Broker**: Name of the brokerage firm placing the risk.
   - Analyze the email content carefully to get broker information. The broker name and details might present in signature of a email body.
7. **Broker Name**: Full name of the individual broker or main point of contact.
8. **Broker Email Address**: Email address of the broker or placing contact.
9. **Underwriter**: Name of the underwriter or underwriting team responsible.
   - Check for keyword like "Underwriter" or refer to Recipient Name ("To:" in email body)
10. **Line of Business Group**: High-level insurance category (e.g., Terrorism, Property, Marine, Casualty).
11. **Trade Sector**: The business or industry classification of the insured (e.g., Construction, Retail, Hotels, Parks).
12. **Status**: The current stage of the email, The value for this field will be either **SUBMISSION** or **RESUBMISSION**.
   - Refer to the email subject and look for keywords like 'RE:' indicating a resubmission.
   - If the email content has previous mails or threads, it is a resubmission.
   - If there is no clue for Resubmission identification return SUBMISSION
13. **New/Renewal Indicator**: Indicates whether the risk is a "New" submission or a "Renewal".
   - If the email body has a reference to 'Renewal' keyword, then indicate as 'Renewal' else 'New'
"""

slip_fields_description = """
1. **Arch Policy Reference**: Unique identifier from Arch Insurance used internally.
   - Often alphanumeric with year/section references (e.g., 010669/01/2025).
   - Capture all sections if multiple exist.
2. **Unique Market Reference (UMR)**: Global slip reference (e.g., "B1234XYZ56789").
   - Appears near header or slip reference line.
3. **Written Date**: Date the policy was finalized (DD/MM/YYYY or MM/DD/YYYY).
   - Check for the word "written" or "Written Date" nearby.
   - Prefer the date associated with policy finalization.
4. **Written Line %**: Percentage of risk written by insurer (e.g., 25%).
   - Often appears section-wise like "Section A - 10%".
   - Capture all section allocations if present.
5. **Legal Entity**: Underwriting legal entity or syndicate responsible.
   - Capture exact legal entity or syndicate name/number.
   - Example: "2012/1955", "A3603" etc.
6. **Risk Code Split**: Categories such as Property, Liability, Marine.
   - Includes section-wise allocation or premium split.
   - Look for Allocation of Premium to Coding title to code the codes for Risk.
   - Look for codes like T, B, W etc. with percentage or section labels like "TS at 100%", "W-100%"
7. **Slip Leader**: Lead underwriter or syndicate coordinating the risk.
   - Capture exactly as shown (e.g., "Chubb Global Markets").
   - Usually labeled "Slip Leader" or "Lead Underwriter".
8. **Business Activities / Description / Interest**: Description of insured's operations or covered interest.
   - Summarize into one line if multiple lines provided.
   - Look for terms like "Business", "Interest", "INTEREST(S)" or insured operations.
9. **Currency**: Financial terms currency (e.g., GBP, USD) - return in 3-letter ISO format.
   - Detect currency near premiums, limits, or payment terms.
   - Convert symbols ($, £) to ISO codes.
10. **Section Name(s)**: Section titles or headings related to coverages.
    - Extract full section headings (e.g., "Section A - Hull and Machinery").
    - Include all sections in order.
11. **GWP 100%**: Gross Written Premium for 100% of risk.
    - Often appears section-wise with numeric values.
    - Check for "Premium" or "GWP" keywords in document or email body.
12. **Limit 100%**: Maximum payout under the policy (100% basis). Return in numeric format.
    - Capture section-wise if listed separately.
    - Ignore sub-limits unless explicitly marked as total.
13. **Attachment 100% Point**: Point at which insurance applies (check excess or attachment point).
    - Capture monetary value, Keywords: "Attachment Point", "Excess Point".
14. **Deductibles / SIRs**: Deductible or self-insured retention amounts.
    - Capture numeric values with any qualifiers (per occurrence, aggregate).
    - Look for "Deductible" or "SIR" in schedules or tables.
15. **Cyber Clause**: Terms or clause names related to cyber risk inclusion or exclusion.
    - Keyword: "Cyber", "Cyber Exclusion Clause", "Cyber Clause (e.g., LMA5402)".
    - Return clause reference or "Not Present".
16. **Sanctions Clause**: Terms or clause names referencing international sanctions compliance.
    - Keyword: "Sanction", "Sanction Clause", "Sanction Limitation and Exclusion" (e.g., JH2010/009, LMA3100).
    - Return exact clause reference or "Not Present".
"""

sov_fields_description = """
1. **Assured Name**: Full legal name of the insured entity.
2. **Internal Risk Reference**: Internal reference or identifier from the broker/insurer system.
3. **Broker**: Name of the brokerage firm submitting the risk.
4. **Broker Name**: Name of the submitting individual broker or main contact.
5. **Broker Email Address**: Email of the submitting broker or main contact.
6. **Status**: The current submission status (e.g., Bound, Quoted, Declined, Pending).
7. **New/Renewal Indicator**: Whether the submission is for a new risk or a renewal.
8. **Location Identifier**: Unique ID or name for the insured location or asset.
9. **Address / Site Details**: Full physical address or geographic description of the insured property.
10. **TIV (Total Insured Value)**: Total declared value of property at the location. Return in numeric format.
11. **Occupancy / Use**: Description of how the property is used (e.g., Office, Manufacturing, Warehouse).
12. **Construction Type**: Details on building materials and structure (e.g., Masonry, Frame, Fire Resistive).
13. **Risk Location / Territory**: Country, region, or zone where the insured property is located.
"""





# skeleton_fields_description = """
#   1.  **Assured Name**: Full legal name of the insured entity.
#   2.  **Garaging Address**: Primary location where the vehicle fleet is based.
#   3.  **Inception Date**: Start date of the policy.
#   4.  **Expiry Date**: End date of the policy.
#   5.  **Broker**: Name of the brokerage firm.
#   6.  **Number of Power Units**: Total count of powered vehicles (trucks, cars) in the fleet.
#   7.  **Business Use / Description**: The primary purpose of the vehicles (e.g., Logistics, Delivery, Taxi Service).
#   8.  **Radius of Operation**: The maximum distance vehicles will travel from their base (e.g., Local <50 miles, Intermediate 50-200 miles, Long Haul >200 miles).
#   9.  **Desired Liability Limit**: The requested combined single limit (CSL) for bodily injury and property damage (e.g., $1,000,000).
#   10. **Target Premium**: The premium amount the client is aiming for.
# """
 
# slip_fields_description = """
#   1.  **Unique Market Reference (UMR)**: Global slip reference.
#   2.  **Assured Name**: Full legal name of the insured entity.
#   3.  **Policy Period**: Start and end dates of the coverage.
#   4.  **Business Description**: Detailed description of the insured's operations involving vehicles.
#   5.  **Primary Liability Limit**: The core liability coverage amount, often expressed as a Combined Single Limit (CSL).
#   6.  **Hired and Non-Owned Auto**: Indicates if coverage is included for vehicles the insured hires or for employees' personal vehicles used for business. Extract "Included" or the specific limit.
#   7.  **Driver Eligibility Criteria**: Specific requirements for drivers (e.g., Minimum Age, MVR standards, Years of Experience).
#   8.  **Deductibles**: The amount the insured pays out-of-pocket for a claim. Specify if it's for Collision or Comprehensive coverage.
#   9.  **Radius of Operation**: The geographic limit of travel for the insured vehicles.
#   10. **Vehicle Schedule Reference**: A reference to the document listing all covered vehicles (e.g., "See attached Vehicle SOV dated 09/25/2025").
#   11. **Key Endorsements / Forms**: List any critical form numbers or endorsement titles attached (e.g., "CA 99 48," "MCS-90").
# """
 
# sov_fields_description = """
#   1.  **Vehicle Number**: A unique identifier for the vehicle within the schedule.
#   2.  **Vehicle Year**: The manufacturing year of the vehicle.
#   3.  **Vehicle Make**: The manufacturer of the vehicle (e.g., Ford, Volvo, Toyota).
#   4.  **Vehicle Model**: The specific model of the vehicle (e.g., F-150, VNL 760, Camry).
#   5.  **Vehicle Identification Number (VIN)**: The 17-digit unique serial number of the vehicle.
#   6.  **Vehicle Type**: The class of vehicle (e.g., Tractor, Trailer, Light Truck, Private Passenger).
#   7.  **Garaging Address**: The full address where the vehicle is typically parked.
#   8.  **Stated Value / Cost New**: The insured value of the vehicle.
#   9.  **Primary Use**: The main purpose of the vehicle (e.g., Service, Delivery, Sales).
# """


# Convenience mapping (if needed by code)
# FIELDS_MAP = {
#     "Skeleton Risk": skeleton_fields_description,
#     "Slip Risk": slip_fields_description,
#     "SOV": sov_fields_description
# }

auto_skeleton_fields_description = """
1. AccountNumber – Unique account number for insured.
2. Name – Insured entity/person name.
3. City – City where insured resides.
4. State – State where insured resides.
5. Country – Country of insured.
6. EffectiveDate – Start date of policy.
7. ExpirationDate – End date of policy.
8. Industry – Insured’s business sector.
9. Subtype – Sub-classification of risk.
10. PrimaryUse – Main use of insured vehicles.
"""

auto_slip_fields_description = """
1. TotalPremiumRPT – Total premium reported.
2. NumberofAccidents – Accident count for insured vehicles.
3. NumberofViolations – Driving violations count.
4. DriversAge – Age of driver(s).
5. DriversLicenseType – Type of driver’s license.
6. DriversExperienceYears – Years of driving experience.
7. NumberOfNamedDrivers – Count of named drivers.
8. OwnershipType – Owned/Leased/Financed.
9. AnnualMileage – Expected yearly mileage.
10. Modifications – Vehicle modifications.
11. AntiTheftOrSafetyFeatures – Security/safety features present.
12. UsagePattern – Usage type (personal, commercial, etc.).
13. RegisteredZipOrArea – Vehicle registration location.
14. ValidRegistrationCertificate – Registration certificate validity.
15. ValidEmissionCertificate – Emission certificate validity.
16. PendingChallansOrLegalIssues – Outstanding legal issues.
17. RegionalWeatherRisks – Weather-related exposures.
"""

auto_sov_fields_description = """
1. Make – Vehicle manufacturer.
2. Model – Vehicle model.
3. Year – Vehicle year of manufacture.
4. VehicleValue – Declared vehicle value.
"""
