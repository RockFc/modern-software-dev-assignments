docker exec -d \
  -e PYTHONDONTWRITEBYTECODE=1 \
  -e TRANSPORT=http \
  -e HOST=0.0.0.0 \
  -e PORT=8765 \
  -e MCP_API_KEY='mcp_f3bbd13d122f0febabca92495ce7bdc2' \
  cs146s-dev \
  /opt/venvs/week3-mcp/bin/python /workspace/modern-software-dev-assignments/week3/server/main.py
