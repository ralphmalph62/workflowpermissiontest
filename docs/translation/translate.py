import os
import yaml
import argparse
import re
import time  # <--- NEW: Import time
from google import genai
from google.genai import types

# Initialize Gemini client with explicit error handling
if "GEMINI_API_KEY" not in os.environ:
    raise RuntimeError(
        "GEMINI_API_KEY environment variable is not set. "
        "Please set GEMINI_API_KEY to your Gemini API key before running this script."
    )

try:
    client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))
except Exception as e:
    raise RuntimeError("Failed to initialize Gemini client.") from e

# NEW: Use 1.5-flash for stability and speed
MODEL_NAME = "gemini-2.0-flash" 
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_BASE_PATH = os.path.join(SCRIPT_DIR, "configs")

LANG_MAP = {
    "en": "English",
    "ja": "Japanese",
    "zh": "Simplified Chinese"
}

class StarRocksTranslator:
    def __init__(self, target_lang: str, dry_run: bool = False):
        self.target_lang = target_lang
        self.target_lang_full = LANG_MAP.get(target_lang, target_lang)
        self.dry_run = dry_run
        
        # 1. Load Templates
        self.system_template = self._read_file(f"{CONFIG_BASE_PATH}/system_prompt.txt")
        self.human_template = self._read_file(f"{CONFIG_BASE_PATH}/human_prompt.txt")
        
        # 2. Load Dictionary
        dict_path = f"{CONFIG_BASE_PATH}/language_dicts/{target_lang}.yaml"
        self.dictionary_str = self._load_dict_as_string(dict_path)

        # 3. Load Synonyms (for normalization)
        synonyms_path = f"{CONFIG_BASE_PATH}/synonyms.yaml"
        self.synonyms = self._load_yaml_as_dict(synonyms_path)
        
        # 4. Load "Never Translate" List
        raw_terms = self._load_yaml_as_list(f"{CONFIG_BASE_PATH}/never_translate.yaml")
        
        # A. Create the string for the System Prompt (Double Safety)
        self.never_translate_str = self._expand_terms(raw_terms)
        
        # B. Inject into Dictionary as "Identity Rules" (Leader: Leader)
        identity_rules = []
        for term in raw_terms:
            identity_rules.append(f"{term}: {term}")          
            identity_rules.append(f"{term.lower()}: {term.lower()}")
            
        if self.dictionary_str:
            self.dictionary_str += "\n" + "\n".join(identity_rules)
        else:
            self.dictionary_str = "\n".join(identity_rules)

    def _expand_terms(self, terms: list) -> str:
        expanded = set()
        for term in terms:
            expanded.add(term)
            expanded.add(term.lower())
        return ", ".join(sorted(expanded))

    def _load_yaml_as_list(self, path: str) -> list:
        if not os.path.exists(path):
            return []
        with open(path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
            return data if isinstance(data, list) else []

    def _read_file(self, path: str) -> str:
        if not os.path.exists(path):
            print(f"::warning::Template file not found: {path}")
            return ""
        with open(path, 'r', encoding='utf-8') as f:
            return f.read()

    def _load_yaml_as_dict(self, path: str) -> dict:
        if not os.path.exists(path):
            print(f"::warning::Synonyms file not found at: {path}. Skipping normalization.")
            return {}
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
                if isinstance(data, dict):
                    print(f"✅ Loaded {len(data)} synonym rules from {path}")
                    return data
                return {}
        except Exception as e:
            print(f"::error::Failed to parse synonyms YAML: {e}")
            return {}
    
    def normalize_content(self, text: str) -> str:
        if not self.synonyms:
            return text
            
        for bad, good in self.synonyms.items():
            pattern = re.compile(r'\b' + re.escape(bad) + r'\b', re.IGNORECASE)
            text = pattern.sub(good, text)        
        return text
    
    def _load_dict_as_string(self, path: str) -> str:
        if not os.path.exists(path):
            print(f"::warning::Dictionary NOT found at: {path}")
            return ""
        print(f"✅ Loaded dictionary from: {path}")
        with open(path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
            return "\n".join([f"{k}: {v}" for k, v in data.items()]) if data else ""

    def validate_mdx(self, original: str, translated: str) -> bool:
        tag_pattern = r'<\s*/?\s*[A-Za-z_][A-Za-z0-9_.-]*\b[^<>]*?/?>'
        return len(re.findall(tag_pattern, original)) == len(re.findall(tag_pattern, translated))

    def translate_file(self, input_file: str):
        if not os.path.exists(input_file):
            print(f"::error::File not found: {input_file}")
            return
        
        source_lang = "en"
        if "docs/zh/" in input_file: source_lang = "zh"
        elif "docs/ja/" in input_file: source_lang = "ja"
        source_lang_full = LANG_MAP.get(source_lang, source_lang)

        abs_input = os.path.abspath(input_file)
        output_file = abs_input.replace(f"/docs/{source_lang}/", f"/docs/{self.target_lang}/")
        
        #if os.path.exists(output_file) and os.path.getmtime(output_file) >= os.path.getmtime(abs_input):
            #print(f"⏩ Skipping {output_file}: Target is up to date.")
            #return

        os.makedirs(os.path.dirname(output_file), exist_ok=True)

        system_instruction = (self.system_template
                              .replace("${source_lang}", source_lang_full)
                              .replace("${target_lang}", self.target_lang_full)
                              .replace("${dictionary}", self.dictionary_str)
                              .replace("${never_translate}", self.never_translate_str))
        
        if self.dry_run:
            print(f"🔍 [DRY RUN] {source_lang_full} -> {self.target_lang_full} | Input: {input_file}")
            return
        
        original_content = self._read_file(input_file)
        content_to_process = self.normalize_content(original_content)
        
        current_human_prompt = (self.human_template
                                .replace("${target_language}", self.target_lang_full) 
                                + f"\n\n### CONTENT TO TRANSLATE ###\n\n{content_to_process}")

        print(f"🚀 Translating {input_file} to {output_file}...")
        
        # NEW: RETRY LOGIC for 429 Errors
        max_retries = 5
        base_delay = 5 # seconds
        translated_text = ""
        
        for attempt in range(max_retries):
            try:
                response = client.models.generate_content(
                    model=MODEL_NAME,
                    config=types.GenerateContentConfig(system_instruction=system_instruction, temperature=0.0),
                    contents=current_human_prompt
                )
                
                if not response.text:
                    print(f"⚠️ Warning: Gemini returned empty response for {input_file} (Blocked?).")
                    return
                    
                translated_text = response.text.strip()
                break # Success
                
            except Exception as e:
                # Check for 429 Resource Exhausted
                if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
                    if attempt < max_retries - 1:
                        wait_time = base_delay * (2 ** attempt) # 2s, 4s, 8s
                        print(f"⏳ Hit rate limit (429). Retrying in {wait_time}s...")
                        time.sleep(wait_time)
                        continue
                
                print(f"❌ Gemini API failed for {input_file}: {e}")
                return

        # Clean Markdown fences if Gemini adds them
        if translated_text.startswith("```"):
            lines = translated_text.splitlines()
            if lines[0].startswith("```"): lines = lines[1:]
            if lines and lines[-1].startswith("```"): lines = lines[:-1]
            translated_text = "\n".join(lines).strip()

        if not self.validate_mdx(original_content, translated_text):
            print(f"❌ Validation warning for {input_file}: Tag mismatch detected.")

        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(translated_text)
        print(f"✅ Saved: {output_file}")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--files", nargs='*', help="Files to process")
    parser.add_argument("-l", "--lang", choices=['ja', 'zh', 'en'], required=True)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    
    translator = StarRocksTranslator(target_lang=args.lang, dry_run=args.dry_run)
    if args.files:
        for f in args.files:
            if f.endswith(('.md', '.mdx')):
                translator.translate_file(f)

if __name__ == "__main__":
    main()

