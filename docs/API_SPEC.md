
# LearnLab API Specification

## Authentication
Currently, no authentication is required. (Add API key/JWT in the future.)

---

## Endpoints

### Root
**GET /**
Returns a welcome message.

**Response:**
```json
{ "message": "Welcome to LearnLab API!" }
```

---

### Health Check
**GET /status**
Returns API status.

**Response:**
```json
{ "status": "ok", "detail": "API is running" }
```

---

### LLM Endpoint
**POST /chat/llm**
Generate a response from the LLM provider.

**Request:**
```json
{
	"prompt": "Hello, world!",
	"model": "gpt-3.5-turbo-instruct",
	"max_completion_tokens": 256,
	"provider": "openai"
}
```
**Response:**
```json
{
	"result": "...LLM output...",
	"raw_response": { /* full LLM API response */ }
}
```

---

### Automation Endpoint
**POST /automate/run**
Trigger an automation agent task.

**Request:**
```json
{
	"payload": { "task": "example" }
}
```
**Response:**
```json
{
	"result": { /* automation agent output */ }
}
```

---

### Integration Endpoint
**POST /n8n/run**
Trigger an integration agent task.

**Request:**
```json
{
	"payload": { "action": "send_email", "data": { "subject": "Test" } }
}
```
**Response:**
```json
{
	"result": { /* integration agent output */ }
}
```

---

### Knowledge Agent (Planned)
**POST /knowledge/run** (to be implemented)
Summarize or fetch knowledge using LLM.

**Request:**
```json
{
	"payload": { "topic": "AI automation" }
}
```
**Response:**
```json
{
	"summary": "...summary text...",
	"raw_response": { /* LLM API response */ }
}
```
