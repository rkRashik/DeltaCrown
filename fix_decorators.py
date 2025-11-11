import re

with open('tests/test_websocket_enhancement_module_4_5.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Fix the backtick-n to actual newline
content = content.replace('@pytest.mark.django_db(transaction=True)`n', '@pytest.mark.django_db(transaction=True)\n')

with open('tests/test_websocket_enhancement_module_4_5.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("Fixed decorator formatting")
