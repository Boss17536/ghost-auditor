import json
from datetime import datetime
from agent.tinyfish_client import AuditingClient

def audit_slack(tf_key: str, workspace_url: str, tool: str, seat_cost: float, slack_cookie: str = "") -> dict:
    if not tf_key:
        print("[!] No TinyFish API Key provided. Cannot run audit.")
        return {"status": "ERROR", "members": []}
        
    client = AuditingClient(api_key=tf_key)
    
    # Process secure session extraction
    d_val = ""
    if slack_cookie:
        for part in slack_cookie.split(';'):
            part = part.strip()
            if part.startswith('d='):
                d_val = part[2:]
                break
                
    injection_prompt = ""
    if d_val:
        print(f"[*] Secure Session Cookie detected. Injecting bypass protocol into agent prompt.")
        injection_prompt = (
            f"CRITICAL: First, execute the javascript EXACTLY as follows: `document.cookie='d={d_val}; domain=.slack.com; path=/';`. "
            "Then, wait 1 second and forcefully refresh the current page to authenticate the browser. "
        )
    
    goal = (
        f"{injection_prompt}"
        "Navigate to the members/admin page of this workspace. "
        "Find the table showing all members. "
        "Extract every row with these fields: name, email, last_active, role. "
        "Return as a JSON list only. No explanation."
    )
    
    print(f"Starting semantic audit on {tool.capitalize()} workspace: {workspace_url}")
    result_data = client.stream_audit(url=workspace_url, goal=goal)
    
    if result_data.get("status") not in ["SUCCESS", "COMPLETED"]:
        print("Audit did not complete successfully.")
        return {"status": "ERROR", "members": []}
        
    raw_result = result_data.get("result")
    if not raw_result:
        print("No extraction results successfully fetched.")
        return {"status": "ERROR", "members": []}
        
    try:
        if isinstance(raw_result, str):
            # Clean up LLM syntax highlighting or weird formats
            cleaned_result = raw_result.strip()
            if cleaned_result.startswith("```json"):
                cleaned_result = cleaned_result[7:]
            if cleaned_result.endswith("```"):
                cleaned_result = cleaned_result[:-3]
            members = json.loads(cleaned_result.strip())
        else:
            members = raw_result
    except json.JSONDecodeError as e:
        print(f"Failed to parse TinyFish JSON output: {e}")
        return {"status": "ERROR", "members": []}
        
    processed_members = []
    
    for m in members:
        is_ghost = False
        last_active = str(m.get("last_active", "Never")).strip()
        
        if last_active.lower() == "never" or not last_active:
            is_ghost = True
        else:
            try:
                # Expect formats like 2025-07-15
                date_obj = datetime.strptime(last_active, "%Y-%m-%d")
                delta = datetime.now() - date_obj
                if delta.days > 30:
                    is_ghost = True
            except ValueError:
                print(f"Unknown date format encountered ({last_active}). Flagging as potential Ghost.")
                is_ghost = True
                
        # Annotate dictionary directly
        m["is_inactive"] = is_ghost
        processed_members.append(m)
        
    print(f"Processed {len(processed_members)} members with activity checks.")
    return {"status": "SUCCESS", "members": processed_members}
