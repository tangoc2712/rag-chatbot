# Project Restructuring Summary

## What Changed

The project has been restructured from a monolithic setup to a **microservices architecture** with two independent services:

### Before (Monolithic)
```
rag-chatbot/
├── airflow/              # Airflow DAGs
├── data/                 # Data files
├── scripts/              # Scripts
├── src/                  # Source code
├── static/               # Web UI
├── tests/                # Tests
├── docker-compose.yml    # Single compose file
├── Dockerfile.airflow    # Airflow dockerfile
└── requirements.txt      # Shared requirements
```

### After (Microservices)
```
rag-chatbot/
├── services/
│   ├── rag-service/              # 🤖 RAG Chatbot Service
│   │   ├── data/                 # Data files
│   │   ├── scripts/              # RAG scripts
│   │   ├── src/                  # FastAPI source
│   │   ├── static/               # Web UI
│   │   ├── tests/                # Tests
│   │   ├── docker-compose.yml    # RAG deployment
│   │   ├── Dockerfile            # RAG dockerfile
│   │   ├── requirements.txt      # RAG dependencies
│   │   ├── .env.example          # RAG environment template
│   │   └── README.md             # RAG documentation
│   │
│   └── airflow/                  # ⚙️ Airflow Service
│       ├── dags/                 # Airflow DAGs
│       ├── config/               # Airflow config
│       ├── docker-compose.yml    # Airflow deployment
│       ├── Dockerfile.airflow    # Airflow dockerfile
│       ├── requirements.txt      # Airflow dependencies
│       ├── .env.example          # Airflow environment template
│       └── README.md             # Airflow documentation
│
├── README.md                     # Project overview
├── DEPLOYMENT.md                 # Deployment guide
├── API_DOCUMENTATION.md          # API reference
└── ARCHITECTURE.md               # Architecture docs
```

## Benefits

### 1. **Independent Deployment**
- Deploy only RAG service for chatbot functionality
- Deploy only Airflow service for embedding pipelines
- No need to run both if you only need one

### 2. **Isolated Dependencies**
- Each service has its own `requirements.txt`
- No dependency conflicts between services
- Easier to update individual services

### 3. **Separate Configuration**
- Each service has its own `.env` file
- Independent Docker Compose configurations
- Different port mappings (RAG: 8000, Airflow: 8080)

### 4. **Better Organization**
- Clear separation of concerns
- Service-specific documentation
- Easier to navigate and maintain

### 5. **Scalability**
- Scale services independently
- Deploy to different servers/clusters
- Optimize resources per service

## Migration Steps Completed

✅ Created `services/rag-service/` directory structure
✅ Moved `data/`, `scripts/`, `src/`, `static/`, `tests/` to RAG service
✅ Created RAG service `docker-compose.yml` with PostgreSQL + FastAPI
✅ Created RAG service `Dockerfile`
✅ Created RAG service `README.md` and `.env.example`

✅ Created `services/airflow/` directory structure
✅ Moved `airflow/dags/`, `airflow/config/` to Airflow service
✅ Created Airflow service `docker-compose.yml` with all components
✅ Copied `Dockerfile.airflow` to Airflow service
✅ Created Airflow service `.env.example`
✅ Updated Airflow service `README.md`

✅ Removed original root-level directories
✅ Removed root-level `docker-compose.yml`, `Dockerfile.airflow`, `requirements.txt`
✅ Updated root `README.md` to reflect new structure
✅ Updated `.gitignore` for new structure
✅ Created `DEPLOYMENT.md` guide

## How to Use

### Deploy RAG Service Only (Most Common)
```bash
cd services/rag-service
cp .env.example .env
# Edit .env with your GOOGLE_API_KEY
docker compose up -d
```

Visit: http://localhost:8000

### Deploy Airflow Service Only
```bash
cd services/airflow
cp .env.example .env
# Edit .env with your GOOGLE_API_KEY
docker compose up -d
```

Visit: http://localhost:8080

### Deploy Both Services
```bash
# Terminal 1
cd services/rag-service
docker compose up -d

# Terminal 2
cd services/airflow
docker compose up -d
```

## Important Notes

### Database Separation
- Each service now has its own PostgreSQL instance
- RAG service uses port 5432
- Airflow service uses port 5433
- This prevents conflicts and allows independent operation

### Environment Files
- Each service has its own `.env` file
- Copy from `.env.example` and configure independently
- Don't commit `.env` files (already in .gitignore)

### Documentation
- **README.md** - Project overview and quick start
- **services/rag-service/README.md** - RAG service details
- **services/airflow/README.md** - Airflow service details
- **DEPLOYMENT.md** - Complete deployment guide
- **API_DOCUMENTATION.md** - API reference
- **ARCHITECTURE.md** - System architecture

## Next Steps

1. **Test RAG Service:**
   ```bash
   cd services/rag-service
   docker compose up -d
   # Wait for services to start
   curl http://localhost:8000/docs
   ```

2. **Test Airflow Service:**
   ```bash
   cd services/airflow
   docker compose up -d
   # Wait for initialization
   open http://localhost:8080
   ```

3. **Run Setup Scripts:**
   ```bash
   cd services/rag-service
   docker compose exec rag-api bash
   python scripts/migrate_db.py
   python scripts/create_chat_history_table.py
   ```

4. **Update Git:**
   ```bash
   git add .
   git commit -m "refactor: split into microservices architecture"
   git push
   ```

## Rollback (If Needed)

If you need to rollback, the old structure is in your git history:
```bash
git log --oneline  # Find commit before restructure
git checkout <commit-hash>
```

## Support

- See individual service README files for detailed documentation
- Check DEPLOYMENT.md for deployment instructions
- Review API_DOCUMENTATION.md for API details
- See ARCHITECTURE.md for system design

## Questions?

Common questions:

**Q: Can I still use both services together?**
A: Yes! Just deploy both services. They work independently but can share data through the database.

**Q: Which service do I need for the chatbot?**
A: Just the RAG service (`services/rag-service/`)

**Q: Do I need Airflow?**
A: Only if you want automated embedding generation. You can manually run scripts in the RAG service.

**Q: How do I update?**
A: Navigate to the specific service directory and run `docker compose pull && docker compose up -d`

**Q: Can I deploy to different servers?**
A: Yes! Each service is completely independent and can be deployed anywhere.
