#!/usr/bin/env python3
"""설계 문서의 구조 검사. 기준은 docs/review-policy.md 4장.

논리가 타당한지는 사람과 리뷰 봇이 판단한다. 여기서는 그 판단을 할 수 있는
최소 구조가 갖춰졌는지만 본다.

사용법:
  python3 scripts/check_design.py                  # 전체 검사
  python3 scripts/check_design.py --base origin/main  # Accepted ADR 불변 검사 포함
  PR_BODY="..." python3 scripts/check_design.py    # PR 본문 검사 포함
"""
import argparse
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ADR_DIR = ROOT / "docs" / "adr"
SCOPE = ROOT / "docs" / "design" / "00-scope.md"
ADR_INDEX = ADR_DIR / "README.md"

SECTIONS = [
    "맥락",
    "결정을 강제하는 요구사항",
    "선택지",
    "평가",
    "결정 전 검증",
    "추천안",
    "결정",
    "결과",
    "이 결정이 깨지는 조건",
    "운영에서 볼 지표와 장애 대응",
    "예상 꼬리질문",
]
PLACEHOLDER = "(결정자 작성)"
STATUS_RE = re.compile(r"^(Proposed|Accepted|Rejected|Superseded by ADR-\d{4})$")
REQ_ID_RE = re.compile(r"\b(FR-\d+|NFR-\d+|L-\d+)\b")
DASHES = (chr(0x2014), chr(0x2013))

errors: list[str] = []


def fail(path: Path, msg: str) -> None:
    errors.append(f"{path.relative_to(ROOT)}: {msg}")


def header_value(text: str, key: str) -> str:
    m = re.search(rf"^\|\s*{re.escape(key)}\s*\|\s*(.*?)\s*\|\s*$", text, re.M)
    return m.group(1) if m else ""


def split_sections(text: str) -> dict[str, str]:
    parts = re.split(r"^## (\d+)\. (.+)$", text, flags=re.M)
    found = {}
    for i in range(1, len(parts), 3):
        # "## 4. 평가: 언어 특성 비교"처럼 콜론 뒤 부제는 허용한다
        name = parts[i + 1].split(":")[0].strip()
        found[name] = (int(parts[i]), parts[i + 2].strip())
    return found


def count_options(body: str) -> int:
    subsections = len(re.findall(r"^### ", body, re.M))
    table_rows = max(0, len(re.findall(r"^\|", body, re.M)) - 2)
    list_items = len(re.findall(r"^- ", body, re.M))
    return max(subsections, table_rows, list_items)


def defined_requirement_ids() -> set[str]:
    return set(REQ_ID_RE.findall(SCOPE.read_text()))


def adr_files() -> list[Path]:
    return sorted(p for p in ADR_DIR.glob("[0-9][0-9][0-9][0-9]-*.md") if not p.name.startswith("0000-"))


def check_adr(path: Path, known_ids: set[str]) -> str:
    text = path.read_text()
    number = path.name[:4]

    if not re.search(rf"^# ADR-{number}: \S", text, re.M):
        fail(path, f"제목은 '# ADR-{number}: 제목' 형식이어야 합니다")

    status = header_value(text, "상태")
    if not STATUS_RE.match(status):
        fail(path, f"상태 값이 올바르지 않습니다: '{status}'")

    reqs = header_value(text, "관련 FR/NFR")
    if not reqs:
        fail(path, "관련 FR/NFR이 비어 있습니다 (Q2)")
    for rid in REQ_ID_RE.findall(text):
        if rid not in known_ids:
            fail(path, f"{rid}는 docs/design/00-scope.md에 정의되지 않았습니다")

    sections = split_sections(text)
    for i, name in enumerate(SECTIONS, start=1):
        if name not in sections:
            fail(path, f"섹션 '## {i}. {name}'이 없습니다")
        elif sections[name][0] != i:
            fail(path, f"섹션 '{name}'의 번호가 {i}가 아닙니다")

    def body(name: str) -> str:
        return sections.get(name, (0, ""))[1]

    if count_options(body("선택지")) < 2:
        fail(path, "선택지가 2개 미만입니다 (Q3)")
    for name, q in (("결과", "Q4"), ("이 결정이 깨지는 조건", "Q7"), ("운영에서 볼 지표와 장애 대응", "Q8")):
        if not body(name):
            fail(path, f"'{name}' 섹션이 비어 있습니다 ({q})")

    if status == "Proposed" and not body("추천안"):
        fail(path, "Proposed ADR에는 추천안이 있어야 합니다")
    if status == "Accepted":
        decision = body("결정")
        if not decision or PLACEHOLDER in decision:
            fail(path, "Accepted ADR의 결정 섹션은 결정자가 채워야 합니다")
        if not header_value(text, "결정일"):
            fail(path, "Accepted ADR에는 결정일이 있어야 합니다")
    return status


def check_index(statuses: dict[str, str]) -> None:
    index = ADR_INDEX.read_text()
    listed = {}
    for m in re.finditer(r"^\|\s*\[(\d{4})\]\(([^)]+)\)\s*\|[^|]*\|\s*([^|]+?)\s*\|", index, re.M):
        listed[m.group(1)] = (m.group(2), m.group(3))
    for number, status in statuses.items():
        if number not in listed:
            fail(ADR_INDEX, f"ADR-{number}이 목록에 없습니다")
        elif listed[number][1] != status:
            fail(ADR_INDEX, f"ADR-{number} 상태가 파일({status})과 목록({listed[number][1]})에서 다릅니다")
    for number, (link, _) in listed.items():
        if not (ADR_DIR / link).exists():
            fail(ADR_INDEX, f"ADR-{number} 링크 대상이 없습니다: {link}")


def check_accepted_immutable(base: str) -> None:
    diff = subprocess.run(
        ["git", "diff", "--name-only", f"{base}...HEAD", "--", "docs/adr/"],
        cwd=ROOT, capture_output=True, text=True, check=True,
    ).stdout.split()
    for rel in diff:
        path = ROOT / rel
        old = subprocess.run(["git", "show", f"{base}:{rel}"], cwd=ROOT, capture_output=True, text=True)
        if old.returncode != 0 or header_value(old.stdout, "상태") != "Accepted":
            continue
        if not path.exists():
            fail(path, "Accepted ADR은 삭제할 수 없습니다. 새 ADR로 대체하세요")
            continue
        strip_status = lambda t: re.sub(r"^\|\s*상태\s*\|.*$", "", t, flags=re.M)
        new = path.read_text()
        if strip_status(old.stdout) != strip_status(new):
            fail(path, "Accepted ADR의 본문이 바뀌었습니다. 상태를 'Superseded by ADR-XXXX'로 바꾸는 것 외에는 새 ADR로 대체하세요")
        elif not header_value(new, "상태").startswith("Superseded by"):
            fail(path, "Accepted ADR의 상태는 Superseded로만 바꿀 수 있습니다")


def check_links_and_dashes() -> None:
    for path in ROOT.rglob("*"):
        if ".git" in path.parts or not path.is_file() or path.suffix not in {".md", ".yaml", ".yml", ".toml", ".py"}:
            continue
        text = path.read_text()
        for n, line in enumerate(text.splitlines(), start=1):
            if any(d in line for d in DASHES):
                fail(path, f"{n}행: 긴 대시 문자를 쓰지 않습니다")
        if path.suffix == ".md":
            for target in re.findall(r"\]\(([^)#\s]+)(?:#[^)]*)?\)", text):
                if "://" in target:
                    continue
                if not (path.parent / target).exists():
                    fail(path, f"깨진 상대 링크: {target}")


def check_pr_body(body: str) -> None:
    pseudo = ROOT / ".github" / "pull_request_template.md"
    if not re.search(r"\b(ADR-\d{4}|FR-\d+|NFR-\d+)\b", body):
        fail(pseudo, "PR 본문에 관련 ADR 또는 FR/NFR이 없습니다 (Q2)")
    m = re.search(r"잃는 것[^:\n]*:\s*(.*)", body)
    if m is None or not m.group(1).strip():
        fail(pseudo, "PR 본문의 '잃는 것' 항목이 비어 있습니다 (Q4)")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", help="비교할 기준 ref. 지정하면 Accepted ADR 불변 검사를 한다")
    args = parser.parse_args()

    known_ids = defined_requirement_ids()
    statuses = {p.name[:4]: check_adr(p, known_ids) for p in adr_files()}
    check_index(statuses)
    check_links_and_dashes()
    if args.base:
        check_accepted_immutable(args.base)
    if os.environ.get("PR_BODY") is not None:
        check_pr_body(os.environ["PR_BODY"])

    if errors:
        print("설계 문서 검사 실패:")
        for e in errors:
            print(f"  - {e}")
        return 1
    print(f"설계 문서 검사 통과: ADR {len(statuses)}개")
    return 0


if __name__ == "__main__":
    sys.exit(main())
