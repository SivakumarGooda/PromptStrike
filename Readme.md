# 🚀 PromptStrike

**PromptStrike** is a lightweight LLM security testing tool for HTTP-based AI applications.  
It performs multi-turn prompt injection and rule disclosure attacks, supports flexible dataset-based testing, captures full request/response evidence, and generates HTML reports for analysis.

---

## 🔥 Features

- 🔍 Test **Prompt Injection** and **Rule Disclosure**
- 🧠 Multi-turn adaptive attack engine
- 📡 Works with any HTTP-based LLM endpoint
- 🧾 Full **request & response logging**
- 📊 Generates **HTML + JSONL reports (per dataset)**
- 🎯 Supports **Base + Target datasets**
- ⚡ Config builder from **curl command**
- ⏸️ Runtime controls: pause / resume / stop

---

## 🏗️ Project Structure

```text
PromptStrike/
├── configs/
│   └── app.config.json
├── core/
├── datasets/
│   ├── base/
│   │   ├── base_rule_disclosure.txt
│   │   └── base_prompt_injection.txt
│   └── targets/
│       └── app/
│           ├── app_rule_disclosure.txt
│           └── app_prompt_injection.txt
├── models/
├── runners/
│   └── run_attack_campaign.py
├── results/
├── main.py
├── target_parser.py
└── requirements.txt
```

---

## ⚙️ Installation

```bash
git clone <your-repo-url>
cd PromptStrike

python3 -m venv .venv
source .venv/bin/activate   # macOS/Linux
# .venv\Scripts\activate   # Windows

pip install -r requirements.txt
```

---

## ▶️ Usage

```bash
python main.py
```

---

## 🧭 Menu Options

```text
1. Build/update target config from curl
2. Run selected datasets from config
3. Exit
h. Help
```

---

## 🔧 Step 1: Build Target Config

```bash
curl http://localhost:8000/chat \
  -X POST \
  -H "Content-Type: application/json" \
  -d '{"message":"hello"}'
```

This generates:

```text
configs/app.config.json
```

---

## 🧠 Dataset Selection

```text
Select dataset mode:
1. Base only
2. Target only
3. Base + Target
4. Custom selection
5. All
```

---

## ⚔️ Step 2: Run Attacks

```text
2 → Run selected datasets from config
```

```text
Enter max requests per dataset [100]:
Enter max turns per case [5]:
Enter output directory [results/app]:
```

---

## 🎮 Runtime Controls

```text
p → pause
r → resume
q → stop safely
```

Press **Enter once** after typing.

---

## 📊 Output

```text
results/app/
```

Example:

```text
base_rule_disclosure.jsonl
base_rule_disclosure.html

base_prompt_injection.jsonl
base_prompt_injection.html

app_rule_disclosure.jsonl
app_rule_disclosure.html

app_prompt_injection.jsonl
app_prompt_injection.html
```

---

## 🧠 How It Works

```text
Payload → Send → Observe → Evaluate → Mutate → Retry → Report
```

---

## ⚠️ Disclaimer

This tool is intended for **authorized security testing only**.  
Do not use against systems without permission.

---

## ⭐ Credits

Built for AI red teaming learning.
