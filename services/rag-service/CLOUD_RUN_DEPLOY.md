# Cloud Run Deployment - Quick Start

Deploy RAG service with **internal-only access** for secure service-to-service communication.

## Architecture

```
Frontend (Firebase) → Backend (hackathon-ecom-server) → RAG Service (Internal) → Cloud SQL (ndsv-db)
```

## Configuration

- **Project**: `hackathon-478514`
- **Region**: `asia-southeast1`
- **Database**: `ndsv-db` (34.177.103.63)
- **Ingress**: Internal only (not accessible from internet)

## Deployment Steps

### 1. Setup API Key in Secret Manager

**⚠️ NEVER put API keys directly in environment variables - they will be exposed in logs and command history!**

```bash
# Create a new API key at: https://console.cloud.google.com/apis/credentials
# Then store it in Secret Manager:

gcloud secrets create google-api-key \
  --project hackathon-478514 \
  --replication-policy="automatic"

# Add your API key to the secret (replace YOUR_NEW_API_KEY)
echo -n "YOUR_API_KEY_HERE" | gcloud secrets versions add google-api-key \
  --project hackathon-478514 \
  --data-file=-

# Grant Cloud Run service account access to the secret
gcloud secrets add-iam-policy-binding google-api-key \
  --project hackathon-478514 \
  --member="serviceAccount:478514-compute@developer.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"
```

### 2. Build Container Image

```bash
cd services/rag-service

# Build and push to Container Registry
gcloud builds submit \
  --tag gcr.io/hackathon-478514/rag-service \
  --project=hackathon-478514
```

*This takes about 2-3 minutes.*

### 3. Deploy with Internal-Only Access

**Option A: Using Cloud SQL Unix Socket (Recommended)**

```bash
gcloud run deploy rag-service \
  --image gcr.io/hackathon-478514/rag-service:latest \
  --project hackathon-478514 \
  --region asia-southeast1 \
  --platform managed \
  --ingress all \
  --allow-unauthenticated \
  --port 8000 \
  --memory 2Gi \
  --cpu 2 \
  --timeout 300 \
  --max-instances 10 \
  --min-instances 0 \
  --set-env-vars "USE_CLOUD_SQL_SOCKET=true,CLOUD_SQL_CONNECTION_NAME=hackathon-478514:asia-southeast1:ndsv-db,DB_USER=postgres,DB_NAME=postgres" \
  --set-secrets "GOOGLE_API_KEY=google-api-key:latest,DB_PASSWORD=db-password:latest" \
  --add-cloudsql-instances hackathon-478514:asia-southeast1:ndsv-db
```

**Option B: Using TCP/IP Connection**

```bash
gcloud run deploy rag-service \
  --image gcr.io/hackathon-478514/rag-service \
  --project hackathon-478514 \
  --region asia-southeast1 \
  --platform managed \
  --ingress internal \
  --allow-unauthenticated \
  --port 8000 \
  --memory 2Gi \
  --cpu 2 \
  --timeout 300 \
  --max-instances 10 \
  --min-instances 0 \
  --set-env-vars "DB_HOST=34.177.103.63,DB_PORT=5432,DB_USER=postgres,DB_NAME=postgres" \
  --set-secrets "GOOGLE_API_KEY=google-api-key:latest,DB_PASSWORD=db-password:latest"
```

**Key settings:**
- `--ingress internal` - Only accessible within GCP project
- `--allow-unauthenticated` - No auth needed (already internal)
- `--add-cloudsql-instances` - Connects via Unix socket (Option A only)
- `--set-secrets` - Securely inject secrets from Secret Manager
- Traffic stays on Google's private network

**Environment Variables:**
- `USE_CLOUD_SQL_SOCKET` - Set to `true` to use Unix socket connection (more secure)
- `CLOUD_SQL_CONNECTION_NAME` - Format: `PROJECT_ID:REGION:INSTANCE_NAME`
- `DB_HOST` - Database host IP (for TCP/IP connection)
- `DB_PORT` - Database port (default: 5432)
- `DB_USER` - Database username
- `DB_NAME` - Database name

**Secrets (from Secret Manager):**
- `DB_PASSWORD` - Database password (stored as `db-password` secret)
- `GOOGLE_API_KEY` - Google Gemini API key (stored as `google-api-key` secret)

**⚠️ Security Best Practice:** Never use `--set-env-vars` for sensitive data like passwords or API keys. Always use `--set-secrets` with Secret Manager.

### 4. Get Service URL

```bash
# Save the service URL
RAG_URL=$(gcloud run services describe rag-service \
  --project=hackathon-478514 \
  --region=asia-southeast1 \
  --format='value(status.url)')

echo "RAG Service URL: $RAG_URL"
# Example: https://rag-service-xxxxx-as.a.run.app
```

**Note:** This URL only works from within your GCP project (internal traffic).

### 5. Update Backend Service

```bash
# Add RAG_SERVICE_URL to your backend
gcloud run services update hackathon-ecom-server \
  --region=asia-southeast1 \
  --project=hackathon-478514 \
  --set-env-vars="RAG_SERVICE_URL=$RAG_URL"
```

### 6. Backend Code Implementation

Add this to your backend (`hackathon-ecom-server`):

```python
import os
import requests
from fastapi import HTTPException

# Get RAG service URL from environment
RAG_SERVICE_URL = os.getenv("RAG_SERVICE_URL")

def query_rag(message: str, role: str = "admin"):
    """
    Query the RAG service from backend.
    No authentication needed - internal traffic only.
    """
    try:
        response = requests.post(
            f"{RAG_SERVICE_URL}/chat/{role}",
            json={"message": message},
            timeout=30
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        raise HTTPException(
            status_code=500, 
            detail=f"RAG service error: {str(e)}"
        )

# Example API endpoint in your backend
@app.post("/api/chat")
async def chat_endpoint(message: str, role: str = "admin"):
    """
    Frontend calls this endpoint.
    This endpoint calls RAG service internally.
    """
    result = query_rag(message, role)
    return {
        "response": result.get("response"),
        "role": role
    }
```

### 7. Test the Integration

```bash
# Get your backend URL
BACKEND_URL=$(gcloud run services describe hackathon-ecom-server \
  --region=asia-southeast1 \
  --project=hackathon-478514 \
  --format='value(status.url)')

# Test from backend to RAG
curl -X POST "$BACKEND_URL/api/chat" \
  -H "Content-Type: application/json" \
  -d '{"message": "What are the top selling products?", "role": "admin"}'
```

### 8. Verify Internal-Only Access

```bash
# This should FAIL (RAG not accessible from internet)
curl https://rag-service-xxxxx-as.a.run.app/health
# Expected: Error - Forbidden

# This should SUCCEED (called through backend)
curl -X POST "$BACKEND_URL/api/chat" \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello", "role": "visitor"}'
# Expected: {"response": "...", "role": "visitor"}
```

This confirms RAG is only accessible internally! ✅

## Complete Flow

```
✅ Setup API key in Secret Manager (REQUIRED - never use plain text API keys!)
✅ Build container image
✅ Deploy with internal ingress using secrets
✅ Get RAG service URL
✅ Update backend environment variable
✅ Add backend code to call RAG
✅ Test integration
✅ Verify internal-only access
```

## Storing DB Password in Secret Manager (Optional but Recommended)

If you haven't already, store the database password in Secret Manager too:

```bash
# Create secret for database password
gcloud secrets create db-password \
  --project hackathon-478514 \
  --replication-policy="automatic"

# Add the password
echo -n "Huypn456785@1" | gcloud secrets versions add db-password \
  --project hackathon-478514 \
  --data-file=-

# Grant access
gcloud secrets add-iam-policy-binding db-password \
  --project hackathon-478514 \
  --member="serviceAccount:478514-compute@developer.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"
```

## Traffic Flow

1. **User** visits Firebase app → `your-app.web.app`
2. **Frontend** calls backend → `POST /api/chat`
3. **Backend** calls RAG internally → Private network call
4. **RAG** queries database → Returns response
5. **Backend** returns to frontend → Response to user

## Monitoring

```bash
# View RAG service logs
gcloud run services logs tail rag-service \
  --project=hackathon-478514 \
  --region=asia-southeast1

# View backend logs
gcloud run services logs tail hackathon-ecom-server \
  --project=hackathon-478514 \
  --region=asia-southeast1

# Cloud Console
echo "https://console.cloud.google.com/run/detail/asia-southeast1/rag-service/logs?project=hackathon-478514"
```

## Update/Redeploy Service

```bash
cd services/rag-service

# Rebuild
gcloud builds submit \
  --tag gcr.io/hackathon-478514/rag-service \
  --project=hackathon-478514

# Redeploy (automatically uses new image)
gcloud run deploy rag-service \
  --image gcr.io/hackathon-478514/rag-service \
  --project=hackathon-478514 \
  --region=asia-southeast1
```

## Security & Benefits

✅ **RAG service not accessible from internet**  
✅ **Traffic stays on Google's private network**  
✅ **Faster response times** (internal routing)  
✅ **No authentication tokens needed** between services  
✅ **Simplified backend code**  
✅ **Cost-effective** (no extra VPC connector)

## Costs Estimate

- **RAG Service (Cloud Run)**: ~$0-10/month (depends on usage)
- **Container Registry**: ~$0-2/month
- **Network egress**: Free (internal traffic)
- **Total additional cost**: ~$0-15/month

Your existing costs (Cloud SQL, backend) remain the same!

## Troubleshooting

### RAG service not accessible from backend

```bash
# Check ingress setting
gcloud run services describe rag-service \
  --project=hackathon-478514 \
  --region=asia-southeast1 \
  --format='value(spec.template.metadata.annotations."run.googleapis.com/ingress")'
# Should show: internal
```

### Database connection errors

```bash
# Test database connectivity
gcloud sql connect ndsv-db \
  --project=hackathon-478514 \
  --user=postgres
```

### Service won't start

```bash
# Check logs for errors
gcloud run services logs read rag-service \
  --project=hackathon-478514 \
  --region=asia-southeast1 \
  --limit 50

# Common issues:
# - Database connection failed
# - Memory/CPU limits too low
# - Invalid GOOGLE_API_KEY
```

### View service details

```bash
gcloud run services describe rag-service \
  --project=hackathon-478514 \
  --region=asia-southeast1
```

## Next Steps

1. ✅ Deploy RAG service with internal ingress
2. ✅ Update backend with RAG_SERVICE_URL
3. ✅ Test integration from backend
4. Monitor logs and performance
5. Set up Cloud Monitoring alerts (optional)

## Support

- [Cloud Run Documentation](https://cloud.google.com/run/docs)
- [Internal Ingress Guide](https://cloud.google.com/run/docs/securing/ingress)
- Check logs: `gcloud run services logs tail rag-service --project=hackathon-478514`
