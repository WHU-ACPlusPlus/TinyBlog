import QtQuick 2.15

Item {
    id: root

    property string emoji: ""
    property int size: 18

    implicitWidth: size
    implicitHeight: size

    Image {
        anchors.fill: parent
        source: {
            var map = {
                "\uD83C\uDF10": "emoji/1f310.svg",   // 🌐
                "\uD83D\uDCAC": "emoji/1f4ac.svg",   // 💬
                "\uD83D\uDC64": "emoji/1f464.svg",   // 👤
                "\uD83D\uDC65": "emoji/1f465.svg",   // 👥
                "\uD83D\uDD0D": "emoji/1f50d.svg",   // 🔍
                "\uD83D\uDD17": "emoji/1f517.svg",   // 🔗
                "\uD83D\uDD04": "emoji/1f504.svg",   // 🔄
                "\uD83D\uDD2E": "emoji/1f52e.svg",   // 🔮
                "\uD83C\uDFE0": "emoji/1f3e0.svg",   // 🏠
                "\uD83C\uDF19": "emoji/1f319.svg",   // 🌙
                "\uD83E\uDEA7": "emoji/1fae7.svg",   // 🫧
                "\uD83E\uDDF5": "emoji/1f9f5.svg",   // 🧵
                "\uD83D\uDDBC": "emoji/1f5bc.svg",   // 🖼
                "\u26A0":        "emoji/26a0.svg",    // ⚠
                "\u25B6":        "emoji/25b6.svg",    // ▶
                "\u23F8":        "emoji/23f8.svg",    // ⏸
                "\u2665":        "emoji/2665.svg",    // ♥
                "\u2661":        "emoji/2661.svg",    // ♡
                "\u2715":        "emoji/2715.svg",    // ✕
                "\u2750":        "emoji/2750.svg",    // ❐
                "\u2600":        "emoji/2600.svg",    // ☀
                "\u25A1":        "emoji/25a1.svg",    // □
            };
            var svg = map[root.emoji];
            return svg ? "qrc:/" + svg : "";
        }
        sourceSize.width: root.size
        sourceSize.height: root.size
        fillMode: Image.PreserveAspectFit
    }
}
