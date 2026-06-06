import asyncio
import httpx
import uuid
import json
import time
from decimal import Decimal
from statistics import mean, median
from typing import List, Dict

BASE_URL = "http://localhost:8000"
CONCURRENCY = 50
TRANSFERS_PER_WORKER = 20

# Global counter to limit error logging
_error_log_count = 0
_error_lock = asyncio.Lock()


class StressMetrics:
    def __init__(self):
        self.transfer_times: List[float] = []
        self.transfer_200 = 0
        self.transfer_400 = 0
        self.transfer_403 = 0
        self.transfer_404 = 0
        self.transfer_409 = 0
        self.transfer_500 = 0
        self.transfer_other = 0
        self.statement_times: List[float] = []
        self.statement_200 = 0
        self.lock = asyncio.Lock()
    
    async def record_transfer(self, status: int, elapsed: float, error_text: str = ""):
        global _error_log_count
        async with self.lock:
            if status == 200:
                self.transfer_200 += 1
                self.transfer_times.append(elapsed)
            elif status == 400:
                self.transfer_400 += 1
            elif status == 403:
                self.transfer_403 += 1
            elif status == 404:
                self.transfer_404 += 1
            elif status == 409:
                self.transfer_409 += 1
            elif status == 500:
                self.transfer_500 += 1
                if _error_log_count < 10 and error_text:
                    _error_log_count += 1
                    print(f"  [500 ERROR #{_error_log_count}] {error_text[:200]}")
            else:
                self.transfer_other += 1
                if _error_log_count < 10 and error_text:
                    _error_log_count += 1
                    print(f"  [{status} ERROR #{_error_log_count}] {error_text[:200]}")
    
    async def record_statement(self, status: int, elapsed: float):
        async with self.lock:
            if status == 200:
                self.statement_200 += 1
                self.statement_times.append(elapsed)
    
    def report(self):
        print("\n" + "="*60)
        print("STRESS TEST REPORT")
        print("="*60)
        total = (self.transfer_200 + self.transfer_400 + self.transfer_403 +
                 self.transfer_404 + self.transfer_409 + self.transfer_500 + self.transfer_other)
        print(f"Total transfer attempts: {total}")
        print(f"  Success (200):        {self.transfer_200} ({self.transfer_200/total*100:.1f}%)")
        print(f"  Bad request (400):    {self.transfer_400} ({self.transfer_400/total*100:.1f}%)")
        print(f"  Forbidden (403):      {self.transfer_403} ({self.transfer_403/total*100:.1f}%)")
        print(f"  Not found (404):      {self.transfer_404} ({self.transfer_404/total*100:.1f}%)")
        print(f"  Conflict (409):        {self.transfer_409} ({self.transfer_409/total*100:.1f}%)")
        print(f"  Server error (500):    {self.transfer_500} ({self.transfer_500/total*100:.1f}%)")
        print(f"  Other:                {self.transfer_other} ({self.transfer_other/total*100:.1f}%)")
        if self.transfer_times:
            print(f"  Latency (ms): min={min(self.transfer_times)*1000:.1f} | max={max(self.transfer_times)*1000:.1f} | avg={mean(self.transfer_times)*1000:.1f} | p50={median(self.transfer_times)*1000:.1f}")
        print(f"Statement reads (200): {self.statement_200}")
        if self.statement_times:
            print(f"  Statement latency avg: {mean(self.statement_times)*1000:.1f} ms")
        print("="*60)


async def worker_transfer(
    client: httpx.AsyncClient,
    metrics: StressMetrics,
    customers: List[Dict],
    worker_id: int
):
    for i in range(TRANSFERS_PER_WORKER):
        src = customers[worker_id % len(customers)]
        dst = customers[(worker_id + i + 1) % len(customers)]
        
        amount = 1 + (i % 500)
        idem = f"stress-{worker_id}-{i}-{uuid.uuid4().hex[:8]}"
        
        payload = {
            "source_account_id": src["account_id"],
            "destination_account_number": dst["account_number"],
            "amount": amount,
            "idempotency_key": idem
        }
        
        start = time.perf_counter()
        try:
            r = await client.post(
                f"{BASE_URL}/transactions/transfer",
                json=payload,
                headers={"Authorization": f"Bearer {src['token']}"}
            )
            elapsed = time.perf_counter() - start
            await metrics.record_transfer(r.status_code, elapsed, r.text)
            
            if r.status_code == 200:
                stmt_start = time.perf_counter()
                sr = await client.get(
                    f"{BASE_URL}/transactions/statement/{src['account_id']}?limit=5",
                    headers={"Authorization": f"Bearer {src['token']}"}
                )
                stmt_elapsed = time.perf_counter() - stmt_start
                await metrics.record_statement(sr.status_code, stmt_elapsed)
                
        except httpx.TimeoutException as e:
            elapsed = time.perf_counter() - start
            print(f"  [CLIENT TIMEOUT] Worker {worker_id} req {i} after {elapsed:.1f}s")
            await metrics.record_transfer(504, elapsed, "Client timeout")
        except Exception as e:
            elapsed = time.perf_counter() - start
            print(f"  [CLIENT ERROR] Worker {worker_id} req {i}: {type(e).__name__}: {e}")
            await metrics.record_transfer(500, elapsed, str(e))

async def worker_credit_request(
    client: httpx.AsyncClient,
    customers: List[Dict],
    worker_id: int
):
    for i in range(5):
        src = customers[worker_id % len(customers)]
        payload = {
            "account_id": src["account_id"],
            "amount": 1000,
            "customer_note": f"Stress credit req {worker_id}-{i}"
        }
        try:
            await client.post(
                f"{BASE_URL}/customer/credit-requests",
                json=payload,
                headers={"Authorization": f"Bearer {src['token']}"}
            )
        except Exception:
            pass
        await asyncio.sleep(0.1)


async def health_probe(client: httpx.AsyncClient):
    while True:
        try:
            r = await client.get(f"{BASE_URL}/health/health")
            if r.status_code != 200:
                print(f"[HEALTH ALERT] Status {r.status_code} at {time.strftime('%H:%M:%S')}")
        except Exception as e:
            print(f"[HEALTH ALERT] Down: {e}")
        await asyncio.sleep(2)


async def run_stress():
    with open("scripts/stress_customers.json") as f:
        customers = json.load(f)
    
    if len(customers) < 2:
        raise RuntimeError("Need at least 2 seeded customers. Run seed_dummy_data.py first.")
    
    metrics = StressMetrics()
    limits = httpx.Limits(max_connections=200, max_keepalive_connections=100)
    timeout = httpx.Timeout(30.0)
    
    async with httpx.AsyncClient(limits=limits, timeout=timeout) as client:
        health_task = asyncio.create_task(health_probe(client))
        credit_tasks = [
            asyncio.create_task(worker_credit_request(client, customers, i))
            for i in range(min(10, len(customers)))
        ]
        
        print(f"Starting {CONCURRENCY} workers × {TRANSFERS_PER_WORKER} transfers = {CONCURRENCY*TRANSFERS_PER_WORKER} total...")
        start_time = time.time()
        
        tasks = [
            asyncio.create_task(worker_transfer(client, metrics, customers, i))
            for i in range(CONCURRENCY)
        ]
        
        await asyncio.gather(*tasks)
        elapsed = time.time() - start_time
        
        health_task.cancel()
        for t in credit_tasks:
            t.cancel()
        
        print(f"\nCompleted in {elapsed:.1f} seconds")
        metrics.report()
        
        await verify_consistency(client, customers)


async def verify_consistency(client: httpx.AsyncClient, customers: List[Dict]):
    print("\n--- CONSISTENCY CHECK ---")
    total_balance = Decimal("0")
    issues = 0
    
    for c in customers:
        try:
            r = await client.get(
                f"{BASE_URL}/customer/accounts/{c['account_id']}",
                headers={"Authorization": f"Bearer {c['token']}"}
            )
            if r.status_code == 200:
                bal = Decimal(r.json()["balance"])
                total_balance += bal
                if bal < -500:
                    print(f"  ISSUE: {c['account_id']} balance {bal} exceeds overdraft!")
                    issues += 1
        except Exception as e:
            print(f"  Failed to read balance for {c['account_id']}: {e}")
    
    print(f"Total system balance: {total_balance}")
    print(f"Consistency issues: {issues}")
    if issues == 0:
        print("All balances consistent.")


if __name__ == "__main__":
    asyncio.run(run_stress())