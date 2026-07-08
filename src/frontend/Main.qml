import QtQuick
import QtQuick.Controls.Basic

ApplicationWindow {
    id: window
    width: 1100
    height: 750
    minimumWidth: 360
    minimumHeight: 500
    visible: true
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
}
