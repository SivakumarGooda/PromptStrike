# 🚀 PromptStrike

**PromptStrike** is a lightweight LLM security testing tool for HTTP-based AI applications.
It performs multi-turn prompt injection and rule disclosure attacks, captures full request/response evidence, and generates HTML reports for analysis.

---

## 🔥 Features

* 🔍 Test **Prompt Injection** and **Rule Disclosure**
* 🧠 Multi-turn adaptive attack engine
* 📡 Works with any HTTP-based LLM endpoint
* 🧾 Full **request & response logging**
* 📊 Generates **HTML + JSONL reports**
* ⏸️ Runtime controls: pause / resume / stop
* ⚡ Config builder from **curl command**

---

## 🏗️ Project Structure

```
PromptStrike/
├── configs/               # Generated target configs (curl → JSON)
│   └── app.config.json    # Default config used by runner
├── core/                  # Engine (attack loop, evaluator, sender)
├── datasets/              # Attack payloads
│   ├── base/              # Generic payloads
│   └── targets/           # Target-specific payloads
├── models/                # Attack state models
├── runners/               # Campaign runner
├── targets/               # HTTP target logic
├── results/               # Generated reports
├── main.py                # Entry point
├── target_parser.py       # Curl → config builder
└── requirements.txt
```

---

## ⚙️ Installation

```bash
git clone <your-repo-url>
cd PromptStrike

python3 -m venv .venv
source .venv/bin/activate   # macOS/Linux
# .venv\Scripts\activate    # Windows

pip install -r requirements.txt
```

---

## ▶️ Usage

Run the tool:

```bash
python main.py
```

---

### Menu Options

```
1. Build/update target config from curl
2. Run prompt injection
3. Run rule disclosure
4. Run both
5. Exit
h. Help
```

---

### 🔧 Step 1: Build Target Config

Paste a curl request:

```bash
curl http://localhost:8000/chat \
  -X POST \
  -H "Content-Type: application/json" \
  -d '{"message":"hello"}'
```

This generates:

```
configs/app.config.json
```

---

### ⚔️ Step 2: Run Attacks

Choose:

```
2 → Prompt Injection
3 → Rule Disclosure
4 → Both
```

You will be prompted:

```
Enter max total requests [100]:
```

---

## 🎮 Runtime Controls

While running, type:

```
p → pause
r → resume
q → stop safely
```

👉 Press **Enter after typing**

---

## 📊 Output

Reports are saved in:

```
results/
```

Files generated:

```
prompt_injection.jsonl
prompt_injection.html
rule_disclosure.jsonl
rule_disclosure.html
```

---

## 🧠 How It Works

```
Payload → Send → Observe → Evaluate → Mutate → Retry → Report
```

Each **case**:

* uses one payload
* runs multiple turns (max 5)
* stops early if success/suspicious detected

---

## 📈 Example Output

```
[+] Category      : rule_disclosure
[+] Cases done    : 41/100
[+] Requests sent : 197
[+] Req/sec       : 0.25
[+] Verdicts      : success=1 | suspicious=6 | failed=34
```

---

## 🎯 Use Cases

* LLM penetration testing
* Red teaming AI applications
* Detecting prompt injection vulnerabilities
* Identifying hidden system prompt leakage

---

## ⚠️ Disclaimer

This tool is intended for **authorized security testing only**.
Do not use against systems without permission.

---

## 🚀 Future Improvements

* LLM-based adaptive attacker (PyRIT-style)
* Advanced scoring & signal analysis
* Resume from previous runs
* CLI mode (`promptstrike scan ...`)

---

## ⭐ Credits

Built for learning and advancing **AI red teaming** techniques.
