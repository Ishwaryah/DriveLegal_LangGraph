import asyncio
import time
import httpx
import statistics

URL = "http://127.0.0.1:8001/agent/query"

PAYLOAD = {
    "text": "what is the fine for drunk driving in Tamil Nadu",
    "history": []
}

async def fetch(client, i):
    start = time.time()
    try:
        response = await client.post(URL, json=PAYLOAD, timeout=10.0)
        latency = time.time() - start
        return response.status_code, latency
    except Exception as e:
        return str(e), time.time() - start

async def run_load_test(concurrency=100):
    print(f"Starting load test with {concurrency} concurrent requests...")
    
    async with httpx.AsyncClient() as client:
        start_total = time.time()
        
        tasks = [fetch(client, i) for i in range(concurrency)]
        results = await asyncio.gather(*tasks)
        
        total_time = time.time() - start_total
        
        latencies = [res[1] for res in results if isinstance(res[0], int) and res[0] == 200]
        errors = [res for res in results if not (isinstance(res[0], int) and res[0] == 200)]
        
        print("\n--- Load Test Results ---")
        print(f"Total time taken: {total_time:.2f}s")
        print(f"Successful requests: {len(latencies)} / {concurrency}")
        print(f"Errors: {len(errors)}")
        
        if len(errors) > 0:
            print(f"Sample error: {errors[0]}")
            
        if latencies:
            print(f"Min Latency: {min(latencies):.3f}s")
            print(f"Max Latency: {max(latencies):.3f}s")
            print(f"Average Latency: {statistics.mean(latencies):.3f}s")
            print(f"p50 Latency: {statistics.median(latencies):.3f}s")
            
            latencies.sort()
            p99_idx = int(len(latencies) * 0.99)
            print(f"p99 Latency: {latencies[p99_idx]:.3f}s")

if __name__ == "__main__":
    asyncio.run(run_load_test(100))
