import QtQuick
import QtQuick.Controls.Basic

ApplicationWindow {
    id: window
    width: 1100
    height: 750
    minimumWidth: 700
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

    // ── 登录/注册成功 → 自动切到 MainPage ──
    Connections {
        target: api

        function onLoginSuccess(cookie) {
            // visible 绑定自动更新
        }
        function onRegisterSuccess(cookie) {
            // visible 绑定自动更新
        }
    }
}
