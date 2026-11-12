# Meeting Intelligence System – Technical Documentation

Whole flow in short then follows the explanation part.

<img width="1266" height="1131" alt="image" src="https://github.com/user-attachments/assets/465bb344-3d12-40c5-b158-d3871b69210b" />


## a. Quick Setup Instructions

**Prerequisites:** Python 3.11+, Node.js, and an LLM API key.

**1. Backend Setup**

```bash
cd backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

Configure `backend/.env` using `.env.example`.

Important configurations:

- `LLM_BASE_URL`
- `LLM_API_KEY`
- `LLM_MODEL`
- `EMBEDDING_MODEL`
- `CHROMA_PATH`

**2. Frontend Setup**

```bash
cd frontend
npm install
npm run dev
```

**3. AI Layer**

The AI layer is an installable Python package (`meeting_ai`) and is included through the backend requirements using `-e ../ai`.

Refer to the individual README files in the root, backend, AI and frontend directories for detailed setup and execution instructions.

## b. Architecture Overview

I kept the application modular, separating the API layer, AI processing layer and frontend.


```text
           React + TypeScript
                  |
               FastAPI
                  |
          Processing Service
                  |
       Parse → Chunk → Embed
                  |
              ChromaDB
                  |
             Index Ready
                  |
          ------------------
          |                |
       Enable Chat    Intelligence Jobs
          |             /    |    \
       RAG Pipeline  Summary Decisions Actions
          |                |
       Retrieval       Independent Results
          |                |
       Context + LLM    Side Panel
          |
    Answer + Citations
```

**Key architectural decision:** Chat availability depends only on successful indexing. Summary, decisions and action items run as independent background jobs, so a failure in one extraction task does not affect the chat experience or other sections.

The codebase has three main parts:

- `frontend/`: React UI, API communication and processing state management.
- `backend/`: FastAPI endpoints, session management and background task orchestration.
- `ai/`: Independent Python package handling transcript parsing, chunking, embeddings, retrieval, LLM calls and intelligence extraction.

##

The current implementation uses persistent local ChromaDB storage and in-process background tasks. It is suitable for a single-instance assignment but would need changes for distributed deployment.

My approach would be:

## c. What Would Be Required to Productionize and Scale?

- **Deployment:** Containerize the services using Docker and deploy on AWS ECS/EKS, GCP Cloud Run/GKE or Azure Container Apps.
- **File Storage:** Use S3, GCS or Azure Blob Storage for uploaded transcripts.
- **Database:** Introduce PostgreSQL for persistent meeting metadata, users, ownership and processing status.
- **Vector Storage:** Move to a scalable managed vector database or a properly managed ChromaDB deployment.
- **Background Processing:** Replace in-process threads with Celery and Redis or a managed queue such as AWS SQS. This would allow independent workers to handle indexing and intelligence extraction.
- **Scalability:** Make API instances stateless and scale API servers and processing workers independently.
- **Security:** Add authentication, authorization, session isolation, encryption, secure secret management and upload validation.
- **Observability:** Introduce structured logging, distributed tracing, processing metrics, LLM latency and token-cost monitoring.

I'd also implement retries, idempotent task execution, rate limiting and automated cleanup of expired sessions.

## d. RAG / LLM Approach & Decisions

**LLM**

I used an OpenAI-compatible client with provider and model configuration managed through environment variables. This allows switching between providers such as Groq and Gemini Flash without changing the core application logic.

**Embeddings**

I chose `sentence-transformers/all-MiniLM-L6-v2` for local embedding generation. It is lightweight, avoids an additional paid embedding API and is sufficient for the assignment's transcript retrieval requirements.

**Vector Database**

I chose ChromaDB because it supports persistent local storage, vector similarity search and metadata filtering. I use two collections:

- `meeting_chunks`: Stores transcript chunks, embeddings and speaker/timestamp metadata.
- `meeting_sessions`: Stores session information, indexing status, individual extraction statuses and generated results.

This avoids introducing a separate relational database for the current scope.

**Orchestration**

I implemented the RAG pipeline directly in Python instead of introducing LangChain or LlamaIndex. Since the workflow is relatively straightforward, I wanted direct control over parsing, chunking, retrieval, context construction and citation handling without unnecessary abstractions.

**Chunking & Retrieval**

- Parse transcripts into speaker turns with timestamps.
- Group consecutive speaker turns using speaker-aware chunking.
- Target approximately 800 characters per chunk with one-turn overlap.
- Generate embeddings and store them in ChromaDB.
- Retrieve the top 5 relevant chunks using cosine similarity and session-based metadata filtering.

**Prompt & Context Management**

The retrieved chunks are formatted with their speaker and timestamp information and passed to the LLM as context.

The grounding prompt instructs the model to answer only from the supplied excerpts. If the answer is not available in the transcript, it should explicitly say so.

For citations, the LLM returns numbered references such as `[1]`. These markers are mapped back to the original chunk metadata to display the correct speaker and timestamp.

For longer transcripts, I use a map-reduce approach for intelligence extraction: process transcript windows independently and merge the intermediate results.

**Guardrails & Quality**

- Validate uploaded files for type, encoding, size and parseable content.
- Validate structured extraction responses using Pydantic.
- Retry once if the LLM returns invalid JSON.
- Keep chat restricted to successfully indexed sessions.
- Prevent duplicate extraction jobs using per-session locks and task claiming.
- Handle extraction failures independently and provide section-level retries.
- Preserve source metadata for citation traceability.

For quality evaluation, I would focus on retrieval relevance, answer correctness, citation accuracy and the system's ability to reject unsupported questions.

## e. Key Technical Decisions and Why

1. **Separate AI layer:** I created an independent `meeting_ai` package so the backend does not directly depend on embedding or LLM implementation details. This also makes the AI pipeline easier to test and reuse.

2. **Persistent ChromaDB:** I used ChromaDB for both vector storage and session state, avoiding the need for a separate database in this assignment.

3. **Independent intelligence extraction:** Summary, decisions and action items run as three separate jobs. This ensures chat becomes available immediately after indexing.

4. **In-process background processing:** FastAPI BackgroundTasks and threads are sufficient for the current single-instance scope. I avoided introducing Redis and Celery prematurely.

5. **Speaker-aware chunking:** Meeting transcripts are conversational, so preserving speaker turns and timestamps provides better context and more meaningful citations than arbitrary text splitting.

6. **Configurable LLM integration:** Using an OpenAI-compatible client makes it easier to switch providers and experiment with different models.

7. **Persistent processing state:** Storing individual statuses and results in separate ChromaDB records avoids concurrent jobs overwriting each other's state.

## f. Engineering Standards Followed and Skipped

**Standards followed:**

- Separation of concerns across frontend, backend and AI layers.
- Modular Python package structure with clear responsibilities.
- Pydantic request, response and structured output validation.
- Centralized environment-based configuration.
- Reusable API clients and AI integrations.
- TypeScript for frontend type safety.
- Component-based React architecture.
- Separate processing states for indexing and intelligence extraction.
- Error handling, retry mechanisms and startup recovery for interrupted jobs.
- Per-session locking and task claiming to avoid duplicate processing.
- README documentation for individual modules.
- Dedicated test directories for the backend and AI layer.

**skipped for this assignment:**

- Redis, Celery and distributed workers.
- Microservices and distributed deployment.
- PostgreSQL and relational database migrations.
- Authentication and multi-user access management.
- Server-Sent Events or WebSockets; status updates use polling.
- Complex frontend state management libraries.
- CI/CD and production deployment automation.

I focused on keeping the code maintainable and modular without introducing infrastructure that the current scope does not require.

## g. How I Used AI Tools in My Development Process

I used Cursor and Claude as development assistants throughout the implementation.

My approach was to define the architecture, module responsibilities and implementation plan before moving into coding.

I used AI tools for:

- Exploring technical approaches and comparing implementation choices.
- Setting up the initial project structure and boilerplate.
- Understanding unfamiliar libraries and APIs.
- Exploring edge cases in transcript parsing and RAG implementation.
- Debugging, reviewing and refactoring code.
- Identifying potential architectural issues.

I reviewed the generated code and validated it against the architecture rather than blindly accepting suggestions. I also used implementation plans and checklists to keep the code aligned with the intended design.

## h. What I'd Do Differently With More Time

There are a few improvements I'd prioritize beyond the current single-meeting workflow:

1. **Multiple Meeting Uploads and different type of upload:** Allow users to upload and manage multiple meeting transcripts in different types instead of maintaining one transcript per session.

2. **Persistent Meetings Dashboard:** Build a dashboard where users can view previously uploaded meetings, search and reopen them, and access their summaries and conversations.

3. **Database-backed Persistence:** Introduce PostgreSQL for meeting records, users, session metadata and processing states, with object storage for original transcript files. ChromaDB would continue handling vector retrieval.

4. **Cross-meeting Search:** Allow users to ask questions across multiple meetings and retrieve relevant discussions from different transcripts.

5. **RAG Evaluation:** Build an evaluation dataset and compare embedding models, chunking strategies and retrieval approaches. Experiment with hybrid search and reranking where needed.

6. **Better User Experience:** Add streaming chat responses and more detailed processing progress.

7. **Testing & Reliability:** Expand automated unit, integration and end-to-end tests, especially around retrieval accuracy, citations and concurrent processing.

My first priority would still be improving retrieval quality and answer reliability before expanding the product features.

## i. Final Thoughts

I intentionally kept the initial scope focused on the core problem: making meeting transcripts searchable and providing reliable, context-aware answers.

The main engineering focus was on preserving speaker and timestamp information, building a modular RAG pipeline and ensuring chat availability was independent of meeting intelligence extraction.

With more time, I'd extend this into a multi-meeting platform with persistent storage and cross-meeting search, while retaining the same separation between ingestion, retrieval and intelligence extraction.
