# CSPM Real-Time Progress Updates - Fix Summary

**Date**: 2025-01-10
**Issue**: Frontend not updating scan progress in real-time; progress jumps from 0% to 45%, requires manual refresh

---

## 🎯 Root Causes Identified

### 1. **WebSocket Connection Not Established**
- **File**: `app/features/msp/cspm/routes/form_routes.py:927`
- **Problem**: `scanStarted` HTMX trigger was disabled, preventing frontend from opening WebSocket connection
- **Status**: ✅ FIXED

### 2. **WebSocket Event Type Mismatch**
- **Files**: Multiple locations
- **Problem**: Backend sending wrong event types (`"progress"`, `"status_change"`) that JavaScript couldn't handle
- **Status**: ✅ FIXED

### 3. **Current Check Name Not Cleared on Completion**
- **Files**: JavaScript handler + database service
- **Problem**: `current_check` field stayed populated after scan completed, showing "100% CIS_1_3_27"
- **Status**: ✅ FIXED

---

## 🔧 All Changes Made

### **Backend Changes**

#### 1. `app/features/msp/cspm/routes/form_routes.py`
**Line 927**: Re-enabled `scanStarted` WebSocket trigger
```python
# BEFORE (DISABLED):
# response.headers["HX-Trigger-After-Settle"] = f"scanStarted:{{\"scan_id\":\"{scan.scan_id}\"}}"

# AFTER (ENABLED):
response.headers["HX-Trigger-After-Settle"] = f"scanStarted:{{\"scan_id\":\"{scan.scan_id}\"}}"
```

#### 2. `app/features/msp/cspm/routes/webhook_routes.py`
**Line 65**: Fixed event type from `"progress"` to `"status"`
```python
# BEFORE:
"event": "progress",  # JavaScript doesn't handle this!

# AFTER:
"event": "status",  # JavaScript recognizes this
```

#### 3. `app/features/msp/cspm/services/cspm_scan_service.py`
**Line 30**: Added websocket_manager import
```python
from app.features.msp.cspm.services.websocket_manager import websocket_manager
```

**Line 247**: Clear `current_check` in database on terminal status
```python
if status in ["completed", "failed", "cancelled"]:
    scan.completed_at = now_utc
    scan.current_check = None  # ✅ Clear check name
```

**Lines 255-266**: Added WebSocket broadcast on status change
```python
await websocket_manager.broadcast(
    scan_id,
    {
        "event": "status",
        "scan_id": scan_id,
        "status": status,
        "progress_percentage": scan.progress_percentage or 0,
        "current_check": None,
        "error_message": error_message
    }
)
```

#### 4. `app/features/msp/cspm/tasks.py`
**Line 105**: Fixed event type for scan start
```python
# BEFORE:
"event": "status_change",  # Wrong!

# AFTER:
"event": "status",  # Correct
```

**Line 109**: Added `current_check: None`

**Line 159**: Fixed event type for scan failure
```python
"event": "status",  # Changed from "status_change"
```

**Line 162**: Added `current_check: None` on failure

**Line 199**: Fixed event type for scan completion
```python
"event": "status",  # Changed from "status_change"
```

**Line 203**: Added `current_check: None` on completion

### **Frontend Changes**

#### 5. `app/features/msp/cspm/static/js/cspm-scans-table.js`

**Lines 95-99**: Clear `current_check` when scan completes
```javascript
if (payload.status) {
  update.status = payload.status;

  // Clear current_check when scan reaches terminal state
  const normalized = payload.status.toLowerCase();
  if (["completed", "failed", "cancelled"].includes(normalized)) {
    update.current_check = null;
  }
}
```

**Lines 101-103**: Handle `current_check` field from webhook
```javascript
if (payload.current_check) {
  update.current_check = payload.current_check;
}
```

**Lines 76-83**: Added debug logging (for troubleshooting)
```javascript
// DEBUG: Log all incoming messages
console.log("[WebSocket] Received message for scan", scanId, ":", payload);

const eventType = payload?.event;
if (!eventType) {
  console.warn("[WebSocket] Message missing 'event' field:", payload);
  return;
}
```

**Lines 137-170**: Enhanced WebSocket connection logging
```javascript
socket.onopen = () => {
  console.log("[WebSocket] Connected successfully for scan:", scanId);
};

socket.onerror = (error) => {
  console.error("[WebSocket] Error for scan", scanId, ":", error);
  closeScanSocket(scanId);
};

socket.onclose = () => {
  console.log("[WebSocket] Connection closed for scan:", scanId);
  delete scanSockets[scanId];
};
```

**Lines 554-565**: Added debug logging for `scanStarted` event
```javascript
document.body.addEventListener("scanStarted", function (event) {
  const scanId = event?.detail?.scan_id;
  console.log("[Event] scanStarted received, scan_id:", scanId);

  if (!scanId) {
    console.warn("[Event] scanStarted missing scan_id");
    return;
  }

  openScanSocket(scanId);
});
```

---

## 🔄 How It Works Now

### **Complete Flow**

```
1. User clicks "Start Scan"
   ↓
2. Backend creates scan record
   ↓
3. Backend returns HX-Trigger: "scanStarted" with scan_id
   ↓
4. Frontend receives event → Opens WebSocket connection
   ↓
5. PowerShell script executes checks (91 total for L1)
   ↓
6. After EACH check:
   - PowerShell → HTTP POST to /msp/cspm/webhook/progress/{scan_id}
   - Webhook updates database (progress_percentage, current_check)
   - Webhook broadcasts to WebSocketManager
   ↓
7. WebSocketManager pushes to all connected WebSocket clients
   ↓
8. Frontend receives message:
   {
     "event": "status",
     "status": "running",
     "progress_percentage": 5,
     "current_check": "CIS_1_1_5"
   }
   ↓
9. JavaScript updates Tabulator row directly (no DB refresh needed!)
   - Progress bar: 5%
   - Current check: "CIS_1_1_5"
   ↓
10. Scan completes:
    - Backend sets status="completed", current_check=None
    - Broadcasts: {"event":"status", "status":"completed", "current_check":null}
    ↓
11. Frontend updates:
    - Status badge: "Completed" (green)
    - Progress: 100%
    - Current check: [cleared]
```

---

## 📋 Architecture Overview

### **Components**

1. **PowerShell Script** (`Start-Checks.ps1`)
   - Executes compliance checks in batches
   - Sends HTTP POST after each check (line 426)
   - URL: `http://127.0.0.1:8000/msp/cspm/webhook/progress/{scan_id}`

2. **Webhook Route** (`webhook_routes.py`)
   - Receives progress updates from PowerShell
   - Updates database (`update_scan_progress`)
   - Broadcasts to WebSocketManager

3. **WebSocket Manager** (`websocket_manager.py`)
   - Singleton managing all WebSocket connections
   - Broadcasts messages to all connected clients for a scan_id
   - Thread-safe with asyncio locks

4. **WebSocket Endpoint** (`scan_routes.py:350`)
   - FastAPI WebSocket endpoint: `/msp/cspm/scans/ws/{scan_id}`
   - Registers connection with WebSocketManager
   - Sends initial snapshot, then pushes live updates

5. **Frontend JavaScript** (`cspm-scans-table.js`)
   - Listens for `scanStarted` event
   - Opens WebSocket connection
   - Handles incoming messages and updates Tabulator rows

### **Key Event Types**

| Event Type | Source | Purpose |
|------------|--------|---------|
| `"status"` | Webhook, Service, Task | Progress update or status change |
| `"snapshot"` | WebSocket endpoint | Initial scan state on connection |
| `"scan-started"` | (Legacy/unused) | Scan initialization |
| `"results-inserted"` | Task | Results saved to DB |
| `"powershell-finished"` | Task | PowerShell execution complete |

---

## 🧪 Testing Instructions

### **Prerequisites**
1. Backend running on port 8000
2. Celery worker running
3. Redis running (for Celery broker)
4. Browser with DevTools

### **Test Steps**

1. **Open Browser DevTools** (F12) → Console tab
2. **Clear console** (🚫 icon)
3. **Navigate to** `/msp/cspm/scans`
4. **Click "Start Scan"** and select an M365 tenant

### **Expected Console Output**

```javascript
[Event] scanStarted received, scan_id: 12345678-abcd-1234-abcd-123456789012
[WebSocket] Connecting to: ws://localhost:8000/msp/cspm/scans/ws/12345678-abcd-1234-abcd-123456789012
[WebSocket] Connected successfully for scan: 12345678-abcd-1234-abcd-123456789012
[WebSocket] Received message for scan 12345678-abcd-1234-abcd-123456789012 : {event: "snapshot", data: {...}}
[WebSocket] Received message for scan 12345678-abcd-1234-abcd-123456789012 : {event: "status", status: "running", progress_percentage: 1, current_check: "CIS_1_1_1"}
[WebSocket] Received message for scan 12345678-abcd-1234-abcd-123456789012 : {event: "status", status: "running", progress_percentage: 2, current_check: "CIS_1_1_2"}
... (91 total updates)
[WebSocket] Received message for scan 12345678-abcd-1234-abcd-123456789012 : {event: "status", status: "completed", progress_percentage: 100, current_check: null}
[WebSocket] Connection closed for scan: 12345678-abcd-1234-abcd-123456789012
```

### **Expected UI Behavior**

- ✅ Progress bar updates smoothly (1% → 2% → 3% ... → 100%)
- ✅ Current check name displays below progress bar during scan
- ✅ Status badge changes to "Completed" immediately when done
- ✅ Progress shows "100%" with NO check name appended
- ✅ After browser refresh: Still shows clean "100%" (database cleared)

---

## 🐛 Known Issues (As of Last Session)

### **Status: Still Investigating**

The user reported that despite all fixes:
- Real-time updates still not working
- Status badge doesn't change on completion
- Progress still shows check name after completion
- Manual refresh required

### **Possible Remaining Issues**

1. **Backend not restarted after code changes**
   - Solution: Restart uvicorn server to load new code

2. **Celery worker not running or outdated**
   - Solution: Restart celery worker
   - Command: `celery -A app.features.core.celery_app worker --loglevel=info`

3. **Redis not running or connection failed**
   - Solution: Check Redis is running
   - Command: `redis-cli ping` (should return "PONG")

4. **Browser caching old JavaScript**
   - Solution: Hard refresh (Ctrl+Shift+R) or clear cache

5. **WebSocket connection blocked by firewall/proxy**
   - Solution: Check browser network tab for WebSocket status
   - Should see `101 Switching Protocols`

6. **Multiple instances of backend running**
   - Solution: Kill all uvicorn processes and restart
   - Command: `pkill -f uvicorn && .venv/bin/uvicorn app.main:app --reload`

---

## 🔍 Debugging Checklist

If real-time updates still not working, check:

### **1. Console Logs**
- [ ] `[Event] scanStarted received` → HTMX trigger firing?
- [ ] `[WebSocket] Connecting to:` → WebSocket being opened?
- [ ] `[WebSocket] Connected successfully` → Connection established?
- [ ] `[WebSocket] Received message` → Messages being received?

### **2. Network Tab (Browser DevTools)**
- [ ] WebSocket connection shows `101 Switching Protocols`
- [ ] WebSocket stays open (not closing immediately)
- [ ] Messages tab shows incoming JSON messages

### **3. Backend Logs**
- [ ] Webhook receiving POST requests: `"Received progress update"`
- [ ] WebSocketManager broadcasting: `"Broadcast sent to WebSocket clients"`
- [ ] WebSocket connections: `"WebSocket client connected"`

### **4. Code Verification**
```bash
# Verify backend changes applied
grep -n "scanStarted" app/features/msp/cspm/routes/form_routes.py
# Should show line 927 with trigger ENABLED (not commented)

grep -n '"event": "status"' app/features/msp/cspm/routes/webhook_routes.py
# Should show line 65 with "status" not "progress"

grep -n '"event": "status"' app/features/msp/cspm/tasks.py
# Should show lines 105, 159, 199 with "status" not "status_change"
```

---

## 📝 Next Steps (If Issue Persists)

1. **Restart all services**:
   ```bash
   # Kill backend
   pkill -f uvicorn

   # Kill celery
   pkill -f celery

   # Restart backend
   .venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

   # Restart celery worker
   celery -A app.features.core.celery_app worker --loglevel=info
   ```

2. **Clear browser cache completely**
   - Chrome: Settings → Privacy → Clear browsing data → Cached images and files
   - Or use Incognito mode

3. **Test WebSocket directly**:
   - Use a WebSocket client (e.g., websocat, wscat)
   - Connect to: `ws://localhost:8000/msp/cspm/scans/ws/{scan_id}`
   - Check if messages arrive

4. **Enable verbose backend logging**:
   ```python
   # In webhook_routes.py, add:
   logger.info("Broadcasting WebSocket message", scan_id=scan_id, message=message)
   ```

5. **Check Celery task execution**:
   ```bash
   # In celery worker terminal, should see:
   [INFO/MainProcess] Task run_cspm_compliance_scan succeeded
   ```

---

## 📚 Related Files Reference

### **Backend**
- `app/features/msp/cspm/routes/form_routes.py` - Scan form submission, HTMX triggers
- `app/features/msp/cspm/routes/webhook_routes.py` - Progress webhook endpoint
- `app/features/msp/cspm/routes/scan_routes.py` - WebSocket endpoint (line 350)
- `app/features/msp/cspm/services/cspm_scan_service.py` - Scan status/progress updates
- `app/features/msp/cspm/services/websocket_manager.py` - WebSocket broadcast manager
- `app/features/msp/cspm/tasks.py` - Celery task orchestration

### **Frontend**
- `app/features/msp/cspm/static/js/cspm-scans-table.js` - Tabulator table + WebSocket handling
- `app/features/msp/cspm/templates/cspm/scans.html` - Scans page template

### **PowerShell**
- `app/features/msp/cspm/CIS_Microsoft_365_Foundations_Benchmark_v5.0.0/Start-Checks.ps1` - Main scan script

---

## 📞 Support

If issue persists after following all steps:
1. Collect full console logs (copy everything)
2. Collect backend logs (last 100 lines)
3. Collect Celery worker logs
4. Share all three for analysis

**Last Updated**: 2025-01-10 16:00 UTC
**Status**: Debugging in progress - all fixes applied, awaiting user testing feedback
