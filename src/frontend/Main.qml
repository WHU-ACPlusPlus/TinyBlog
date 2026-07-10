import QtQuick
import QtQuick.Controls.Basic

ApplicationWindow {
    id: window
    width: 1100
    height: 750
    minimumWidth: 360
    minimumHeight: 500
    visible: true
    flags: Qt.FramelessWindowHint | Qt.Window
    color: "transparent"
    title: Qt.locale().name.substring(0, 2) === "zh" ? "微微博" : "Tiny Blog"

    // ── 深色模式色板 ──
    // darkModeFollowSystem=0: 跟随系统;  1: 手动深色;  2: 手动浅色
    property int darkModeFollowSystem: 0
    property bool darkMode: darkModeFollowSystem === 1 ? true : (darkModeFollowSystem === 2 ? false : (Qt.styleHints.colorScheme === Qt.Dark))

    // 当前活跃风格模式（由 MainPage 更新）：0=普通  1=玻璃  2=SoftUI
    // 非 0 时深色模式不生效，所有颜色保持浅色固定值
    property int activeStyleMode: 0

    readonly property color bgPage:    (activeStyleMode !== 0) ? "#f5f5f5" : (darkMode ? "#1e1e1e" : "#f5f5f5")
    readonly property color bgSurface: (activeStyleMode !== 0) ? "white"   : (darkMode ? "#2d2d2d" : "white")
    readonly property color bgSidebar: (activeStyleMode !== 0) ? "#2c2c2c" : (darkMode ? "#1a1a1a" : "#2c2c2c")
    readonly property color bgCard:    (activeStyleMode !== 0) ? "white"   : (darkMode ? "#333333" : "white")
    readonly property color bgInput:   (activeStyleMode !== 0) ? "white"   : (darkMode ? "#3a3a3a" : "white")
    readonly property color bgLogin:   (activeStyleMode !== 0) ? "#ededed" : (darkMode ? "#1e1e1e" : "#ededed")
    readonly property color textPrimary:   (activeStyleMode !== 0) ? "#333"       : (darkMode ? "#e0e0e0" : "#333")
    readonly property color textSecondary: (activeStyleMode !== 0) ? "#999"       : (darkMode ? "#888888" : "#999")
    readonly property color textOnDark:    "#e0e0e0"
    readonly property color accent:    (activeStyleMode !== 0) ? "#6cf"       : (darkMode ? "#4db8ff" : "#6cf")
    readonly property color border:    (activeStyleMode !== 0) ? "#ddd"       : (darkMode ? "#444444" : "#ddd")
    readonly property color divider:   (activeStyleMode !== 0) ? "#eee"       : (darkMode ? "#3a3a3a" : "#eee")
    readonly property color selectedBg: (activeStyleMode !== 0) ? "#4a4a4a"   : (darkMode ? "#3a3a3a" : "#4a4a4a")

    // ── 视频内嵌播放（B站/视频卡片触发）──
    property string videoPlayBvid: ""
    property string videoPlayCid: ""
    property bool showVideoBg: false

    // ── 最小化动画 ──
    function animateMinimize() {
        minimizeAnim.start()
    }

    SequentialAnimation {
        id: minimizeAnim
        PropertyAnimation {
            target: window
            property: "opacity"
            to: 0
            duration: 150
            easing.type: Easing.InCubic
        }
        ScriptAction {
            script: {
                window.opacity = 1   // 先恢复透明度再最小化
                winHelper.minimize()
            }
        }
    }

    // ═══════════════════════════════════════════
    // 全局标题栏（无边框窗口控制，始终可见）
    // ═══════════════════════════════════════════
    Rectangle {
        id: titleBar
        anchors.top: parent.top
        anchors.left: parent.left
        anchors.right: parent.right
        height: 32
        z: 100
        color: {
            if (window.activeStyleMode === 2) return Qt.rgba(0.84, 0.89, 0.93, 0.92)
            if (window.activeStyleMode === 1) return Qt.rgba(1, 1, 1, 0.08)
            if (window.darkMode) return "#1a1a1a"
            return "transparent"
        }

        MouseArea {
            anchors.fill: parent
            anchors.rightMargin: 120
            property point lastPos: Qt.point(0, 0)
            onPressed: function(mouse) { lastPos = Qt.point(mouse.x, mouse.y) }
            onPositionChanged: function(mouse) {
                if (pressed) { window.x += mouse.x - lastPos.x; window.y += mouse.y - lastPos.y }
            }
        }

        Row {
            anchors.right: parent.right
            anchors.verticalCenter: parent.verticalCenter
            anchors.rightMargin: 8
            spacing: 4

            Rectangle {
                width: 28; height: 28; radius: 6
                color: minHover.hovered ? Qt.rgba(1,1,1,0.15) : "transparent"
                Text { anchors.centerIn: parent; text: "─"; font.pixelSize: 14; color: window.textPrimary }
                MouseArea { anchors.fill: parent; onClicked: window.animateMinimize() }
                HoverHandler { id: minHover; cursorShape: Qt.PointingHandCursor }
            }
            Rectangle {
                width: 28; height: 28; radius: 6
                color: maxHover.hovered ? Qt.rgba(1,1,1,0.15) : "transparent"
                Canvas {
                    anchors.centerIn: parent
                    width: 13; height: 13
                    onPaint: {
                        var ctx = getContext("2d");
                        ctx.strokeStyle = window.textPrimary;
                        ctx.lineWidth = 1.5;
                        if (window.visibility === Window.Maximized) {
                            ctx.strokeRect(2, 4, 9, 7);
                            ctx.strokeRect(4, 2, 7, 9);
                        } else {
                            ctx.strokeRect(2, 2, 9, 9);
                        }
                    }
                }
                MouseArea { anchors.fill: parent; onClicked: winHelper.toggleMaximize() }
                HoverHandler { id: maxHover; cursorShape: Qt.PointingHandCursor }
            }
            Rectangle {
                width: 28; height: 28; radius: 6
                color: closeHover.hovered ? "#e55" : "transparent"
                Canvas {
                    anchors.centerIn: parent
                    width: 13; height: 13
                    onPaint: {
                        var ctx = getContext("2d");
                        ctx.strokeStyle = closeHover.hovered ? "white" : window.textPrimary;
                        ctx.lineWidth = 2;
                        ctx.beginPath();
                        ctx.moveTo(2, 2); ctx.lineTo(11, 11);
                        ctx.moveTo(11, 2); ctx.lineTo(2, 11);
                        ctx.stroke();
                    }
                }
                MouseArea { anchors.fill: parent; onClicked: winHelper.closeWindow() }
                HoverHandler { id: closeHover; cursorShape: Qt.PointingHandCursor }
            }
        }
    }

    // 主页面通过 visible 切换：没登录 → LoginFlow，已登录 → MainPage
    LoginFlow {
        id: loginFlow
        anchors.fill: parent
        visible: !api.isLoggedIn
    }

    MainPage {
        id: mainPage
        anchors.fill: parent
        visible: api.isLoggedIn
    }

    // ── 登录/注册/登出 ──
    Connections {
        target: api

        function onLoginSuccess(cookie) {
            // visible 绑定自动更新
        }
        function onRegisterSuccess(cookie) {
            // visible 绑定自动更新
        }
        function onLoggedInChanged() {
            if (!api.isLoggedIn) {
                // 登出后重新显示登录页，MainPage 被隐藏时 SquarePage 等子组件也随之卸载
            }
        }
    }

    // ── 视频壁纸背景层 ──
    VideoWallpaperBg {
        id: videoBg
        width: window.width
        height: window.height
        z: -10
        visible: window.showVideoBg
    }

    // 同步 api 属性到 window 属性
    Connections {
        target: api
        function onVideoWallpaperPathChanged() {
            window.showVideoBg = (api.videoWallpaperPath.length > 0)
        }
    }
    Timer {
        interval: 200; running: true; repeat: false
        onTriggered: { window.showVideoBg = (api.videoWallpaperPath.length > 0) }
    }

    // ── 视频内嵌播放弹窗 ──
    VideoPlayerOverlay {
        id: videoOverlay
        width: window.width
        height: window.height
        visible: window.videoPlayBvid !== ""
        bvid: window.videoPlayBvid
        onClosed: {
            window.videoPlayBvid = ""
            window.videoPlayCid = ""
        }
    }

    onVideoPlayBvidChanged: {
        if (window.videoPlayBvid !== "") {
            api.fetchVideoPlayUrl(window.videoPlayBvid, window.videoPlayCid)
        }
    }
}
