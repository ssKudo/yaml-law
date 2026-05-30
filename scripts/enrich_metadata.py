#!/usr/bin/env python3
import argparse
import json
import os
import re
from pathlib import Path

# Paths
WORKSPACE_DIR = Path(__file__).parent.parent.resolve()
SCRATCH_DIR = Path("C:/Users/owner/.gemini/antigravity/brain/6c2f04d3-c024-468f-adea-2fd0954b6e14/scratch")
SCRATCH_DIR.mkdir(parents=True, exist_ok=True)

BATCH_INPUT_PATH = SCRATCH_DIR / "batch_input.json"
BATCH_OUTPUT_PATH = SCRATCH_DIR / "batch_output.json"


def escape_yaml_string(val):
    if val is None:
        return "null"
    # Simple escape for YAML double quotes
    escaped = val.replace('\\', '\\\\').replace('"', '\\"')
    return f'"{escaped}"'

def format_keywords_yaml(keywords):
    if not keywords:
        return "[]"
    escaped_keywords = [escape_yaml_string(k) for k in keywords]
    return "[" + ", ".join(escaped_keywords) + "]"

def scan_and_prepare(max_article_num, data_dir):
    articles_dir = data_dir / "articles"
    if not articles_dir.exists():
        print(f"Error: Articles directory {articles_dir} does not exist.")
        return

    # Find and sort article yaml files
    yaml_files = sorted(list(articles_dir.glob("article_*.yaml")))
    
    batch = []
    for yf in yaml_files:
        content = yf.read_text(encoding="utf-8")
        
        # Extract article_num
        num_match = re.search(r'article_num:\s*"([^"]+)"', content)
        if not num_match:
            continue
        
        art_num_str = num_match.group(1)
        # Parse the main part of the article number (e.g. 5 from "5_6")
        main_num_str = art_num_str.split("_")[0]
        try:
            main_num = int(main_num_str)
        except ValueError:
            continue
            
        if main_num > max_article_num:
            continue

        # Extract text path from YAML
        text_path_match = re.search(r'text_path:\s*"([^"]+)"', content)
        if not text_path_match:
            continue
        
        rel_text_path = text_path_match.group(1)
        text_file_path = (yf.parent / rel_text_path).resolve()
        
        if not text_file_path.exists():
            print(f"Warning: Text file {text_file_path} not found for {yf.name}")
            continue
            
        text_content = text_file_path.read_text(encoding="utf-8")
        
        # Extract caption and title
        caption_match = re.search(r'article_caption:\s*"([^"]+)"', content)
        title_match = re.search(r'article_title:\s*"([^"]+)"', content)
        
        caption = caption_match.group(1) if caption_match else ""
        title = title_match.group(1) if title_match else ""
        
        batch.append({
            "file_name": yf.name,
            "file_path": str(yf),
            "title": title,
            "caption": caption,
            "text": text_content.strip()
        })

    # Write to batch_input.json
    BATCH_INPUT_PATH.write_text(json.dumps(batch, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Prepared batch input for {len(batch)} articles at {BATCH_INPUT_PATH}")

def apply_metadata():
    if not BATCH_OUTPUT_PATH.exists():
        print(f"Error: Batch output file {BATCH_OUTPUT_PATH} not found. Please generate description and keywords first.")
        return
        
    try:
        results = json.loads(BATCH_OUTPUT_PATH.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"Error parsing batch output: {e}")
        return

    updated_count = 0
    for item in results:
        file_path = Path(item["file_path"])
        if not file_path.exists():
            print(f"Warning: File {file_path} not found, skipping.")
            continue
            
        content = file_path.read_text(encoding="utf-8")
        
        # Format values
        desc_escaped = escape_yaml_string(item["description"])
        keywords_formatted = format_keywords_yaml(item.get("keywords", []))
        
        # Let's replace the description line and insert the keywords line after it
        # We look for a line starting with description:
        lines = content.splitlines()
        new_lines = []
        updated = False
        for line in lines:
            if line.startswith("description:"):
                new_lines.append(f"description: {desc_escaped}")
                # Check if keywords already exists in the next line or is present
                # If keywords doesn't exist in the file, we add it right after description
                if "keywords:" not in content:
                    new_lines.append(f"keywords: {keywords_formatted}")
                updated = True
            elif line.startswith("keywords:"):
                # If keywords line already exists, update it here
                new_lines.append(f"keywords: {keywords_formatted}")
            else:
                new_lines.append(line)
                
        if updated:
            file_path.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
            print(f"Updated {file_path.name}")
            updated_count += 1
            
    print(f"Successfully updated {updated_count} files.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Enrich article metadata with description and keywords")
    parser.add_argument("--prepare", action="store_true", help="Scan articles and prepare batch input JSON")
    parser.add_argument("--apply", action="store_true", help="Apply batch output JSON back to article YAMLs")
    parser.add_argument("--limit", type=int, default=10, help="Number of articles to process in this batch")
    parser.add_argument("--slug", type=str, default="building_standard_act", help="Dataset slug (e.g. building_standard_act_enforcement_order)")
    args = parser.parse_args()
    
    data_dir = WORKSPACE_DIR / "data" / args.slug
    
    if args.prepare:
        scan_and_prepare(args.limit, data_dir)
    elif args.apply:
        apply_metadata()
    else:
        parser.print_help()
