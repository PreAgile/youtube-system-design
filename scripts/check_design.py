#!/usr/bin/env python3
"""Check the current problem card, ADR structure and local Markdown links.

This does not assess decision quality, user approval or implementation truth.
Run: python3 scripts/check_design.py
"""
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parent.parent
REQ_RE = re.compile(r"\b(?:FR|NFR)-\d+\b")
SECTIONS = [
    "문제와 제약", "대안과 판단 기준", "사용자 제안과 검토", "결정과 이유",
    "얻는 것과 감수한 비용", "검증과 남은 불확실성", "재검토 조건",
]


def field(text, key):
    match = re.search(rf"^\|\s*{re.escape(key)}\s*\|\s*(.*?)\s*\|$", text, re.M)
    return match.group(1) if match else ""


def validate_adr(path, text, requirements):
    problems = []
    number = path.name[:4]
    if not re.search(rf"^# ADR-{number}: \S", text, re.M):
        problems.append("title must match the filename ADR number")
    status = field(text, "상태")
    if not re.fullmatch(r"Proposed|Accepted|Rejected|Superseded by ADR-\d{4}", status):
        problems.append("invalid or missing status")
    refs = set(REQ_RE.findall(field(text, "관련 FR/NFR")))
    if not refs:
        problems.append("related FR/NFR is missing")
    unknown = set(REQ_RE.findall(text)) - requirements
    if unknown:
        problems.append("undefined requirements: " + ", ".join(sorted(unknown)))
    if not field(text, "작성일"):
        problems.append("creation date is missing")
    sections = list(re.finditer(r"^## (\d+)\. (.+)$", text, re.M))
    if [(int(m[1]), m[2].strip()) for m in sections] != list(enumerate(SECTIONS, 1)):
        problems.append("expected the seven numbered sections from the ADR template")
    for index, match in enumerate(sections):
        end = sections[index + 1].start() if index + 1 < len(sections) else len(text)
        body = text[match.end():end].strip()
        if not body:
            problems.append(f"section {match[1]} is empty")
        if match[1] == "4" and status == "Accepted" and re.search(r"미정|비교 중|결정자 작성", body):
            problems.append("Accepted decision still contains an undecided placeholder")
    if status == "Accepted" and not re.fullmatch(r"\d{4}-\d{2}-\d{2}", field(text, "결정일")):
        problems.append("Accepted decision needs a decision date")
    return problems


def anchors(text):
    counts = {}
    result = set()
    for heading in re.findall(r"^#{1,6}\s+(.+)$", text, re.M):
        slug = re.sub(r"[^\w\-\s]", "", heading.lower()).replace(" ", "-")
        count = counts.get(slug, 0)
        counts[slug] = count + 1
        result.add(slug if count == 0 else f"{slug}-{count}")
    return result


def check(root=ROOT):
    errors = []
    readme = root / "README.md"
    if not readme.exists():
        return ["README.md is missing"], 0
    problem = readme.read_text(encoding="utf-8")
    defined = re.findall(r"^\|\s*((?:FR|NFR)-\d+)\s*\|", problem, re.M)
    requirements = set(defined)
    if not any(r.startswith("FR-") for r in requirements) or not any(r.startswith("NFR-") for r in requirements):
        errors.append("README.md must define both FR and NFR table rows")
    if len(defined) != len(requirements):
        errors.append("README.md has duplicate requirement definitions")
    for name in ["AGENTS.md", "CLAUDE.md", "docs/interview/progress.md", "docs/adr/README.md", "docs/adr/0000-template.md"]:
        if not (root / name).exists():
            errors.append(f"{name} is missing")
    adr_dir = root / "docs/adr"
    index_path = adr_dir / "README.md"
    index = index_path.read_text(encoding="utf-8") if index_path.exists() else ""
    listed = {}
    for m in re.finditer(r"^\|\s*\[(\d{4})\]\(([^)]+)\)\s*\|[^|]*\|\s*([^|]+)\|", index, re.M):
        listed[m[1]] = (m[2], m[3].strip())
    records = [p for p in sorted(adr_dir.glob("[0-9][0-9][0-9][0-9]-*.md")) if not p.name.startswith("0000-")]
    numbers = {p.name[:4] for p in records}
    if len(numbers) != len(records):
        errors.append("ADR filenames contain duplicate numbers")
    for p in records:
        text = p.read_text(encoding="utf-8")
        rel = p.relative_to(root)
        errors.extend(f"{rel}: {msg}" for msg in validate_adr(p, text, requirements))
        item = listed.get(p.name[:4])
        if item != (p.name, field(text, "상태")):
            errors.append(f"{rel}: index filename/status does not match")
        status = field(text, "상태")
        if status.startswith("Superseded by ADR-") and status[-4:] not in numbers:
            errors.append(f"{rel}: replacement ADR is missing")
    for number in set(listed) - numbers:
        errors.append(f"docs/adr/README.md: ADR-{number} file is missing")
    markdown_files = [p for p in root.rglob("*.md") if ".git" not in p.relative_to(root).parts]
    for p in markdown_files:
        for target in re.findall(r"\]\(([^)\s]+)\)", p.read_text(encoding="utf-8")):
            if "://" in target or target.startswith("mailto:"):
                continue
            name, separator, fragment = target.partition("#")
            destination = p.parent / name if name else p
            if not destination.exists():
                errors.append(f"{p.relative_to(root)}: missing link {target}")
            elif separator and fragment and destination.suffix == ".md" and fragment not in anchors(destination.read_text(encoding="utf-8")):
                errors.append(f"{p.relative_to(root)}: missing heading {target}")
    return errors, len(records)


if __name__ == "__main__":
    errors, count = check()
    if errors:
        print("\n".join(errors), file=sys.stderr)
        raise SystemExit(1)
    print(f"문서 검사 통과: README 요구사항·진행 기준·상대 링크, ADR {count}개")
