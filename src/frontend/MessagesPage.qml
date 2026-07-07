import QtQuick
import QtQuick.Controls.Basic

Rectangle {
    color: window.bgPage

    Text {
        anchors.centerIn: parent
        text: qsTr("消息")
        font.pixelSize: 28
        color: window.textSecondary
    }
}
