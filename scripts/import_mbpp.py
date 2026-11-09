# scripts/import_mbpp.py
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from db import supabase
from datasets import load_dataset

def import_mbpp():
    ds = load_dataset("google-research-datasets/mbpp", "sanitized")
    total = 0
    skip = 0
    # 遍历全部split
    for split_name in ds:
        for item in ds[split_name]:
            prompt_text = item["prompt"]
            # 先查询这条题目是否已经存在
            exist_res = supabase.table("problems").select("id").eq("prompt", prompt_text).execute()
            if len(exist_res.data) > 0:
                skip +=1
                continue

            payload = {
                "dataset_name": "mbpp",
                "subset": "sanitized",
                "prompt": item["prompt"],
                "reference_solution": item["code"],
                "test_cases": item["test_list"],
                "test_imports": item["test_imports"]
            }
            supabase.table("problems").insert(payload).execute()
            total +=1
            if total % 20 ==0:
                print(f"✅ 已新增 {total} 条，跳过重复 {skip}")
    print(f"\n导入完成！新增：{total} 条，跳过已存在：{skip} 条")

if __name__ == "__main__":
    import_mbpp()
