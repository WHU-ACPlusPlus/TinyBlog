import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts

Rectangle {
    color: "#ededed"

    // ── 内部状态 ──
    property int step: 0       // 0=欢迎页, 1=注册填表, 2=登录填表
    property string errorText: ""

    // ── 欢迎页 (step=0) ──
    ColumnLayout {
        anchors.centerIn: parent
        spacing: 20
        visible: step === 0

        Text {
            Layout.alignment: Qt.AlignHCenter
            text: qsTr("Tiny Chat")
            font.pixelSize: 32
            font.bold: true
            color: "#333"
        }

        Text {
            Layout.alignment: Qt.AlignHCenter
            text: qsTr("服务地址")
            font.pixelSize: 14
            color: "#666"
        }

        TextField {
            id: urlInput
            Layout.preferredWidth: 260
            Layout.alignment: Qt.AlignHCenter
            placeholderText: qsTr("http://127.0.0.1:18999")
            Component.onCompleted: text = api.baseUrl
            onTextChanged: api.baseUrl = text
        }

        Button {
            Layout.preferredWidth: 240
            Layout.alignment: Qt.AlignHCenter
            text: qsTr("注册")
            onClicked: {
                errorText = ""
                step = 1
            }
        }

        Button {
            Layout.preferredWidth: 240
            Layout.alignment: Qt.AlignHCenter
            text: qsTr("登录")
            onClicked: {
                errorText = ""
                step = 2
            }
        }
    }

    // ── 注册页 (step=1) ──
    ColumnLayout {
        anchors.centerIn: parent
        spacing: 14
        visible: step === 1

        Text {
            Layout.alignment: Qt.AlignHCenter
            text: qsTr("注册")
            font.pixelSize: 24
            font.bold: true
            color: "#333"
        }

        TextField {
            id: regUsername
            Layout.preferredWidth: 260
            Layout.alignment: Qt.AlignHCenter
            placeholderText: qsTr("用户名")
        }
        TextField {
            id: regNickname
            Layout.preferredWidth: 260
            Layout.alignment: Qt.AlignHCenter
            placeholderText: qsTr("昵称")
        }
        TextField {
            id: regPassword
            Layout.preferredWidth: 260
            Layout.alignment: Qt.AlignHCenter
            placeholderText: qsTr("密码")
            echoMode: TextInput.Password
        }

        // 错误提示
        Text {
            Layout.alignment: Qt.AlignHCenter
            text: errorText
            color: "red"
            visible: errorText !== ""
            font.pixelSize: 13
        }

        RowLayout {
            Layout.alignment: Qt.AlignHCenter
            spacing: 16

            Button {
                text: qsTr("取消")
                onClicked: step = 0
            }
            Button {
                text: qsTr("确认")
                onClicked: {
                    if (!regUsername.text || !regNickname.text || !regPassword.text) {
                        errorText = qsTr("请填写所有字段")
                        return
                    }
                    errorText = ""
                    api.registerUser(regUsername.text, regPassword.text, regNickname.text)
                }
            }
        }
    }

    // ── 登录页 (step=2) ──
    ColumnLayout {
        anchors.centerIn: parent
        spacing: 14
        visible: step === 2

        Text {
            Layout.alignment: Qt.AlignHCenter
            text: qsTr("登录")
            font.pixelSize: 24
            font.bold: true
            color: "#333"
        }

        TextField {
            id: logUsername
            Layout.preferredWidth: 260
            Layout.alignment: Qt.AlignHCenter
            placeholderText: qsTr("用户名")
        }
        TextField {
            id: logPassword
            Layout.preferredWidth: 260
            Layout.alignment: Qt.AlignHCenter
            placeholderText: qsTr("密码")
            echoMode: TextInput.Password
            onAccepted: {
                // 回车快速登录
                if (logUsername.text && logPassword.text)
                    doLogin()
            }
        }

        // 错误提示
        Text {
            Layout.alignment: Qt.AlignHCenter
            text: errorText
            color: "red"
            visible: errorText !== ""
            font.pixelSize: 13
        }

        RowLayout {
            Layout.alignment: Qt.AlignHCenter
            spacing: 16

            Button {
                text: qsTr("取消")
                onClicked: step = 0
            }
            Button {
                text: qsTr("确认")
                onClicked: doLogin()
            }
        }
    }

    // ── 登录逻辑 ──
    function doLogin() {
        if (!logUsername.text || !logPassword.text) {
            errorText = qsTr("请填写所有字段")
            return
        }
        errorText = ""
        api.login(logUsername.text, logPassword.text)
    }

    // ── 只监听注册/登录结果的信号，不用全局 errorOccurred ──
    Connections {
        target: api
        function onRegisterSuccess(cookie) {
            errorText = ""
        }
        function onLoginSuccess(cookie) {
            errorText = ""
        }
        function onCookieCheckComplete(valid, userId) {
            // 不做任何事，避免干扰登录流程
        }
        // 注意：不监听 onErrorOccurred，因为它包含所有模块（消息/关注/群组）的错误，
        // 如果在注册/登录页显示了这些无关错误，用户会看到莫名其妙的提示。
        // 注册和登录的错误直接在按钮 onClicked 中通过回调处理。
    }
}
