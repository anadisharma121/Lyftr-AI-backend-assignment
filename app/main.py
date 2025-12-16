import time
import uuid
import hmac
import hashlib
import datetime
import aiosqlite
from fastapi import FastAPI, Request, HTTPException, Header, Response
from fastapi.responses import JSONResponse, PlainTextResponse
from pydantic import BaseModel, Field
from prometheus_client import generate_latest

from app.config import settings
from app.storage import init_db, insert_message
from app.logging_utils import logger
from app.metrics import HTTP_REQUESTS, WEBHOOK_OUTCOMES, LATENCY
from app.models import WebhookPayload
from fastapi import Query

from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    if not settings.WEBHOOK_SECRET:
        raise RuntimeError("WEBHOOK_SECRET not set")
    await init_db()
    yield

app = FastAPI(lifespan=lifespan)


class WebhookPayload(BaseModel):
    message_id: str = Field(..., min_length=1)
    from_: str = Field(..., alias="from", pattern=r"^\+\d+$")
    to: str = Field(..., pattern=r"^\+\d+$")
    ts: str = Field(..., pattern=r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
    text: str = Field(default="", max_length=4096)



@app.middleware("http")
async def logging_middleware(request: Request, call_next):
    start_time = time.time()
    request_id = str(uuid.uuid4())
    
    request.state.request_id = request_id
    
    response = await call_next(request)
    
    process_time = (time.time() - start_time) * 1000
    
    HTTP_REQUESTS.labels(path=request.url.path, status=response.status_code).inc()
    LATENCY.observe(process_time)
    
    log_data = {
        "ts": datetime.datetime.utcnow().isoformat(),
        "level": "INFO",
        "request_id": request_id,
        "method": request.method,
        "path": request.url.path,
        "status": response.status_code,
        "latency_ms": round(process_time, 2)
    }
    

    if hasattr(request.state, "webhook_log_extras"):
        log_data.update(request.state.webhook_log_extras)
        
    logger.info("request_processed", extra=log_data)
    return response


@app.post("/webhook")
async def webhook(
    request: Request,
    x_signature: str = Header(None)
):

    body_bytes = await request.body()
    
    if not x_signature:
        WEBHOOK_OUTCOMES.labels(result="invalid_signature").inc()
        request.state.webhook_log_extras = {"result": "invalid_signature"}
        return JSONResponse({"detail": "invalid signature"}, status_code=401)
        
    expected_sig = hmac.new(
        settings.WEBHOOK_SECRET.encode(),
        body_bytes,
        hashlib.sha256
    ).hexdigest()
    
    if not hmac.compare_digest(x_signature, expected_sig):
        WEBHOOK_OUTCOMES.labels(result="invalid_signature").inc()
        request.state.webhook_log_extras = {"result": "invalid_signature"}
        return JSONResponse({"detail": "invalid signature"}, status_code=401)


    try:
        data = await request.json()
        payload = WebhookPayload(**data)
    except Exception as e:
        WEBHOOK_OUTCOMES.labels(result="validation_error").inc()
        request.state.webhook_log_extras = {"result": "validation_error"}
        raise HTTPException(status_code=422, detail=str(e))


    row_data = {
        "message_id": payload.message_id,
        "from": payload.from_,
        "to": payload.to,
        "ts": payload.ts,
        "text": payload.text,
        "created_at": datetime.datetime.utcnow().isoformat() + "Z"
    }
    
    inserted = await insert_message(row_data)
    
    if inserted:
        result = "created"
        dup = False
    else:
        result = "duplicate"
        dup = True
        
    WEBHOOK_OUTCOMES.labels(result=result).inc()
    request.state.webhook_log_extras = {
        "message_id": payload.message_id, 
        "dup": dup, 
        "result": result
    }
    
    return {"status": "ok"}

@app.get("/messages")
async def list_messages(
   
    limit: int = Query(50, ge=1, le=100), 
    offset: int = Query(0, ge=0),
    from_: str = Query(None, alias="from"), 
    since: str = None,
    q: str = None
):
    
    db_path = settings.DATABASE_URL.replace("sqlite:///", "")
    
    where_clauses = []
    params = {}
    
    if from_:
        where_clauses.append("from_msisdn = :from_val")
        params["from_val"] = from_
    if since:
        where_clauses.append("ts >= :since_val")
        params["since_val"] = since
    if q:
        where_clauses.append("text LIKE :q_val")
        params["q_val"] = f"%{q}%"
        
    where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"
    
    async with aiosqlite.connect(db_path) as db:
        db.row_factory = aiosqlite.Row
        

        count_query = f"SELECT COUNT(*) as count FROM messages WHERE {where_sql}"
        async with db.execute(count_query, params) as cursor:
            total = (await cursor.fetchone())['count']
            

        data_query = f"""
            SELECT message_id, from_msisdn as 'from', to_msisdn as 'to', ts, text 
            FROM messages 
            WHERE {where_sql} 
            ORDER BY ts ASC, message_id ASC 
            LIMIT :limit OFFSET :offset
        """
        params.update({"limit": limit, "offset": offset})
        
        async with db.execute(data_query, params) as cursor:
            rows = await cursor.fetchall()
            data = [dict(row) for row in rows]
            
    return {"data": data, "total": total, "limit": limit, "offset": offset}

@app.get("/stats")
async def get_stats():
    db_path = settings.DATABASE_URL.replace("sqlite:///", "")
    async with aiosqlite.connect(db_path) as db:
        db.row_factory = aiosqlite.Row
        

        basic_query = """
            SELECT 
                COUNT(*) as total, 
                COUNT(DISTINCT from_msisdn) as senders,
                MIN(ts) as first_ts,
                MAX(ts) as last_ts
            FROM messages
        """
        async with db.execute(basic_query) as cursor:
            basic = await cursor.fetchone()
            

        senders_query = """
            SELECT from_msisdn as 'from', COUNT(*) as count
            FROM messages
            GROUP BY from_msisdn
            ORDER BY count DESC
            LIMIT 10
        """
        async with db.execute(senders_query) as cursor:
            senders_rows = await cursor.fetchall()
            
    return {
        "total_messages": basic['total'],
        "senders_count": basic['senders'],
        "messages_per_sender": [dict(r) for r in senders_rows],
        "first_message_ts": basic['first_ts'],
        "last_message_ts": basic['last_ts']
    }

@app.get("/health/live")
async def health_live():
    return Response(status_code=200)

@app.get("/health/ready")
async def health_ready():
    if not settings.WEBHOOK_SECRET:
        return Response(status_code=503)
    try:
        db_path = settings.DATABASE_URL.replace("sqlite:///", "")
        async with aiosqlite.connect(db_path) as db:
            await db.execute("SELECT 1")
        return Response(status_code=200)
    except:
        return Response(status_code=503)

@app.get("/metrics")
async def metrics():
    return PlainTextResponse(generate_latest())