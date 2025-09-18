import streamlit as st
import pandas as pd
from openai import OpenAI
import json
import os
import time
import plotly.express as px

# ==============================
# 1. Setup Streamlit Page
# ==============================
st.set_page_config(page_title="RCA Agent", page_icon="🕵️‍♂️", layout="wide")

st.title("🕵️ RCA Failure Pattern Agent")
st.markdown("Upload your **RCA_Report.xlsx** to analyze and maintain a self-learning master RCA catalog.")

# ==============================
# 2. Setup OpenAI LLM
# ==============================
client = OpenAI(api_key="YOUR_API_KEY")  # replace with your key

def ask_llm(prompt, model="gpt-4o-mini"):
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": "You are an expert production architect analyzing RCA reports."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.2
    )
    return response.choices[0].message.content.strip()

# ==============================
# 3. File Upload
# ==============================
uploaded_file = st.file_uploader("📂 Upload RCA_Report.xlsx", type=["xlsx"])

if uploaded_file:
    df = pd.read_excel(uploaded_file)

    required_columns = {"TicketNumber", "State", "LOBT", "CRFailReason"}
    if not required_columns.issubset(df.columns):
        st.error(f"Excel must contain columns: {required_columns}")
        st.stop()

    fail_reasons = df["CRFailReason"].dropna().tolist()

    # ==============================
    # 4. Load Master Catalog
    # ==============================
    master_file = "RCA_Master_Catalog.xlsx"
    if os.path.exists(master_file):
        master_df = pd.read_excel(master_file)
    else:
        master_df = pd.DataFrame(columns=["pattern", "examples", "frequency", "category",
                                          "root_cause", "fix_type", "prevention_step"])

    known_examples = set()
    for ex_list in master_df["examples"].dropna():
        try:
            items = json.loads(ex_list) if isinstance(ex_list, str) else []
            known_examples.update(items)
        except:
            continue

    new_reasons = [r for r in fail_reasons if r not in known_examples]

    # ==============================
    # 5. Process New Fail Reasons
    # ==============================
    if new_reasons:
        with st.spinner("🔎 Analyzing new failure reasons..."):
            time.sleep(1.5)

            prompt_cluster = f"""
            You are analyzing new RCA failure reasons from production deployments.

            Here is the list of NEW failure reasons:
            {new_reasons}

            Your task:
            1. Group them into patterns.
            2. For each pattern, provide:
               - Pattern Name
               - Example Reasons
               - Frequency Count (number of items in examples)
               - Suggested Category (Infra, Code, Config, Security, Process, External Dependency, Other)

            Return JSON list with fields:
            [{{"pattern": "...", "examples": [...], "frequency": n, "category": "..."}}]
            """
            patterns_json = ask_llm(prompt_cluster)

            try:
                new_patterns = json.loads(patterns_json)
            except json.JSONDecodeError:
                st.error("⚠️ Could not parse patterns from LLM response.")
                st.text(patterns_json)
                new_patterns = []

        if new_patterns:
            st.success("✨ New failure patterns detected!")
            st.json(new_patterns)

            with st.spinner("🛠️ Generating preventive actions..."):
                prompt_prevention = f"""
                You are an RCA prevention advisor.

                Given these new failure patterns:
                {json.dumps(new_patterns, indent=2)}

                For each pattern, suggest:
                - Root Cause
                - Recommended Fix Type (Process Fix, Automation Fix, Code Fix, Infra Fix, Monitoring Fix)
                - Prevention Step

                Return JSON list with fields:
                [{{"pattern": "...", "root_cause": "...", "fix_type": "...", "prevention_step": "..."}}]
                """
                prevention_json = ask_llm(prompt_prevention)

                try:
                    new_prevention = json.loads(prevention_json)
                except json.JSONDecodeError:
                    st.error("⚠️ Could not parse prevention actions.")
                    st.text(prevention_json)
                    new_prevention = []

            for pat in new_patterns:
                prevention_match = next((p for p in new_prevention if p["pattern"] == pat["pattern"]), {})
                row = {
                    "pattern": pat["pattern"],
                    "examples": json.dumps(pat["examples"]),
                    "frequency": pat["frequency"],
                    "category": pat["category"],
                    "root_cause": prevention_match.get("root_cause", ""),
                    "fix_type": prevention_match.get("fix_type", ""),
                    "prevention_step": prevention_match.get("prevention_step", "")
                }
                master_df = pd.concat([master_df, pd.DataFrame([row])], ignore_index=True)

    # ==============================
    # 6. Update Frequencies
    # ==============================
    for i, row in master_df.iterrows():
        if pd.isna(row["examples"]):
            continue
        try:
            ex_list = json.loads(row["examples"]) if isinstance(row["examples"], str) else []
        except:
            ex_list = []
        count = sum(fr in ex_list for fr in fail_reasons)
        master_df.at[i, "frequency"] = count

    # ==============================
    # 7. Save Master Catalog
    # ==============================
    master_df.to_excel(master_file, index=False)
    st.success(f"✅ Master catalog updated and saved to {master_file}")

    # ==============================
    # 8. Show Results with Animations
    # ==============================
    st.header("📊 Failure Patterns Overview")

    with st.expander("🔍 View Full Catalog"):
        st.dataframe(master_df, use_container_width=True)

    if not master_df.empty:
        fig = px.bar(master_df, x="pattern", y="frequency", color="category",
                     title="Failure Patterns by Frequency",
                     text_auto=True)
        st.plotly_chart(fig, use_container_width=True)

        fig2 = px.pie(master_df, names="category", values="frequency",
                      title="Failure Categories Distribution")
        st.plotly_chart(fig2, use_container_width=True)

    st.markdown("🎉 Analysis complete! Upload new RCA reports anytime to keep improving the master catalog.")
                  
