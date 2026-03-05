# Invoice Processor

A lightweight AI-powered invoice processing system that extracts structured data from invoices, provides details about its category and automatically approves or reject them based on business rules. 

## Overview

Finance teams receive invoices frequently and in various formats, (PDF, scanned images), which have to be manually reviewed. This system aims to reduce this manual labour by automating the review workflow by handling: 

- The ingest of invoices (PDF and image formats, supported: .pdf, .png, .jpg, .jpeg, .tiff, .tif)
- Extracting structured fields using a vision-language model
- Categorising invoices into expense categories based on their items
- Applying deterministic approval guidelines to produce ACCEPT or REJECT decisions with clear auditable explanations.
- Outputting the result into machine-readable JSON format
- Providing a simple UI for ease of use

## Architecture and Design Decisions

### Vision-Language model

**Vision-Language Model vs Traditional OCR:**

While standard OCR techniques can be used for text extraction from invoices, they do not retain spatial layout. Something which is essential for invoices that rely on structure. The position of data determines its meaning (usually via headers) and understanding this context significantly improves extraction precision. 

Vision-Language models are able to process visual layout and text simultaneously, solving this problem while also reducing the need for complex post processing logic to handle edge cases introduced by varying invoice templates. This keeps the overall solution lightweight, making Vision-Language models the natural choice for this task. Specifically one which has toolcalling capabilities to allow for the use of a dedicated data parsing library as described in the section: Structured Data Extraction.

### MultiModal Input Strategy

Although the data contains a variety of input modalities (text and image), the choice was made to implement a standardised image pipeline, converting all documents to JPEG before sending them to the model. This was decided for two reasons:

1. Retaining the structural integrity as described above. 
2. Normalising the input to a single data type, simplifying the preprocessing pipeline. 

PDFs are converted to images using matrix scaling rather than simple DPI scaling. Where DPI increases the number of pixels per inch across the entire image, which quickly results in extremely large file sizes. Instead, matrix scaling with a maximum dimension of 1750px is used while preserving the aspect ratio (preventing text from being warped, which is highly unwanted for precise text extraction), keeping inference costs low and processing fast. 

> **Note:** The current implementation assumes single-page documents, which matches the provided sample invoices. Multi-page support can be added by iterating over pages and deciding which to process.

### Model Selection

The recommended model is `gpt-5o-mini-2025-08-07`, balancing both inference speed and costs ($0.002 per invoice). `gpt-5-nano` is cheaper but was found during testing to reduce extraction accuracy. A larger model was decided against as the complexity of the task does not justify the additional cost.

During development, `gpt-4o-mini` was the initial choice. However, testing revealed unexpected token consumption of approximately 37,500 tokens per invoice call. Investigation showed the API was processing the image bytes as base64 text rather than routing them through the dedicated vision encoder. This made `gpt-4o-mini` both costly and slow for this use case. Switching to `gpt-5o-mini` resolved the issue, correctly using its vision pipeline and resulting in the expected token usage. 

### Pydantic AI Framework & Structured Data Extraction:

To remain flexible and allow for both self-hosted (privacy concerns) and model provider inference, the Pydantic AI framework was selected. Pydantic AI introduces and abstraction layer, which allows easy switching between different models and endpoints. avoiding vendor lock-in. Also, its natural support structured output (via Pydantic) is of up most use for our task, where having consistent structured data is essential. 

As an added bonus, Pydantic AI integrates seamlessly with Logfire, an observability platform for tracing agent calls, which is also supported in this solution.

#### **Structured Data Extraction**

As mentioned Pydantic AI perfectly integrates with the Pydantic library. Allowing for easy type checking and ensuring consistent inputs and outputs throughout the pipeline. The  `InvoiceData` schema was designed to capture all fields relevant to the approval rules and thus the assignment, plus additional fields worth explaining: 

- **Gross vs. Net amounts**: The assignment specifies `total_amount` but invoices include VAT. Both gross and net amounts are extracted along with the VAT. Ensuring completeness for possible future tax claims.  Both for the invoice summary and `line_items`.
- **Invoice Number**: For the sole reason of completenes and retainability. 
- **Payment Information** To act on the acceptance it would be beneficial to have the payment information of that invoice in the same data output, To be able to act on it swiftly either manually or also via an automated pipeline. 
- **Expense Category:** Although required, I would like to elaborate on the choice of making `category` a `set[ExpenseCategory]` rather than a single value. This because a single invoice can contain multiple categories (e.g. both books and toys on the same invoice). Furthermore, using a Enum enforces consistency and prevents free-form strings something necessary when possible grouping or joining might be done in the future. 
- **Currency**: To ensure that it is known in which currency the payment needs to be done/is received. 
    > **Note:** In the assignment the deterministic rules are, if revolving around prices, in euros. However, all sample invoices are in US dollars. I decided to not act on this since it is stated that the solution needed to be lightweight. As can be seen I did extract the currency such that it could possibly be converted before the rule evaluation. 

##### Date Parsing

The `invoice_date` field uses the `dateparser` library as a `BeforeValidator` (always passed through the parser before model validation) on the Pydantic model. This acts as a safety net for cases where the model returns a date as a string in a non-standard format rather than a proper date object, which is common with LLMs in practice (from experience). 

The motivation for using `dateparser` is its ability to handle regional date formats. With the tought that invoices may contain dates like `12 june 2025`, time zone abbreviations or UTC offsets. `dateparser` supports parsing of these format in almost all languages making it robust against international invoices at the cost of a slightly heavier library.

### Duplicate Detection

Duplicate detection is implemented using a human-readable hash composed of:

```
{vendor_name}_{invoice_date}_{invoice_number}_{total_amount_gross}
```

A cryptographic hash was intentionally not used here. A readable hash makes it easy to inspect and debug which invoices were considered duplicates during a session, which is valuable for a prototype and makes it easier for review of the assignment. In a production system, a proper hash function (e.g. SHA-256) with a persistent database would be used instead.

> **Note:** Duplicate detection is session-scoped in the Streamlit app. Clearing the session, refreshing the web-page or restarting the app resets the duplicate history. 

### Approval Rules & Auditability

All thresholds are stored in `config/approval_thresholds.yaml`. The decision engine evaluates all rules independently in a single pass, meaning an invoice can be rejected for multiple reasons simultaneously. 

To ensure the output data is in a consistent format the `InvoiceResult` is introduced. This holds: 
- **status:** Restricted to either be `ACCEPT` when the invoice is accepted or `REJECT` when the invoice is rejected according to the approval guidelines. 
- **reasons**: List holding all the reasons for rejection, if empty there is no reason for denial and thus the invoice is accepted
- **extracted data:** Copy of the `InvoiceData` holding the extracted data from the invoice
- **metadata:** To ensure information is retained about the processing of the invoice if results need to be revisited and to store the hash value. `InvoiceResultMetadata` is introduced, containing: 
    - **model used**: The name of the model used for extraction
    - **file name**: The name of the original file
    - **hash value**: The hash value generated as described above
    - **created time**: The moment the invoice was processed (UTC standardised for possible database use)

# Getting Started

### Prerequisites

- [uv](https://docs.astral.sh/uv/getting-started/installation/) or [Docker](https://docs.docker.com/get-docker/)
- Either: 
    - OpenAI key for the default end-point (`https://api.openai.com/v1`)
    - API-key for a custom endpoint: 
        - Ollama: (http://localhost:11434/v1)
        mistral-small3.2:latest is recommended here
        - Gemini: (https://generativelanguage.googleapis.com/v1beta/openai)
        - etc.

### Setup

```bash
git clone https://github.com/MartijnHilders/invoice-processor
cd invoice-processor
cp .env.example .env
# Edit .env and fill in your API key, model name and/or Model base URL (and Logfire token if wanting the logfire observability)
```


#### Environment Variables

See `.env.example` for all available options. The key variables are:

| Variable | Required | Description |
|---|---|---|
| `MODEL_NAME` | Yes | Model identifier (recommended: `gpt-5-mini-2025-08-07`) |
| `MODEL_API_KEY` | Yes | API key for your provider (OpenAI, Azure, Gemini, Ollama, etc.) |
| `MODEL_BASE_URL` | No (OpenAI) / Yes (other) | Custom base URL for non-standard endpoints (e.g. Azure, Gemini, Ollama) |
| `LOGFIRE_TOKEN` | No | Logfire token for observability |

> Do **NOT** use **`MODEL_NAME=gpt-4o-mini`** for this pipeline for the reasons described in section: Model Selection

---

## Running the App

### Docker (recommended)
```bash
docker build -t invoice-processor .
docker run -p 8501:8501 --env-file .env invoice-processor
```

Then open [http://localhost:8501](http://localhost:8501).

### Local
```bash
uv sync
uv run streamlit run app.py
```

## Running Tests

Requires local installation.
```bash
uv run pytest
```

## Running the Extraction Script

Script which pulls invoices from /data folder and saves to .json at root folder location, designed to test the extraction. Requires local installation.

```bash
uv run python scripts/extract_invoices.py
```

## Configuration

Approval thresholds are stored in `config/approval_thresholds.yaml`. Update this file to change business rules without modifying code. When using docker rebuild is obviously required after changes. 





