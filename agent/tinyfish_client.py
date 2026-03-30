import time
from tinyfish import TinyFish
try:
    from tinyfish.events import StartedEvent, ProgressEvent, CompleteEvent
except ImportError:
    # If the exact package version differs, fallback to duck-typing class names later
    pass

class AuditingClient:
    def __init__(self, api_key: str):
        self.tf = TinyFish(api_key=api_key)
        
    def stream_audit(self, url: str, goal: str) -> dict:
        print("Connecting to TinyFish API...")
        agent = self.tf.agents.create()
        print(f"Agent {agent.id} created successfully.")
        
        run_id = None
        result_json = None
        status = "STARTED"
        
        try:
            for event in agent.stream(url=url, goal=goal):
                event_type = type(event).__name__
                if "StartedEvent" in event_type:
                    run_id = event.run_id
                    print(f"Run {run_id} started. Navigating to layout...")
                elif "ProgressEvent" in event_type:
                    print(f"Progress: {getattr(event, 'message', 'Step complete')}")
                elif "CompleteEvent" in event_type:
                    print(f"Run {getattr(event, 'run_id', run_id)} completed. Status: {getattr(event, 'status', 'SUCCESS')}")
                    result_json = getattr(event, 'result_json', None)
                    status = getattr(event, 'status', 'SUCCESS')
                    if not status or status == "unknown":
                        status = "SUCCESS"
                    break
        except Exception as e:
            print(f"Stream interrupted during execution: {e}")
            if run_id:
                print("Attempting to recover run data via fallback polling...")
                status = "ERROR"
            else:
                return {"status": "ERROR", "error": str(e), "run_id": None}
                
        # CSV trigger / fallback if no result_json
        if not result_json and run_id:
            try:
                print("No JSON result found in stream closure. Attempting API fetch fallback...")
                time.sleep(2)
                run = self.tf.runs.get(run_id)
                status = getattr(run, "status", status)
                result_json = getattr(run, "result_json", None)
                if not result_json:
                    print(f"Fallback check failed to extract JSON payload. Final Run Status: {status}")
                else:
                    print("Recovered result payload from fallback API check.")
            except Exception as e:
                print(f"Fallback API query failed: {e}")
                
        return {
            "status": "SUCCESS" if status in ["success", "SUCCESS", "COMPLETED"] else status,
            "result": result_json,
            "run_id": run_id
        }
