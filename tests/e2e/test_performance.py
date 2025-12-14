"""Performance and load testing for EduSched."""

import pytest
import httpx
import asyncio
import time
from concurrent.futures import ThreadPoolExecutor
import statistics

pytestmark = pytest.mark.performance


class TestPerformance:
    """Performance testing suite."""

    @pytest.mark.asyncio
    async def test_api_response_times(self):
        """TC-PERF-API-001: Measure API response times."""
        client = httpx.AsyncClient(base_url="http://localhost:8000")

        # Test various endpoints
        endpoints = [
            ("/health", 100),     # Health check: < 100ms
            ("/api/v1/schedules", 500),  # List schedules: < 500ms
            ("/api/v1/resources", 500),  # List resources: < 500ms
            ("/api/v1/constraints", 200) # List constraints: < 200ms
        ]

        results = {}

        for endpoint, max_time in endpoints:
            times = []

            # Measure 10 requests
            for _ in range(10):
                start = time.time()
                response = await client.get(endpoint)
                end = time.time()

                assert response.status_code == 200
                times.append((end - start) * 1000)  # Convert to ms

            # Calculate statistics
            avg_time = statistics.mean(times)
            p95_time = statistics.quantiles(times, n=20)[18]  # 95th percentile

            results[endpoint] = {
                "average": avg_time,
                "p95": p95_time,
                "max": max(times)
            }

            # Assert performance requirements
            assert avg_time < max_time, f"Average time for {endpoint} exceeded {max_time}ms"

        print("\nAPI Performance Results:")
        for endpoint, stats in results.items():
            print(f"{endpoint}:")
            print(f"  Average: {stats['average']:.2f}ms")
            print(f"  95th percentile: {stats['p95']:.2f}ms")
            print(f"  Max: {stats['max']:.2f}ms")

        await client.aclose()

    @pytest.mark.asyncio
    async def test_concurrent_request_throughput(self):
        """TC-PERF-API-002: Test concurrent request handling."""
        base_url = "http://localhost:8000"

        async def make_request():
            async with httpx.AsyncClient(base_url=base_url) as client:
                start = time.time()
                response = await client.get("/api/v1/schedules")
                end = time.time()
                return {
                    "status": response.status_code,
                    "duration": end - start
                }

        # Test with 50 concurrent requests
        concurrent_requests = 50
        tasks = [make_request() for _ in range(concurrent_requests)]

        start_time = time.time()
        results = await asyncio.gather(*tasks)
        end_time = time.time()

        # Calculate throughput
        total_time = end_time - start_time
        requests_per_second = concurrent_requests / total_time

        # Verify all requests succeeded
        assert all(r["status"] == 200 for r in results)

        # Assert minimum throughput (50 RPS for read operations)
        assert requests_per_second >= 50, f"Throughput too low: {requests_per_second} RPS"

        print(f"\nThroughput: {requests_per_second:.2f} RPS")
        print(f"Total time: {total_time:.2f} seconds")

    @pytest.mark.asyncio
    async def test_load_sustained(self):
        """TC-PERF-API-003: Test under sustained load."""
        async def worker_worker(worker_id: int, duration: int):
            """Worker that makes requests for specified duration."""
            async with httpx.AsyncClient(base_url="http://localhost:8000") as client:
                start_time = time.time()
                requests_made = 0
                errors = 0

                while time.time() - start_time < duration:
                    # Mix of different operations
                    operations = [
                        client.get("/api/v1/schedules"),
                        client.get("/api/v1/resources"),
                        client.get("/api/v1/constraints"),
                        client.get("/health")
                    ]

                    for op in operations:
                        try:
                            response = await op
                            if response.status_code != 200:
                                errors += 1
                            requests_made += 1
                        except Exception:
                            errors += 1

                    # Small delay between requests
                    await asyncio.sleep(0.1)

                return {
                    "worker_id": worker_id,
                    "requests": requests_made,
                    "errors": errors
                }

        # Start 10 concurrent workers for 60 seconds
        num_workers = 10
        duration = 60

        print(f"\nStarting {num_workers} workers for {duration} seconds...")

        start_time = time.time()
        tasks = [
            worker_worker(i, duration)
            for i in range(num_workers)
        ]

        results = await asyncio.gather(*tasks)
        total_time = time.time() - start_time

        # Calculate metrics
        total_requests = sum(r["requests"] for r in results)
        total_errors = sum(r["errors"] for r in results)
        avg_requests_per_worker = total_requests / num_workers
        overall_rps = total_requests / total_time
        error_rate = total_errors / total_requests if total_requests > 0 else 0

        # Assert performance and reliability
        assert overall_rps >= 100, f"Sustained load too low: {overall_rps} RPS"
        assert error_rate < 0.01, f"Error rate too high: {error_rate*100:.2f}%"

        print(f"\nSustained Load Results:")
        print(f"Total requests: {total_requests}")
        print(f"Total errors: {total_errors}")
        print(f"Average RPS: {overall_rps:.2f}")
        print(f"Error rate: {error_rate*100:.2f}%")
        print(f"Avg requests per worker: {avg_requests_per_worker}")

    @pytest.mark.asyncio
    async def test_memory_usage(self):
        """Test memory usage during operations."""
        import psutil
        import os

        # Get initial memory
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB

        # Perform memory-intensive operations
        async with httpx.AsyncClient(base_url="http://localhost:8000") as client:
            # Create large schedule
            large_data = {
                "name": "Memory Test Schedule",
                "bulk_create": True,
                "num_items": 1000
            }

            response = await client.post("/api/v1/schedules", json=large_data, timeout=300.0)
            assert response.status_code == 201
            schedule_id = response.json()["id"]

            # Perform multiple operations
            for _ in range(10):
                response = await client.get(f"/api/v1/schedules/{schedule_id}")
                assert response.status_code == 200

                response = await client.get(f"/api/v1/schedules/{schedule_id}/assignments")
                assert response.status_code == 200

            # Export large dataset
            response = await client.get(f"/api/v1/schedules/{schedule_id}/export?format=json")
            assert response.status_code == 200

            # Clean up
            await client.delete(f"/api/v1/schedules/{schedule_id}")

        # Check final memory
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = final_memory - initial_memory

        print(f"\nMemory Usage:")
        print(f"Initial: {initial_memory:.2f} MB")
        print(f"Final: {final_memory:.2f} MB")
        print(f"Increase: {memory_increase:.2f} MB")

        # Memory increase should be reasonable (less than 500MB for large operations)
        assert memory_increase < 500, f"Memory leak detected: increased by {memory_increase} MB"

    @pytest.mark.asyncio
    async def test_optimization_performance(self):
        """Test optimization solver performance."""
        client = httpx.AsyncClient(base_url="http://localhost:8000")

        # Test optimization with different problem sizes
        problem_sizes = [
            {"name": "Small", "courses": 50, "rooms": 20, "teachers": 10},
            {"name": "Medium", "courses": 200, "rooms": 50, "teachers": 30},
            {"name": "Large", "courses": 500, "rooms": 100, "teachers": 50}
        ]

        for size in problem_sizes:
            print(f"\nTesting {size['name']} problem size...")

            # Create problem
            problem_data = {
                "name": f"Perf Test {size['name']}",
                "courses": size["courses"],
                "rooms": size["rooms"],
                "teachers": size["teachers"],
                "solver": "heuristic"
            }

            start_time = time.time()
            response = await client.post("/api/v1/schedules", json=problem_data)
            create_time = time.time() - start_time

            assert response.status_code == 201
            schedule_data = response.json()

            # Run optimization
            optimization_data = {
                "schedule_id": schedule_data["id"],
                "solver": "heuristic",
                "time_limit": 60
            }

            start_time = time.time()
            response = await client.post("/api/v1/optimization/run", json=optimization_data)
            assert response.status_code == 202

            job_id = response.json()["job_id"]

            # Wait for completion
            while True:
                response = await client.get(f"/api/v1/optimization/status/{job_id}")
                status = response.json()["status"]

                if status in ["completed", "failed"]:
                    break

                await asyncio.sleep(1)

            optimization_time = time.time() - start_time

            print(f"  Create time: {create_time:.2f}s")
            print(f"  Optimization time: {optimization_time:.2f}s")
            print(f"  Total assignments: {schedule_data.get('total_assignments', 'N/A')}")

            # Performance assertions
            if size["name"] == "Small":
                assert create_time < 5, "Small problem creation too slow"
                assert optimization_time < 10, "Small problem optimization too slow"
            elif size["name"] == "Medium":
                assert create_time < 15, "Medium problem creation too slow"
                assert optimization_time < 30, "Medium problem optimization too slow"
            elif size["name"] == "Large":
                assert create_time < 30, "Large problem creation too slow"
                assert optimization_time < 60, "Large problem optimization too slow"

        await client.aclose()

    @pytest.mark.asyncio
    async def test_database_performance(self):
        """TC-PERF-DB-001: Test database query performance."""
        client = httpx.AsyncClient(base_url="http://localhost:8000")

        # Test query with different result sizes
        queries = [
            {
                "name": "Single Schedule",
                "endpoint": "/api/v1/schedules/schedule-123"
            },
            {
                "name": "List Schedules (paged)",
                "endpoint": "/api/v1/schedules?limit=50"
            },
            {
                "name": "Complex Query",
                "endpoint": "/api/v1/schedules/search?q=programming&dept=CS&status=active"
            },
            {
                "name": "Aggregation Query",
                "endpoint": "/api/v1/analytics/utilization"
            }
        ]

        for query in queries:
            times = []

            # Run query 10 times
            for _ in range(10):
                start = time.time()
                response = await client.get(query["endpoint"])
                end = time.time()

                # Note: Some endpoints might return 404, focus on timing
                if response.status_code in [200, 404]:
                    times.append((end - start) * 1000)

            if times:
                avg_time = statistics.mean(times)
                print(f"\n{query['name']}:")
                print(f"  Average query time: {avg_time:.2f}ms")

                # Database queries should be fast
                assert avg_time < 1000, f"{query['name']} too slow: {avg_time:.2f}ms"

        await client.aclose()

    @pytest.mark.asyncio
    async def test_connection_pool_efficiency(self):
        """TC-PERF-DB-002: Test connection pool behavior."""
        # Create many concurrent clients to test connection pooling
        async def make_db_query():
            async with httpx.AsyncClient(base_url="http://localhost:8000") as client:
                response = await client.get("/api/v1/schedules")
                return response.status_code

        # Launch 100 concurrent requests
        num_requests = 100
        tasks = [make_db_query() for _ in range(num_requests)]

        start_time = time.time()
        results = await asyncio.gather(*tasks)
        end_time = time.time()

        # All should succeed without connection errors
        success_count = sum(1 for r in results if r == 200)

        print(f"\nConnection Pool Test:")
        print(f"Success rate: {success_count}/{num_requests} ({success_count/num_requests*100:.1f}%)")
        print(f"Total time: {end_time - start_time:.2f}s")

        # High success rate indicates efficient connection pooling
        assert success_count >= 95, f"Too many connection failures: {num_requests - success_count}"