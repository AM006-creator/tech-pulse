#!/usr/bin/env python3
from flask import Flask, jsonify, send_file
from pathlib import Path
import os
import json
import re
from anthropic import Anthropic

app = Flask(__name__)
golem_folder = Path(os.getcwd())
api_key = os.environ.get("ANTHROPIC_API_KEY")

if not api_key:
    print("WARNING: ANTHROPIC_API_KEY not set")

print(f"Init: folder={golem_folder}, html_exists={(golem_folder / 'tech-pulse.html').exists()}")

def root():
    """Serve HTML dashboard"""
    html_file = golem_folder / 'tech-pulse.html'
    print(f"Request to / - serving {html_file}")
    with open(html_file, 'r') as f:
        return f.read(), 200, {'Content-Type': 'text/html'}

def health_check():
    """Health endpoint"""
    return jsonify({"status": "ok", "folder": str(golem_folder)})

def create_skill_post():
    """Create a new skill"""
    from flask import request
    try:
        data = request.json or {}
        skill_name = data.get('skillName', 'test').strip()

        # Validate name
        if not re.match(r'^[a-z0-9]+(?:-[a-z0-9]+)*$', skill_name):
            return jsonify({"error": "Invalid skill name"}), 400

        # Generate code
        client = Anthropic(api_key=api_key)
        prompt = f"Write a simple Python tool. Output ONLY the code, no markdown."
        msg = client.messages.create(model="claude-opus-4-6", max_tokens=1000, messages=[{"role": "user", "content": prompt}])
        code = msg.content[0].text.strip()
        code = re.sub(r'^```.*\n?', '', code)
        code = re.sub(r'\n?```$', '', code)

        # Write file
        filename = skill_name.replace('-', '_') + '.py'
        filepath = golem_folder / filename
        with open(filepath, 'w') as f:
            f.write(code)

        return jsonify({"success": True, "filename": filename}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500

def handle_options():
    """CORS preflight"""
    return '', 204

def cors_headers(response):
    """Add CORS headers"""
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
    return response

# Register routes
app.add_url_rule('/', 'root', root, methods=['GET'])
app.add_url_rule('/health', 'health', health_check, methods=['GET'])
app.add_url_rule('/create-skill', 'create_skill', create_skill_post, methods=['POST'])
app.add_url_rule('/create-skill', 'options', handle_options, methods=['OPTIONS'])
app.after_request(cors_headers)

if __name__ == '__main__':
    print("\n" + "="*60)
    print("TECH PULSE BUILDER")
    print(f"Folder: {golem_folder}")
    print("Routes:")
    for rule in app.url_map.iter_rules():
        print(f"  {rule.rule} -> {rule.endpoint}")
    print("="*60 + "\n")
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port, debug=False)
