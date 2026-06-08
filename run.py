import argparse
import json
import sys
import os
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from api.api_client import APIClient
from utils.knowledge_base import KnowledgeBase
from civil_court import CivilCourt

def load_cases(jsonl_path: str, start_idx: int, end_idx: int):

    cases = []
    with open(jsonl_path, 'r', encoding='utf-8') as f:
        for i, line in enumerate(f):
            if start_idx <= i <= end_idx:
                if line.strip():
                    cases.append(json.loads(line))
    return cases

def parse_optional_bool(value: str) -> bool:

    normalized = value.strip().lower()
    if normalized in {"true", "1", "yes", "y", "on"}:
        return True
    if normalized in {"false", "0", "no", "n", "off"}:
        return False
    raise argparse.ArgumentTypeError("布尔参数只能是 true/false")

def format_optional_bool(value):

    if value is None:
        return "未设置"
    return str(value)

def format_api_key_status(value, default_value=None):

    if value:
        return "自定义"
    return "默认" if default_value and default_value != "sk-empty" else "未设置"

def format_base_url_status(value, default_value=None):

    if value:
        return "自定义"
    return "默认" if default_value else "未设置"

def parse_args():

    parser = argparse.ArgumentParser(description="运行民事模拟法庭")
    parser.add_argument("start_idx", type=int, help="起始案件索引(包含)")
    parser.add_argument("end_idx", type=int, help="结束案件索引(包含)")
    parser.add_argument("--judge-model", default="deepseek-v3.2", help="法官使用的模型名")
    parser.add_argument("--plaintiff-model", default="qwen3-32b", help="原告使用的模型名")
    parser.add_argument("--defendant-model", default="qwen3-32b", help="被告使用的模型名")
    parser.add_argument("--summary-model", default="qwen3-32b", help="阶段总结使用的模型名")
    parser.add_argument("--embedding-model", default="text-embedding-v4", help="法条检索使用的embedding模型名")
    parser.add_argument("--judge-enable-thinking", type=parse_optional_bool, default=None, help="法官模型是否传 enable_thinking")
    parser.add_argument("--plaintiff-enable-thinking", type=parse_optional_bool, default=None, help="原告模型是否传 enable_thinking")
    parser.add_argument("--defendant-enable-thinking", type=parse_optional_bool, default=None, help="被告模型是否传 enable_thinking")
    parser.add_argument("--summary-enable-thinking", type=parse_optional_bool, default=None, help="总结模型是否传 enable_thinking")
    parser.add_argument("--judge-stream", type=parse_optional_bool, default=None, help="法官模型是否启用流式输出")
    parser.add_argument("--plaintiff-stream", type=parse_optional_bool, default=None, help="原告模型是否启用流式输出")
    parser.add_argument("--defendant-stream", type=parse_optional_bool, default=None, help="被告模型是否启用流式输出")
    parser.add_argument("--summary-stream", type=parse_optional_bool, default=None, help="总结模型是否启用流式输出")
    parser.add_argument("--judge-base-url", default=os.getenv("JUDGE_BASE_URL"), help="法官模型专用 base_url")
    parser.add_argument("--plaintiff-base-url", default=os.getenv("PLAINTIFF_BASE_URL"), help="原告模型专用 base_url")
    parser.add_argument("--defendant-base-url", default=os.getenv("DEFENDANT_BASE_URL"), help="被告模型专用 base_url")
    parser.add_argument("--summary-base-url", default=os.getenv("SUMMARY_BASE_URL"), help="总结模型专用 base_url")
    parser.add_argument("--embedding-base-url", default=os.getenv("EMBEDDING_BASE_URL"), help="embedding 模型专用 base_url")
    parser.add_argument("--judge-api-key", default=os.getenv("JUDGE_API_KEY"), help="法官模型专用 api_key")
    parser.add_argument("--plaintiff-api-key", default=os.getenv("PLAINTIFF_API_KEY"), help="原告模型专用 api_key")
    parser.add_argument("--defendant-api-key", default=os.getenv("DEFENDANT_API_KEY"), help="被告模型专用 api_key")
    parser.add_argument("--summary-api-key", default=os.getenv("SUMMARY_API_KEY"), help="总结模型专用 api_key")
    parser.add_argument("--embedding-api-key", default=os.getenv("EMBEDDING_API_KEY"), help="embedding 模型专用 api_key")
    return parser.parse_args()

def create_run_output_dir(base_output_dir: str) -> tuple[str, str]:

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_output_dir = os.path.join(base_output_dir, timestamp)

    suffix = 1
    while os.path.exists(run_output_dir):
        run_output_dir = os.path.join(base_output_dir, f"{timestamp}_{suffix:02d}")
        suffix += 1

    os.makedirs(run_output_dir, exist_ok=True)
    return timestamp, run_output_dir

def save_run_config(args, run_timestamp: str, run_output_dir: str, case_ids: list[int]) -> None:

    config = {
        "run_timestamp": run_timestamp,
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "case_range": {
            "start_idx": args.start_idx,
            "end_idx": args.end_idx,
        },
        "case_count": len(case_ids),
        "case_ids": case_ids,
        "models": {
            "judge": args.judge_model,
            "plaintiff": args.plaintiff_model,
            "defendant": args.defendant_model,
            "summary": args.summary_model,
            "embedding": args.embedding_model,
        },
        "enable_thinking": {
            "judge": args.judge_enable_thinking,
            "plaintiff": args.plaintiff_enable_thinking,
            "defendant": args.defendant_enable_thinking,
            "summary": args.summary_enable_thinking,
        },
        "stream": {
            "judge": args.judge_stream,
            "plaintiff": args.plaintiff_stream,
            "defendant": args.defendant_stream,
            "summary": args.summary_stream,
        },
        "configured_base_url": {
            "default": bool(os.getenv("OPENAI_BASE_URL")),
            "judge": bool(args.judge_base_url),
            "plaintiff": bool(args.plaintiff_base_url),
            "defendant": bool(args.defendant_base_url),
            "summary": bool(args.summary_base_url),
            "embedding": bool(args.embedding_base_url),
        },
        "custom_api_key": {
            "judge": bool(args.judge_api_key),
            "plaintiff": bool(args.plaintiff_api_key),
            "defendant": bool(args.defendant_api_key),
            "summary": bool(args.summary_api_key),
            "embedding": bool(args.embedding_api_key),
        },
        "paths": {
            "output_dir": run_output_dir,
            "cases": "data/selected_cases.jsonl",
            "law_library": "data/law_library.jsonl",
        },
    }

    config_path = os.path.join(run_output_dir, "config.json")
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)

def main(args):

    print("="*60)
    print("民事模拟法庭系统")
    print("="*60)

    API_URL = os.getenv("OPENAI_BASE_URL", "")
    API_KEY = os.getenv("OPENAI_API_KEY", "sk-empty")
    LAW_LIBRARY_PATH = "data/law_library.jsonl"
    CASES_PATH = "data/selected_cases.jsonl"
    OUTPUT_DIR = "output"

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    run_timestamp, run_output_dir = create_run_output_dir(OUTPUT_DIR)
    print(f"\n本次运行输出目录: {run_output_dir}")

    print("\n初始化API客户端...")
    print(f"  法官模型: {args.judge_model}")
    print(f"    enable_thinking: {format_optional_bool(args.judge_enable_thinking)}")
    print(f"    stream: {format_optional_bool(args.judge_stream)}")
    print(f"    base_url: {format_base_url_status(args.judge_base_url, API_URL)}")
    print(f"    api_key: {format_api_key_status(args.judge_api_key, API_KEY)}")
    print(f"  原告模型: {args.plaintiff_model}")
    print(f"    enable_thinking: {format_optional_bool(args.plaintiff_enable_thinking)}")
    print(f"    stream: {format_optional_bool(args.plaintiff_stream)}")
    print(f"    base_url: {format_base_url_status(args.plaintiff_base_url, API_URL)}")
    print(f"    api_key: {format_api_key_status(args.plaintiff_api_key, API_KEY)}")
    print(f"  被告模型: {args.defendant_model}")
    print(f"    enable_thinking: {format_optional_bool(args.defendant_enable_thinking)}")
    print(f"    stream: {format_optional_bool(args.defendant_stream)}")
    print(f"    base_url: {format_base_url_status(args.defendant_base_url, API_URL)}")
    print(f"    api_key: {format_api_key_status(args.defendant_api_key, API_KEY)}")
    print(f"  总结模型: {args.summary_model}")
    print(f"    enable_thinking: {format_optional_bool(args.summary_enable_thinking)}")
    print(f"    stream: {format_optional_bool(args.summary_stream)}")
    print(f"    base_url: {format_base_url_status(args.summary_base_url, API_URL)}")
    print(f"    api_key: {format_api_key_status(args.summary_api_key, API_KEY)}")
    print(f"  Embedding模型: {args.embedding_model}")
    print(f"    base_url: {format_base_url_status(args.embedding_base_url, API_URL)}")
    print(f"    api_key: {format_api_key_status(args.embedding_api_key, API_KEY)}")
    api_client = APIClient(
        API_URL,
        API_KEY,
        judge_model=args.judge_model,
        plaintiff_model=args.plaintiff_model,
        defendant_model=args.defendant_model,
        summary_model=args.summary_model,
        embedding_model=args.embedding_model,
        judge_enable_thinking=args.judge_enable_thinking,
        plaintiff_enable_thinking=args.plaintiff_enable_thinking,
        defendant_enable_thinking=args.defendant_enable_thinking,
        summary_enable_thinking=args.summary_enable_thinking,
        judge_stream=args.judge_stream,
        plaintiff_stream=args.plaintiff_stream,
        defendant_stream=args.defendant_stream,
        summary_stream=args.summary_stream,
        judge_base_url=args.judge_base_url,
        plaintiff_base_url=args.plaintiff_base_url,
        defendant_base_url=args.defendant_base_url,
        summary_base_url=args.summary_base_url,
        embedding_base_url=args.embedding_base_url,
        judge_api_key=args.judge_api_key,
        plaintiff_api_key=args.plaintiff_api_key,
        defendant_api_key=args.defendant_api_key,
        summary_api_key=args.summary_api_key,
        embedding_api_key=args.embedding_api_key,
    )

    print("初始化法条知识库...")
    knowledge_base = KnowledgeBase(api_client, LAW_LIBRARY_PATH)
    knowledge_base.build_index()

    print(f"\n加载案件数据 (索引 {args.start_idx} 到 {args.end_idx})...")
    cases = load_cases(CASES_PATH, args.start_idx, args.end_idx)
    print(f"共加载 {len(cases)} 个案件")
    case_ids = [case_data.get('id', args.start_idx + i) for i, case_data in enumerate(cases)]
    save_run_config(args, run_timestamp, run_output_dir, case_ids)
    print(f"配置已保存到: {run_output_dir}/config.json")

    for i, case_data in enumerate(cases):
        case_id = case_data.get('id', args.start_idx + i)

        try:

            court = CivilCourt(
                api_client=api_client,
                knowledge_base=knowledge_base,
                case_data=case_data,
                case_id=case_id,
                output_dir=run_output_dir
            )

            court.run()

        except Exception as e:
            print(f"\n案件 {case_id} 处理失败: {e}")
            import traceback
            traceback.print_exc()
            continue

    print("\n" + "="*60)
    print("所有案件处理完成！")
    print(f"结果保存在: {run_output_dir}/")
    print("="*60)

if __name__ == "__main__":
    try:
        args = parse_args()

        if args.start_idx < 0 or args.end_idx < args.start_idx:
            print("错误: 索引范围无效")
            sys.exit(1)

        main(args)
    except KeyboardInterrupt:
        print("\n\n程序被用户中断")
        sys.exit(0)
    except Exception as e:
        print(f"\n程序运行出错: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
