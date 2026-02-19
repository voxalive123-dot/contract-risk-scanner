from fastapi import FastAPI
from analyzer.scorer import score_contract

app = FastAPI()

@app.get("/")
def home():
    return {"status": "Contract Risk API running"}

@app.post("/analyze")
def analyze_contract(data: dict):
    text = data.get("text", "")
    result = score_contract(text)
    return result
