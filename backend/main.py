from fastapi import FastAPI, Request, HTTPException, Response
import os, time
from dotenv import load_dotenv

# Load .env.development only if not running in Docker
if not os.getenv("DOCKER_ENV"):
    load_dotenv(".env.development")

from backend.routers import chat, automation, n8n_integration, knowledge, admin as admin_router, research, summarize, code_gen, planner, quiz, post, scheduler
from backend.utils.env_setup import get_logger
from backend.routers import agents as agents_router
from backend.utils.tracing import setup_tracing, instrument_app
from backend.utils.rate_limit_mw import rate_limit_middleware, RATE_LIMIT_RPM
from backend.routers import auth as auth_router
from backend.utils.auth import verify_api_key_or_jwt, AuthError, JWT_SECRET, JWT_AUDIENCE, JWT_ISSUER, AUTH_REQUIRED
import jwt

# Prometheus metrics
try:
	from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
	HAS_PROM = True
except Exception:
	HAS_PROM = False

from backend.services.scheduler_service import SchedulerService

logger = get_logger()

app = FastAPI()
setup_tracing()
instrument_app(app)
logger.info("LearnLab FastAPI app starting up...")

@app.on_event("startup")
async def startup_event():
    scheduler = SchedulerService()
    scheduler.start()

# CORS
try:
	from fastapi.middleware.cors import CORSMiddleware
	origins = [o.strip() for o in os.getenv("CORS_ORIGINS", "*").split(",") if o.strip()]
	app.add_middleware(
		CORSMiddleware,
		allow_origins=origins if origins != ['*'] else ["*"],
		allow_credentials=True,
		allow_methods=["*"],
		allow_headers=["*"],
	)
except Exception:
	pass

# Metrics
if HAS_PROM:
	REQ_COUNT = Counter('ll_requests_total', 'Requests total', ['method','path','status'])
	REQ_LATENCY = Histogram('ll_request_latency_seconds', 'Request latency', ['method','path'])

	@app.middleware("http")
	async def metrics_middleware(request: Request, call_next):
		start = time.perf_counter()
		response = await call_next(request)
		try:
			lat = time.perf_counter() - start
			REQ_LATENCY.labels(request.method, request.url.path).observe(lat)
			REQ_COUNT.labels(request.method, request.url.path, str(response.status_code)).inc()
		except Exception:
			pass
		return response

# Auth middleware (optional)
# AUTH_REQUIRED imported from utils.auth
API_KEY = os.getenv("API_KEY", "")
PUBLIC_PATHS = {"/", "/status", "/healthz", "/readyz", "/metrics", "/version", "/docs", "/openapi.json", "/auth/login", "/auth/register"}

SCOPE_MAP = [
	{"prefix": "/admin", "scope": "admin"},
	{"prefix": "/knowledge/ingest", "scope": "ingest"},
	{"prefix": "/knowledge/ingest_", "scope": "ingest"},
	{"prefix": "/agents", "scope": "query"},
	{"prefix": "/chat", "scope": "query"},
]

@app.middleware("http")
async def auth_middleware(request: Request, call_next):
	if AUTH_REQUIRED and request.url.path not in PUBLIC_PATHS:
		api_key = request.headers.get("X-API-Key")
		bearer = request.headers.get("Authorization")
		try:
			ok, info = verify_api_key_or_jwt(api_key, bearer)
			if not ok:
				raise AuthError("Unauthorized")
			# Attach user for JWT
			if info and info.get("method") == "jwt":
				claims = info.get("claims") or {}
				request.state.user = {
					"id": claims.get("sub"),
					"email": claims.get("email"),
					"scopes": claims.get("scopes", []),
					"roles": claims.get("roles", []),
				}
			# Scope enforcement for JWT only (API key bypass)
			if (not api_key) and bearer:
				required = None
				for m in SCOPE_MAP:
					if request.url.path.startswith(m["prefix"]):
						required = m["scope"]; break
				if required:
					claims = info.get("claims") or {}
					scopes = claims.get("scopes") or claims.get("scope") or []
					if isinstance(scopes, str): scopes = [scopes]
					roles = claims.get("roles", [])
					if required not in scopes and not (required == "admin" and ("admin" in roles)):
						raise AuthError("Forbidden: missing scope")
		except AuthError as e:
			raise HTTPException(status_code=401, detail=str(e))
	return await call_next(request)

# Register rate limit middleware if configured
if int(float(os.getenv("RATE_LIMIT_RPM", "0"))) > 0:
	app.middleware("http")(rate_limit_middleware)

# Include routers
app.include_router(chat.router, prefix="/chat")
app.include_router(automation.router, prefix="/automate")
app.include_router(n8n_integration.router, prefix="/n8n")
app.include_router(knowledge.router, prefix="/knowledge")
app.include_router(agents_router.router, prefix="/agents")
app.include_router(admin_router.router, prefix="/admin")
app.include_router(auth_router.router, prefix="/auth")
app.include_router(research.router, prefix="/research")
app.include_router(summarize.router, prefix="/summarize")
app.include_router(code_gen.router, prefix="/code")
app.include_router(planner.router)  # Planner routes at /v1/plans
app.include_router(quiz.router, prefix="/quiz")
app.include_router(post.router, prefix="/post")
app.include_router(scheduler.router, prefix="/scheduler")

@app.get("/")
def root():
	logger.info("Root endpoint accessed.")
	return {"message": "Welcome to LearnLab API!"}

@app.get("/status")
def status():
	logger.info("Status endpoint checked.")
	return {"status": "ok", "detail": "API is running"}

@app.get("/debug/env")
def debug_env():
	openai = os.getenv("OPENAI_API_KEY")
	anthropic = os.getenv("ANTHROPIC_API_KEY")
	return {
		"OPENAI_API_KEY_present": bool(openai),
		"OPENAI_API_KEY_prefix": (openai[:6] + "...") if openai else None,
		"ANTHROPIC_API_KEY_present": bool(anthropic),
	}

@app.get("/debug/config")
def debug_config():
    required = [
        "JWT_SECRET",
        "MONGO_URI_DOCKER",
        "OPENAI_API_KEY",
        # Add more required settings as needed
    ]
    config = {k: bool(os.getenv(k)) for k in required}
    return {"ready": all(config.values()), "config": config}

# Health/ready/version/metrics
@app.get("/healthz")
def healthz():
	return {"status": "ok"}

@app.get("/readyz")
def readyz():
	# TODO: check vector store or dependencies
	return {"ready": True}

@app.get("/version")
def version():
	sha = os.getenv("GIT_SHA")
	if not sha:
		try:
			import subprocess
			sha = subprocess.check_output(["git","rev-parse","--short","HEAD"], cwd=os.getcwd(), timeout=2).decode().strip()
		except Exception:
			sha = None
	return {"version": os.getenv("APP_VERSION", "dev"), "git_sha": sha}

if HAS_PROM:
	@app.get("/metrics")
	def metrics():
		return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
