import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts

Rectangle {
    color: window.bgLogin

    // ── 内部状态 ──
    property int step: 0       // 0=欢迎, 1=注册填表, 2=验证码+邮箱, 3=邮箱验证码, 4=登录填表, 5=登录验证码, 6=登录邮箱
    property string errorText: ""

    // ── 语言 ──
    property string currentLang: Qt.locale().name.substring(0, 5) === "zh_CN" ? "zh_CN" : "en_US"
    property string langLabel: currentLang === "zh_CN" ? "English" : "中文"

    Component.onCompleted: {
        // 初始化语言
        api.setLanguage(currentLang)
    }

    // 注册流程暂存
    property string regCookie: ""
    property string captchaB64: ""
    property string regEmail: ""

    // 登录流程暂存
    property string loginCookie: ""
    property bool loginNeedCaptcha: false
    property bool loginNeedEmail: false
    property string loginCaptchaB64: ""
    property string loginEmail: ""
    property bool loginEmailSent: false

    // ── 欢迎页 (step=0) ──
    ColumnLayout {
        anchors.fill: parent
        spacing: 20
        visible: step === 0

        Item { Layout.fillHeight: true }

        Text {
            Layout.alignment: Qt.AlignHCenter
            text: qsTr("Tiny Chat")
            font.pixelSize: 32
            font.bold: true
            color: window.textPrimary
        }

        Text {
            Layout.alignment: Qt.AlignHCenter
            text: qsTr("服务地址")
            font.pixelSize: 14
            color: window.textSecondary
        }

        TextField {
            id: urlInput
            Layout.preferredWidth: 260
            Layout.alignment: Qt.AlignHCenter
            placeholderText: qsTr("服务地址")
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
                step = 4
            }
        }

        Item { Layout.fillHeight: true }

        // ── 语言切换 ──
        Button {
            Layout.alignment: Qt.AlignHCenter
            flat: true
            text: langLabel
            Layout.bottomMargin: 20
            onClicked: {
                if (currentLang === "zh_CN") {
                    currentLang = "en_US"
                    langLabel = "中文"
                } else {
                    currentLang = "zh_CN"
                    langLabel = "English"
                }
                api.setLanguage(currentLang)
            }
        }
    }

    // ── 注册第一步：填写资料 (step=1) ──
    ColumnLayout {
        anchors.centerIn: parent
        spacing: 14
        visible: step === 1

        Text {
            Layout.alignment: Qt.AlignHCenter
            text: qsTr("注册")
            font.pixelSize: 24
            font.bold: true
            color: window.textPrimary
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
                text: qsTr("下一步")
                onClicked: {
                    if (!regUsername.text || !regNickname.text || !regPassword.text) {
                        errorText = qsTr("请填写所有字段")
                        return
                    }
                    errorText = ""
                    api.startRegister(regUsername.text, regPassword.text, regNickname.text)
                }
            }
        }
    }

    // ── 注册第二步：图形验证码 + 邮箱 (step=2) ──
    ColumnLayout {
        anchors.centerIn: parent
        spacing: 14
        visible: step === 2

        Text {
            Layout.alignment: Qt.AlignHCenter
            text: qsTr("验证身份")
            font.pixelSize: 24
            font.bold: true
            color: window.textPrimary
        }

        Image {
            id: captchaImg
            Layout.alignment: Qt.AlignHCenter
            Layout.preferredWidth: captchaImg.sourceSize.width
            Layout.preferredHeight: captchaImg.sourceSize.height
            source: captchaB64 ? "data:image/png;base64," + captchaB64 : ""
            fillMode: Image.PreserveAspectFit
        }

        TextField {
            id: captchaInput
            Layout.preferredWidth: 260
            Layout.alignment: Qt.AlignHCenter
            placeholderText: qsTr("输入图片中的字符")
        }

        TextField {
            id: emailInput
            Layout.preferredWidth: 260
            Layout.alignment: Qt.AlignHCenter
            placeholderText: qsTr("邮箱地址")
        }

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
                text: qsTr("上一步")
                onClicked: { step = 1; errorText = "" }
            }
            Button {
                text: qsTr("发送验证码")
                onClicked: {
                    if (!captchaInput.text) { errorText = qsTr("请输入图形验证码"); return }
                    if (!emailInput.text) { errorText = qsTr("请输入邮箱地址"); return }
                    regEmail = emailInput.text
                    errorText = ""
                    api.verifyRegister(regCookie, captchaInput.text, regEmail)
                }
            }
        }
    }

    // ── 注册第三步：邮箱验证码 (step=3) ──
    ColumnLayout {
        anchors.centerIn: parent
        spacing: 14
        visible: step === 3

        Text {
            Layout.alignment: Qt.AlignHCenter
            text: qsTr("验证邮箱")
            font.pixelSize: 24
            font.bold: true
            color: window.textPrimary
        }

        Text {
            Layout.alignment: Qt.AlignHCenter
            text: qsTr("验证码已发送至 %1").arg(regEmail)
            font.pixelSize: 13
            color: window.textSecondary
        }

        TextField {
            id: emailCodeInput
            Layout.preferredWidth: 260
            Layout.alignment: Qt.AlignHCenter
            placeholderText: qsTr("输入邮件中的验证码")
        }

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
                text: qsTr("上一步")
                onClicked: { step = 2; errorText = "" }
            }
            Button {
                text: qsTr("确认")
                onClicked: {
                    if (!emailCodeInput.text) { errorText = qsTr("请输入验证码"); return }
                    errorText = ""
                    api.completeRegister(regCookie, emailCodeInput.text)
                }
            }
        }
    }

    // ── 登录页 (step=4) ──
    ColumnLayout {
        anchors.centerIn: parent
        spacing: 14
        visible: step === 4

        Text {
            Layout.alignment: Qt.AlignHCenter
            text: qsTr("登录")
            font.pixelSize: 24
            font.bold: true
            color: window.textPrimary
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
            onAccepted: { tryLogin() }
        }

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
                text: qsTr("登录")
                onClicked: tryLogin()
            }
        }
    }

    // ── 登录验证码 (step=5) ──
    ColumnLayout {
        anchors.centerIn: parent
        spacing: 14
        visible: step === 5

        Text {
            Layout.alignment: Qt.AlignHCenter
            text: qsTr("安全验证")
            font.pixelSize: 24
            font.bold: true
            color: window.textPrimary
        }

        Text {
            Layout.alignment: Qt.AlignHCenter
            text: qsTr("登录尝试过于频繁，请输入验证码")
            font.pixelSize: 13
            color: window.textSecondary
        }

        Image {
            id: loginCaptchaImg
            Layout.alignment: Qt.AlignHCenter
            source: loginCaptchaB64 ? "data:image/png;base64," + loginCaptchaB64 : ""
            fillMode: Image.PreserveAspectFit
        }

        TextField {
            id: loginCaptchaInput
            Layout.preferredWidth: 260
            Layout.alignment: Qt.AlignHCenter
            placeholderText: qsTr("输入图片中的字符")
            onAccepted: { submitLoginCaptcha() }
        }

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
                text: qsTr("返回")
                onClicked: { step = 4; errorText = "" }
            }
            Button {
                text: qsTr("确认")
                onClicked: submitLoginCaptcha()
            }
        }
    }

    // ── 登录邮箱验证 (step=6) ──
    ColumnLayout {
        anchors.centerIn: parent
        spacing: 14
        visible: step === 6

        Text {
            Layout.alignment: Qt.AlignHCenter
            text: qsTr("邮箱验证")
            font.pixelSize: 24
            font.bold: true
            color: window.textPrimary
        }

        Text {
            Layout.alignment: Qt.AlignHCenter
            text: loginEmailSent
                  ? qsTr("验证码已发送至 %1").arg(loginEmail)
                  : qsTr("验证码将发送至 %1").arg(loginEmail)
            font.pixelSize: 13
            color: window.textSecondary
            visible: loginEmail !== ""
        }

        RowLayout {
            Layout.alignment: Qt.AlignHCenter
            visible: !loginEmailSent
            Button {
                text: qsTr("发送验证码")
                onClicked: {
                    errorText = ""
                    api.loginSendEmailCode(loginCookie)
                }
            }
        }

        TextField {
            id: loginEmailCodeInput
            Layout.preferredWidth: 260
            Layout.alignment: Qt.AlignHCenter
            placeholderText: qsTr("输入邮件中的验证码")
            visible: loginEmailSent
            onAccepted: { submitLoginEmailCode() }
        }

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
            visible: loginEmailSent
            Button {
                text: qsTr("返回")
                onClicked: { step = 4; errorText = "" }
            }
            Button {
                text: qsTr("确认")
                onClicked: submitLoginEmailCode()
            }
        }
    }

    // ── 登录辅助函数 ──
    function tryLogin() {
        if (!logUsername.text || !logPassword.text) {
            errorText = qsTr("请填写所有字段")
            return
        }
        errorText = ""
        api.startLogin(logUsername.text, logPassword.text)
    }

    function submitLoginCaptcha() {
        if (!loginCaptchaInput.text) {
            errorText = qsTr("请输入验证码")
            return
        }
        errorText = ""
        api.loginVerifyCaptcha(loginCookie, loginCaptchaInput.text)
    }

    function submitLoginEmailCode() {
        if (!loginEmailCodeInput.text) {
            errorText = qsTr("请输入验证码")
            return
        }
        errorText = ""
        api.loginVerifyEmail(loginCookie, loginEmailCodeInput.text)
    }

    function proceedAfterLoginFinish() {
        // 如果还有 email 验证未完成，跳到邮箱页
        if (loginNeedEmail && !loginEmailSent) {
            step = 6
        } else {
            // 所有验证完成，完成登录
            api.completeLogin(loginCookie)
        }
    }

    // ── 监听 API 信号 ──
    Connections {
        target: api

        // ── 注册信号 ──
        function onRegisterStep1Done(cookie, captcha) {
            regCookie = cookie
            captchaB64 = captcha
            errorText = ""
            step = 2
        }
        function onRegisterStep2Done() {
            errorText = qsTr("验证码已发送，请查收邮件")
            step = 3
        }
        function onRegisterSuccess(cookie) {
            // api 已自动保存 cookie，进入主界面
        }

        // ── 登录信号 ──
        function onLoginStep1Done(cookie, needCaptcha, needEmail, captcha, email) {
            loginCookie = cookie
            loginNeedCaptcha = needCaptcha
            loginNeedEmail = needEmail
            loginCaptchaB64 = captcha
            loginEmail = email || ""
            loginEmailSent = false

            if (needCaptcha) {
                // 先校验图形验证码
                step = 5
            } else if (needEmail) {
                // 直接进邮箱验证
                step = 6
            } else {
                // 无需额外验证，直接完成登录
                api.completeLogin(cookie)
            }
        }

        function onLoginStep2Done() {
            // 图形验证码通过 → 如果还需要邮箱则跳邮箱页，否则完成
            if (loginNeedEmail) {
                step = 6
            } else {
                api.completeLogin(loginCookie)
            }
        }

        function onLoginStep3Done() {
            // 邮箱验证码已发送或已校验 → 如果已发送但未校验则等待输入
            if (step === 6 && loginEmailSent) {
                // 已发送、已校验 → 完成登录
                api.completeLogin(loginCookie)
            } else {
                // 首次进入或刚发送 → 显示输入框
                loginEmailSent = !loginEmailSent
            }
        }

        function onLoginSuccess(cookie) {
            // api 已自动保存 cookie，进入主界面
        }

        function onErrorOccurred(msg) {
            if (step >= 1 && step <= 6)
                errorText = msg
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
