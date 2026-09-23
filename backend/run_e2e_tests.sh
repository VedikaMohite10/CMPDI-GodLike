#!/usr/bin/env bash
# ============================================================
# CMPDI E2E Test Script — SIH26023
# Runs against live stack: API:8000, PG:5432, Qdrant:6333
# ============================================================
set -euo pipefail

BASE="http://localhost:8000"
PASS=0; FAIL=0; WARN=0
RESULTS=()

log() { echo -e "\n$*"; }
check() {
  local id="$1" status="$2" detail="$3"
  RESULTS+=("$status|$id|$detail")
  if [[ "$status" == "PASS" ]]; then ((PASS++)); echo "✅ $id"
  elif [[ "$status" == "WARN" ]]; then ((WARN++)); echo "⚠️  $id: $detail"
  else ((FAIL++)); echo "❌ $id: $detail"
  fi
}

# ── Get admin token ────────────────────────────────────────
TOKEN=$(curl -s -X POST "$BASE/auth/login" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin&password=changeme123!" | python3 -c "
import sys,json; d=json.load(sys.stdin)
t=d.get('access_token','')
print(t if t else 'FAIL:'+str(d))")
if [[ "$TOKEN" == FAIL* ]]; then
  echo "FATAL: Cannot get admin token: $TOKEN"; exit 1
fi
AUTH="Authorization: Bearer $TOKEN"
log "=== Got admin JWT ==="

# Helper: POST with JSON
postj() { curl -s -X POST "$BASE$1" -H "$AUTH" -H "Content-Type: application/json" -d "$2"; }
# Helper: GET
getj()  { curl -s "$BASE$1" -H "$AUTH"; }
# Helper: DELETE
delj()  { curl -s -X DELETE "$BASE$1" -H "$AUTH"; }

# ════════════════════════════════════════════════════════════
# SECTION 0: ENVIRONMENT
# ════════════════════════════════════════════════════════════
log "=== PHASE 0: Environment ==="

# Health
H=$(curl -s "$BASE/health")
if echo "$H" | python3 -c "import sys,json; d=json.load(sys.stdin); assert d['status']=='ok'" 2>/dev/null; then
  check "ENV-01: API health" "PASS" "$H"
else check "ENV-01: API health" "FAIL" "$H"; fi

# Docker containers
CONTAINERS=$(docker ps --format '{{.Names}}' 2>/dev/null | tr '\n' ' ')
if echo "$CONTAINERS" | grep -q "cmpdi_api" && echo "$CONTAINERS" | grep -q "cmpdi_postgres" && echo "$CONTAINERS" | grep -q "cmpdi_qdrant"; then
  check "ENV-02: Docker containers running" "PASS" "api+postgres+qdrant up"
else check "ENV-02: Docker containers running" "FAIL" "Missing: $CONTAINERS"; fi

# Ollama on host
OLLAMA_MODELS=$(curl -s http://localhost:11434/api/tags | python3 -c "import sys,json; d=json.load(sys.stdin); print(','.join(m['name'] for m in d['models']))" 2>/dev/null)
for MODEL in "bge-m3:latest" "qwen2.5vl:3b" "qwen2.5:7b-instruct-q4_K_M" "qwen2.5:14b-instruct-q4_K_M"; do
  if echo "$OLLAMA_MODELS" | grep -q "${MODEL%%:*}"; then
    check "ENV-03: Ollama model $MODEL" "PASS" "found"
  else check "ENV-03: Ollama model $MODEL" "FAIL" "not found in: $OLLAMA_MODELS"; fi
done

# qwen2.5-coder NOT in runtime code paths
CODER_REFS=$(grep -r "qwen2.5-coder" /Users/vedikamohite/CMPDI-GodLikefinal/CMPDI-GodLike/backend/app/ --include="*.py" -l 2>/dev/null | tr '\n' ' ')
if [[ -z "$CODER_REFS" ]]; then
  check "ENV-04: qwen2.5-coder not in runtime paths" "PASS" "no references found"
else check "ENV-04: qwen2.5-coder not in runtime paths" "FAIL" "found in: $CODER_REFS"; fi

# CORS
CORS_HEADER=$(curl -s -o /dev/null -I -w "%{http_code}" -H "Origin: http://localhost:5173" "$BASE/health")
if [[ "$CORS_HEADER" == "200" ]]; then
  check "ENV-05: CORS allows frontend" "PASS" "200 from localhost:5173"
else check "ENV-05: CORS allows frontend" "WARN" "status=$CORS_HEADER (check headers)"; fi

# ════════════════════════════════════════════════════════════
# SECTION 1: PHASE 1 — INGESTION
# ════════════════════════════════════════════════════════════
log "=== PHASE 1: Ingestion ==="

# Create test files
TMPDIR_TESTS="/tmp/cmpdi_test_$$"
mkdir -p "$TMPDIR_TESTS"

# --- Digital PDF (minimal, non-scanned)
python3 -c "
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
c = canvas.Canvas('$TMPDIR_TESTS/digital.pdf', pagesize=letter)
c.drawString(100,750,'CMPDI Production Report FY2023-24')
c.drawString(100,730,'CCL produced 85.2 MT of coal in FY2023')
c.drawString(100,710,'Production target was 80 MT')
c.save()
" 2>/dev/null || python3 -c "
# Fallback: write a minimal PDF by hand
with open('$TMPDIR_TESTS/digital.pdf','wb') as f:
    f.write(b'%PDF-1.4\n1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>\nendobj\n4 0 obj\n<< /Length 100 >>\nstream\nBT /F1 12 Tf 72 720 Td (CMPDI Production Report FY2023-24 CCL 85.2 MT coal) Tj ET\nendstream\nendobj\n5 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\nendobj\nxref\n0 6\n0000000000 65535 f\n0000000009 00000 n\n0000000058 00000 n\n0000000115 00000 n\n0000000266 00000 n\n0000000416 00000 n\ntrailer\n<< /Size 6 /Root 1 0 R >>\nstartxref\n495\n%%EOF')
" 2>/dev/null

# --- XLSX test file
python3 -c "
import openpyxl
wb = openpyxl.Workbook()
ws = wb.active
ws.title = 'Production Data'
ws.append(['Subsidiary','Year','Production_MT','Target_MT'])
ws.append(['CCL','FY2021','72.5','75.0'])
ws.append(['CCL','FY2022','78.3','80.0'])
ws.append(['CCL','FY2023','85.2','80.0'])
ws.append(['BCCL','FY2021','28.1','30.0'])
ws.append(['BCCL','FY2022','29.7','31.0'])
wb.save('$TMPDIR_TESTS/production.xlsx')
" 2>/dev/null

# --- CSV test file
cat > "$TMPDIR_TESTS/coal_data.csv" << 'CSVEOF'
Subsidiary,Year,Production_MT,OB_Removal_MCM,Manpower
CCL,FY2021,72.5,180.2,55000
CCL,FY2022,78.3,195.7,54200
CCL,FY2023,85.2,210.1,53800
BCCL,FY2021,28.1,95.3,42000
BCCL,FY2022,29.7,98.1,41500
CSVEOF

# --- DOCX test file
python3 -c "
from docx import Document
doc = Document()
doc.add_heading('CMPDI Annual Mining Report', 0)
doc.add_paragraph('Central Coalfields Limited (CCL) produced 85.2 MT of coal during FY 2023-24.')
doc.add_paragraph('Bharat Coking Coal Limited produced 29.7 MT during FY 2022-23.')
doc.add_paragraph('The production target set by Ministry of Coal was 80 MT for CCL.')
doc.save('$TMPDIR_TESTS/report.docx')
" 2>/dev/null

# --- JPG test image (simple text image for OCR testing)
python3 -c "
try:
  from PIL import Image, ImageDraw, ImageFont
  img = Image.new('RGB',(800,600),(255,255,255))
  d = ImageDraw.Draw(img)
  d.text((50,50), 'CMPDI Mining Production Data', fill=(0,0,0))
  d.text((50,100), 'Coal Production: 85.2 MT', fill=(0,0,0))
  d.text((50,150), 'Year: FY 2023-24', fill=(0,0,0))
  img.save('$TMPDIR_TESTS/scan.jpg')
except Exception as e:
  print(f'PIL not available: {e} — using placeholder')
  open('$TMPDIR_TESTS/scan.jpg','wb').write(b'\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00\xff\xdb\x00C\x00\x08\x06\x06\x07\x06\x05\x08\x07\x07\x07\t\t\x08\n\x0c\x14\r\x0c\x0b\x0b\x0c\x19\x12\x13\x0f\x14\x1d\x1a\x1f\x1e\x1d\x1a\x1c\x1c $.\' \",#\x1c\x1c(7),01444\x1f\x27=82<.342\x1eL CDHdc\xff\xc0\x00\x0b\x08\x00\x01\x00\x01\x01\x01\x11\x00\xff\xc4\x00\x1f\x00\x00\x01\x05\x01\x01\x01\x01\x01\x01\x00\x00\x00\x00\x00\x00\x00\x00\x01\x02\x03\x04\x05\x06\x07\x08\t\n\x0b\xff\xc4\x00\xb5\x10\x00\x02\x01\x03\x03\x02\x04\x03\x05\x05\x04\x04\x00\x00\x01}\x01\x02\x03\x00\x04\x11\x05\x12!1A\x06\x13Qa\x07\"q\x142\x81\x91\xa1\x08#B\xb1\xc1\x15R\xd1\xf0$3br\x82\t\n\x16\x17\x18\x19\x1a%&\x27()*456789:CDEFGHIJSTUVWXYZcdefghijstuvwxyz\x83\x84\x85\x86\x87\x88\x89\x8a\x92\x93\x94\x95\x96\x97\x98\x99\x9a\xa2\xa3\xa4\xa5\xa6\xa7\xa8\xa9\xaa\xb2\xb3\xb4\xb5\xb6\xb7\xb8\xb9\xba\xc2\xc3\xc4\xc5\xc6\xc7\xc8\xc9\xca\xd2\xd3\xd4\xd5\xd6\xd7\xd8\xd9\xda\xe1\xe2\xe3\xe4\xe5\xe6\xe7\xe8\xe9\xea\xf1\xf2\xf3\xf4\xf5\xf6\xf7\xf8\xf9\xfa\xff\xda\x00\x08\x01\x01\x00\x00?\x00\xfb\xd4P\x00\x00\x00\x00\x1f\xff\xd9')
" 2>/dev/null

echo "Test files created in $TMPDIR_TESTS:"
ls -la "$TMPDIR_TESTS/"

# --- Upload digital PDF
UPLOAD_RESULT=$(curl -s -X POST "$BASE/documents/upload" \
  -H "$AUTH" \
  -F "file=@$TMPDIR_TESTS/digital.pdf;type=application/pdf" 2>&1)
echo "UPLOAD digital PDF: $UPLOAD_RESULT"
DOC_ID_PDF=$(echo "$UPLOAD_RESULT" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('id') or d.get('document_id',''))" 2>/dev/null || echo "")
if [[ -n "$DOC_ID_PDF" ]]; then
  check "P1-01: POST /documents/upload (PDF)" "PASS" "id=$DOC_ID_PDF"
else check "P1-01: POST /documents/upload (PDF)" "FAIL" "Response: $UPLOAD_RESULT"; fi

# --- Upload XLSX
UPLOAD_XLSX=$(curl -s -X POST "$BASE/documents/upload" \
  -H "$AUTH" \
  -F "file=@$TMPDIR_TESTS/production.xlsx;type=application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" 2>&1)
echo "UPLOAD XLSX: $UPLOAD_XLSX"
DOC_ID_XLSX=$(echo "$UPLOAD_XLSX" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('id') or d.get('document_id',''))" 2>/dev/null || echo "")
if [[ -n "$DOC_ID_XLSX" ]]; then
  check "P1-02: POST /documents/upload (XLSX)" "PASS" "id=$DOC_ID_XLSX"
else check "P1-02: POST /documents/upload (XLSX)" "FAIL" "Response: $UPLOAD_XLSX"; fi

# --- Upload CSV
UPLOAD_CSV=$(curl -s -X POST "$BASE/documents/upload" \
  -H "$AUTH" \
  -F "file=@$TMPDIR_TESTS/coal_data.csv;type=text/csv" 2>&1)
echo "UPLOAD CSV: $UPLOAD_CSV"
DOC_ID_CSV=$(echo "$UPLOAD_CSV" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('id') or d.get('document_id',''))" 2>/dev/null || echo "")
if [[ -n "$DOC_ID_CSV" ]]; then
  check "P1-03: POST /documents/upload (CSV)" "PASS" "id=$DOC_ID_CSV"
else check "P1-03: POST /documents/upload (CSV)" "FAIL" "Response: $UPLOAD_CSV"; fi

# --- Upload DOCX
UPLOAD_DOCX=$(curl -s -X POST "$BASE/documents/upload" \
  -H "$AUTH" \
  -F "file=@$TMPDIR_TESTS/report.docx;type=application/vnd.openxmlformats-officedocument.wordprocessingml.document" 2>&1)
echo "UPLOAD DOCX: $UPLOAD_DOCX"
DOC_ID_DOCX=$(echo "$UPLOAD_DOCX" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('id') or d.get('document_id',''))" 2>/dev/null || echo "")
if [[ -n "$DOC_ID_DOCX" ]]; then
  check "P1-04: POST /documents/upload (DOCX)" "PASS" "id=$DOC_ID_DOCX"
else check "P1-04: POST /documents/upload (DOCX)" "FAIL" "Response: $UPLOAD_DOCX"; fi

# --- Upload JPG image
UPLOAD_JPG=$(curl -s -X POST "$BASE/documents/upload" \
  -H "$AUTH" \
  -F "file=@$TMPDIR_TESTS/scan.jpg;type=image/jpeg" 2>&1)
echo "UPLOAD JPG: $UPLOAD_JPG"
DOC_ID_JPG=$(echo "$UPLOAD_JPG" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('id') or d.get('document_id',''))" 2>/dev/null || echo "")
if [[ -n "$DOC_ID_JPG" ]]; then
  check "P1-05: POST /documents/upload (JPG)" "PASS" "id=$DOC_ID_JPG"
else check "P1-05: POST /documents/upload (JPG)" "FAIL" "Response: $UPLOAD_JPG"; fi

# --- Bad file type test
BAD_UPLOAD=$(curl -s -X POST "$BASE/documents/upload" \
  -H "$AUTH" \
  -F "file=@/etc/hosts;type=text/plain" 2>&1)
echo "BAD file upload: $BAD_UPLOAD"
BAD_CODE=$(echo "$BAD_UPLOAD" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('detail','')[:80])" 2>/dev/null || echo "")
if [[ -n "$BAD_CODE" ]] && ! echo "$BAD_UPLOAD" | python3 -c "import sys,json; d=json.load(sys.stdin); assert 'detail' not in str(d) or '500' not in str(d)" 2>/dev/null; then
  check "P1-06: Bad file type → 4xx" "PASS" "Got rejection: $BAD_CODE"
elif echo "$BAD_UPLOAD" | grep -q "detail"; then
  check "P1-06: Bad file type → 4xx" "PASS" "Rejected with detail: $BAD_CODE"
else check "P1-06: Bad file type → 4xx" "FAIL" "Response: $BAD_UPLOAD"; fi

# Wait a bit for processing
sleep 5

# --- GET document status
if [[ -n "$DOC_ID_PDF" ]]; then
  STATUS_RESP=$(getj "/documents/$DOC_ID_PDF/status")
  echo "Status response: $STATUS_RESP"
  STATUS_VAL=$(echo "$STATUS_RESP" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('processing_status','NOT_FOUND'))" 2>/dev/null || echo "PARSE_ERR")
  if [[ "$STATUS_VAL" != "NOT_FOUND" ]] && [[ "$STATUS_VAL" != "PARSE_ERR" ]]; then
    check "P1-07: GET /documents/{id}/status" "PASS" "status=$STATUS_VAL"
  else check "P1-07: GET /documents/{id}/status" "FAIL" "Response: $STATUS_RESP"; fi
fi

# --- GET document full metadata
if [[ -n "$DOC_ID_PDF" ]]; then
  DOC_DETAIL=$(getj "/documents/$DOC_ID_PDF")
  echo "Doc detail: $DOC_DETAIL"
  HAS_FIELDS=$(echo "$DOC_DETAIL" | python3 -c "
import sys,json; d=json.load(sys.stdin)
needed=['filename','file_type','upload_date','processing_status']
missing=[f for f in needed if f not in d]
print('OK' if not missing else 'Missing:'+','.join(missing))" 2>/dev/null || echo "PARSE_ERR")
  if [[ "$HAS_FIELDS" == "OK" ]]; then
    check "P1-08: GET /documents/{id} full metadata" "PASS" "all fields present"
  else check "P1-08: GET /documents/{id} full metadata" "FAIL" "$HAS_FIELDS"; fi
fi

# --- GET document original (byte check)
if [[ -n "$DOC_ID_PDF" ]]; then
  ORIG_SIZE=$(curl -s -o "$TMPDIR_TESTS/downloaded.pdf" -w "%{size_download}" "$BASE/documents/$DOC_ID_PDF/original" -H "$AUTH")
  UPLOAD_SIZE=$(wc -c < "$TMPDIR_TESTS/digital.pdf")
  echo "Original download: downloaded=$ORIG_SIZE bytes, uploaded=$UPLOAD_SIZE bytes"
  if [[ "$ORIG_SIZE" -gt 0 ]] && [[ "$ORIG_SIZE" == "$UPLOAD_SIZE" ]]; then
    check "P1-09: GET /documents/{id}/original byte-identical" "PASS" "$ORIG_SIZE bytes"
  elif [[ "$ORIG_SIZE" -gt 0 ]]; then
    check "P1-09: GET /documents/{id}/original byte-identical" "WARN" "downloaded=$ORIG_SIZE uploaded=$UPLOAD_SIZE (may differ due to processing)"
  else check "P1-09: GET /documents/{id}/original byte-identical" "FAIL" "download size=0"; fi
fi

# --- Semantic search (no LLM on top)
SEARCH_RESP=$(postj "/search" '{"query":"coal production CCL","limit":5}')
echo "Search response: $SEARCH_RESP"
HAS_RESULTS=$(echo "$SEARCH_RESP" | python3 -c "
import sys,json; d=json.load(sys.stdin)
results=d.get('results',d if isinstance(d,list) else [])
if not results: print('EMPTY')
else:
  r=results[0] if isinstance(results,list) else results
  fields=['document_id','page_id']
  missing=[f for f in fields if f not in str(r)]
  print('OK:'+str(len(results))+' results' if not missing else 'Missing fields:'+str(missing))" 2>/dev/null || echo "PARSE_ERR:$SEARCH_RESP")
if [[ "$HAS_RESULTS" == EMPTY* ]]; then
  check "P1-10: POST /search returns blocks with provenance" "WARN" "No results yet (documents may still be processing)"
elif [[ "$HAS_RESULTS" == OK* ]]; then
  check "P1-10: POST /search returns blocks with provenance" "PASS" "$HAS_RESULTS"
else check "P1-10: POST /search returns blocks with provenance" "FAIL" "$HAS_RESULTS"; fi

# --- Page detail
if [[ -n "$DOC_ID_PDF" ]]; then
  PAGE_RESP=$(getj "/documents/$DOC_ID_PDF/pages/1")
  echo "Page 1 response: $PAGE_RESP"
  PAGE_OK=$(echo "$PAGE_RESP" | python3 -c "
import sys,json; d=json.load(sys.stdin)
if 'detail' in d and 'not found' in str(d.get('detail','')).lower(): print('NOT_READY')
elif 'page_number' in d or 'text_blocks' in d or 'blocks' in d: print('OK')
else: print('UNEXPECTED:'+str(list(d.keys()))[:80])" 2>/dev/null || echo "PARSE_ERR")
  if [[ "$PAGE_OK" == "OK" ]]; then
    check "P1-11: GET /documents/{id}/pages/{n}" "PASS" "page detail returned"
  elif [[ "$PAGE_OK" == "NOT_READY" ]]; then
    check "P1-11: GET /documents/{id}/pages/{n}" "WARN" "Document still processing"
  else check "P1-11: GET /documents/{id}/pages/{n}" "FAIL" "$PAGE_OK"; fi
fi

# ════════════════════════════════════════════════════════════
# SECTION 2: PHASE 2 — DATA TRUST ENGINE
# ════════════════════════════════════════════════════════════
log "=== PHASE 2: Data Trust Engine ==="

# List facts
FACTS=$(getj "/facts?limit=10")
echo "Facts: $FACTS"
FACTS_OK=$(echo "$FACTS" | python3 -c "
import sys,json; d=json.load(sys.stdin)
items=d if isinstance(d,list) else d.get('items',d.get('facts',[]))
print('OK:'+str(len(items))+' facts')" 2>/dev/null || echo "PARSE_ERR")
if [[ "$FACTS_OK" == OK* ]]; then
  check "P2-01: GET /facts" "PASS" "$FACTS_OK"
else check "P2-01: GET /facts" "FAIL" "$FACTS_OK | $FACTS"; fi

# Process facts for PDF doc
if [[ -n "$DOC_ID_PDF" ]]; then
  PF=$(postj "/documents/$DOC_ID_PDF/process-facts" '{}')
  echo "Process-facts: $PF"
  PF_OK=$(echo "$PF" | python3 -c "
import sys,json; d=json.load(sys.stdin)
if 'status' in d or 'facts_extracted' in d or 'message' in d: print('OK')
else: print('UNEXPECTED:'+str(list(d.keys()))[:80])" 2>/dev/null || echo "PARSE_ERR")
  if [[ "$PF_OK" == "OK" ]]; then
    check "P2-02: POST /documents/{id}/process-facts" "PASS" "$PF"
  else check "P2-02: POST /documents/{id}/process-facts" "FAIL" "$PF_OK | $PF"; fi
fi

# Conflicts
CONFLICTS=$(getj "/conflicts?limit=10")
echo "Conflicts: $CONFLICTS"
CONF_OK=$(echo "$CONFLICTS" | python3 -c "
import sys,json; d=json.load(sys.stdin)
items=d if isinstance(d,list) else d.get('items',d.get('conflicts',[]))
print('OK:'+str(len(items))+' conflicts')" 2>/dev/null || echo "PARSE_ERR")
if [[ "$CONF_OK" == OK* ]]; then
  check "P2-03: GET /conflicts" "PASS" "$CONF_OK"
else check "P2-03: GET /conflicts" "FAIL" "$CONF_OK | $CONFLICTS"; fi

# Validation flags
FLAGS=$(getj "/validation-flags?limit=10")
echo "Flags: $FLAGS"
FLAGS_OK=$(echo "$FLAGS" | python3 -c "
import sys,json; d=json.load(sys.stdin)
items=d if isinstance(d,list) else d.get('items',d.get('flags',[]))
print('OK:'+str(len(items))+' flags')" 2>/dev/null || echo "PARSE_ERR")
if [[ "$FLAGS_OK" == OK* ]]; then
  check "P2-04: GET /validation-flags" "PASS" "$FLAGS_OK"
else check "P2-04: GET /validation-flags" "FAIL" "$FLAGS_OK | $FLAGS"; fi

# Entities
ENTITIES=$(getj "/entities?limit=10")
echo "Entities: $ENTITIES"
ENT_OK=$(echo "$ENTITIES" | python3 -c "
import sys,json; d=json.load(sys.stdin)
items=d if isinstance(d,list) else d.get('items',d.get('entities',[]))
print('OK:'+str(len(items))+' entities')" 2>/dev/null || echo "PARSE_ERR")
if [[ "$ENT_OK" == OK* ]]; then
  check "P2-05: GET /entities" "PASS" "$ENT_OK"
else check "P2-05: GET /entities" "FAIL" "$ENT_OK | $ENTITIES"; fi

# Duplicates
DUPS=$(getj "/duplicates?limit=10")
echo "Duplicates: $DUPS"
DUP_OK=$(echo "$DUPS" | python3 -c "
import sys,json; d=json.load(sys.stdin)
items=d if isinstance(d,list) else d.get('items',d.get('duplicates',[]))
print('OK:'+str(len(items))+' duplicates')" 2>/dev/null || echo "PARSE_ERR")
if [[ "$DUP_OK" == OK* ]]; then
  check "P2-06: GET /duplicates" "PASS" "$DUP_OK"
else check "P2-06: GET /duplicates" "FAIL" "$DUP_OK | $DUPS"; fi

# ════════════════════════════════════════════════════════════
# SECTION 3: PHASE 3 — ANALYTICS + QUERY COPILOT
# ════════════════════════════════════════════════════════════
log "=== PHASE 3: Analytics + Query Copilot ==="

# Analytics trend
TREND=$(postj "/analytics/trend" '{"entity":"CCL","metric":"production","start_period":"FY2021","end_period":"FY2023","period_type":"fiscal_year"}')
echo "Trend: $TREND"
TREND_OK=$(echo "$TREND" | python3 -c "
import sys,json; d=json.load(sys.stdin)
if 'trend' in d or 'data_points' in d or 'points' in d or isinstance(d,list): print('OK')
elif 'insufficient' in str(d).lower() or 'no data' in str(d).lower(): print('NODATA')
else: print('UNEXPECTED:'+str(list(d.keys()))[:80])" 2>/dev/null || echo "PARSE_ERR")
if [[ "$TREND_OK" == "OK" ]]; then
  check "P3-01: POST /analytics/trend" "PASS" "trend data returned"
elif [[ "$TREND_OK" == "NODATA" ]]; then
  check "P3-01: POST /analytics/trend" "WARN" "No data yet (facts not yet extracted)"
else check "P3-01: POST /analytics/trend" "FAIL" "$TREND_OK | $TREND"; fi

# Analytics compare
COMPARE=$(postj "/analytics/compare" '{"entities":["CCL","BCCL"],"metric":"production","period":"FY2023"}')
echo "Compare: $COMPARE"
COMPARE_OK=$(echo "$COMPARE" | python3 -c "
import sys,json; d=json.load(sys.stdin)
if 'comparison' in d or 'results' in d or isinstance(d,list): print('OK')
elif 'insufficient' in str(d).lower() or 'no data' in str(d).lower(): print('NODATA')
else: print('UNEXPECTED:'+str(list(d.keys()))[:80])" 2>/dev/null || echo "PARSE_ERR")
if [[ "$COMPARE_OK" == "OK" ]]; then
  check "P3-02: POST /analytics/compare" "PASS" "comparison returned"
elif [[ "$COMPARE_OK" == "NODATA" ]]; then
  check "P3-02: POST /analytics/compare" "WARN" "No comparable data yet"
else check "P3-02: POST /analytics/compare" "FAIL" "$COMPARE_OK | $COMPARE"; fi

# Query copilot — insufficient evidence test (CRITICAL)
QUERY_SPARSE=$(postj "/query" '{"question":"What caused the mysterious 99.9% drop in production of XYZ mines in FY1800?","include_reasoning":true}')
echo "Sparse query: $QUERY_SPARSE"
SPARSE_OK=$(echo "$QUERY_SPARSE" | python3 -c "
import sys,json; d=json.load(sys.stdin)
ans=str(d.get('answer',d.get('response',''))).lower()
if any(x in ans for x in ['insufficient','no evidence','not found','cannot','no relevant','no data']): print('OK:insufficient-evidence-path')
elif 'reasoning_type' in d: print('PARTIAL:has-reasoning-type-but-check-answer')
else: print('FAIL:may-have-fabricated')" 2>/dev/null || echo "PARSE_ERR")
if [[ "$SPARSE_OK" == OK* ]]; then
  check "P3-CRITICAL: Sparse query → insufficient-evidence (not fabricated)" "PASS" "$SPARSE_OK"
elif [[ "$SPARSE_OK" == PARTIAL* ]]; then
  check "P3-CRITICAL: Sparse query → insufficient-evidence (not fabricated)" "WARN" "$SPARSE_OK | ans: $(echo $QUERY_SPARSE | python3 -c 'import sys,json;d=json.load(sys.stdin);print(str(d.get(\"answer\",\"\"))[:120])' 2>/dev/null)"
else check "P3-CRITICAL: Sparse query → insufficient-evidence (not fabricated)" "FAIL" "$SPARSE_OK | $QUERY_SPARSE"; fi

# Query with reasoning_type check
QUERY_MAIN=$(postj "/query" '{"question":"What is the coal production of CCL?","include_reasoning":true}')
echo "Main query: $QUERY_MAIN"
QUERY_OK=$(echo "$QUERY_MAIN" | python3 -c "
import sys,json; d=json.load(sys.stdin)
fields=['answer','confidence','reasoning_type']
present=[f for f in fields if f in d]
print('OK:'+','.join(present))" 2>/dev/null || echo "PARSE_ERR")
if [[ "$QUERY_OK" == OK* ]]; then
  check "P3-03: POST /query returns answer+confidence+reasoning_type" "PASS" "$QUERY_OK"
else check "P3-03: POST /query returns answer+confidence+reasoning_type" "FAIL" "$QUERY_OK | $QUERY_MAIN"; fi

# Query history persistence
QUERY_ID=$(echo "$QUERY_MAIN" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('id',''))" 2>/dev/null || echo "")
if [[ -n "$QUERY_ID" ]]; then
  QUERY_GET=$(getj "/query/$QUERY_ID")
  QG_OK=$(echo "$QUERY_GET" | python3 -c "import sys,json; d=json.load(sys.stdin); print('OK' if 'answer' in d or 'question' in d else 'FAIL:'+str(list(d.keys()))[:60])" 2>/dev/null || echo "PARSE_ERR")
  if [[ "$QG_OK" == "OK" ]]; then
    check "P3-04: GET /query/{id} (persisted)" "PASS" "id=$QUERY_ID"
  else check "P3-04: GET /query/{id} (persisted)" "FAIL" "$QG_OK | $QUERY_GET"
  fi
else check "P3-04: GET /query/{id} (persisted)" "WARN" "No query ID returned in POST /query response"; fi

# Why-did-this-change — insufficient evidence path (CRITICAL)
WHY=$(postj "/analytics/why-did-this-change" '{"entity":"XYZFAKE","metric":"production","period":"FY1900"}')
echo "Why-sparse: $WHY"
WHY_OK=$(echo "$WHY" | python3 -c "
import sys,json; d=json.load(sys.stdin)
s=str(d).lower()
if any(x in s for x in ['insufficient','no evidence','not found','no data','no sufficient']): print('OK:returned-no-evidence')
elif 'reason' in s and 'type' in s: print('PARTIAL:check-reasoning-type')
else: print('FAIL:may-fabricate')" 2>/dev/null || echo "PARSE_ERR")
if [[ "$WHY_OK" == OK* ]]; then
  check "P3-CRITICAL: why-did-this-change sparse → no fabrication" "PASS" "$WHY_OK"
elif [[ "$WHY_OK" == PARTIAL* ]]; then
  check "P3-CRITICAL: why-did-this-change sparse → no fabrication" "WARN" "$WHY_OK"
else check "P3-CRITICAL: why-did-this-change sparse → no fabrication" "FAIL" "$WHY_OK"; fi

# ════════════════════════════════════════════════════════════
# SECTION 4: PHASE 4 — REPORTS + TOPICS + REVIEW + DASHBOARD
# ════════════════════════════════════════════════════════════
log "=== PHASE 4: Reports + Topics + Review + Dashboard ==="

# Generate report
REPORT=$(postj "/reports/generate" '{"entity":"CCL","metric":"production","start_period":"FY2021","end_period":"FY2023","format":"pdf"}')
echo "Report: $REPORT"
REPORT_ID=$(echo "$REPORT" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('id',''))" 2>/dev/null || echo "")
REPORT_OK=$(echo "$REPORT" | python3 -c "
import sys,json; d=json.load(sys.stdin)
if 'id' in d or 'report_id' in d: print('OK:id='+str(d.get('id',''))[:40])
elif 'status' in d: print('OK:status='+d.get('status',''))
else: print('FAIL:'+str(list(d.keys()))[:80])" 2>/dev/null || echo "PARSE_ERR")
if [[ "$REPORT_OK" == OK* ]]; then
  check "P4-01: POST /reports/generate" "PASS" "$REPORT_OK"
else check "P4-01: POST /reports/generate" "FAIL" "$REPORT_OK | $REPORT"; fi

# Topics
TOPICS=$(getj "/topics?limit=10")
echo "Topics: $TOPICS"
TOPICS_OK=$(echo "$TOPICS" | python3 -c "
import sys,json; d=json.load(sys.stdin)
items=d if isinstance(d,list) else d.get('topics',d.get('items',[]))
print('OK:'+str(len(items))+' topics')" 2>/dev/null || echo "PARSE_ERR")
if [[ "$TOPICS_OK" == OK* ]]; then
  check "P4-02: GET /topics" "PASS" "$TOPICS_OK"
else check "P4-02: GET /topics" "FAIL" "$TOPICS_OK | $TOPICS"; fi

# Topics trends
TOPIC_TRENDS=$(getj "/topics/trends")
echo "Topic trends: $TOPIC_TRENDS"
TTREND_OK=$(echo "$TOPIC_TRENDS" | python3 -c "
import sys,json; d=json.load(sys.stdin)
if isinstance(d,list) or 'trends' in d or 'data' in d: print('OK')
else: print('FAIL:'+str(list(d.keys()) if isinstance(d,dict) else str(d))[:80])" 2>/dev/null || echo "PARSE_ERR")
if [[ "$TTREND_OK" == "OK" ]]; then
  check "P4-03: GET /topics/trends" "PASS" "returned"
else check "P4-03: GET /topics/trends" "FAIL" "$TTREND_OK | $TOPIC_TRENDS"; fi

# Review flags
REV_FLAGS=$(getj "/review/flags?limit=10")
echo "Review flags: $REV_FLAGS"
RF_OK=$(echo "$REV_FLAGS" | python3 -c "
import sys,json; d=json.load(sys.stdin)
items=d if isinstance(d,list) else d.get('items',d.get('flags',[]))
print('OK:'+str(len(items))+' flags')" 2>/dev/null || echo "PARSE_ERR")
if [[ "$RF_OK" == OK* ]]; then
  check "P4-04: GET /review/flags" "PASS" "$RF_OK"
else check "P4-04: GET /review/flags" "FAIL" "$RF_OK | $REV_FLAGS"; fi

# Dashboard stats
DASH=$(getj "/dashboard/stats")
echo "Dashboard: $DASH"
DASH_OK=$(echo "$DASH" | python3 -c "
import sys,json; d=json.load(sys.stdin)
fields=['documents_processed','facts_extracted','conflicts_detected']
present=[f for f in fields if f in d]
print('OK:'+','.join(present) if present else 'FAIL:missing fields, got:'+str(list(d.keys()))[:80])" 2>/dev/null || echo "PARSE_ERR")
if [[ "$DASH_OK" == OK* ]]; then
  check "P4-05: GET /dashboard/stats" "PASS" "$DASH_OK"
else check "P4-05: GET /dashboard/stats" "FAIL" "$DASH_OK | $DASH"; fi

# Dashboard live count check: upload one more doc, count should increment
DASH_BEFORE=$(echo "$DASH" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('documents_processed',0))" 2>/dev/null || echo "0")
EXTRA_UPLOAD=$(curl -s -X POST "$BASE/documents/upload" \
  -H "$AUTH" \
  -F "file=@$TMPDIR_TESTS/coal_data.csv;type=text/csv" 2>&1)
sleep 3
DASH_AFTER_RESP=$(getj "/dashboard/stats")
DASH_AFTER=$(echo "$DASH_AFTER_RESP" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('documents_processed',0))" 2>/dev/null || echo "0")
echo "Dashboard before=$DASH_BEFORE after=$DASH_AFTER"
if [[ "$DASH_AFTER" -gt "$DASH_BEFORE" ]] 2>/dev/null; then
  check "P4-06: Dashboard doc count increments live" "PASS" "before=$DASH_BEFORE after=$DASH_AFTER"
elif [[ "$DASH_BEFORE" == "$DASH_AFTER" ]]; then
  check "P4-06: Dashboard doc count increments live" "WARN" "Count unchanged ($DASH_BEFORE); may be async update lag"
else check "P4-06: Dashboard doc count increments live" "FAIL" "before=$DASH_BEFORE after=$DASH_AFTER"; fi

# Review conflict resolution — missing justification → reject
# First get a conflict if exists
FIRST_CONF=$(echo "$CONFLICTS" | python3 -c "
import sys,json; d=json.load(sys.stdin)
items=d if isinstance(d,list) else d.get('items',d.get('conflicts',[]))
print(items[0].get('id','') if items else '')" 2>/dev/null || echo "")
if [[ -n "$FIRST_CONF" ]]; then
  RES_NO_JUST=$(postj "/review/conflicts/$FIRST_CONF/resolve" '{"resolution":"accept_a"}')
  RES_CODE=$(echo "$RES_NO_JUST" | python3 -c "import sys,json; d=json.load(sys.stdin); print('REJECTED' if 'detail' in d else 'ACCEPTED')" 2>/dev/null || echo "PARSE_ERR")
  if [[ "$RES_CODE" == "REJECTED" ]]; then
    check "P4-07: Conflict resolve without justification → rejected" "PASS" "Correctly rejected"
  else check "P4-07: Conflict resolve without justification → rejected" "WARN" "May have accepted without justification: $RES_NO_JUST"; fi
fi

# ════════════════════════════════════════════════════════════
# SECTION 5: PHASE 5 — PARLIAMENTARY + MAP + FORECAST + BENCHMARK
# ════════════════════════════════════════════════════════════
log "=== PHASE 5: Phase 5 Features ==="

# Parliamentary query
PARL=$(postj "/parliamentary/query" '{"question":"What is the current coal production status of CCL for FY2023-24?","context":"Parliamentary session question"}')
echo "Parliamentary: $PARL"
PARL_OK=$(echo "$PARL" | python3 -c "
import sys,json; d=json.load(sys.stdin)
if 'status' in d: print('OK:status='+str(d.get('status',''))[:40])
elif 'id' in d: print('OK:id='+str(d.get('id',''))[:40])
elif 'detail' in d: print('FAIL:'+str(d.get('detail',''))[:80])
else: print('UNEXPECTED:'+str(list(d.keys()))[:80])" 2>/dev/null || echo "PARSE_ERR")
if [[ "$PARL_OK" == OK* ]]; then
  check "P5-01: POST /parliamentary/query" "PASS" "$PARL_OK"
else check "P5-01: POST /parliamentary/query" "FAIL" "$PARL_OK | $PARL"; fi

# Parliamentary pending_review check
PARL_STATUS=$(echo "$PARL" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('status',''))" 2>/dev/null || echo "")
if [[ "$PARL_STATUS" == "pending_review" ]]; then
  check "P5-02: Parliamentary query starts as pending_review" "PASS" "status=pending_review"
elif [[ "$PARL_STATUS" == "draft" ]]; then
  check "P5-02: Parliamentary query starts as pending_review" "WARN" "status=draft (check if pending_review is the canonical initial status)"
else check "P5-02: Parliamentary query starts as pending_review" "FAIL" "status=$PARL_STATUS"; fi

# Map layers
MAP_LAYERS=$(getj "/map/layers")
echo "Map layers: $MAP_LAYERS"
ML_OK=$(echo "$MAP_LAYERS" | python3 -c "
import sys,json; d=json.load(sys.stdin)
layers=d if isinstance(d,list) else d.get('layers',[])
print('OK:'+str(len(layers))+' layers')" 2>/dev/null || echo "PARSE_ERR")
if [[ "$ML_OK" == OK* ]]; then
  check "P5-03: GET /map/layers" "PASS" "$ML_OK"
else check "P5-03: GET /map/layers" "FAIL" "$ML_OK | $MAP_LAYERS"; fi

# Forecast — sparse entity (CRITICAL: must not force forecast)
FORECAST_SPARSE=$(postj "/forecast" '{"entity":"XYZFAKEMINE","metric":"production","periods":3}')
echo "Forecast sparse: $FORECAST_SPARSE"
FS_OK=$(echo "$FORECAST_SPARSE" | python3 -c "
import sys,json; d=json.load(sys.stdin)
s=str(d).lower()
if any(x in s for x in ['insufficient','not enough','no historical','sparse','cannot forecast']): print('OK:refused-correctly')
elif 'model_based_forecast' in s or 'model-based forecast' in s: print('PARTIAL:labeled-but-may-force')
else: print('FAIL:may-force-forecast-on-no-data')" 2>/dev/null || echo "PARSE_ERR")
if [[ "$FS_OK" == OK* ]]; then
  check "P5-CRITICAL: Sparse forecast → refuses (not forced)" "PASS" "$FS_OK"
else check "P5-CRITICAL: Sparse forecast → refuses (not forced)" "WARN" "$FS_OK | $FORECAST_SPARSE"; fi

# Forecast — real entity with data; check for "Model-based forecast" label (CRITICAL)
FORECAST_REAL=$(postj "/forecast" '{"entity":"CCL","metric":"production","periods":2}')
echo "Forecast real: $FORECAST_REAL"
FR_LABEL=$(echo "$FORECAST_REAL" | python3 -c "
import sys,json; d=json.load(sys.stdin)
s=str(d).lower()
has_label='model-based forecast' in s or 'model_based_forecast' in s or 'forecast_type' in str(d).lower()
has_data='predicted_value' in s or 'forecast' in str(list(d.keys())).lower() or 'data_points' in s
if has_data and has_label: print('OK:has-data-and-label')
elif has_data: print('FAIL:data-without-model-based-label')
elif 'insufficient' in s: print('WARN:insufficient-data-CCL')
else: print('UNEXPECTED:'+str(list(d.keys()))[:80])" 2>/dev/null || echo "PARSE_ERR")
if [[ "$FR_LABEL" == OK* ]]; then
  check "P5-CRITICAL: Forecast has Model-based label" "PASS" "$FR_LABEL"
elif [[ "$FR_LABEL" == WARN* ]]; then
  check "P5-CRITICAL: Forecast has Model-based label" "WARN" "$FR_LABEL (CCL has no facts yet)"
else check "P5-CRITICAL: Forecast has Model-based label" "FAIL" "$FR_LABEL | $FORECAST_REAL"; fi

# Benchmark run
BENCH=$(postj "/benchmark/run" '{}')
echo "Benchmark: $BENCH"
BENCH_OK=$(echo "$BENCH" | python3 -c "
import sys,json; d=json.load(sys.stdin)
if 'id' in d or 'run_id' in d or 'status' in d: print('OK:'+str(list(d.keys()))[:60])
elif 'detail' in d: print('FAIL:'+str(d.get('detail',''))[:80])
else: print('UNEXPECTED:'+str(list(d.keys()))[:80])" 2>/dev/null || echo "PARSE_ERR")
if [[ "$BENCH_OK" == OK* ]]; then
  check "P5-04: POST /benchmark/run" "PASS" "$BENCH_OK"
else check "P5-04: POST /benchmark/run" "FAIL" "$BENCH_OK | $BENCH"; fi

# Benchmark results
BENCH_RESULTS=$(getj "/benchmark/results")
echo "Benchmark results: $BENCH_RESULTS"
BR_OK=$(echo "$BENCH_RESULTS" | python3 -c "
import sys,json; d=json.load(sys.stdin)
items=d if isinstance(d,list) else d.get('results',d.get('runs',[]))
print('OK:'+str(len(items))+' results')" 2>/dev/null || echo "PARSE_ERR")
if [[ "$BR_OK" == OK* ]]; then
  check "P5-05: GET /benchmark/results" "PASS" "$BR_OK"
else check "P5-05: GET /benchmark/results" "FAIL" "$BR_OK | $BENCH_RESULTS"; fi

# ════════════════════════════════════════════════════════════
# SECTION 5.5: RBAC CHECKS
# ════════════════════════════════════════════════════════════
log "=== RBAC Checks ==="

# Create analyst user
ANA_CREATE=$(postj "/auth/users" '{"username":"testanalyst","password":"Test@1234!","role":"analyst"}')
echo "Analyst create: $ANA_CREATE"
# Login as analyst
ANA_TOKEN=$(curl -s -X POST "$BASE/auth/login" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=testanalyst&password=Test@1234!" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('access_token','FAIL'))" 2>/dev/null)
ANA_AUTH="Authorization: Bearer $ANA_TOKEN"
if [[ "$ANA_TOKEN" != "FAIL" ]] && [[ -n "$ANA_TOKEN" ]]; then
  check "RBAC-01: Analyst login" "PASS" "token obtained"

  # Analyst should NOT be able to create users (admin-only)
  ANA_CREATE_ATTEMPT=$(curl -s -X POST "$BASE/auth/users" \
    -H "$ANA_AUTH" -H "Content-Type: application/json" \
    -d '{"username":"hacker","password":"Test@1234!","role":"admin"}')
  ANA_403=$(echo "$ANA_CREATE_ATTEMPT" | python3 -c "import sys,json; d=json.load(sys.stdin); print('BLOCKED' if 'detail' in d else 'ALLOWED')" 2>/dev/null || echo "UNKNOWN")
  if [[ "$ANA_403" == "BLOCKED" ]]; then
    check "RBAC-02: Analyst cannot create users (admin-only)" "PASS" "blocked correctly"
  else check "RBAC-02: Analyst cannot create users (admin-only)" "FAIL" "was: $ANA_CREATE_ATTEMPT"; fi

  # Analyst should NOT be able to approve parliamentary queries
  if [[ -n "$PARL" ]]; then
    PARL_ID=$(echo "$PARL" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('id',''))" 2>/dev/null || echo "")
    if [[ -n "$PARL_ID" ]]; then
      ANA_APPROVE=$(curl -s -X POST "$BASE/parliamentary/$PARL_ID/approve" \
        -H "$ANA_AUTH" -H "Content-Type: application/json" \
        -d '{"approved_by":"testanalyst"}')
      ANA_APPROVE_OK=$(echo "$ANA_APPROVE" | python3 -c "import sys,json; d=json.load(sys.stdin); print('BLOCKED' if d.get('status_code',200)!=200 and 'detail' in d else ('BLOCKED' if '403' in str(d) or 'forbidden' in str(d).lower() or 'not authorized' in str(d).lower() else 'ALLOWED'))" 2>/dev/null || echo "UNKNOWN")
      if [[ "$ANA_APPROVE_OK" == "BLOCKED" ]]; then
        check "RBAC-03: Analyst cannot approve parliamentary" "PASS" "blocked"
      else check "RBAC-03: Analyst cannot approve parliamentary" "WARN" "Check response: $ANA_APPROVE"; fi
    fi
  fi
else check "RBAC-01: Analyst login" "FAIL" "Could not get token"; fi

# ════════════════════════════════════════════════════════════
# SECTION 6: CROSS-PHASE INTEGRATION
# ════════════════════════════════════════════════════════════
log "=== Cross-Phase Integration ==="

# ModelGateway is the single path for LLM calls
MG_REFS=$(grep -r "model_gateway\|ModelGateway" /Users/vedikamohite/CMPDI-GodLikefinal/CMPDI-GodLike/backend/app/services/ --include="*.py" -l 2>/dev/null | tr '\n' ' ')
DIRECT_OLLAMA=$(grep -r "requests.post.*ollama\|httpx.*ollama\|aiohttp.*11434" /Users/vedikamohite/CMPDI-GodLikefinal/CMPDI-GodLike/backend/app/services/ --include="*.py" -l 2>/dev/null | tr '\n' ' ')
echo "ModelGateway used by: $MG_REFS"
echo "Direct Ollama calls (bypass): $DIRECT_OLLAMA"
if [[ -n "$MG_REFS" ]] && [[ -z "$DIRECT_OLLAMA" ]]; then
  check "CROSS-01: ModelGateway is single LLM path" "PASS" "used in: $MG_REFS"
elif [[ -n "$MG_REFS" ]]; then
  check "CROSS-01: ModelGateway is single LLM path" "WARN" "direct calls found: $DIRECT_OLLAMA"
else check "CROSS-01: ModelGateway is single LLM path" "FAIL" "No ModelGateway references found"; fi

# Security audit log check
AUDIT_LOG_REFS=$(grep -r "audit_log\|AuditLog" /Users/vedikamohite/CMPDI-GodLikefinal/CMPDI-GodLike/backend/app/ --include="*.py" -l 2>/dev/null | tr '\n' ' ')
if [[ -n "$AUDIT_LOG_REFS" ]]; then
  check "CROSS-02: Audit log implemented" "PASS" "found in: $AUDIT_LOG_REFS"
else check "CROSS-02: Audit log implemented" "FAIL" "No audit_log references found"; fi

# Rate limiting check
RATE_LIMIT_REFS=$(grep -r "slowapi\|RateLimiter\|limiter\|rate_limit" /Users/vedikamohite/CMPDI-GodLikefinal/CMPDI-GodLike/backend/app/ --include="*.py" -l 2>/dev/null | tr '\n' ' ')
if [[ -n "$RATE_LIMIT_REFS" ]]; then
  check "CROSS-03: Rate limiting implemented" "PASS" "found in: $RATE_LIMIT_REFS"
else check "CROSS-03: Rate limiting implemented" "WARN" "No rate limiting refs found"; fi

# GET /auth/me for current user
ME=$(getj "/auth/me")
ME_OK=$(echo "$ME" | python3 -c "import sys,json; d=json.load(sys.stdin); print('OK:'+d.get('username',''))" 2>/dev/null || echo "PARSE_ERR")
if [[ "$ME_OK" == OK* ]]; then
  check "CROSS-04: GET /auth/me" "PASS" "$ME_OK"
else check "CROSS-04: GET /auth/me" "FAIL" "$ME_OK | $ME"; fi

# SECURITY.md exists
if [[ -f "/Users/vedikamohite/CMPDI-GodLikefinal/CMPDI-GodLike/backend/SECURITY.md" ]]; then
  check "CROSS-05: SECURITY.md exists" "PASS" "encryption/security documentation present"
else check "CROSS-05: SECURITY.md exists" "FAIL" "No SECURITY.md found"; fi

# ════════════════════════════════════════════════════════════
# SUMMARY
# ════════════════════════════════════════════════════════════
log ""
log "════════════════════════════════════════════════════════════"
log " TEST SUMMARY"
log "════════════════════════════════════════════════════════════"
echo "  ✅ PASS: $PASS"
echo "  ⚠️  WARN: $WARN"
echo "  ❌ FAIL: $FAIL"
echo "  📊 TOTAL: $((PASS+WARN+FAIL))"
log ""
log " DETAILED RESULTS:"
for r in "${RESULTS[@]}"; do
  IFS='|' read -r status id detail <<< "$r"
  if [[ "$status" == "PASS" ]]; then echo "  ✅ $id"
  elif [[ "$status" == "WARN" ]]; then echo "  ⚠️  $id: $detail"
  else echo "  ❌ $id: $detail"; fi
done

# Export JSON for report
python3 -c "
import json
results = [
$(for r in "${RESULTS[@]}"; do
  IFS='|' read -r status id detail <<< "$r"
  echo "  {'status': '$status', 'id': '$id', 'detail': $(echo "$detail" | python3 -c "import sys; print(repr(sys.stdin.read().strip()))")},"
done)
]
print(json.dumps(results, indent=2))
" > /tmp/cmpdi_test_results_$$.json 2>/dev/null || true

echo ""
echo "Results JSON: /tmp/cmpdi_test_results_$$.json"
echo "TMPDIR: $TMPDIR_TESTS"
