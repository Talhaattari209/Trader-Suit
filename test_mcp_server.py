"""
Test script for Alpaca MCP Server.
Launches the server as a subprocess and sends JSON-RPC messages to verify tools.
"""
import json
import subprocess
import sys
import time

def run_test():
    # command to run the server
    cmd = [sys.executable, "-m", "src.mcp.alpaca_server"]
    
    print(f"Starting server with command: {' '.join(cmd)}")
    
    # Start the server process
    process = subprocess.Popen(
        cmd,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=sys.stderr,
        text=True,
        cwd="C:\\Users\\User\\Downloads\\claude"
    )

    # Helper to send a message and get response
    def send_request(method, params=None, req_id=1):
        msg = {
            "jsonrpc": "2.0",
            "method": method,
            "id": req_id
        }
        if params is not None:
            msg["params"] = params
        
        json_line = json.dumps(msg)
        print(f"\nSending: {json_line}")
        process.stdin.write(json_line + "\n")
        process.stdin.flush()
        
        # Read response
        response_line = process.stdout.readline()
        print(f"Received: {response_line.strip()}")
        return json.loads(response_line)

    try:
        # 1. Initialize
        resp = send_request("initialize", req_id=1)
        assert "result" in resp
        assert "serverInfo" in resp["result"]
        print("[OK] Initialize successful")

        # 2. List Tools
        resp = send_request("tools/list", req_id=2)
        assert "result" in resp
        tools = resp["result"]["tools"]
        tool_names = [t["name"] for t in tools]
        print(f"[OK] Found tools: {tool_names}")
        assert "get_market_data" in tool_names
        assert "submit_order" in tool_names

        # 3. List Resources
        resp = send_request("resources/list", req_id=3)
        assert "result" in resp
        resources = resp["result"]["resources"]
        res_names = [r["name"] for r in resources]
        print(f"[OK] Found resources: {res_names}")

        # 4. Call Tool: get_market_data (using US30 as default)
        # Note: This might make a real API call if keys are set
        print("\nTesting get_market_data...")
        resp = send_request("tools/call", {
            "name": "get_market_data",
            "arguments": {"symbol": "AAPL", "limit": 2}
        }, req_id=4)
        
        if "error" in resp:
            print(f"[WARN] Tool call returned error (expected if keys invalid): {resp['error']}")
        else:
            print("[OK] Tool call successful")
            # print(resp["result"])

    except Exception as e:
        print(f"[FAIL] Test failed: {e}")
    finally:
        process.terminate()

if __name__ == "__main__":
    run_test()
