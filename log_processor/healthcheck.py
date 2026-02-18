import requests
import sys
import os

def check_health():
    try:
        # Check if Prometheus metrics endpoint is responding
        # This confirms the event loop is running and the HTTP server is alive
        port = os.getenv("METRICS_PORT", "8080")
        response = requests.get(f"http://localhost:{port}/metrics", timeout=5)
        if response.status_code == 200:
            print("Health check passed: Metrics endpoint is responding.")
            sys.exit(0)
        else:
            print(f"Health check failed: Metrics endpoint returned status {response.status_code}.")
            sys.exit(1)
    except Exception as e:
        print(f"Health check failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    check_health()
