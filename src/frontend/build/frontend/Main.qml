import QtQuick
import QtQuick.Controls.Basic

ApplicationWindow {
    id: window
    width: 1100
    height: 750
    minimumWidth: 700
    minimumHeight: 500
    visible: true
    title: Qt.locale().name.substring(0, 2) === "zh" ? "微微博" : "Tiny Blog"

    // ── 深色模式色板 ──
    property bool darkMode: Qt.styleHints.colorScheme === Qt.Dark

    readonly property color bgPage:    darkMode ? "#1e1e1e" : "#f5f5f5"
    readonly property color bgSurface: darkMode ? "#2d2d2d" : "white"
    readonly property color bgSidebar: darkMode ? "#1a1a1a" : "#2c2c2c"
    readonly property color bgCard:    darkMode ? "#333333" : "white"
    readonly property color bgInput:   darkMode ? "#3a3a3a" : "white"
    readonly property color bgLogin:   darkMode ? "#1e1e1e" : "#ededed"
    readonly property color textPrimary:   darkMode ? "#e0e0e0" : "#333"
    readonly property color textSecondary: darkMode ? "#888888" : "#999"
    readonly property color textOnDark:    darkMode ? "#e0e0e0" : "#e0e0e0"
    readonly property color accent:    darkMode ? "#4db8ff" : "#6cf"
    readonly property color border:    darkMode ? "#444444" : "#ddd"
    readonly property color divider:   darkMode ? "#3a3a3a" : "#eee"
    readonly property color selectedBg: darkMode ? "#3a3a3a" : "#4a4a4a"

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
