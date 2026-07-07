import QtQuick
import QtQuick.Controls.Basic

ApplicationWindow {
    id: window
    width: 420
    height: 720
    minimumWidth: 360
    minimumHeight: 500
    visible: true
    title: qsTr("Tiny Chat")

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
