#!/usr/bin/env python3
"""Tech Pulse Builder - Flask backend for skill generation"""
from flask import Flask, jsonify, request, send_file
from pathlib import Path
import os
import json
import re
import sys

app = Flask(__name__)
golem_folder = Path(os.getcwd())
api_key = os.environ.get("ANTHROPIC_API_KEY")

if not api_key:
    print("WARNING: ANTHROPIC_API_KEY environment variable not set", file=sys.stderr)

print(f"Tech Pulse Builder started. Folder: {golem_folder}")

@app.route('/', methods=['GET'])
def root():
    """Serve the dashboard HTML"""
    html_file = golem_folder / 'index.html'
    if not html_file.exists():
        return jsonify({"error": "Dashboard not found"}), 404
    with open(html_file, 'r', encoding='utf-8') as f:
        return f.read(), 200, {'Content-Type': 'text/html; charset=utf-8'}

@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({"status": "ok", "running": True}), 200

@app.route('/create-skill', methods=['POST', 'OPTIONS'])
def create_skill():
    """Create a new skill by generating code with Claude"""
    if request.method == 'OPTIONS':
        return '', 204

    try:
        data = request.get_json() or {}
        skill_name = data.get('skillName', 'untitled-skill').strip()
        item_type = data.get('itemType', 'idea')
        item_data = data.get('itemData', {})

        # Validate skill name format
        if not re.match(r'^[a-z0-9]+(?:-[a-z0-9]+)*$', skill_name):
            return jsonify({"error": "Skill name must be lowercase with hyphens only"}), 400

        # Generate code using Claude API (direct HTTP call)
        code = generate_code_with_claude(skill_name, item_type, item_data)

        # Write to file
        filename = skill_name.replace('-', '_') + '.py'
        filepath = golem_folder / filename

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(code)

        return jsonify({
            "success": True,
            "skillName": skill_name,
            "filename": filename,
            "filepath": str(filepath),
            "message": f"✅ Skill '{skill_name}' created successfully!",
            "instructions": f"Run: python {filename}"
        }), 201

    except Exception as e:
        print(f"Error in create_skill: {e}", file=sys.stderr)
        return jsonify({"error": str(e)}), 500

def generate_code_with_claude(skill_name, item_type, item_data):
    """Generate Python code using Claude API"""
    import urllib.request
    import json

    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY not configured")

    # Build the prompt based on item type
    title = item_data.get('title', 'Tool')
    description = item_data.get('description', 'A useful tool')

    prompt = f"""Create a complete, runnable Python script for: {title}

Description: {description}

Requirements:
- Complete, working code (not a template)
- Use only Python stdlib (no external dependencies except as comments)
- Include docstring and usage example
- Works immediately with: python script.py
- Main execution block: if __name__ == '__main__':

Output ONLY the Python code, no markdown, no explanations."""

    # Call Claude API directly via HTTP
    url = "https://api.anthropic.com/v1/messages"
    headers = {
        "Content-Type": "application/json",
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01"
    }

    payload = {
        "model": "claude-opus-4",
        "max_tokens": 2000,
        "messages": [
            {
                "role": "user",
                "content": prompt
            }
        ]
    }

    req = urllib.request.Request(url, data=json.dumps(payload).encode('utf-8'), headers=headers, method='POST')

    try:
        with urllib.request.urlopen(req, timeout=120) as response:
            result = json.loads(response.read().decode('utf-8'))
            code = result['content'][0]['text'].strip()

            # Remove markdown code blocks if present
            code = re.sub(r'^```(?:python)?\n?', '', code)
            code = re.sub(r'\n?```$', '', code)

            return code
    except urllib.error.HTTPError as e:
        error_text = e.read().decode('utf-8')
        raise Exception(f"Claude API error: {error_text}")

if __name__ == '__main__':
    # Render compatibility: listen on 0.0.0.0:10000
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port, debug=False)
