#!/bin/bash
# Dashboard Functionality Test Script

echo "🧪 Testing SawDisk Dashboard Functionality"
echo "=========================================="
echo ""

BASE_URL="http://localhost:5000"
PASSED=0
FAILED=0

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test function
test_endpoint() {
    local name=$1
    local endpoint=$2
    local expected_status=${3:-200}
    
    echo -n "Testing $name... "
    response=$(curl -s -w "\n%{http_code}" "$BASE_URL$endpoint" 2>/dev/null)
    http_code=$(echo "$response" | tail -n1)
    body=$(echo "$response" | sed '$d')
    
    if [ "$http_code" -eq "$expected_status" ]; then
        echo -e "${GREEN}✓ PASSED${NC} (HTTP $http_code)"
        ((PASSED++))
        return 0
    else
        echo -e "${RED}✗ FAILED${NC} (HTTP $http_code, expected $expected_status)"
        ((FAILED++))
        return 1
    fi
}

# Test function with JSON validation
test_json_endpoint() {
    local name=$1
    local endpoint=$2
    local json_key=$3
    
    echo -n "Testing $name... "
    response=$(curl -s "$BASE_URL$endpoint" 2>/dev/null)
    http_code=$(curl -s -o /dev/null -w "%{http_code}" "$BASE_URL$endpoint" 2>/dev/null)
    
    if [ "$http_code" -eq "200" ]; then
        # Check if JSON is valid and contains expected key
        if echo "$response" | python3 -c "import sys, json; d=json.load(sys.stdin); sys.exit(0 if '$json_key' in d else 1)" 2>/dev/null; then
            echo -e "${GREEN}✓ PASSED${NC} (HTTP $http_code, contains '$json_key')"
            ((PASSED++))
            return 0
        else
            echo -e "${RED}✗ FAILED${NC} (HTTP $http_code, but missing '$json_key')"
            ((FAILED++))
            return 1
        fi
    else
        echo -e "${RED}✗ FAILED${NC} (HTTP $http_code)"
        ((FAILED++))
        return 1
    fi
}

# Test 1: Main Dashboard Page
echo "1. Testing Dashboard Pages"
echo "-------------------------"
test_endpoint "Dashboard (/) " "/"
test_endpoint "Scan Page (/scan)" "/scan"
test_endpoint "Summary Page (/summary)" "/summary"
echo ""

# Test 2: API Endpoints
echo "2. Testing API Endpoints"
echo "------------------------"
test_json_endpoint "System Info API" "/api/system-info" "mounts"
test_json_endpoint "Scan Status API" "/api/scan/status" "status"
test_json_endpoint "Scan History API" "/api/scan/history" "scans"
echo ""

# Test 3: Static Assets
echo "3. Testing Static Assets"
echo "------------------------"
test_endpoint "CSS Stylesheet" "/static/css/style.css"
test_endpoint "JavaScript App" "/static/js/app.js"
echo ""

# Test 4: Detailed API Checks
echo "4. Detailed API Validation"
echo "--------------------------"

# System Info
echo -n "Checking System Info (mounts count)... "
mounts_count=$(curl -s "$BASE_URL/api/system-info" | python3 -c "import sys, json; d=json.load(sys.stdin); print(len(d.get('mounts', [])))" 2>/dev/null)
if [ -n "$mounts_count" ] && [ "$mounts_count" -ge 0 ]; then
    echo -e "${GREEN}✓ PASSED${NC} (Found $mounts_count mount(s))"
    ((PASSED++))
else
    echo -e "${RED}✗ FAILED${NC}"
    ((FAILED++))
fi

# Scan Status
echo -n "Checking Scan Status (is_running field)... "
has_is_running=$(curl -s "$BASE_URL/api/scan/status" | python3 -c "import sys, json; d=json.load(sys.stdin); sys.exit(0 if 'is_running' in d else 1)" 2>/dev/null && echo "yes" || echo "no")
if [ "$has_is_running" = "yes" ]; then
    echo -e "${GREEN}✓ PASSED${NC} (has 'is_running' field)"
    ((PASSED++))
else
    echo -e "${RED}✗ FAILED${NC} (missing 'is_running' field)"
    ((FAILED++))
fi

# Scan History
echo -n "Checking Scan History (scans array)... "
has_scans=$(curl -s "$BASE_URL/api/scan/history" | python3 -c "import sys, json; d=json.load(sys.stdin); sys.exit(0 if 'scans' in d else 1)" 2>/dev/null && echo "yes" || echo "no")
if [ "$has_scans" = "yes" ]; then
    scans_count=$(curl -s "$BASE_URL/api/scan/history" | python3 -c "import sys, json; d=json.load(sys.stdin); print(len(d.get('scans', [])))" 2>/dev/null)
    echo -e "${GREEN}✓ PASSED${NC} (Found $scans_count scan(s) in history)"
    ((PASSED++))
else
    echo -e "${RED}✗ FAILED${NC} (missing 'scans' array)"
    ((FAILED++))
fi

echo ""
echo "=========================================="
echo "Test Results Summary"
echo "=========================================="
echo -e "${GREEN}Passed: $PASSED${NC}"
echo -e "${RED}Failed: $FAILED${NC}"
echo "Total: $((PASSED + FAILED))"
echo ""

if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}✓ All tests passed! Dashboard is working correctly.${NC}"
    exit 0
else
    echo -e "${YELLOW}⚠ Some tests failed. Please check the errors above.${NC}"
    exit 1
fi
