#!/usr/bin/env python3
"""
Transform QML emoji usage to SVG-based Image components.
Handles known patterns in each QML file specifically.
"""

import re, os, shutil

PROJECT = os.path.dirname(os.path.abspath(__file__))

# ── Emoji to codepoint SVG path mapping ──
EMOJI_SVG = {
    '\U0001F310': '1f310.svg',   # 🌐
    '\U0001F4AC': '1f4ac.svg',   # 💬
    '\U0001F464': '1f464.svg',   # 👤
    '\U0001F465': '1f465.svg',   # 👥
    '\U0001F50D': '1f50d.svg',   # 🔍
    '\U0001F517': '1f517.svg',   # 🔗
    '\U0001F504': '1f504.svg',   # 🔄
    '\U0001F52E': '1f52e.svg',   # 🔮
    '\U0001F3E0': '1f3e0.svg',   # 🏠
    '\U0001F319': '1f319.svg',   # 🌙
    '\U0001FAE7': '1fae7.svg',   # 🫧
    '\U0001F9F5': '1f9f5.svg',   # 🧵
    '\U0001F5BC': '1f5bc.svg',   # 🖼
}

def emoji_to_src(e):
    """Convert emoji char to qrc SVG source path."""
    base = EMOJI_SVG.get(e)
    if not base:
        return None
    return f"emoji/{base}"

# ── Helper regex to find emoji in text ──
EMOJI_PAT = re.compile('[' + ''.join(EMOJI_SVG.keys()) + ']')

def has_smp_emoji(s):
    return bool(EMOJI_PAT.search(s))

# ═══════════════════════════════════════════════
#  File-specific transforms
# ═══════════════════════════════════════════════

def transform_mainpage(content):
    """MainPage.qml transforms"""
    lines = content.split('\n')
    new_lines = []
    changes = []
    
    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        
        # ── Transform 1: darkIcon() function ──
        # Change returns from emoji to source path
        if stripped == 'function darkIcon() {':
            new_lines.append(line)
            i += 1
            # Read next few lines
            indent = line[:len(line) - len(line.lstrip())]
            while i < len(lines):
                cl = lines[i]
                # return "🌙" → return "emoji/1f319.svg"
                cl = cl.replace('return "🌙"', 'return "emoji/1f319.svg"')
                # return "☀️" → keep as BMP text (☀ is BMP, renders fine)
                # Actually ☀ has a FE0F variation selector, but it's BMP
                # Keep ☀ as-is since it's a BMP char
                cl = cl.replace('return "☀️"', 'return "emoji/2600.svg"')
                new_lines.append(cl)
                if '}' in cl.strip():
                    break
                i += 1
            changes.append("darkIcon() returns SVG paths")
            i += 1
            continue
        
        # ── Transform 2: styleIcon(mode) function ──
        if stripped == 'function styleIcon(mode) {':
            new_lines.append(line)
            i += 1
            while i < len(lines):
                cl = lines[i]
                cl = cl.replace('return "🔮"', 'return "emoji/1f52e.svg"')
                cl = cl.replace('return "🫧"', 'return "emoji/1fae7.svg"')
                cl = cl.replace('return "🏠"', 'return "emoji/1f3e0.svg"')
                new_lines.append(cl)
                if '}' in cl.strip():
                    break
                i += 1
            changes.append("styleIcon() returns SVG paths")
            i += 1
            continue
        
        # ── Transform 3: Nav model items (L313-315) ──
        # Change { icon: "🌐", tip: qsTr("广场") } → { icon: "emoji/1f310.svg", ... }
        for emoji_char, svg_file in EMOJI_SVG.items():
            pattern = f'icon: "{emoji_char}"'
            if pattern in line:
                line = line.replace(pattern, f'icon: "emoji/{svg_file}"')
                changes.append(f"Model icon: {emoji_char} -> {svg_file}")
        
        # ── Transform 4: Text { text: modelData.icon } ──
        # Change from Text to Image
        # Simple heuristic: check for 'text: modelData.icon'
        if 'text: modelData.icon' in stripped:
            indent = line[:len(line) - len(line.lstrip())]
            
            # Read the parent Text block
            text_start = i
            text_lines = [lines[i]]
            i += 1
            while i < len(lines) and not lines[i].strip().startswith('}') or (lines[i].strip() == '}' and text_start < i):
                # Check for closing brace at this level
                stripped_i = lines[i].strip()
                if stripped_i == '}':
                    # This closes the Text block
                    text_lines.append(lines[i])
                    break
                text_lines.append(lines[i])
                i += 1
            
            # Collect Text properties
            font_size = 20  # default
            for tl in text_lines:
                m = re.search(r'font\.pixelSize:\s*(\d+)', tl)
                if m:
                    font_size = int(m.group(1))
            
            # Replace Text block with Image block
            print(f"    Replacing Text(modelData.icon) at L{i+1}, font_size={font_size}")
            new_text = [
                f"{indent}Image {{",
                f"{indent}    anchors.centerIn: parent",
                f'{indent}    source: {{ var m={{}};',
                f'{indent}        m["emoji/1f310.svg"]="qrc:/emoji/1f310.svg";',
                f'{indent}        m["emoji/1f4ac.svg"]="qrc:/emoji/1f4ac.svg";',
                f'{indent}        m["emoji/1f464.svg"]="qrc:/emoji/1f464.svg";',
                f'{indent}        return m[modelData.icon] || ""',
                f'{indent}    }}()',
                f'{indent}    sourceSize.width: {font_size}',
                f'{indent}    sourceSize.height: {font_size}',
                f'{indent}    fillMode: Image.PreserveAspectFit',
                f'{indent}}}',
            ]
            new_lines.extend(new_text)
            changes.append(f"Text(modelData.icon) -> Image at text_size={font_size}")
            i += 1
            continue
        
        # ── Transform 5: Uses of darkIcon() / styleIcon() in Text ──
        # Find patterns like: Text { text: root.darkIcon() }
        # and replace with Image
        for func_name in ['root.darkIcon()', 'root.styleIcon(root.styleMode)']:
            if f'text: {func_name}' in stripped:
                indent = line[:len(line) - len(line.lstrip())]
                text_start = i
                text_lines = [line]
                i += 1
                while i < len(lines):
                    stripped_i = lines[i].strip()
                    if stripped_i == '}':
                        text_lines.append(lines[i])
                        break
                    text_lines.append(lines[i])
                    i += 1
                
                # Get font size
                font_size = 18
                for tl in text_lines:
                    m = re.search(r'font\.pixelSize:\s*(\d+)', tl)
                    if m:
                        font_size = int(m.group(1))
                
                # Determine SVG path function
                if 'darkIcon' in func_name:
                    fname = 'darkIcon'
                else:
                    fname = 'styleIcon'
                
                new_text = [
                    f"{indent}Image {{",
                    f"{indent}    anchors.centerIn: parent",
                    f'{indent}    source: "qrc:/" + root.{fname}()',
                    f'{indent}    sourceSize.width: {font_size}',
                    f'{indent}    sourceSize.height: {font_size}',
                    f'{indent}    fillMode: Image.PreserveAspectFit',
                    f'{indent}}}',
                ]
                new_lines.extend(new_text)
                changes.append(f"Text({fname}()) -> Image")
                i += 1
                break
            else:
                continue
            break
        else:
            new_lines.append(line)
            i += 1
    
    return '\n'.join(new_lines), changes


def transform_squarepage(content):
    """SquarePage.qml transforms"""
    lines = content.split('\n')
    new_lines = []
    changes = []
    
    # Handle 🧵 inline text: "🧵 %1 条评论"
    # This needs RichText with img tag, but SVG doesn't work in RichText img
    # We'll pre-render 🧵 to a PNG and use that
    
    for i, line in enumerate(lines):
        if '🧵' in line:
            # Replace inline emoji with RichText img tag
            # "🧵 %1 条评论" → "<img src='qrc:/emoji/1f9f5.png' width=12 height=12 /> %1 条评论"
            line = line.replace(
                '"🧵 %1 条评论".arg(modelData.comments.length)',
                '"<img src=\\\'qrc:/emoji/1f9f5.png\\\' width=12 height=12 /> %1 条评论".arg(modelData.comments.length)'
            )
            changes.append("🧵 inline -> RichText img tag (PNG needed)")
        
        # Also ensure it uses textFormat: Text.RichText
        if changes and not any('textFormat' in l for l in new_lines[-3:]):
            pass  # We'll handle this differently
        
        new_lines.append(line)
    
    return '\n'.join(new_lines), changes


def transform_profilepage(content):
    """ProfilePage.qml transforms"""
    lines = content.split('\n')
    new_lines = []
    changes = []
    
    i = 0
    while i < len(lines):
        line = lines[i]
        new_lines.append(line)
        
        # Check if line has a Text block with emoji
        if 'text:' in line and has_smp_emoji(line):
            # Find the parent Text block boundaries
            # The line might be inside a Text block or be the Text opening
            indent = line[:len(line) - len(line.lstrip())]
            
            if 'Text {' in line:
                # This is the opening; collect until closing }
                text_lines = [line]
                i += 1
                while i < len(lines):
                    text_lines.append(lines[i])
                    if lines[i].strip() == '}':
                        break
                    i += 1
                
                # Parse properties
                font_size = 14
                has_center = False
                emoji_char = None
                for tl in text_lines:
                    m = re.search(r'font\.pixelSize:\s*(\d+)', tl)
                    if m:
                        font_size = int(m.group(1))
                    if 'anchors.centerIn' in tl:
                        has_center = True
                    for ec in EMOJI_SVG:
                        if ec in tl:
                            emoji_char = ec
                
                if emoji_char:
                    svg = emoji_to_src(emoji_char)
                    changes.append(f"ProfilePage: {emoji_char} -> Image({svg}) size={font_size}")
                    
                    # Build Image replacement
                    new_block = [
                        f"{indent}Image {{",
                    ]
                    if has_center:
                        new_block.append(f"{indent}    anchors.centerIn: parent")
                    new_block.append(f"{indent}    source: \"qrc:/{svg}\"")
                    new_block.append(f"{indent}    sourceSize.width: {font_size}")
                    new_block.append(f"{indent}    sourceSize.height: {font_size}")
                    new_block.append(f"{indent}    fillMode: Image.PreserveAspectFit")
                    new_block.append(f"{indent}}}")
                    
                    # Replace last few lines (remove the Text block, add Image block)
                    for _ in range(len(text_lines)):
                        new_lines.pop()
                    new_lines.extend(new_block)
            else:
                # Emoji standalone text value like: text: "👤"
                # Try to find a nearby font.pixelSize
                font_size = 14
                for j in range(max(0, i-5), i):
                    m = re.search(r'font\.pixelSize:\s*(\d+)', new_lines[j])
                    if m:
                        font_size = int(m.group(1))
                
                for ec in EMOJI_SVG:
                    if ec in line:
                        svg = emoji_to_src(ec)
                        # Replace just the text property
                        new_lines[-1] = line.replace(
                            f'text: "{ec}"',
                            f'source: "qrc:/{svg}"'
                        )
                        changes.append(f"ProfilePage: {ec} -> source (inline)")
                        break
        
        i += 1
    
    return '\n'.join(new_lines), changes


def transform_convlistpanel(content):
    """ConversationListPanel.qml transforms"""
    lines = content.split('\n')
    new_lines = []
    changes = []
    
    for line in lines:
        # Model data icon: { text: qsTr("创建群聊"), icon: "👥" }
        for ec, svg in EMOJI_SVG.items():
            pattern = f'icon: "{ec}"'
            if pattern in line:
                line = line.replace(pattern, f'icon: "emoji/{svg}"')
                changes.append(f"ConvListPanel model icon: {ec}")
        
        # Standalone text: text: "emoji"
        for ec, svg in EMOJI_SVG.items():
            pattern = f'text: "{ec}"'
            if pattern in line:
                line = line.replace(pattern, f'text: "emoji/{svg}"')
                changes.append(f"ConvListPanel text: {ec} -> text: {svg}")
        
        new_lines.append(line)
    
    return '\n'.join(new_lines), changes


def transform_chatpanel(content):
    """ChatPanel.qml transforms"""
    lines = content.split('\n')
    new_lines = []
    changes = []
    
    for line in lines:
        dir(line)
        new_lines.append(line)
    
    return '\n'.join(new_lines), changes


def transform_conversationitem(content):
    """ConversationItem.qml - 👥 is inside a conditional, complex, skip for now"""
    return content, []


def transform_messagespage(content):
    """MessagesPage.qml transforms"""
    lines = content.split('\n')
    new_lines = []
    changes = []
    
    i = 0
    while i < len(lines):
        line = lines[i]
        
        # Look for Text { text: "👥" } pattern
        stripped = line.strip()
        if stripped == 'Text {' and i + 1 < len(lines):
            next_line = lines[i + 1]
            for ec in EMOJI_SVG:
                if f'text: "{ec}"' in next_line:
                    # Replace this Text block
                    indent = line[:len(line) - len(line.lstrip())]
                    font_size = 16
                    # Look ahead for font.pixelSize
                    j = i + 1
                    while j < len(lines) and '}' not in lines[j]:
                        m = re.search(r'font\.pixelSize:\s*(\d+)', lines[j])
                        if m:
                            font_size = int(m.group(1))
                        j += 1
                    
                    svg = emoji_to_src(ec)
                    new_block = [
                        f"{indent}Image {{",
                        f"{indent}    anchors.centerIn: parent",
                        f'{indent}    source: "qrc:/{svg}"',
                        f'{indent}    sourceSize.width: {font_size}',
                        f'{indent}    sourceSize.height: {font_size}',
                        f'{indent}    fillMode: Image.PreserveAspectFit',
                        f'{indent}}}',
                    ]
                    new_lines.extend(new_block)
                    # Skip the Text block lines
                    i += 1
                    while i < len(lines) and lines[i].strip() != '}':
                        i += 1
                    i += 1  # skip the closing }
                    changes.append(f"MessagesPage: {ec} -> Image size={font_size}")
                    break
            else:
                new_lines.append(line)
                i += 1
        else:
            new_lines.append(line)
            i += 1
    
    return '\n'.join(new_lines), changes


# ═══════════════════════════════════════════════
#  Update resources.qrc with emoji files
# ═══════════════════════════════════════════════

def update_qrc():
    qrc_path = os.path.join(PROJECT, 'resources.qrc')
    with open(qrc_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Check if emoji section exists
    if 'emoji/' in content:
        print("  QRC already has emoji entries")
        return
    
    # Find </RCC> and insert before it, or find last </qresource> or <RCC>
    # Find the last </qresource> tag
    insert_pos = content.rfind('</RCC>')
    if insert_pos == -1:
        print("  ERROR: Cannot find </RCC> in resources.qrc")
        return
    
    # Build emoji file entries
    emoji_section = '\n    <qresource prefix="/emoji">\n'
    for svg in sorted(os.listdir(os.path.join(PROJECT, 'emoji'))):
        if svg.endswith('.svg'):
            emoji_section += f'        <file alias="{svg}">emoji/{svg}</file>\n'
    emoji_section += '    </qresource>\n  '
    
    new_content = content[:insert_pos] + emoji_section + content[insert_pos:]
    with open(qrc_path, 'w', encoding='utf-8') as f:
        f.write(new_content)
    print(f"  QRC updated with emoji resources")


# ═══════════════════════════════════════════════
#  Main
# ═══════════════════════════════════════════════

TRANSFORMS = {
    'MainPage.qml': transform_mainpage,
    'SquarePage.qml': transform_squarepage,
    'ProfilePage.qml': transform_profilepage,
    'ConversationListPanel.qml': transform_convlistpanel,
    'ChatPanel.qml': transform_chatpanel,
    'ConversationItem.qml': transform_conversationitem,
    'MessagesPage.qml': transform_messagespage,
}

def main():
    os.chdir(PROJECT)
    
    # Update QRC first
    print("=== Updating resources.qrc ===")
    update_qrc()
    
    print("\n=== Transforming QML files ===")
    
    for fname, transform_func in TRANSFORMS.items():
        fpath = os.path.join(PROJECT, fname)
        if not os.path.exists(fpath):
            print(f"  SKIP {fname} (not found)")
            continue
        
        # Backup
        bak_path = fpath + '.bak'
        if not os.path.exists(bak_path):
            shutil.copy2(fpath, bak_path)
            print(f"  BACKUP {fname} -> {fname}.bak")
        
        # Read
        with open(fpath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check if any emoji patterns exist
        if not has_smp_emoji(content):
            print(f"  SKIP {fname} (no SMP emoji)")
            continue
        
        # Transform
        new_content, changes = transform_func(content)
        
        if changes:
            with open(fpath, 'w', encoding='utf-8') as f:
                f.write(new_content)
            print(f"  ✓ {fname}:")
            for c in changes:
                print(f"    - {c}")
        else:
            print(f"  — {fname}: no changes applied")
    
    print("\nDone! Backup files created as *.qml.bak")


if __name__ == '__main__':
    main()
