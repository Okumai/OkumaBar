import QtQuick
import QtQuick.Controls as Controls
import Quickshell
import Quickshell.Io
import qs.Ui
import qs.Commons
import qs.Commons as Commons

BarWidget {
    id: root
    moduleName: "okuma.dev_bar4omarchy.ram-cleaner"
    implicitWidth: button.implicitWidth
    implicitHeight: button.implicitHeight
    readonly property real openPanelIndicatorWidth: button.labelWidth
    property var stats: null
    property var apps: []
    property string message: "Open a window to review it and close it manually. No apps are stopped automatically."
    property bool panelOpen: false
    readonly property bool opened: panelOpen
    property bool popoutSwitchClosing: false
    readonly property string panelFont: root.bar ? root.bar.fontFamily : Style.font.family
    readonly property color foreground: root.bar ? root.bar.foreground : Commons.Color.foreground
    readonly property string helper: Qt.resolvedUrl("memory.py").toString().replace(/^file:\/\//, "")

    function gib(bytes) { return (bytes / 1073741824).toFixed(1) + " GiB" }
    function open() { panelOpen = true; refresh() }
    function close() { panelOpen = false }
    function closeForPopoutSwitch() {
        popoutSwitchClosing = true
        close()
        Qt.callLater(function() { root.popoutSwitchClosing = false })
    }
    function refresh() {
        if (poll.running) return
        poll.command = ["python3", helper, root.opened ? "details" : "stats"]
        poll.running = true
    }
    function openWindow(app) {
        if (opener.running || focusDelay.running) return
        opener.command = ["python3", root.helper, "focus", app.address, String(app.pid), app.start]
        root.close()
        // Release the overlay's keyboard focus and finish dismissal before focusing the app.
        focusDelay.restart()
    }
    function switchPanel(direction) {
        if (bar && typeof bar.switchPanelFrom === "function") return bar.switchPanelFrom(root, direction)
        return false
    }

    component PanelText: Text {
        color: root.foreground
        font.family: root.panelFont
        font.pixelSize: Style.font.body
        textFormat: Text.PlainText
        horizontalAlignment: Text.AlignLeft
        wrapMode: Text.WordWrap
    }
    component Action: Button {
        fontFamily: root.panelFont
        fontSize: Style.font.body
        foreground: root.foreground
        leftAlign: true
    }

    Component.onCompleted: refresh()
    Timer { interval: 5000; running: true; repeat: true; onTriggered: root.refresh() }
    Process {
        id: poll
        stdout: StdioCollector {
            onStreamFinished: {
                try {
                    var data = JSON.parse(text)
                    if (data.error) { root.message = data.error; return }
                    root.stats = data
                    if (data.windows !== undefined) root.apps = data.windows
                } catch (e) { root.message = "Unable to read memory information" }
            }
        }
    }
    Timer {
        id: focusDelay
        interval: Style.duration(180) + 30
        onTriggered: opener.running = true
    }
    Process {
        id: opener
        stdout: StdioCollector {
            onStreamFinished: {
                try {
                    var data = JSON.parse(text)
                    root.message = data.error || data.message
                    if (data.error) root.open()
                } catch (e) {
                    root.message = "Unable to focus window"
                    root.open()
                }
            }
        }
    }
    WidgetButton {
        id: button
        anchors.fill: parent
        bar: root.bar
        text: root.stats ? "RAM " + root.stats.percent + "%" : "RAM …"
        labelVisible: true
        horizontalMargin: 8.5
        onPressed: function(b) {
            if (b === Qt.RightButton) root.refresh()
            else if (root.opened) root.close()
            else root.open()
        }
    }
    LeftPanel {
        id: popup
        anchorItem: button
        owner: root
        bar: root.bar
        open: root.opened
        focusTarget: keyCatcher
        contentWidth: fittedContentWidth(Style.space(400))
        contentHeight: fittedContentHeight(content.implicitHeight, Style.space(640))
        // Use the stock panel border, background, animation and dismissal surfaces.
        PanelKeyCatcher {
            id: keyCatcher
            anchors.fill: parent
            onCloseRequested: root.close()
            onTabRequested: function(direction) { root.switchPanel(direction) }
            Flickable {
                id: scroll
                anchors.fill: parent
                contentWidth: width
                contentHeight: content.implicitHeight
                clip: true
                boundsBehavior: Flickable.StopAtBounds
                interactive: contentHeight > height
                Controls.ScrollBar.vertical: Controls.ScrollBar {
                    policy: Controls.ScrollBar.AsNeeded
                }
                Column {
                    id: content
                    width: scroll.width
                    spacing: Style.space(14)
                    PanelText {
                        width: parent.width
                        text: "RAM Checker"
                        horizontalAlignment: Text.AlignHCenter
                        font.pixelSize: Style.font.title
                    }
                    PanelText {
                        width: parent.width
                        text: root.stats ? root.gib(root.stats.used) + " / " + root.gib(root.stats.total)
                            + "  ·  " + root.stats.percent + "%" : "Loading…"
                        horizontalAlignment: Text.AlignHCenter
                        wrapMode: Text.NoWrap
                        fontSizeMode: Text.HorizontalFit
                        minimumPixelSize: Style.font.body
                        font.pixelSize: Style.font.display
                    }
                    Rectangle {
                        width: parent.width
                        height: Style.space(6)
                        radius: height / 2
                        color: Qt.alpha(root.foreground, 0.15)
                        Rectangle {
                            width: parent.width * (root.stats ? root.stats.percent / 100 : 0)
                            height: parent.height
                            radius: height / 2
                            color: Commons.Color.accent
                        }
                    }
                    Item {
                        width: parent.width
                        implicitHeight: Math.max(memoryDetails.implicitHeight, refreshButton.implicitHeight)
                        PanelText {
                            id: memoryDetails
                            anchors.left: parent.left
                            anchors.right: refreshButton.left
                            anchors.rightMargin: Style.space(12)
                            anchors.verticalCenter: parent.verticalCenter
                            text: root.stats ? "Available  " + root.gib(root.stats.available)
                                + "\nCache      " + root.gib(root.stats.cache)
                                + "\nSwap       " + root.gib(root.stats.swap) : ""
                        }
                        Action {
                            id: refreshButton
                            anchors.right: parent.right
                            anchors.verticalCenter: parent.verticalCenter
                            text: "Refresh"
                            enabled: !poll.running
                            onClicked: root.refresh()
                        }
                    }
                    PanelSeparator { width: parent.width }
                    PanelText {
                        width: parent.width
                        text: "Linux reclaims cache automatically. Process-tree RSS estimates below may count shared memory more than once."
                        opacity: 0.65
                        font.pixelSize: Style.font.bodySmall
                    }
                    ListView {
                        id: appList
                        width: parent.width
                        // Bound the list independently of its item count; the rest
                        // of the panel can also scroll on unusually short screens.
                        height: Math.min(Style.space(240), popup.availableCardHeight * 0.35,
                                         count * Style.space(64))
                        clip: true
                        boundsBehavior: Flickable.StopAtBounds
                        interactive: contentHeight > height
                        spacing: Style.space(4)
                        model: root.apps
                        delegate: Item {
                            required property var modelData
                            width: ListView.view.width - Style.space(12)
                            height: Style.space(60)
                            Column {
                                anchors { left: parent.left; verticalCenter: parent.verticalCenter }
                                width: parent.width - openButton.width - Style.space(16)
                                spacing: Style.space(4)
                                PanelText {
                                    width: parent.width
                                    text: modelData.name + " · " + root.gib(modelData.rss)
                                    wrapMode: Text.NoWrap
                                    elide: Text.ElideRight
                                }
                                PanelText {
                                    width: parent.width
                                    // PID is language-neutral; window titles can contain arbitrary languages.
                                    text: "PID " + modelData.pid
                                    opacity: 0.65
                                    font.pixelSize: Style.font.bodySmall
                                }
                            }
                            Action {
                                id: openButton
                                anchors { right: parent.right; verticalCenter: parent.verticalCenter }
                                text: "Open"
                                enabled: !opener.running && !focusDelay.running
                                onClicked: root.openWindow(modelData)
                            }
                        }
                        Controls.ScrollBar.vertical: Controls.ScrollBar {
                            policy: Controls.ScrollBar.AsNeeded
                        }
                    }
                    PanelText {
                        width: parent.width
                        visible: root.apps.length === 0
                        text: "No open application windows"
                    }
                    PanelText {
                        width: parent.width
                        text: root.message
                        opacity: 0.65
                        font.pixelSize: Style.font.bodySmall
                    }
                }
            }
        }
    }
}
