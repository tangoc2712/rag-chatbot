# Deployment Guide for hackathon-478514

Deploy RAG service with **internal-only access** for secure backend-to-backend communication.

## Architecture

```
Frontend (Firebase) → Backend (hackathon-ecom-server) → RAG Service (Internal Only)
                                                              ↓
                                                      Cloud SQL (ndsv-db)
```

## Configuration

- **GCP Project**: `hackathon-478514`
- **Region**: `asia-southeast1`
- **Database**: `ndsv-db` (34.177.103.63)
- **DB Name**: `postgres`
- **Ingress**: Internal (only accessible from your GCP project)

## Step 1: Build Container Image

```bash
cd services/rag-service

# Build and push to Container Registry
gcloud builds submit \
  --tag gcr.io/hackathon-478514/rag-service \
  --project=hackathon-478514
```

This takes about 2-3 minutes.

## Step 2: Deploy to Cloud Run (Internal Only)

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
  --set-env-vars "DB_HOST=34.177.103.63,DB_PORT=5432,DB_USER=postgres,DB_NAME=postgres,DB_PASSWORD=Huypn456785@1,GOOGLE_API_KEY=AIzaSyA7fxxwd5WaZ4Q9vi9Si7QtykqmGq2adqE"
```

**Key settings:**
- `--ingress internal` - Only accessible from your GCP project (not from internet)
- `--allow-unauthenticated` - No auth needed since it's internal-only
- Traffic stays on Google's private network

## Step 3: Get RAG Service URL

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

## Step 4: Update Backend Service

### A. Add Environment Variable to Backend

```bash
# Update your backend service with RAG URL
gcloud run services update hackathon-ecom-server \
  --region=asia-southeast1 \
  --project=hackathon-478514 \
  --set-env-vars="RAG_SERVICE_URL=$RAG_URL"
```

### B. Backend Code Implementation

Add this to your backend (`hackathon-ecom-server`):

```python
import os
import requests
from fastapi import HTTPException

# Get RAG service URL from environment
RAG_SERVICE_URL = os.getenv("RAG_SERVICE_URL")

def query_rag(message: str, role: str = "admin"):
    """
    Query the RAG service from backend
    No authentication needed - internal traffic only
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
        raise HTTPException(status_code=500, detail=f"RAG service error: {str(e)}")

# Example API endpoint in your backend
@app.post("/api/chat")
async def chat_endpoint(message: str, role: str = "admin"):
    """
    Frontend calls this endpoint
    This endpoint calls RAG service internally
    """
    result = query_rag(message, role)
    return {
        "response": result.get("response"),
        "role": role
    }
```

### C. Test from Backend

```bash
# Get your backend URL
BACKEND_URL=$(gcloud run services describe hackathon-ecom-server \
  --region=asia-southeast1 \
  --project=hackathon-478514 \
  --format='value(status.url)')

# Test the integration
curl -X POST "$BACKEND_URL/api/chat" \
  -H "Content-Type: application/json" \
  -d '{"message": "What are the top selling products?", "role": "admin"}'
```

## Step 5: Verify Internal Access

### Test RAG Service is Internal-Only

```bash
# This should FAIL (RAG not accessible from internet)
curl https://rag-service-xxxxx-as.a.run.app/health
# Expected: Error - Forbidden

# This should SUCCEED (called from your backend)
curl -X POST "$BACKEND_URL/api/chat" \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello", "role": "visitor"}'
# Expected: {"response": "...", "role": "visitor"}
```

This confirms RAG is only accessible internally! ✅

## Complete Deployment Flow Summary

```
✅ Step 1: Build container image
✅ Step 2: Deploy with internal ingress
✅ Step 3: Get RAG service URL
✅ Step 4: Update backend environment variable
✅ Step 5: Verify internal-only access
```

## Frontend → Backend → RAG Flow

1. **User visits Firebase app**: `your-app.web.app`
2. **Frontend calls backend**: `POST /api/chat`
3. **Backend calls RAG internally**: Internal network call
4. **RAG queries database**: Returns response
5. **Backend returns to frontend**: Response to user

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

# View in Cloud Console
echo "https://console.cloud.google.com/run/detail/asia-southeast1/rag-service/logs?project=hackathon-478514"
```

## Update/Redeploy

To update the RAG service:

```bash
cd services/rag-service

# Rebuild
gcloud builds submit --tag gcr.io/hackathon-478514/rag-service --project=hackathon-478514

# Redeploy (Cloud Run will automatically use new image)
gcloud run deploy rag-service \
  --image gcr.io/hackathon-478514/rag-service \
  --project=hackathon-478514 \
  --region=asia-southeast1
```

## Security & Benefits

✅ **RAG service is not accessible from internet**  
✅ **Traffic stays on Google's private network**  
✅ **Faster response times (internal routing)**  
✅ **No authentication tokens needed between services**  
✅ **Simplified backend code**  
✅ **Cost-effective (no extra VPC connector needed)**

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

### View service details

```bash
gcloud run services describe rag-service \
  --project=hackathon-478514 \
  --region=asia-southeast1
```

## Cost Estimate

- **RAG Service (Cloud Run)**: ~$0-10/month (depends on usage)
- **Container Registry**: ~$0-2/month
- **Network egress**: Free (internal traffic)
- **Total**: ~$0-15/month additional cost

Your existing costs (Cloud SQL, backend) remain the same! 🚀
