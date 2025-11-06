from fastapi import FastAPI, HTTPException, BackgroundTasks, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel, EmailStr
from typing import Optional, List, Dict
import os
import uuid
from dotenv import load_dotenv
import stripe
import asyncio

from database import init_db, create_job, update_job_status, get_job, update_payment_intent, log_analytics, get_stats
from ai_processor import init_openai, process_job

# Load environment variables
load_dotenv()

# Initialize FastAPI
app = FastAPI(title="Cash System API", version="1.0.0")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize Stripe
stripe.api_key = os.getenv('STRIPE_SECRET_KEY', '')

# Service pricing
PRICING = {
    'resume_optimization': {'base': 35, 'rush': 52.50},
    'cover_letter': {'base': 25, 'rush': 37.50},
    'linkedin_optimization': {'base': 45, 'rush': 67.50},
    'blog_post': {'base': 80, 'rush': 120},
    'product_descriptions': {'base': 10, 'rush': 15},  # per product
    'social_media_content': {'base': 50, 'rush': 75},
    'business_name': {'base': 20, 'rush': 30},
    'email_template': {'base': 30, 'rush': 45},
}

# Pydantic models
class ServiceRequest(BaseModel):
    service_type: str
    input_data: Dict
    customer_email: EmailStr
    rush: bool = False

class PaymentIntent(BaseModel):
    job_id: str

class JobStatus(BaseModel):
    job_id: str

# Initialize database and OpenAI on startup
@app.on_event("startup")
async def startup_event():
    init_db()
    openai_ready = init_openai()
    if not openai_ready:
        print("WARNING: OpenAI API not configured. Set OPENAI_API_KEY in .env file.")
    print("✅ Cash System API is running!")
    print(f"📊 Dashboard: http://localhost:8000")

# Background job processor
async def process_job_background(job_id: str):
    """Process a job in the background"""
    try:
        job = get_job(job_id)
        if not job:
            return
        
        # Update status to processing
        update_job_status(job_id, 'processing')
        
        # Process with AI
        result = await process_job(job['service_type'], job['input_data'])
        
        if 'error' in result:
            update_job_status(job_id, 'failed', error_message=result['error'])
            log_analytics('job_failed', {'job_id': job_id, 'error': result['error']})
        else:
            update_job_status(job_id, 'completed', output_data=result)
            log_analytics('job_completed', {'job_id': job_id, 'service': job['service_type']})
            
            # TODO: Send email notification to customer
            print(f"✅ Job {job_id} completed successfully")
    
    except Exception as e:
        update_job_status(job_id, 'failed', error_message=str(e))
        log_analytics('job_error', {'job_id': job_id, 'error': str(e)})
        print(f"❌ Job {job_id} failed: {e}")

# API Endpoints
@app.get("/", response_class=HTMLResponse)
async def root():
    """Serve the main frontend"""
    try:
        with open('/vercel/sandbox/cash-system/frontend/index.html', 'r') as f:
            return f.read()
    except FileNotFoundError:
        return "<h1>Cash System API</h1><p>Frontend not found. API is running at /docs</p>"

@app.get("/api/services")
async def get_services():
    """Get available services and pricing"""
    services = []
    for service_type, pricing in PRICING.items():
        services.append({
            'id': service_type,
            'name': service_type.replace('_', ' ').title(),
            'base_price': pricing['base'],
            'rush_price': pricing['rush'],
        })
    return {'services': services}

@app.post("/api/quote")
async def get_quote(request: ServiceRequest):
    """Get a price quote for a service"""
    if request.service_type not in PRICING:
        raise HTTPException(status_code=400, detail="Invalid service type")
    
    pricing = PRICING[request.service_type]
    
    # Calculate price based on quantity (for product descriptions)
    quantity = 1
    if request.service_type == 'product_descriptions':
        quantity = len(request.input_data.get('products', []))
        quantity = max(1, min(quantity, 10))  # Limit to 10
    
    base_price = pricing['base'] * quantity
    final_price = pricing['rush'] * quantity if request.rush else base_price
    
    return {
        'service_type': request.service_type,
        'quantity': quantity,
        'base_price': base_price,
        'rush_fee': (pricing['rush'] - pricing['base']) * quantity if request.rush else 0,
        'final_price': final_price,
        'estimated_delivery': '1 hour' if request.rush else '6-12 hours'
    }

@app.post("/api/create-order")
async def create_order(request: ServiceRequest, background_tasks: BackgroundTasks):
    """Create a new order and payment intent"""
    if request.service_type not in PRICING:
        raise HTTPException(status_code=400, detail="Invalid service type")
    
    # Calculate price
    pricing = PRICING[request.service_type]
    quantity = 1
    if request.service_type == 'product_descriptions':
        quantity = len(request.input_data.get('products', []))
        quantity = max(1, min(quantity, 10))
    
    final_price = (pricing['rush'] if request.rush else pricing['base']) * quantity
    
    # Create job
    job_id = str(uuid.uuid4())
    success = create_job(job_id, request.service_type, request.input_data, final_price, request.customer_email)
    
    if not success:
        raise HTTPException(status_code=500, detail="Failed to create job")
    
    # Create Stripe payment intent
    try:
        if stripe.api_key and stripe.api_key != 'sk_test_your-stripe-key-here':
            payment_intent = stripe.PaymentIntent.create(
                amount=int(final_price * 100),  # Convert to cents
                currency='usd',
                metadata={'job_id': job_id},
                receipt_email=request.customer_email,
            )
            
            update_payment_intent(job_id, payment_intent.id)
            
            log_analytics('order_created', {
                'job_id': job_id,
                'service': request.service_type,
                'price': final_price,
                'rush': request.rush
            })
            
            return {
                'job_id': job_id,
                'client_secret': payment_intent.client_secret,
                'amount': final_price
            }
        else:
            # Demo mode - process immediately without payment
            background_tasks.add_task(process_job_background, job_id)
            return {
                'job_id': job_id,
                'demo_mode': True,
                'message': 'Demo mode - job processing started without payment'
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Payment error: {str(e)}")

@app.post("/api/webhook")
async def stripe_webhook(request: Request, background_tasks: BackgroundTasks):
    """Handle Stripe webhooks"""
    payload = await request.body()
    sig_header = request.headers.get('stripe-signature')
    
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, os.getenv('STRIPE_WEBHOOK_SECRET', '')
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    # Handle payment success
    if event['type'] == 'payment_intent.succeeded':
        payment_intent = event['data']['object']
        job_id = payment_intent['metadata'].get('job_id')
        
        if job_id:
            # Start processing the job
            background_tasks.add_task(process_job_background, job_id)
            log_analytics('payment_succeeded', {'job_id': job_id})
    
    return {'status': 'success'}

@app.get("/api/job/{job_id}")
async def get_job_status(job_id: str):
    """Get job status and results"""
    job = get_job(job_id)
    
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    return {
        'job_id': job['id'],
        'status': job['status'],
        'service_type': job['service_type'],
        'created_at': job['created_at'],
        'completed_at': job['completed_at'],
        'output_data': job['output_data'] if job['status'] == 'completed' else None,
        'error_message': job['error_message'] if job['status'] == 'failed' else None
    }

@app.get("/api/stats")
async def get_statistics():
    """Get system statistics"""
    stats = get_stats()
    return stats

@app.post("/api/demo-process/{job_id}")
async def demo_process(job_id: str, background_tasks: BackgroundTasks):
    """Manually trigger job processing (for demo/testing)"""
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    if job['status'] != 'pending':
        raise HTTPException(status_code=400, detail="Job already processed or processing")
    
    background_tasks.add_task(process_job_background, job_id)
    return {'message': 'Job processing started', 'job_id': job_id}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
