"""Quick brace/bracket/paren balance checker for JS files."""
import sys

def check(path):
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
    stack = []
    pairs = {")": "(", "]": "[", "}": "{"}
    in_string = None
    escape_next = False
    line_num = 1
    for ch in content:
        if ch == "\n":
            line_num += 1
        if escape_next:
            escape_next = False
            continue
        if ch == "\\" and in_string:
            escape_next = True
            continue
        if ch in ('"', "'", "`"):
            if in_string == ch:
                in_string = None
            elif not in_string:
                in_string = ch
            continue
        if in_string:
            continue
        if ch in "([{":
            stack.append((ch, line_num))
        elif ch in ")]}":
            if not stack:
                print(f"ERROR: Unmatched {ch} at line {line_num}")
                return 1
            top, tline = stack.pop()
            if top != pairs[ch]:
                print(f"ERROR: Mismatched {top} (line {tline}) closed by {ch} at line {line_num}")
                return 1
    if stack:
        for s, ln in stack:
            print(f"ERROR: Unclosed {s} opened at line {ln}")
        return 1
    print(f"OK - {line_num} lines, all brackets balanced")
    return 0

if __name__ == "__main__":
    sys.exit(check(sys.argv[1]))
