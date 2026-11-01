import QtQuick
import QtQuick.Controls as Controls
import QtQuick.Layouts
import org.kde.kirigami as Kirigami

Kirigami.ScrollablePage {
    id: page
    title: installerBackend.tr("screen.confirm.title")

    property bool installStarted: false

    Component.onCompleted: summaryLabel.text = installerBackend.getSummary()

    ColumnLayout {
        width: parent.width
        spacing: Kirigami.Units.largeSpacing

        Kirigami.InlineMessage {
            type: Kirigami.MessageType.Warning
            visible: debugMode
            Layout.fillWidth: true
            text: installerBackend.tr("confirm.debug_notice")
        }

        Kirigami.Card {
            Layout.fillWidth: true
            contentItem: Controls.Label {
                id: summaryLabel
                wrapMode: Text.WordWrap
                padding: Kirigami.Units.largeSpacing
            }
        }

        Controls.Button {
            text: debugMode ? installerBackend.tr("confirm.install_dryrun") : installerBackend.tr("confirm.install")
            icon.name: "system-run"
            highlighted: true
            enabled: !page.installStarted
            Layout.alignment: Qt.AlignRight
            onClicked: {
                page.installStarted = true
                installerBackend.startInstall()
            }
        }

        Kirigami.Heading {
            level: 4
            text: installerBackend.tr("confirm.log")
            visible: page.installStarted
        }

        Controls.ScrollView {
            visible: page.installStarted
            Layout.fillWidth: true
            Layout.preferredHeight: 260
            Controls.TextArea {
                id: logArea
                readOnly: true
                wrapMode: TextEdit.Wrap
                font.family: "monospace"
            }
        }
    }

    Connections {
        target: installerBackend
        function onLogLine(line) {
            logArea.text += line + "\n"
        }
        function onStepStarted(title, index, total) {
            logArea.text += "\n[" + index + "/" + total + "] " + title + "...\n"
        }
        function onFinished(success, message) {
            logArea.text += "\n" + (success ? "✔ " : "✘ ") + message + "\n"
        }
    }
}
