import json, re
from collections import Counter
ex = json.load(open("/Users/jiang/WorkSpace/JWLCode/JWLCode-frappe/_lms_convert/work/exercises.json"))
tc = json.load(open("/Users/jiang/WorkSpace/JWLCode/JWLCode-frappe/_lms_convert/work/test_cases.json"))
htmls = [e["problem_statement"] or "" for e in ex]
def count(pred): return sum(1 for h in htmls if pred(h))
print("total statements:", len(htmls))
print("has <math>:", count(lambda h: "<math" in h))
print("has <img:", count(lambda h: "<img" in h))
print("has <pre>:", count(lambda h: "<pre" in h))
print("has <code>:", count(lambda h: "<code" in h))
print("has 样例输入 (exact):", count(lambda h: "样例输入" in h))
print("has 输入格式:", count(lambda h: "输入格式" in h))
print("has 输出格式:", count(lambda h: "输出格式" in h))
print("has 题目描述:", count(lambda h: "题目描述" in h))
print("has 数据范围:", count(lambda h: "数据范围" in h))
print("has 样例(s):", count(lambda h: re.search(r"样例\s*\d*\s*输入", h)))
print("has <h4>:", count(lambda h: "<h4>" in h))
print("has <strong>:", count(lambda h: "<strong>" in h))
print("has 提示:", count(lambda h: "提示" in h))
print("has 本地评测说明:", count(lambda h: "本地评测说明" in h))
# count number of samples per statement
sample_counts = Counter()
for h in htmls:
    n = len(re.findall(r"样例\s*\d*\s*输入", h))
    sample_counts[n] += 1
print("sample-block counts:", dict(sorted(sample_counts.items())))
# distinct section headers (h4/h3)
hdrs = Counter()
for h in htmls:
    for m in re.findall(r"<h[34][^>]*>(.*?)</h[34]>", h, re.S):
        txt = re.sub(r"<[^>]+>", "", m).strip()
        hdrs[txt] += 1
print("\nTop section headers:")
for k,v in hdrs.most_common(30): print(f"  {v:3}  {k}")
