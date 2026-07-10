import QtQuick
import QtQuick.Controls.Basic
import QtMultimedia

Rectangle {
    id: root
    color: "#e6000000"
    property string videoUrl: ""
    property string videoFormat: ""
    property string videoTitle: ""
    property string bvid: ""
    property bool loading: false
    signal closed()
    z: 1000

    MouseArea {
        anchors.fill: parent
        onClicked: root.closed()
    }

    // 播放器卡片
    Rectangle {
        id: playerCard
        width: Math.min(parent.width - 40, 800)
        height: Math.min(parent.height - 40, 520)
        anchors.centerIn: parent
        radius: 16
        color: "#1a1a1a"
        border.color: "#333"

        // 顶部栏
        Rectangle {
            anchors.top: parent.top; anchors.left: parent.left; anchors.right: parent.right
            height: 44; color: "transparent"
            Text {
                anchors.left: parent.left; anchors.leftMargin: 16
                anchors.verticalCenter: parent.verticalCenter
                text: root.bvid ? "🎬 B站视频 " + root.bvid : "🎬 视频播放"
                font.pixelSize: 15; font.weight: Font.DemiBold; color: "#fff"
                width: parent.width - 50; elide: Text.ElideRight
            }
            Rectangle {
                anchors.right: parent.right; anchors.rightMargin: 8
                anchors.verticalCenter: parent.verticalCenter
                width: 32; height: 32; radius: 16
                color: "#40ffffff"
                Text { anchors.centerIn: parent; text: "✕"; font.pixelSize: 18; color: "#aaa" }
                MouseArea {
                    anchors.fill: parent
                    onClicked: { mediaPlayer.stop(); root.closed() }
                }
            }
        }

        // 视频区
        Rectangle {
            anchors.top: parent.top; anchors.topMargin: 44
            anchors.left: parent.left; anchors.right: parent.right
            anchors.bottom: parent.bottom; anchors.bottomMargin: 40
            color: "#000"
            VideoOutput {
                id: videoOutput
                anchors.fill: parent
                fillMode: VideoOutput.PreserveAspectFit
            }
            Text {
                anchors.centerIn: parent
                text: root.loading ? "⏳ 加载中..." : (mediaPlayer.source == "" ? "🎬" : "")
                font.pixelSize: 18; color: "#888"
            }
            MouseArea {
                anchors.fill: parent
                onClicked: {
                    if (mediaPlayer.playbackState === MediaPlayer.PlayingState)
                        mediaPlayer.pause()
                    else if (mediaPlayer.source != "")
                        mediaPlayer.play()
                }
            }
        }

        // 底部控制栏
        Rectangle {
            anchors.bottom: parent.bottom
            anchors.left: parent.left; anchors.right: parent.right
            height: 40; color: "#0d0d0d"
            Row {
                anchors.centerIn: parent; spacing: 12
                Text {
                    text: mediaPlayer.playbackState === MediaPlayer.PlayingState ? "⏸" : "▶"
                    font.pixelSize: 16; color: "#fff"
                    MouseArea {
                        anchors.fill: parent
                        onClicked: {
                            if (mediaPlayer.playbackState === MediaPlayer.PlayingState)
                                mediaPlayer.pause()
                            else if (mediaPlayer.source != "")
                                mediaPlayer.play()
                        }
                    }
                }
                Text {
                    text: formatTime(mediaPlayer.position) + " / " + formatTime(mediaPlayer.duration)
                    font.pixelSize: 12; color: "#888"
                }
            }
        }
    }

    MediaPlayer {
        id: mediaPlayer
        videoOutput: videoOutput
        audioOutput: AudioOutput { volume: 0.9 }
        onErrorOccurred: function(error, errorString) {
            console.warn("[VideoPlayer] Error:", errorString)
            root.loading = false
        }
    }

    Connections {
        target: api
        function onVideoPlayUrlReady(bvid, url, format) {
            if (bvid !== root.bvid) return
            root.videoUrl = url
            root.loading = false
            if (url !== "") mediaPlayer.source = url
        }
    }

    function formatTime(ms) {
        if (ms <= 0) return "0:00"
        var totalSec = Math.floor(ms / 1000)
        var min = Math.floor(totalSec / 60)
        var sec = totalSec % 60
        return min + ":" + (sec < 10 ? "0" : "") + sec
    }

    focus: true
    Keys.onPressed: function(event) {
        if (event.key === Qt.Key_Escape) {
            mediaPlayer.stop(); root.closed()
        } else if (event.key === Qt.Key_Space) {
            if (mediaPlayer.playbackState === MediaPlayer.PlayingState)
                mediaPlayer.pause()
            else if (mediaPlayer.source != "")
                mediaPlayer.play()
        }
    }
}
