import json
from openai import OpenAI

# ==============================
# 1. Setup OpenAI LLM
# ==============================
client = OpenAI(api_key="YOUR_API_KEY")  # replace with your key

def ask_llm(prompt, model="gpt-4o-mini"):
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": "You are a production deployment architect. Your task is to analyze code diffs against known RCA failure patterns."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.2
    )
    return response.choices[0].message.content.strip()

# ==============================
# 2. Load Existing Patterns (from Prompt 1 output)
# ==============================
patterns_json = """
[
  {"pattern": "DB Connection Issues", "examples": ["DB Timeout", "DB not reachable"], "category": "Infra"},
  {"pattern": "Config Errors", "examples": ["YAML error", "Config mismatch"], "category": "Config"},
  {"pattern": "Permission Issues", "examples": ["Unauthorized access", "Role missing"], "category": "Security"},
  {"pattern": "Code NullPointer", "examples": ["NullPointerException"], "category": "Code"}
]
"""
patterns = json.loads(patterns_json)

# ==============================
# 3. Provide Code Diff for Analysis
# ==============================
code_diff = """
- db_url = "jdbc:mysql://old-host:3306/app"
+ db_url = "jdbc:mysql://new-host:3306/app"

- user.setName(name);
+ user.setName(null);  // temporary null assignment
"""

# ==============================
# 4. Build Prompt for LLM
# ==============================
prompt = f"""
We have the following known failure patterns:
{json.dumps(patterns, indent=2)}

Now analyze this code diff:
{code_diff}

Tasks:
1. If everything looks fine → respond: "✅ Everything looks fine".
2. If risks exist:
   - Identify the risky code changes.
   - Map them to one or more of the failure patterns above.
   - Highlight why that change could lead to the mapped failure.

Return structured JSON with fields:
- status: "fine" or "issues"
- issues: [{{"code_snippet": "...", "pattern": "...", "reason": "..."}}]
"""

# ==============================
# 5. Run LLM
# ==============================
analysis_result = ask_llm(prompt)

try:
    analysis = json.loads(analysis_result)
except json.JSONDecodeError:
    print("⚠️ Could not parse JSON. Raw output:")
    print(analysis_result)
    analysis = {}

print("🔎 Analysis Result:")
print(json.dumps(analysis, indent=2))
