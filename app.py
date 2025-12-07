import streamlit as st
import http.client
import urllib.parse
import json
import time
from typing import List, Dict, Any, Optional, Tuple
from collections import deque
import concurrent.futures

st.set_page_config(page_title="TrainSurf - Seat Hop Engine", layout="wide", initial_sidebar_state="collapsed")

# Custom CSS for better UI
st.markdown("""
<style>
    .main-header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 2rem;
        border-radius: 15px;
        margin-bottom: 2rem;
        box-shadow: 0 8px 32px rgba(102, 126, 234, 0.3);
    }
    .main-header h1 {
        color: white;
        margin: 0;
        font-size: 2.5rem;
        text-shadow: 2px 2px 4px rgba(0,0,0,0.2);
    }
    .main-header p {
        color: rgba(255,255,255,0.9);
        margin: 0.5rem 0 0 0;
        font-size: 1.1rem;
    }
    .stButton > button {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border: none;
        padding: 0.75rem 2rem;
        font-size: 1.1rem;
        font-weight: 600;
        border-radius: 10px;
        box-shadow: 0 4px 15px rgba(102, 126, 234, 0.4);
        transition: all 0.3s ease;
    }
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(102, 126, 234, 0.6);
    }
    .segment-card {
        background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
        padding: 1.5rem;
        border-radius: 12px;
        margin: 1rem 0;
        border-left: 5px solid #667eea;
        box-shadow: 0 4px 12px rgba(0,0,0,0.1);
    }
    .metric-card {
        background: white;
        padding: 1.5rem;
        border-radius: 12px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.08);
        text-align: center;
        border-top: 4px solid #667eea;
    }
    .progress-text {
        font-size: 1.1rem;
        color: #667eea;
        font-weight: 600;
        margin: 1rem 0;
    }
    div[data-testid="stExpander"] {
        background: white;
        border-radius: 10px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.05);
    }
    label, .stTextInput label, .stTextInput > label > div, div[data-baseweb="base-input"] label {
        color: #000000 !important;
    }
    .stExpander label {
        color: #000000 !important;
    }
</style>
""", unsafe_allow_html=True)

# Header
st.markdown("""
<div class="main-header">
    <h1>🚂 TrainSurf — Seat Hop Engine</h1>
    <p>Find the optimal journey with minimum seat changes using intelligent segment stitching</p>
</div>
""", unsafe_allow_html=True)

# API Configuration
with st.expander("⚙️ Configuration", expanded=True):
    api_key = st.text_input("🔑 RapidAPI Key", type="password", placeholder="Enter your RapidAPI key")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        train_no = st.text_input("🚆 Train Number", placeholder="e.g., 17644")
    with col2:
        source = st.text_input("📍 Source Station", placeholder="e.g., COA")
    with col3:
        destination = st.text_input("🎯 Destination Station", placeholder="e.g., MS")
    
    col4, col5, col6 = st.columns(3)
    with col4:
        date = st.date_input("📅 Date", min_value=st.session_state.get('today', None) or __import__('datetime').date(2025, 12, 6), value=None, format="YYYY-MM-DD")
    with col5:
        class_type = st.text_input("💺 Class", placeholder="e.g., 2A, 3A, SL")
    with col6:
        quota = st.text_input("🎫 Quota", placeholder="e.g., GN, TQ")

debug_mode = st.checkbox("🔍 Show debug information", value=False)

# Memoization cache for API calls
availability_cache = {}

def http_get(path: str, params: Dict[str, str], api_key: str, host: str = "irctc1.p.rapidapi.com", timeout: int = 20) -> Dict[str, Any]:
    """Make HTTP GET request to RapidAPI"""
    query = "?" + urllib.parse.urlencode(params) if params else ""
    conn = http.client.HTTPSConnection(host, timeout=timeout)
    headers = {
        "x-rapidapi-key": api_key,
        "x-rapidapi-host": host,
        "Accept": "application/json",
        "User-Agent": "TrainSurf/2.0"
    }
    try:
        conn.request("GET", f"{path}{query}", headers=headers)
        res = conn.getresponse()
        data = res.read()
        text = data.decode("utf-8", errors="ignore")
        
        if not text:
            return {"error": "empty response", "status_code": res.status}
        
        try:
            return json.loads(text)
        except Exception as e:
            return {"error": f"JSON parse error: {str(e)}", "raw_text": text[:200], "status_code": res.status}
    except Exception as e:
        return {"error": f"Connection error: {str(e)}"}
    finally:
        try:
            conn.close()
        except Exception:
            pass

def get_train_details(train_no: str, api_key: str) -> Dict[str, Any]:
    """Get train details"""
    return http_get("/api/v1/train-details", {"trainNo": train_no}, api_key, host="irctc-train-api.p.rapidapi.com")

def get_live_train_status(train_no: str, api_key: str, start_day: int = 0) -> Dict[str, Any]:
    """Get live train status"""
    return http_get("/api/v1/live-train-status", {"trainNo": train_no, "startDay": str(start_day)}, api_key, host="irctc-train-api.p.rapidapi.com")

def check_seat_availability_raw(train_no: str, from_code: str, to_code: str, date: str, class_type: str, quota: str, api_key: str) -> Dict[str, Any]:
    """Check seat availability for a segment - raw API call"""
    params = {
        "trainNo": train_no,
        "fromStationCode": from_code,
        "toStationCode": to_code,
        "classType": class_type,
        "quota": quota,
        "date": date
    }
    return http_get("/api/v1/checkSeatAvailability", params, api_key)

def extract_station_codes_from_train_details(details_json: Dict[str, Any]) -> List[str]:
    """Extract station codes from train-details API"""
    if "error" in details_json:
        raise ValueError(f"API Error: {details_json['error']}")
    
    if not details_json.get("status"):
        raise ValueError("API returned status: false")
    
    codes = []
    if isinstance(details_json.get("data"), dict):
        train_route = details_json["data"].get("trainRoute")
        if isinstance(train_route, list):
            for station in train_route:
                if isinstance(station, dict):
                    station_name = station.get("stationName", "")
                    if " - " in station_name:
                        parts = station_name.split(" - ")
                        if len(parts) >= 2:
                            code = parts[-1].strip().upper()
                            codes.append(code)
    
    if codes:
        return codes
    raise ValueError("Could not extract station codes")

def extract_station_codes_from_live_status(status_json: Dict[str, Any]) -> List[str]:
    """Extract station codes from live-train-status API"""
    if "error" in status_json:
        raise ValueError(f"API Error: {status_json['error']}")
    
    codes = []
    route = status_json.get("route")
    if isinstance(route, list):
        for station in route:
            if isinstance(station, dict):
                code = station.get("stationCode")
                if code:
                    codes.append(str(code).strip().upper())
    
    if codes:
        return codes
    raise ValueError("Could not extract station codes")

def slice_route_between(codes: List[str], source: str, destination: str) -> List[str]:
    """Slice route between source and destination"""
    src = source.strip().upper()
    dst = destination.strip().upper()
    codes_upper = [c.strip().upper() for c in codes]
    
    try:
        i = codes_upper.index(src)
    except ValueError:
        available = ', '.join(codes[:20])
        raise ValueError(f"❌ Source '{source}' not found.\n\n**Available:** {available}")
    
    try:
        j = codes_upper.index(dst)
    except ValueError:
        available = ', '.join(codes[:20])
        raise ValueError(f"❌ Destination '{destination}' not found.\n\n**Available:** {available}")
    
    if j < i:
        raise ValueError(f"❌ Destination before source in route")
    
    return codes[i:j+1]

def is_available_status(status: str) -> bool:
    """Check if status means available"""
    if not status:
        return False
    
    s = status.strip().upper()
    
    # Explicitly check for NOT AVAILABLE first
    if "NOT AVAILABLE" in s or "NOT_AVAILABLE" in s:
        return False
    
    # Check for confirmed/available seats
    if "AVAILABLE" in s and "NOT" not in s:
        if "AVAILABLE-" in s:
            try:
                parts = s.split("AVAILABLE-")
                if len(parts) > 1:
                    num = int(parts[1].split()[0])
                    return num > 0
            except:
                pass
        return True
    
    if "CNF" in s or "CONFIRM" in s:
        return True
    
    # RAC is available
    if "RAC" in s:
        return True
    
    # Waitlist statuses are NOT available
    if any(wl in s for wl in ["WL", "GNWL", "RLWL", "PQWL", "TQWL", "CKWL"]):
        return False
    
    return False

def parse_availability_for_date(resp: Dict[str, Any], target_date: str) -> Tuple[bool, str]:
    """Parse availability JSON"""
    if not isinstance(resp, dict):
        return False, "INVALID_RESPONSE"
    
    if "error" in resp:
        return False, f"ERROR: {resp.get('error', 'unknown')}"
    
    if resp.get("status") is False:
        return False, "API_STATUS_FALSE"
    
    data = resp.get("data")
    if isinstance(data, list) and len(data) > 0:
        for row in data:
            if isinstance(row, dict):
                row_date = row.get("date", "")
                if row_date == target_date:
                    status = row.get("current_status") or row.get("currentStatus") or row.get("status")
                    if status:
                        status_str = str(status).strip()
                        return is_available_status(status_str), status_str
        
        first = data[0]
        if isinstance(first, dict):
            status = first.get("current_status") or first.get("currentStatus") or first.get("status")
            if status:
                status_str = str(status).strip()
                return is_available_status(status_str), status_str
    
    if isinstance(data, dict):
        avail = data.get("availability")
        if isinstance(avail, list) and len(avail) > 0:
            for row in avail:
                if isinstance(row, dict):
                    row_date = row.get("date", "")
                    if row_date == target_date:
                        status = row.get("status") or row.get("currentStatus")
                        if status:
                            status_str = str(status).strip()
                            return is_available_status(status_str), status_str
            
            first = avail[0]
            if isinstance(first, dict):
                status = first.get("status") or first.get("currentStatus")
                if status:
                    status_str = str(status).strip()
                    return is_available_status(status_str), status_str
    
    return False, "NO_DATA"

def check_segment_parallel(args):
    """Wrapper for parallel segment checking"""
    train_no, from_code, to_code, date, class_type, quota, api_key = args
    cache_key = f"{train_no}|{from_code}|{to_code}|{date}|{class_type}|{quota}"
    
    if cache_key in availability_cache:
        return cache_key, availability_cache[cache_key]
    
    resp = check_seat_availability_raw(train_no, from_code, to_code, date, class_type, quota, api_key)
    time.sleep(0.05)
    
    result = parse_availability_for_date(resp, date)
    return cache_key, result

def check_segment_sequential(train_no: str, from_code: str, to_code: str, date: str, 
                             class_type: str, quota: str, api_key: str) -> Tuple[bool, str]:
    """Check segment sequentially"""
    cache_key = f"{train_no}|{from_code}|{to_code}|{date}|{class_type}|{quota}"
    
    if cache_key in availability_cache:
        return availability_cache[cache_key]
    
    resp = check_seat_availability_raw(train_no, from_code, to_code, date, class_type, quota, api_key)
    time.sleep(0.1)
    
    result = parse_availability_for_date(resp, date)
    availability_cache[cache_key] = result
    
    return result

def find_all_possible_paths(route: List[str], available_segments: List[Tuple[int, int, Dict]]) -> List[List[Dict]]:
    """
    Find ALL possible paths from source to destination using available segments.
    Handles overlapping segments (e.g., if 0→7 and 6→12 exist, they can be stitched).
    """
    n = len(route)
    src_idx = 0
    dst_idx = n - 1
    
    if debug_mode:
        st.write("### 🔍 Finding ALL possible paths")
        st.write(f"Source: {route[src_idx]} (idx {src_idx})")
        st.write(f"Destination: {route[dst_idx]} (idx {dst_idx})")
    
    # Build adjacency graph
    # A segment [from_idx, to_idx] creates a direct edge from from_idx to to_idx
    # AND for overlap handling: if we're at any position between from_idx and to_idx-1,
    # we can still use this segment to reach to_idx
    graph = {i: [] for i in range(n)}
    segment_info = {}
    
    for from_idx, to_idx, seg_info in available_segments:
        # Direct connection: from from_idx to to_idx
        graph[from_idx].append(to_idx)
        segment_info[(from_idx, to_idx)] = seg_info
        
        # Overlap handling: if we're anywhere inside this segment, we can use it to reach the end
        # Example: segment [0, 7] means if we're at positions 1,2,3,4,5,6 we can reach 7
        for pos in range(from_idx + 1, to_idx):
            graph[pos].append(to_idx)
            segment_info[(pos, to_idx)] = seg_info
    
    if debug_mode:
        st.write("**Graph connections:**")
        for pos in range(n):
            if graph[pos]:
                reachable = [f"{r}({route[r]})" for r in sorted(set(graph[pos]))]
                st.write(f"  From {pos}({route[pos]}): → {', '.join(reachable)}")
    
    # DFS to find all paths
    all_paths = []
    
    def dfs(current: int, path: List[int], visited: set):
        if current == dst_idx:
            # Convert to segment list
            segments = []
            for i in range(len(path) - 1):
                from_pos = path[i]
                to_pos = path[i + 1]
                if (from_pos, to_pos) in segment_info:
                    segments.append(segment_info[(from_pos, to_pos)])
            if segments:
                all_paths.append(segments)
            return
        
        # Try all next positions
        for next_pos in sorted(set(graph[current]), reverse=True):
            if next_pos not in visited:
                visited.add(next_pos)
                dfs(next_pos, path + [next_pos], visited)
                visited.remove(next_pos)
    
    dfs(src_idx, [src_idx], {src_idx})
    
    if debug_mode:
        st.write(f"**Found {len(all_paths)} possible path(s)**")
        for idx, path in enumerate(all_paths, 1):
            path_str = ' → '.join([f"{seg['from']}→{seg['to']}" for seg in path])
            st.write(f"Path {idx}: {path_str} ({len(path)} segments = {len(path)-1} transfers)")
    
    return all_paths

def find_optimal_journey(route: List[str], train_no: str, date: str, 
                        class_type: str, quota: str, api_key: str) -> Optional[List[Dict]]:
    """
    OPTIMIZED STRATEGY for comprehensive checking with parallel processing:
    1. Check direct source → destination first (1 call)
    2. Check ALL possible segments in parallel for complete coverage
    3. Use enhanced parallel processing for maximum speed
    """
    
    n = len(route)
    src_idx = 0
    dst_idx = n - 1
    
    progress_placeholder = st.empty()
    api_calls_made = 0
    
    if debug_mode:
        st.write(f"### 🎯 Comprehensive Search Strategy")
        st.write(f"Route: {' → '.join(route)}")
        st.write(f"Total stations: {n}")
    
    # STEP 1: Check direct path first (ALWAYS - most important)
    if debug_mode:
        st.write("### STEP 1: Checking direct path (Priority 1)")
    
    progress_placeholder.markdown('<p class="progress-text">🔍 Checking direct path...</p>', unsafe_allow_html=True)
    
    is_avail, status = check_segment_sequential(train_no, route[src_idx], route[dst_idx], 
                                                date, class_type, quota, api_key)
    api_calls_made += 1
    
    if is_avail:
        if debug_mode:
            st.success(f"✅ Direct available! API calls used: {api_calls_made}")
        progress_placeholder.empty()
        return [{"from": route[src_idx], "to": route[dst_idx], "status": status}]
    
    if debug_mode:
        st.write(f"❌ Direct not available: {status}")
        st.write(f"API calls used: {api_calls_made}")
    
    # STEP 2: Check ALL possible segments
    if debug_mode:
        st.write("### STEP 2: Comprehensive segment checking")
    
    segments_to_check = []
    
    # Check all possible segments
    for i in range(src_idx, dst_idx):
        for j in range(i + 1, dst_idx + 1):
            segments_to_check.append((train_no, route[i], route[j], date, class_type, quota, api_key))
    
    total_to_check = len(segments_to_check)
    
    if debug_mode:
        st.write(f"**Total segments to check: {total_to_check}**")
    
    progress_placeholder.markdown(f'<p class="progress-text">⚡ Checking {total_to_check} segments in parallel...</p>', unsafe_allow_html=True)
    
    # Execute checks with enhanced parallel processing
    progress_bar = st.progress(0)
    with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
        futures = {executor.submit(check_segment_parallel, seg): idx for idx, seg in enumerate(segments_to_check)}
        completed = 0
        for future in concurrent.futures.as_completed(futures):
            cache_key, result = future.result()
            availability_cache[cache_key] = result
            completed += 1
            api_calls_made += 1
            if completed % 10 == 0 or completed == total_to_check:
                progress_bar.progress(completed / total_to_check)
    progress_bar.empty()
    
    if debug_mode:
        st.info(f"**Total API calls made: {api_calls_made}**")
    
    # STEP 3: Collect all available segments
    if debug_mode:
        st.write("### STEP 3: Collecting available segments")
        st.write(f"Analyzing {len(availability_cache)} checked segments")
    
    progress_placeholder.markdown('<p class="progress-text">📊 Analyzing results...</p>', unsafe_allow_html=True)
    
    available_segments = []
    unavailable_count = 0
    
    for cache_key, (is_avail, status) in availability_cache.items():
        parts = cache_key.split("|")
        from_code = parts[1]
        to_code = parts[2]
        
        try:
            from_idx = route.index(from_code)
            to_idx = route.index(to_code)
            
            if is_avail:
                seg_info = {"from": from_code, "to": to_code, "status": status}
                available_segments.append((from_idx, to_idx, seg_info))
                
                if debug_mode:
                    st.write(f"✅ [{from_idx}→{to_idx}] {from_code} → {to_code} ({status})")
            else:
                unavailable_count += 1
        except ValueError:
            pass
    
    if debug_mode:
        st.write(f"**Available: {len(available_segments)} | Unavailable: {unavailable_count}**")
    
    if not available_segments:
        progress_placeholder.empty()
        return None
    
    # STEP 4: Find all possible paths
    if debug_mode:
        st.write("### STEP 4: Finding paths with overlap detection")
    
    progress_placeholder.markdown('<p class="progress-text">🧩 Stitching segments...</p>', unsafe_allow_html=True)
    
    all_paths = find_all_possible_paths(route, available_segments)
    
    if not all_paths:
        progress_placeholder.empty()
        return None
    
    # STEP 5: Select path with minimum transfers
    if debug_mode:
        st.write("### STEP 5: Selecting best path")
    
    all_paths.sort(key=lambda x: len(x))
    best_path = all_paths[0]
    
    if debug_mode:
        st.success(f"✅ Best path: {len(best_path)} bookings, {len(best_path)-1} transfers")
        if len(all_paths) > 1:
            st.info(f"Found {len(all_paths)} total paths")
    
    progress_placeholder.empty()
    return best_path

# ==================== MAIN EXECUTION ====================
if st.button("🚀 Run TrainSurf Algorithm", type="primary", use_container_width=True):
    if not api_key:
        st.error("⚠️ Please enter your RapidAPI Key")
    elif not train_no or not source or not destination or not date or not class_type or not quota:
        st.error("⚠️ Please fill in all fields")
    else:
        # Convert date to string format
        date_str = str(date)
        availability_cache.clear()
        
        try:
            with st.spinner("🔄 Fetching train route..."):
                details_resp = get_train_details(train_no, api_key)
                
                try:
                    station_codes = extract_station_codes_from_train_details(details_resp)
                except Exception:
                    st.info("Trying alternative endpoint...")
                    status_resp = get_live_train_status(train_no, api_key)
                    station_codes = extract_station_codes_from_live_status(status_resp)
            
            st.success(f"✅ Route loaded: {len(station_codes)} stations")
            
            if debug_mode:
                with st.expander("📋 All station codes", expanded=False):
                    for idx, code in enumerate(station_codes):
                        st.markdown(f'<span style="color: #000000;">{idx}: {code}</span>', unsafe_allow_html=True)
            
            sliced = slice_route_between(station_codes, source, destination)
            st.info(f"🗺️ **Journey:** {sliced[0]} → {len(sliced)} stations → {sliced[-1]}")
            
            st.write("### 🧠 TrainSurf - Smart Segment Stitching Algorithm")
            st.write("Checking all segments in parallel and finding path with minimum transfers...")
            
            plan = find_optimal_journey(sliced, train_no, date_str, class_type, quota, api_key)
            
            st.markdown("---")
            st.markdown("## 📊 Results")
            
            if plan:
                seat_changes = len(plan) - 1
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.markdown(f"""
                    <div class="metric-card">
                        <h2 style="color: #667eea; margin: 0;">{len(plan)}</h2>
                        <p style="margin: 0.5rem 0 0 0; color: #666;">Bookings Needed</p>
                    </div>
                    """, unsafe_allow_html=True)
                with col2:
                    st.markdown(f"""
                    <div class="metric-card">
                        <h2 style="color: #667eea; margin: 0;">{seat_changes}</h2>
                        <p style="margin: 0.5rem 0 0 0; color: #666;">Seat Changes</p>
                    </div>
                    """, unsafe_allow_html=True)
                with col3:
                    st.markdown(f"""
                    <div class="metric-card">
                        <h2 style="color: #667eea; margin: 0;">{len(availability_cache)}</h2>
                        <p style="margin: 0.5rem 0 0 0; color: #666;">Segments Checked</p>
                    </div>
                    """, unsafe_allow_html=True)
                
                st.success(f"✅ **Optimal journey found with {seat_changes} seat change(s)**")
                
                st.markdown("### 🎫 Recommended Booking Plan")
                for idx, booking in enumerate(plan, 1):
                    st.markdown(f"""
                    <div class="segment-card">
                        <strong style="font-size: 1.2rem; color: #667eea;">Booking {idx}</strong><br>
                        <span style="font-size: 1.1rem;">{booking['from']} → {booking['to']}</span><br>
                        <span style="color: #28a745; font-weight: 600;">Status: {booking['status']}</span>
                    </div>
                    """, unsafe_allow_html=True)
                
                result = {
                    "success": True,
                    "plan": plan,
                    "seat_changes": seat_changes,
                    "segments_checked": len(availability_cache),
                    "algorithm": "TrainSurf - Smart Segment Stitching"
                }
                
                st.download_button(
                    "📥 Download Full Report",
                    json.dumps(result, indent=2, default=str),
                    file_name=f"trainsurf_{train_no}_{source}-{destination}_{date_str}.json",
                    mime="application/json",
                    use_container_width=True
                )
                
            else:
                st.error("❌ **No available path found for this journey**")
                st.warning(f"Checked {len(availability_cache)} segments but couldn't form complete path")
                
                available_segments = sum(1 for v in availability_cache.values() if v[0])
                st.info(f"**Available segments found:** {available_segments} out of {len(availability_cache)}")
                
                if debug_mode:
                    with st.expander("🔍 Show all checked segments", expanded=False):
                        for cache_key, (is_avail, status) in availability_cache.items():
                            parts = cache_key.split("|")
                            icon = "✅" if is_avail else "❌"
                            st.markdown(f'<span style="color: #000000;">{icon} {parts[1]} → {parts[2]} ({status})</span>', unsafe_allow_html=True)
            
        except ValueError as e:
            st.error(str(e))
        except Exception as e:
            st.error(f"❌ Error: {str(e)}")
            if debug_mode:
                st.exception(e)