"""SafePlate CLI — offline meal plan via local Gemma.

Usage: python safeplate.py peanuts,shrimp [servings]
Needs: pip install llama-cpp-python + model in Temp/opencode/models/
"""
import json
import sys

from server import generate

if __name__ == "__main__":
    allergies = sys.argv[1].split(",") if len(sys.argv) > 1 else ["peanuts", "shrimp"]
    servings = int(sys.argv[2]) if len(sys.argv) > 2 else 2
    result = generate(allergies, servings, "student budget", 7)
    print(json.dumps(result, ensure_ascii=False, indent=2)[:4000])
