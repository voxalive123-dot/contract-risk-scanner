from fastapi import FastAPI
from analyzer.scorer import score_contract

app = FastAPI()

@app.get("/")
def home():
    return {"status": "API running"}

@app.post("/analyze")
def analyze(payload: dict):
    text = payload.get("text", "")
    return score_contract(text)


# ---------- CLI MODE ----------
if __name__ == "__main__":
    print("Contract Risk Scanner")
    mode = input("Type 1 = paste text, 2 = load file: ")

    if mode == "1":
        text = input("Paste contract text:\n")
    else:
        path = input("Enter file path: ")
        with open(path, "r", encoding="utf-8") as f:
            text = f.read()

    result = score_contract(text)
    print("\nRESULT:\n", result)
