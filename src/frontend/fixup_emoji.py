#!/usr/bin/env python3
"""Second-pass fixups for edge cases the initial transform missed."""
import re, os, subprocess

PROJECT = os.path.dirname(os.path.abspath(__file__))
os.chdir(PROJECT)

EMOJI_SVG = {
    '\U0001F310': '1f310.svg',
    '\U0001F4AC': '1f4ac.svg',
    '\U0001F464': '1f464.svg',
    '\U0001F465': '1f465.svg',
    '\U0001F50D': '1f50d.svg',
    '\U0001F517': '1f517.svg',
    '\U0001F504': '1f504.svg',
    '\U0001F52E': '1f52e.svg',
    '\U0001F3E0': '1f3e0.svg',
    '\U0001F319': '1f319.svg',
    '\U0001FAE7': '1fae7.svg',
    '\U0001F9F5': '1f9f5.svg',
    '\U0001F5BC': '1f5bc.svg',
}

# Also match emoji with FE0F variation selector
EMOJI_FE0F = {k + '\uFE0F': v for k, v in EMOJI_SVG.items()}

def find_all_emoji(line):
    """Find all SMP emoji (with or without FE0F) in a line."""
    results = []
    # Check FE0F variants first (longer match)
    for ec, svg in EMOJI_FE0F.items():
        if ec in line:
            results.append((ec, svg))
            line = line.replace(ec, '')
    for ec, svg in EMOJI_SVG.items():
        if ec in line:
            results.append((ec, svg))
            line = line.replace(ec, '')
    return results


# ═══════════════════════════════════════════════
#  Fix 1: ProfilePage 🖼️ (with FE0F) 
# ═══════════════════════════════════════════════

def fix_profilepage():
    fpath = os.path.join(PROJECT, 'ProfilePage.qml')
    with open(fpath, 'r') as f:
        content = f.read()
    
    original = content
    
    # 🖼️ (with FE0F) in text -> Image
    content = content.replace(
        'text: "\U0001F5BC\uFE0F"',
        'source: "qrc:/emoji/1f5bc.svg"'
    )
    
    # Add textFormat: Text.RichText to the 🖼️ case since it has FE0F
    # Actually, the FE0F is now removed from text since we replaced the whole thing
    # with an Image source. That's fine.
    
    if content != original:
        with open(fpath, 'w') as f:
            f.write(content)
        print("✓ ProfilePage: Fixed 🖼️ (FE0F variant)")
    else:
        print("— ProfilePage: No FE0F fix needed")


# ═══════════════════════════════════════════════
#  Fix 2: ConvListPanel text->Image
# ═══════════════════════════════════════════════

def fix_convlist():
    fpath = os.path.join(PROJECT, 'ConversationListPanel.qml')
    with open(fpath, 'r') as f:
        lines = f.readlines()
    
    new_lines = []
    changes = []
    i = 0
    while i < len(lines):
        line = lines[i]
        
        # Pattern: Text { text: "emoji/xxx.svg" ... }
        # Need to find Text blocks where text starts with "emoji/"
        if line.strip().startswith('Text {') and i + 1 < len(lines):
            next_line = lines[i + 1]
            if 'text: "emoji/' in next_line:
                indent = line[:len(line)-len(line.lstrip())]
                text_indent = next_line[:len(next_line)-len(next_line.lstrip())]
                
                # Get font size
                font_size = 14
                j = i + 1
                closing_idx = -1
                while j < len(lines):
                    if lines[j].strip() == '}':
                        closing_idx = j
                        break
                    m = re.search(r'font\.pixelSize:\s*(\d+)', lines[j])
                    if m:
                        font_size = int(m.group(1))
                    j += 1
                
                if closing_idx >= 0:
                    svg_path = re.search(r'text: "(emoji/[^"]+)"', lines[i+1])
                    if svg_path:
                        svg = svg_path.group(1)
                        new_block = [
                            f"{indent}Image {{\n",
                            f"{text_indent}source: \"qrc:/{svg}\"\n",
                            f"{text_indent}sourceSize.width: {font_size}\n",
                            f"{text_indent}sourceSize.height: {font_size}\n",
                            f"{text_indent}fillMode: Image.PreserveAspectFit\n",
                            f"{indent}}}\n",
                        ]
                        new_lines.extend(new_block)
                        i = closing_idx + 1
                        changes.append(f"Text -> Image for {svg}")
                        continue
        
        # Pattern: model icon display: Text { ... text: modelData.icon ... }
        # The model data now has icon: "emoji/xxx.svg" instead of emoji chars
        # Find Text that displays modelData.icon or similar
        if 'text: modelData.icon' in line:
            indent = line[:len(line)-len(line.lstrip())]
            # Find parent Text block
            start = i
            # Go back to find "Text {"
            for lookback in range(i, max(0, i-5)-1, -1):
                if lines[lookback].strip() == 'Text {':
                    start = lookback
                    break
            
            # Forward to find closing }
            closing_idx = -1
            font_size = 14
            for j in range(start + 1, len(lines)):
                if lines[j].strip() == '}':
                    closing_idx = j
                    break
                m = re.search(r'font\.pixelSize:\s*(\d+)', lines[j])
                if m:
                    font_size = int(m.group(1))
            
            if closing_idx >= 0:
                parent_indent = lines[start][:len(lines[start])-len(lines[start].lstrip())]
                new_block = [
                    f"{parent_indent}Image {{\n",
                    f"{lines[start+1][:len(lines[start+1])-len(lines[start+1].lstrip())]}anchors.centerIn: parent\n",
                    f"{lines[start+1][:len(lines[start+1])-len(lines[start+1].lstrip())]}source: \"qrc:/\" + modelData.icon\n",
                    f"{lines[start+1][:len(lines[start+1])-len(lines[start+1].lstrip())]}sourceSize.width: {font_size}\n",
                    f"{lines[start+1][:len(lines[start+1])-len(lines[start+1].lstrip())]}sourceSize.height: {font_size}\n",
                    f"{lines[start+1][:len(lines[start+1])-len(lines[start+1].lstrip())]}fillMode: Image.PreserveAspectFit\n",
                    f"{parent_indent}}}\n",
                ]
                # Remove old lines from start to closing_idx
                while len(new_lines) > start:
                    new_lines.pop()
                new_lines.extend(new_block)
                i = closing_idx + 1
                changes.append("modelData.icon -> Image")
                continue
        
        new_lines.append(line)
        i += 1
    
    if changes:
        with open(fpath, 'w') as f:
            f.writelines(new_lines)
        print(f"✓ ConversationListPanel:")
        for c in changes:
            print(f"  - {c}")
    else:
        print("— ConversationListPanel: no changes")


# ═══════════════════════════════════════════════
#  Fix 3: MessagesPage single-line Text with 👥
# ═══════════════════════════════════════════════

def fix_messagespage():
    fpath = os.path.join(PROJECT, 'MessagesPage.qml')
    with open(fpath, 'r') as f:
        content = f.read()
    
    original = content
    
    # Text { anchors.centerIn: parent; text: "👥"; font.pixelSize: 16 }
    content = content.replace(
        'Text { anchors.centerIn: parent; text: "\U0001F465"; font.pixelSize: 16 }',
        'Image { anchors.centerIn: parent; source: "qrc:/emoji/1f465.svg"; sourceSize.width: 16; sourceSize.height: 16; fillMode: Image.PreserveAspectFit }'
    )
    
    if content != original:
        with open(fpath, 'w') as f:
            f.write(content)
        print("✓ MessagesPage: Fixed 👥 single-line Text")
    else:
        print("— MessagesPage: no changes")


# ═══════════════════════════════════════════════
#  Fix 4: ChatPanel conditional 👥 
# ═══════════════════════════════════════════════

def fix_chatpanel():
    fpath = os.path.join(PROJECT, 'ChatPanel.qml')
    with open(fpath, 'r') as f:
        lines = f.readlines()
    
    new_lines = []
    i = 0
    changed = False
    
    while i < len(lines):
        line = lines[i]
        
        # Find Text block with 👥 in conditional
        if line.strip() == 'Text {' and i + 3 < len(lines):
            # Check if emoji in the next lines
            combined = ''.join(lines[i:i+6])
            if '\U0001F465' in combined and 'text:' in combined:
                indent = line[:len(line)-len(line.lstrip())]
                
                # Collect the Text block
                block = []
                while i < len(lines):
                    block.append(lines[i])
                    if lines[i].strip() == '}':
                        break
                    i += 1
                
                # Parse properties
                font_size = 14
                has_center = False
                for bl in block:
                    if 'anchors.centerIn' in bl:
                        has_center = True
                    m = re.search(r'font\.pixelSize:\s*(\d+)', bl)
                    if m:
                        font_size = int(m.group(1))
                
                # Build replacement
                # The conditional chooses between "👥" and a single char
                # We keep the conditional but the emoji branch uses Image
                # Since we can't conditionally render a different component type,
                # we'll use a Loader
                
                new_block = [
                    f"{indent}Loader {{\n",
                    f"{indent}    anchors.centerIn: parent\n",
                    f"{indent}    sourceComponent: root.currentConversation && root.currentConversation.type === \"group\"\n",
                    f"{indent}                  ? groupIcon : singleCharText\n",
                    f"{indent}}}\n",
                    f"\n",
                    f"{indent}Component {{ id: groupIcon\n",
                    f"{indent}    Image {{\n",
                    f'{indent}        source: "qrc:/emoji/1f465.svg"\n',
                    f"{indent}        sourceSize.width: 16\n",
                    f"{indent}        sourceSize.height: 16\n",
                    f"{indent}        fillMode: Image.PreserveAspectFit\n",
                    f"{indent}    }}\n",
                    f"{indent}}}\n",
                    f"\n",
                    f"{indent}Component {{ id: singleCharText\n",
                    f"{indent}    Text {{\n",
                    f'{indent}        text: root.currentConversation && root.currentConversation.target_name\n',
                    f'{indent}              ? root.currentConversation.target_name.charAt(0) : "?"\n',
                    f'{indent}        font.pixelSize: 14\n',
                    f'{indent}        color: window.textSecondary\n',
                    f'{indent}    }}\n',
                    f"{indent}}}\n",
                ]
                
                new_lines.extend(new_block)
                changed = True
                i += 1
                print(f"✓ ChatPanel: Fixed 👥 conditional Text -> Loader")
                continue
        
        new_lines.append(line)
        i += 1
    
    if changed:
        with open(fpath, 'w') as f:
            f.writelines(new_lines)
    else:
        print("— ChatPanel: no changes")


# ═══════════════════════════════════════════════
#  Fix 5: ConversationItem conditional 👥
# ═══════════════════════════════════════════════

def fix_conversationitem():
    fpath = os.path.join(PROJECT, 'ConversationItem.qml')
    with open(fpath, 'r') as f:
        lines = f.readlines()
    
    new_lines = []
    i = 0
    changed = False
    
    while i < len(lines):
        line = lines[i]
        
        if line.strip() == 'Text {' and i + 3 < len(lines):
            combined = ''.join(lines[i:i+6])
            if '\U0001F465' in combined and 'text:' in combined:
                indent = line[:len(line)-len(line.lstrip())]
                
                # Collect block
                block = []
                while i < len(lines):
                    block.append(lines[i])
                    if lines[i].strip() == '}':
                        break
                    i += 1
                
                font_size = 18
                for bl in block:
                    m = re.search(r'font\.pixelSize:\s*(\d+)', bl)
                    if m:
                        font_size = int(m.group(1))
                
                new_block = [
                    f"{indent}Loader {{\n",
                    f"{indent}    anchors.centerIn: parent\n",
                    f"{indent}    sourceComponent: root.convType === \"group\" ? convGroupIcon : convSingleChar\n",
                    f"{indent}}}\n",
                    f"\n",
                    f"{indent}Component {{ id: convGroupIcon\n",
                    f"{indent}    Image {{\n",
                    f'{indent}        source: "qrc:/emoji/1f465.svg"\n',
                    f"{indent}        sourceSize.width: 18\n",
                    f"{indent}        sourceSize.height: 18\n",
                    f"{indent}        fillMode: Image.PreserveAspectFit\n",
                    f"{indent}    }}\n",
                    f"{indent}}}\n",
                    f"\n",
                    f"{indent}Component {{ id: convSingleChar\n",
                    f"{indent}    Text {{\n",
                    f'{indent}        text: root.targetName ? root.targetName.charAt(0) : "?"\n',
                    f'{indent}        font.pixelSize: 16\n',
                    f'{indent}        color: window.textSecondary\n',
                    f'{indent}    }}\n',
                    f"{indent}}}\n",
                ]
                
                new_lines.extend(new_block)
                changed = True
                i += 1
                print(f"✓ ConversationItem: Fixed 👥 conditional Text -> Loader")
                continue
        
        new_lines.append(line)
        i += 1
    
    if changed:
        with open(fpath, 'w') as f:
            f.writelines(new_lines)
    else:
        print("— ConversationItem: no changes")


# ═══════════════════════════════════════════════
#  Fix 6: SquarePage 🧵 RichText needs textFormat + PNG generation
# ═══════════════════════════════════════════════

def fix_squarepage_richtext():
    fpath = os.path.join(PROJECT, 'SquarePage.qml')
    with open(fpath, 'r') as f:
        content = f.read()
    
    original = content
    
    # Add textFormat: Text.RichText to the Text block that has 🧵
    # Find: font.pixelSize: 12 (right after the 🧵 RichText line)
    # Insert textFormat: Text.RichText before font.pixelSize
    if '<img src' in content:
        content = content.replace(
            '<img src=\\\'qrc:/emoji/1f9f5.png\\\'',
            '<img src=\'qrc:/emoji/1f9f5.png\''
        )
    
    # Try to fix the escaped quotes
    # The issue is \\' - python escaping. Let me check the actual content
    # Actually let me just add textFormat after the RichText img line
    
    if '\'qrc:/emoji/1f9f5.png\'' in content:
        # Find the Text block with RichText
        lines = content.split('\n')
        new_lines = []
        added_text_format = False
        for line in lines:
            new_lines.append(line)
            if 'qrc:/emoji/1f9f5.png' in line and not added_text_format:
                # Add textFormat on the next indented line
                indent = line[:len(line)-len(line.lstrip())]
                new_lines.append(f'{indent}    textFormat: Text.RichText\n')
                added_text_format = True
        content = '\n'.join(new_lines)
    
    if content != original:
        with open(fpath, 'w') as f:
            f.write(content)
        print("✓ SquarePage: Fixed 🧵 RichText formatting")
    else:
        print("— SquarePage: no RichText fix needed")


# Also generate a PNG for 🧵 from its SVG (for RichText img tag)
def generate_emoji_pngs():
    """Generate PNG versions for emoji used in RichText img tags."""
    from PIL import Image as PILImage
    import io, cairosvg
    
    emoji_dir = os.path.join(PROJECT, 'emoji')
    
    # Which emoji need PNG? Currently only 🧵 (1f9f5)
    for svg_name in ['1f9f5.svg']:  # Add more if RichText img tags need them
        svg_path = os.path.join(emoji_dir, svg_name)
        png_path = os.path.join(emoji_dir, svg_name.replace('.svg', '.png'))
        
        if os.path.exists(png_path):
            print(f"  — {png_path} already exists")
            continue
        
        if not os.path.exists(svg_path):
            print(f"  ✗ {svg_path} not found")
            continue
        
        try:
            import cairosvg
            with open(svg_path, 'rb') as f:
                svg_data = f.read()
            png_data = cairosvg.svg2png(svg_data, output_width=48, output_height=48)
            with open(png_path, 'wb') as f:
                f.write(png_data)
            print(f"  ✓ Generated {png_path} ({len(png_data)} bytes)")
        except ImportError:
            print(f"  ! cairosvg not available, trying rsvg-convert...")
            try:
                subprocess.run(['rsvg-convert', svg_path, '-o', png_path, '-w', '48', '-h', '48'], check=True)
                size = os.path.getsize(png_path)
                print(f"  ✓ Generated {png_path} ({size} bytes)")
            except (FileNotFoundError, subprocess.CalledProcessError):
                print(f"  ✗ Cannot convert SVG to PNG (need cairosvg or librsvg)")


# ═══════════════════════════════════════════════
#  Run all fixes
# ═══════════════════════════════════════════════

if __name__ == '__main__':
    print("=== Fix 1: ProfilePage 🖼️ (FE0F) ===")
    fix_profilepage()
    
    print("\n=== Fix 2: ConversationListPanel Text→Image ===")
    fix_convlist()
    
    print("\n=== Fix 3: MessagesPage 👥 Text→Image ===")
    fix_messagespage()
    
    print("\n=== Fix 4: ChatPanel 👥 conditional → Loader ===")
    fix_chatpanel()
    
    print("\n=== Fix 5: ConversationItem 👥 conditional → Loader ===")
    fix_conversationitem()
    
    print("\n=== Fix 6: SquarePage 🧵 RichText ===")
    fix_squarepage_richtext()
    
    print("\n=== PNG Generation for RichText ===")
    generate_emoji_pngs()
    
    print("\nDone!")
