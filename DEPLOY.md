# Deployment Guide - Polaris Product Search MCP

This guide describes how to deploy the Polaris Product Search MCP server to an AWS EC2 instance in the benchmark runner's region with prebuilt SEO indexing and zero-downtime reliability.

---

## 1. Prerequisites and Infrastructure Architecture

- **AWS Region**: Deploy to the same region as the benchmark evaluation runner (e.g., `us-east-1` or `ap-south-1`) to minimize network latency.
- **Instance Sizing**: 
  - Recommended: `t3.medium` or `c6i.large` (2 vCPU, 4GB RAM minimum).
  - Memory footprint: The complete columnar index and catalog facts reside in memory at ~600MB.
- **Security Group Ingress**:
  - Expose port `8000` strictly to the benchmark runner's IP address (or VPC CIDR).
  - Expose port `22` (SSH) only to your admin IP.

---

## 2. Docker Packaging & Index Prebuilding

The Docker image encapsulates the complete catalog dataset (`data/products.json`), verified canonical taxonomy, alias graphs, and precomputed columnar binary structures (`index/columnar.npz`, `index/index_data.pkl`).

### Build Docker Image
```bash
docker build -t polaris-mcp .
```

*Note: The prebuilt index is automatically baked into the image. Startup time is under 3 seconds with zero compilation at runtime.*

---

## 3. Host Header Configuration (`MCP_ALLOWED_HOSTS`)

The MCP Python SDK strictly enforces Host header validation. When receiving requests from external clients or the benchmark runner, requests with disallowed Host headers will be rejected.

Set the `MCP_ALLOWED_HOSTS` environment variable to include your EC2 public IP and host aliases:
```bash
export MCP_ALLOWED_HOSTS="<YOUR_PUBLIC_IP>:8000,<YOUR_PUBLIC_IP>:*,localhost:*,127.0.0.1:*"
```

---

## 4. Running the Container

Run the Docker container in detached mode with automatic restart policies:

```bash
docker run -d \
  --name polaris-search-mcp \
  --restart always \
  -p 8000:8000 \
  -e MCP_ALLOWED_HOSTS="<YOUR_PUBLIC_IP>:8000,<YOUR_PUBLIC_IP>:*,localhost:*,127.0.0.1:*" \
  polaris-mcp
```

### Healthcheck Verification
Check that the container passed its internal health check:
```bash
docker ps
```
The status should display `healthy`.

---

## 5. Verification from Outside the Host

Run these verification commands from your local machine or external test runner:

### 1. Healthz Check
```bash
curl -i http://<YOUR_PUBLIC_IP>:8000/healthz
```
Expected Output:
```http
HTTP/1.1 200 OK
Content-Type: application/json

{"status":"ok","products":105126}
```

### 2. Protocol & GET Rejection Check
```bash
curl -i http://<YOUR_PUBLIC_IP>:8000/mcp
```
Expected Output:
```http
HTTP/1.1 406 Not Acceptable (or 405 Method Not Allowed)
```

### 3. Run Compatibility Smoke Test
Run the official benchmark compatibility smoke test over the public endpoint:
```bash
python smoke_test.py http://<YOUR_PUBLIC_IP>:8000/mcp
```
Expected Output:
```text
PASS: MCP initialization, exact schemas, structured JSON responses, search, and validation
```

---

## 6. Service Management Commands

- **View Live Logs**:
  ```bash
  docker logs -f polaris-search-mcp
  ```
- **Restart Container**:
  ```bash
  docker restart polaris-search-mcp
  ```
- **Stop Container**:
  ```bash
  docker stop polaris-search-mcp
  ```
