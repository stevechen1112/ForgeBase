import re
f = "/opt/forgebase/app/admin/src/app/(dashboard)/dashboard/content-optimizer/page.tsx"
c = open(f, "rb").read()

# Fix scoreColor function - replace entire function with clean version
old_pat = rb"function scoreColor\(score: number\) \{.*?\}"
new_fn = (
    b"function scoreColor(score: number) {\n"
    b"  if (score >= 70) return { text: \"text-green-600\", bar: \"bg-green-500\", label: \"\xe8\x89\xaf\xe5\xa5\xbd\" };\n"
    b"  if (score >= 50) return { text: \"text-yellow-600\", bar: \"bg-yellow-400\", label: \"\xe5\xbe\x85\xe6\x94\xb9\xe5\x96\x84\" };\n"
    b"  return { text: \"text-red-500\", bar: \"bg-red-400\", label: \"\xe9\x9c\x80\xe5\x84\x98\xe5\x8c\x96\" };\n"
    b"}"
)
result = re.sub(old_pat, new_fn, c, flags=re.DOTALL)

# Also fix any corrupted throw new Error messages
result2 = result.replace(b"\"\xe5\x84\x98\xe5\x8c\x96\xe5\xa4\xb1\xe6\x95\x97\"", b"\"\xe5\x84\x98\xe5\x8c\x96\xe5\xa4\xb1\xe6\x95\x97\"")

open(f, "wb").write(result)
print("fixed scoreColor, lines:", result.count(b"\n"))
