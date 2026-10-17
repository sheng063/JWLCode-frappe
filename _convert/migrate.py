#!/usr/bin/env python3
"""Create LMS Programming Exercise docs from the authored specs, swap lesson
assignment blocks to program blocks, and optionally delete old LMS Assignment docs.

Run inside the site context (bench --site school.localhost console / execute).
Specs are read from /workspace/lms/_convert/specs/*.json.
"""
import glob
import json
import os

COURSE = "c1-2024"
SPEC_DIR = "/workspace/lms/_convert/specs"
DELETE_OLD_ASSIGNMENTS = True

# Load specs keyed by assignment
specs = {}
for p in sorted(glob.glob(os.path.join(SPEC_DIR, "*.json"))):
    spec = json.load(open(p, encoding="utf-8"))
    specs[spec["assignment"]] = spec

print("Loaded specs for", len(specs), "assignments")

# Load all lessons in the course
lessons = frappe.get_all("Course Lesson", {"course": COURSE}, ["name", "content"])
created = []
skipped = []
missing = []

for lesson in lessons:
    try:
        content = json.loads(lesson["content"])
    except Exception as e:
        print("PARSE ERROR on lesson", lesson["name"], e)
        continue
    changed = False
    for block in content.get("blocks", []):
        if block.get("type") == "assignment":
            asg = block["data"].get("assignment")
            spec = specs.get(asg)
            if not spec:
                missing.append(asg)
                print("NO SPEC for", asg, "in lesson", lesson["name"])
                continue
            # Create the programming exercise
            ex = frappe.new_doc("LMS Programming Exercise")
            ex.title = spec["title"]
            ex.problem_statement = spec["problem_statement"]
            ex.language = "C++"
            ex.evaluation_mode = "Judge Service"
            ex.time_limit_seconds = 2
            ex.memory_limit_kb = 128000
            for tc in spec["test_cases"]:
                ex.append("test_cases", {"input": tc.get("input", ""), "expected_output": tc.get("expected_output", "")})
            ex.insert(ignore_permissions=True)
            # Swap block to program
            block["type"] = "program"
            block["data"] = {"exercise": ex.name}
            changed = True
            created.append((asg, ex.name, lesson["name"], spec["title"]))
    if changed:
        les = frappe.get_doc("Course Lesson", lesson["name"])
        les.content = json.dumps(content, ensure_ascii=False)
        les.save(ignore_permissions=True)
        print("Updated lesson", lesson["name"])

print("\n=== CREATED exercises ===")
for asg, exname, lesson, title in created:
    print(f"{asg} -> {exname} ({title}) in lesson {lesson}")
print("total created:", len(created))
if missing:
    print("MISSING specs (not created):", missing)

if DELETE_OLD_ASSIGNMENTS:
    print("\n=== DELETING old LMS Assignment docs ===")
    for asg in list(specs.keys()):
        if frappe.db.exists("LMS Assignment", asg):
            frappe.delete_doc("LMS Assignment", asg, ignore_permissions=True)
            print("deleted", asg)
        else:
            print("not found", asg)

frappe.db.commit()
print("\nDONE")
