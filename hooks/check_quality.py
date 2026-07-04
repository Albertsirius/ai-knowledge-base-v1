#!/usr/bin/env python3
"""Quality check for knowledge entry JSON files with 5-dimension scoring.

Usage:
    python hooks/check_quality.py <json_file> [json_file2...]
    python hooks/check_quality.py *.json
    python hooks/check_quality.py knowledge/articles/*.json
"""

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

# ---------------------------------------------------------------------------
# Dataclass definitions
# ---------------------------------------------------------------------------


@dataclass
class DimensionScore:
    name: str
    points: float
    max_points: int
    details: str = ""


@dataclass
class QualityReport:
    filepath: str
    entry_id: str
    title: str = ""
    dimensions: list[DimensionScore] = field(default_factory=list)
    total: float = 0.0
    grade: str = "C"
    errors: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

STANDARD_TAGS: set[str] = {
    "large-language-model",
    "agent-framework",
    "rag",
    "mcp",
    "fine-tuning",
    "prompt-engineering",
    "multi-agent",
    "code-generation",
    "transformer",
    "attention",
    "embedding",
    "vector-database",
    "knowledge-graph",
    "langchain",
    "llamaindex",
    "openai",
    "anthropic",
    "deepseek",
    "huggingface",
    "chatbot",
    "code-assistant",
    "data-analysis",
    "document-qa",
    "workflow-automation",
    "python",
    "typescript",
    "rust",
    "go",
    "react",
    "cli",
    "api",
    "sdk",
    "docker",
    "kubernetes",
    "evaluation",
    "benchmark",
    "safety",
    "alignment",
}

TECH_KEYWORDS: list[re.Pattern] = [
    re.compile(rf"\b{k}\b", re.IGNORECASE)
    for k in [
        "LLM",
        "RAG",
        "Agent",
        "Transformer",
        "Fine-tuning",
        "MCP",
        "Prompt",
        "Embedding",
        "Vector",
        "Inference",
        "Training",
        "RLHF",
        "MoE",
        "LoRA",
        "Quantization",
        "GPU",
        "CUDA",
        "Token",
        "Attention",
        "Diffusion",
        "LangChain",
        "LlamaIndex",
        "Chroma",
        "Pinecone",
        "Milvus",
        "Weaviate",
        "OpenAI",
        "Anthropic",
        "API",
        "SDK",
        "CLI",
        "Open Source",
    ]
]

BUZZWORDS_CN: list[str] = [
    "赋能",
    "抓手",
    "闭环",
    "打通",
    "全链路",
    "底层逻辑",
    "颗粒度",
    "对齐",
    "拉通",
    "沉淀",
    "强大的",
]

BUZZWORDS_EN: list[re.Pattern] = [
    re.compile(rf"(?<![a-zA-Z-]){re.escape(bw)}(?![a-zA-Z-])", re.IGNORECASE)
    for bw in [
        "groundbreaking",
        "revolutionary",
        "game-changing",
        "cutting-edge",
        "state-of-the-art",
        "best-in-class",
        "world-class",
        "next-generation",
        "disruptive",
        "paradigm-shift",
        "unprecedented",
        "bleeding-edge",
    ]
]

TIMESTAMP_FIELDS = {
    "created_at",
    "updated_at",
    "analyzed_at",
    "published_at",
}

TAG_PATTERN = re.compile(r"^[a-z0-9][a-z0-9-]*$")


# ---------------------------------------------------------------------------
# File collection (same pattern as validate_json.py)
# ---------------------------------------------------------------------------


def collect_files(paths: list[str]) -> list[Path]:
    files: set[Path] = set()
    for raw in paths:
        path = Path(raw)
        if "*" in raw or "?" in raw:
            matches = list(Path.cwd().glob(raw))
            if not matches:
                print(
                    f"Warning: pattern '{raw}' matched no files",
                    file=sys.stderr,
                )
            files.update(matches)
        elif path.is_file():
            files.add(path)
        else:
            print(f"Warning: file not found: {path}", file=sys.stderr)
    return sorted(files)


# ---------------------------------------------------------------------------
# Scoring functions
# ---------------------------------------------------------------------------


def score_summary_quality(summary: str) -> DimensionScore:
    max_pts = 25
    if not isinstance(summary, str):
        return DimensionScore("摘要质量", 0, max_pts, "summary 字段缺失或非字符串")

    length = len(summary)

    if length >= 50:
        base = 20.0
    elif length >= 20:
        base = round(length / 50 * 20, 1)
    else:
        return DimensionScore(
            "摘要质量",
            0,
            max_pts,
            f"摘要过短 ({length} 字，最低 20 字)",
        )

    keyword_hits = sum(1 for pat in TECH_KEYWORDS if pat.search(summary))
    bonus = min(keyword_hits, 5)

    points = min(base + bonus, max_pts)
    return DimensionScore(
        "摘要质量",
        points,
        max_pts,
        f"长度 {length} 字 ({'达标' if length >= 50 else '基本达标'})，"
        f"技术关键词命中 {keyword_hits} 个 (+{bonus})",
    )


def score_technical_depth(score_value) -> DimensionScore:
    max_pts = 25
    if score_value is None:
        return DimensionScore("技术深度", 0, max_pts, "缺少 score 字段")

    if not isinstance(score_value, (int, float)) or isinstance(score_value, bool):
        return DimensionScore(
            "技术深度", 0, max_pts, f"score 类型无效: {type(score_value).__name__}"
        )

    if not (1 <= score_value <= 10):
        return DimensionScore(
            "技术深度",
            0,
            max_pts,
            f"score ({score_value}) 超出 1-10 范围",
        )

    points = round(score_value * 2.5, 1)
    return DimensionScore(
        "技术深度",
        points,
        max_pts,
        f"原始 score={score_value} → {points}/{max_pts}",
    )


def score_format_compliance(entry: dict) -> DimensionScore:
    max_pts = 20
    checks = [
        ("id", "id" in entry and isinstance(entry["id"], str) and entry["id"] != ""),
        (
            "title",
            "title" in entry
            and isinstance(entry["title"], str)
            and entry["title"] != "",
        ),
        (
            "url",
            "url" in entry and isinstance(entry["url"], str) and entry["url"] != "",
        ),
        (
            "status",
            "status" in entry
            and isinstance(entry["status"], str)
            and entry["status"] != "",
        ),
        (
            "timestamp",
            any(
                entry.get(f)
                for f in TIMESTAMP_FIELDS
                if f in entry and entry.get(f) is not None
            ),
        ),
    ]

    per_item = max_pts // len(checks)
    passed = sum(1 for _, ok in checks if ok)
    points = passed * per_item

    failed_fields = [name for name, ok in checks if not ok]
    detail = f"通过 {passed}/{len(checks)} 项"
    if failed_fields:
        detail += f"，缺失: {', '.join(failed_fields)}"

    return DimensionScore("格式规范", points, max_pts, detail)


def score_tag_precision(tags) -> DimensionScore:
    max_pts = 15
    if not isinstance(tags, list):
        return DimensionScore("标签精度", 0, max_pts, "tags 字段缺失或非数组")

    if len(tags) == 0:
        return DimensionScore("标签精度", 0, max_pts, "标签列表为空")

    invalid_tags: list[str] = []
    nonstandard_tags: list[str] = []

    for t in tags:
        if not isinstance(t, str) or not TAG_PATTERN.match(t):
            invalid_tags.append(str(t))
        elif t not in STANDARD_TAGS:
            nonstandard_tags.append(t)

    if invalid_tags:
        return DimensionScore(
            "标签精度",
            0,
            max_pts,
            f"存在非法格式标签: {', '.join(invalid_tags)} (需小写字母/数字/连字符)",
        )

    valid_count = len(tags)
    non_std_count = len(nonstandard_tags)

    if valid_count <= 3:
        points = 15.0
    else:
        points = max(15.0 - (valid_count - 3) * 3, 3.0)

    if non_std_count > 0:
        points = max(points - non_std_count * 2, 0.0)

    detail = f"{valid_count} 个标签"
    if nonstandard_tags:
        detail += f"，{non_std_count} 个非标准标签: {', '.join(nonstandard_tags)}"
    if valid_count > 3:
        detail += f"，超出推荐数量 (-{min((valid_count - 3) * 3, 12)})"

    return DimensionScore("标签精度", round(points, 1), max_pts, detail)


def score_buzzword_detection(summary: str) -> DimensionScore:
    max_pts = 15
    if not isinstance(summary, str):
        return DimensionScore("空洞词检测", max_pts, max_pts, "无 summary 可检测，默认满分")

    hits: list[str] = []

    for word in BUZZWORDS_CN:
        if word in summary:
            hits.append(word)

    for pat in BUZZWORDS_EN:
        match = pat.search(summary)
        if match:
            hits.append(match.group())

    count = len(hits)
    if count == 0:
        points = max_pts
        return DimensionScore("空洞词检测", points, max_pts, "未检测到空洞词")
    elif count == 1:
        points = 12.0
    elif count == 2:
        points = 8.0
    else:
        points = 0.0

    return DimensionScore(
        "空洞词检测",
        points,
        max_pts,
        f"检测到 {count} 个空洞词: {', '.join(hits)}",
    )


# ---------------------------------------------------------------------------
# Quality check entry point
# ---------------------------------------------------------------------------

STATIC_MAX = 80


def determine_grade(total: float) -> str:
    if total >= 80:
        return "A"
    elif total >= 60:
        return "B"
    else:
        return "C"


def check_entry(entry: dict, filepath: Path, index: int) -> QualityReport:
    eid = entry.get("id", f"{filepath}#{index}")
    title = entry.get("title", "")
    summary = entry.get("summary", "")
    score_val = entry.get("score")
    tags = entry.get("tags")

    dims = [
        score_summary_quality(summary),
        score_technical_depth(score_val),
        score_format_compliance(entry),
        score_tag_precision(tags),
        score_buzzword_detection(summary),
    ]

    total = round(sum(d.points for d in dims), 1)
    grade = determine_grade(total)

    return QualityReport(
        filepath=str(filepath),
        entry_id=eid,
        title=title,
        dimensions=dims,
        total=total,
        grade=grade,
    )


# ---------------------------------------------------------------------------
# Render helpers
# ---------------------------------------------------------------------------


def render_progress_bar(current: int, total: int, width: int = 30) -> str:
    if total == 0:
        return "[                              ] 0%"
    pct = int(current / total * 100)
    filled = int(current / total * width)
    bar = "█" * filled + "░" * (width - filled)
    return f"[{bar}] {pct}%"


def render_grade(grade: str) -> str:
    colors = {"A": "\033[92m", "B": "\033[93m", "C": "\033[91m"}
    reset = "\033[0m"
    color = colors.get(grade, "")
    return f"{color}{grade}{reset}"


def print_report(report: QualityReport) -> None:
    title_display = report.title
    if len(title_display) > 60:
        title_display = title_display[:57] + "..."

    print(f"\n{'─' * 62}")
    print(f"  {report.entry_id}")
    print(f"  {title_display}")
    print(f"{'─' * 62}")

    for dim in report.dimensions:
        bar_len = 20
        filled = int(dim.points / dim.max_points * bar_len) if dim.max_points > 0 else 0
        bar = "█" * filled + "░" * (bar_len - filled)
        print(f"  {dim.name:<10} {bar} {dim.points:>5.1f}/{dim.max_points}")
        print(f"             {dim.details}")

    print(f"{'─' * 62}")
    total_display = f"{report.total:.1f}/100"
    print(f"  总分: {total_display:<10}  等级: {render_grade(report.grade)}")
    print(f"{'─' * 62}")


def print_summary_table(reports: list[QualityReport]) -> None:
    print(f"\n{'=' * 72}")
    print(f"  质量检查汇总")
    print(f"{'=' * 72}")
    print(f"  {'文件':<30} {'总分':>6} {'等级':>6}  {'摘要':>6} {'深度':>6} {'格式':>6} {'标签':>6} {'空洞':>6}")
    print(f"  {'─' * 30} {'─' * 6} {'─' * 6}  {'─' * 6} {'─' * 6} {'─' * 6} {'─' * 6} {'─' * 6}")

    for r in reports:
        fname = Path(r.filepath).name
        if len(fname) > 28:
            fname = fname[:25] + "..."
        dim_scores = {d.name: d.points for d in r.dimensions}
        print(
            f"  {fname:<30} {r.total:>5.1f}  {render_grade(r.grade):>4}  "
            f"{dim_scores.get('摘要质量', 0):>5.1f} "
            f"{dim_scores.get('技术深度', 0):>5.1f} "
            f"{dim_scores.get('格式规范', 0):>5.1f} "
            f"{dim_scores.get('标签精度', 0):>5.1f} "
            f"{dim_scores.get('空洞词检测', 0):>5.1f}"
        )

    a_count = sum(1 for r in reports if r.grade == "A")
    b_count = sum(1 for r in reports if r.grade == "B")
    c_count = sum(1 for r in reports if r.grade == "C")
    avg_total = round(sum(r.total for r in reports) / len(reports), 1) if reports else 0

    print(f"  {'─' * 30} {'─' * 6} {'─' * 6}  {'─' * 6} {'─' * 6} {'─' * 6} {'─' * 6} {'─' * 6}")
    print(f"\n  共 {len(reports)} 条 | "
          f"\033[92mA: {a_count}\033[0m | "
          f"\033[93mB: {b_count}\033[0m | "
          f"\033[91mC: {c_count}\033[0m | "
          f"平均分: {avg_total:.1f}")
    print(f"{'=' * 72}\n")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Quality check knowledge entry JSON files (5-dimension scoring).",
    )
    parser.add_argument(
        "files",
        nargs="+",
        help="JSON files and/or glob patterns (e.g. *.json)",
    )
    parser.add_argument(
        "--no-progress",
        action="store_true",
        help="Disable progress bar (for CI / piped output)",
    )
    args = parser.parse_args()

    files = collect_files(args.files)
    if not files:
        print("Error: no JSON files found", file=sys.stderr)
        return 1

    reports: list[QualityReport] = []
    total_entries = 0
    read_errors: list[str] = []

    for filepath in files:
        try:
            data = json.loads(filepath.read_text(encoding="utf-8"))
        except OSError as exc:
            read_errors.append(f"{filepath}: cannot read file — {exc}")
            continue
        except json.JSONDecodeError as exc:
            read_errors.append(f"{filepath}: invalid JSON — {exc}")
            continue

        if isinstance(data, dict):
            entries = [data]
        elif isinstance(data, list):
            entries = data
        else:
            read_errors.append(
                f"{filepath}: top-level must be dict or list, got {type(data).__name__}"
            )
            continue

        for idx, entry in enumerate(entries):
            if not isinstance(entry, dict):
                read_errors.append(
                    f"{filepath}#{idx}: entry must be dict, got {type(entry).__name__}"
                )
                continue

            report = check_entry(entry, filepath, idx)
            reports.append(report)
            total_entries += 1

            if not args.no_progress:
                print(
                    f"\r  {render_progress_bar(total_entries, total_entries)}",
                    end="",
                    file=sys.stderr,
                )

    if not args.no_progress:
        print("\r" + " " * 50 + "\r", end="", file=sys.stderr)

    if read_errors:
        print("\n读取错误:", file=sys.stderr)
        for err in read_errors:
            print(f"  {err}", file=sys.stderr)
        print()

    if not reports:
        print("Error: no valid entries found to check", file=sys.stderr)
        return 1

    for report in reports:
        print_report(report)

    print_summary_table(reports)

    has_c_grade = any(r.grade == "C" for r in reports)
    if has_c_grade:
        print(
            "💡 提示: 存在 C 级条目，建议优化后再提交\n"
            "   - 摘要质量不足 → 扩展至 50 字以上并包含技术细节\n"
            "   - 技术深度不足 → 确保 score 字段在 1-10 范围内\n"
            "   - 格式规范不足 → 补充 id/title/url/status/timestamp\n"
            "   - 标签精度不足 → 使用标准标签，控制在 1-3 个\n"
            "   - 空洞词检测 → 避免使用赋能/抓手/闭环等空洞词",
        )
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
