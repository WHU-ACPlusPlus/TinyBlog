import QtQuick
import QtQuick.Controls.Basic
import QtMultimedia
Rectangle {
    id: root
    color: "#000000"
    VideoOutput { id: vo; anchors.fill: parent; fillMode: VideoOutput.PreserveAspectCrop }
    Rectangle { anchors.fill: parent; color: window.activeStyleMode === 1 ? Qt.rgba(0,0,0,0.20) : Qt.rgba(0,0,0,0.35) }
    MediaPlayer { id: mp; videoOutput: vo; loops: MediaPlayer.Infinite; autoPlay: true; source: api.videoWallpaperPath.length > 0 ? ("file:///" + api.videoWallpaperPath) : ""; audioOutput: AudioOutput { muted: true; volume: 0 } }
}
