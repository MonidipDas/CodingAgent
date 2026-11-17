# Sandbox coding agent

## Browser server

Install with `pip install .` and build the sandbox image as described below. Configure `GROQ_API_KEY`, `AGENT_ACCESS_TOKEN` (a random secret of at least 32 characters), and `AGENT_WORKSPACE` (an existing disposable repository directory writable by UID 65534) on the server. Keep credentials outside that workspace.

Start the application with `uvicorn server:app --host 127.0.0.1 --port 8000 --workers 1`. Open the browser interface at http://127.0.0.1:8000, enter the access token, and submit a coding task. Users interact through the browser. Server startup is an administrator operation.

For remote hosting, run this process under a service manager on a dedicated Docker-capable VM and put an HTTPS reverse proxy in front of port 8000. Use exactly one application worker. The shared workspace accepts one task at a time and rejects overlapping submissions. Task history is bounded and held in memory, so restarting the server loses it. Changes persist in the configured workspace. This is a single-user initial server implementation, with no account management, durable job queue, or recovery of interrupted tasks. A completed status means the agent process exited successfully, not independent verification of its claims.

The existing GCP script installs dependencies and the sandbox image. Starting and configuring this web service and HTTPS remain deployment steps.

Python CLI agent using Groq through the OpenAI-compatible Python client, scikit-learn TF-IDF retrieval over repository chunks, and the Docker SDK. It repeatedly inspects, edits, and tests a workspace until it reports completion or reaches a bounded step limit.

## Run

Use a dedicated Linux machine with Python 3.11+ and Docker Engine. Install the controller with `pip install .` and build its sandbox with `docker build -f Dockerfile.sandbox -t coding-sandbox:local .`.

Set `GROQ_API_KEY` in the controller environment. Run `coding-agent /absolute/path/to/workspace "Implement the requested change and run tests"`. The workspace must be writable by UID 65534. Use a disposable clone and inspect the resulting diff. Model input includes retrieved source code and execution output.

Commands run as an unprivileged container user with no network, all capabilities dropped, a read-only root filesystem, CPU/memory/PID limits, and a 60-second deadline. Only the workspace is writable. API credentials and the Docker socket are kept outside the sandbox. Docker shares the host kernel, so run this on a dedicated VM for untrusted workloads. The controller requires Docker access and is trusted. Repository retrieval is lexical RAG, capped at 2,000 chunks, and excludes hidden paths. Files placed in the workspace remain accessible to sandbox commands.

Install project-specific build dependencies into a derived sandbox image before running. Commands cannot download packages. The controller runs one foreground task at a time. Completion is the model's report and should be reviewed alongside test output.

## GCP

`deploy.sh PROJECT_ID ZONE` provisions a dedicated Ubuntu Compute Engine VM with Docker and Python, uploads this source, and installs the controller. Requires authenticated gcloud and permissions to create instances and use SSH. VM charges apply. No public service ports or application API are exposed. Access it with gcloud compute ssh, export GROQ_API_KEY in your session, then run the CLI against a disposable writable workspace. The deployment intentionally creates no service account for sandbox workloads.

The implementation has no multi-user accounts, persistent queue, or automatic GitHub publication of generated changes.

The default Groq model is openai/gpt-oss-120b. Override it with AGENT_MODEL or --model. Requests go to https://api.groq.com/openai/v1. The OpenAI library is used as an HTTP client for Groq.

.env.example documents the required environment variables. The CLI reads the process environment and does not automatically load .env files. Export GROQ_API_KEY in your shell or configure it through your runtime secret manager. Keep real credentials outside the repository and sandbox workspace.
