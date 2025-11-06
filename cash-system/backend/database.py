import sqlite3
import json
from datetime import datetime
from typing import Optional, List, Dict
import os

DB_PATH = "/vercel/sandbox/cash-system/jobs.db"

def init_db():
    """Initialize the database with required tables"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS jobs (
            id TEXT PRIMARY KEY,
            service_type TEXT NOT NULL,
            status TEXT NOT NULL,
            input_data TEXT NOT NULL,
            output_data TEXT,
            price REAL NOT NULL,
            payment_intent_id TEXT,
            customer_email TEXT,
            created_at TEXT NOT NULL,
            completed_at TEXT,
            error_message TEXT
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS analytics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_type TEXT NOT NULL,
            data TEXT NOT NULL,
            timestamp TEXT NOT NULL
        )
    """)
    
    conn.commit()
    conn.close()

def create_job(job_id: str, service_type: str, input_data: dict, price: float, customer_email: str) -> bool:
    """Create a new job in the database"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO jobs (id, service_type, status, input_data, price, customer_email, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (job_id, service_type, 'pending', json.dumps(input_data), price, customer_email, datetime.utcnow().isoformat()))
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Error creating job: {e}")
        return False

def update_job_status(job_id: str, status: str, output_data: Optional[dict] = None, error_message: Optional[str] = None):
    """Update job status and optionally set output data"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    if status == 'completed':
        cursor.execute("""
            UPDATE jobs 
            SET status = ?, output_data = ?, completed_at = ?
            WHERE id = ?
        """, (status, json.dumps(output_data) if output_data else None, datetime.utcnow().isoformat(), job_id))
    elif status == 'failed':
        cursor.execute("""
            UPDATE jobs 
            SET status = ?, error_message = ?
            WHERE id = ?
        """, (status, error_message, job_id))
    else:
        cursor.execute("""
            UPDATE jobs 
            SET status = ?
            WHERE id = ?
        """, (status, job_id))
    
    conn.commit()
    conn.close()

def get_job(job_id: str) -> Optional[Dict]:
    """Get job details by ID"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM jobs WHERE id = ?", (job_id,))
    row = cursor.fetchone()
    conn.close()
    
    if row:
        job = dict(row)
        job['input_data'] = json.loads(job['input_data'])
        if job['output_data']:
            job['output_data'] = json.loads(job['output_data'])
        return job
    return None

def update_payment_intent(job_id: str, payment_intent_id: str):
    """Update job with payment intent ID"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("""
        UPDATE jobs 
        SET payment_intent_id = ?
        WHERE id = ?
    """, (payment_intent_id, job_id))
    
    conn.commit()
    conn.close()

def log_analytics(event_type: str, data: dict):
    """Log analytics event"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO analytics (event_type, data, timestamp)
            VALUES (?, ?, ?)
        """, (event_type, json.dumps(data), datetime.utcnow().isoformat()))
        
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Error logging analytics: {e}")

def get_stats() -> Dict:
    """Get overall statistics"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) as total, SUM(price) as revenue FROM jobs WHERE status = 'completed'")
    result = cursor.fetchone()
    
    cursor.execute("SELECT COUNT(*) as pending FROM jobs WHERE status IN ('pending', 'processing')")
    pending = cursor.fetchone()
    
    conn.close()
    
    return {
        'total_completed': result[0] or 0,
        'total_revenue': result[1] or 0,
        'pending_jobs': pending[0] or 0
    }
