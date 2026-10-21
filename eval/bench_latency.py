#!/usr/bin/env python3
"""Latency benchmark over real HTTP via MCP protocol.

Tests empty-query filter and sort calls with limit=10, offset=0.
Executes:
- 20 warmup calls
- 3 rounds of:
  - 50 calls at concurrency 1
  - 50 calls at concurrency 5
Reports p50, p95, min, max, and error rates.
"""
import asyncio
import json
import statistics
import sys
import time
from pathlib import Path

from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

BENCHMARK_SCENARIOS = [
    {"limit": 10, "offset": 0},
    {"filters": {"category": "Ladieswear"}, "limit": 10, "offset": 0},
    {"filters": {"color": "Black", "max_price": 2000}, "sort_by": "price", "sort_order": "asc", "limit": 10, "offset": 0},
    {"filters": {"min_rating": 4.0}, "sort_by": "rating", "sort_order": "desc", "limit": 10, "offset": 0},
    {"filters": {"audience": "Men", "product_type": "T-shirt"}, "limit": 10, "offset": 0},
]


async def run_single_call(session: ClientSession, args: dict) -> tuple[float, bool]:
    t0 = time.perf_counter()
    try:
        res = await session.call_tool("search_products", args)
        t1 = time.perf_counter()
        lat_ms = (t1 - t0) * 1000.0
        return lat_ms, not res.isError
    except Exception:
        t1 = time.perf_counter()
        return (t1 - t0) * 1000.0, False


async def run_batch(session: ClientSession, num_calls: int, concurrency: int) -> tuple[list[float], int]:
    latencies = []
    errors = 0
    sem = asyncio.Semaphore(concurrency)

    async def worker(idx: int):
        nonlocal errors
        args = BENCHMARK_SCENARIOS[idx % len(BENCHMARK_SCENARIOS)]
        async with sem:
            lat, success = await run_single_call(session, args)
            latencies.append(lat)
            if not success:
                errors += 1

    tasks = [asyncio.create_task(worker(i)) for i in range(num_calls)]
    await asyncio.gather(*tasks)
    return latencies, errors


async def main(url: str):
    print(f"Connecting to MCP server at {url}...")
    async with streamable_http_client(url) as (read, write, _):
        async with ClientSession(read, write) as session:
            init = await session.initialize()
            print(f"Connected! MCP Protocol Version: {init.protocolVersion}")

            # 1. Warmup
            print("Warming up with 20 calls...")
            _, _ = await run_batch(session, num_calls=20, concurrency=1)
            print("Warmup complete.\n")

            # 2. Benchmark 3 rounds
            all_c1_latencies = []
            all_c5_latencies = []
            total_c1_errors = 0
            total_c5_errors = 0

            for r in range(1, 4):
                print(f"=== ROUND {r} / 3 ===")
                # Concurrency 1 (50 calls)
                c1_lats, c1_errs = await run_batch(session, num_calls=50, concurrency=1)
                all_c1_latencies.extend(c1_lats)
                total_c1_errors += c1_errs
                p50_1 = statistics.median(c1_lats)
                p95_1 = sorted(c1_lats)[int(0.95 * len(c1_lats))]
                print(f"  Concurrency 1: 50 calls | p50: {p50_1:.2f} ms | p95: {p95_1:.2f} ms | errors: {c1_errs}")

                # Concurrency 5 (50 calls)
                c5_lats, c5_errs = await run_batch(session, num_calls=50, concurrency=5)
                all_c5_latencies.extend(c5_lats)
                total_c5_errors += c5_errs
                p50_5 = statistics.median(c5_lats)
                p95_5 = sorted(c5_lats)[int(0.95 * len(c5_lats))]
                print(f"  Concurrency 5: 50 calls | p50: {p50_5:.2f} ms | p95: {p95_5:.2f} ms | errors: {c5_errs}")

            # Aggregate Summary
            c1_sorted = sorted(all_c1_latencies)
            c5_sorted = sorted(all_c5_latencies)

            print("\n" + "=" * 65)
            print("BENCHMARK LATENCY SUMMARY REPORT")
            print("=" * 65)
            print(f"Concurrency 1 (150 calls total):")
            print(f"  p50:    {statistics.median(c1_sorted):.2f} ms")
            print(f"  p90:    {c1_sorted[int(0.90 * len(c1_sorted))]:.2f} ms")
            print(f"  p95:    {c1_sorted[int(0.95 * len(c1_sorted))]:.2f} ms")
            print(f"  Min:    {min(c1_sorted):.2f} ms")
            print(f"  Max:    {max(c1_sorted):.2f} ms")
            print(f"  Errors: {total_c1_errors} ({total_c1_errors / len(c1_sorted) * 100:.1f}%)")

            print(f"\nConcurrency 5 (150 calls total):")
            print(f"  p50:    {statistics.median(c5_sorted):.2f} ms")
            print(f"  p90:    {c5_sorted[int(0.90 * len(c5_sorted))]:.2f} ms")
            print(f"  p95:    {c5_sorted[int(0.95 * len(c5_sorted))]:.2f} ms")
            print(f"  Min:    {min(c5_sorted):.2f} ms")
            print(f"  Max:    {max(c5_sorted):.2f} ms")
            print(f"  Errors: {total_c5_errors} ({total_c5_errors / len(c5_sorted) * 100:.1f}%)")
            print("=" * 65)


if __name__ == "__main__":
    url = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8000/mcp"
    asyncio.run(main(url))
