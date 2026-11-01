import QtQuick
import QtQuick.Controls as Controls
import QtQuick.Layouts
import org.kde.kirigami as Kirigami

Kirigami.Page {
    title: installerBackend.tr("welcome.title")

    ColumnLayout {
        anchors.centerIn: parent
        width: Math.min(parent.width - Kirigami.Units.gridUnit * 4, 480)
        spacing: Kirigami.Units.largeSpacing

        Kirigami.Icon {
            source: "distributor-logo-archlinux"
            Layout.alignment: Qt.AlignHCenter
            Layout.preferredWidth: Kirigami.Units.iconSizes.huge
            Layout.preferredHeight: Kirigami.Units.iconSizes.huge
        }

        Kirigami.Heading {
            text: installerBackend.tr("welcome.title")
            level: 1
            horizontalAlignment: Text.AlignHCenter
            Layout.fillWidth: true
        }

        Controls.Label {
            text: installerBackend.tr("welcome.body") + "\n\n" +
                  (debugMode ? installerBackend.tr("welcome.body.debug")
                             : installerBackend.tr("welcome.body.warning"))
            wrapMode: Text.WordWrap
            horizontalAlignment: Text.AlignHCenter
            Layout.fillWidth: true
            color: debugMode ? Kirigami.Theme.neutralTextColor : Kirigami.Theme.textColor
        }

        Controls.Button {
            text: installerBackend.tr("welcome.start")
            icon.name: "go-next"
            highlighted: true
            Layout.alignment: Qt.AlignHCenter
            // Первый экран визарда теперь "Локаль" — язык/регион выбираются
            // сразу после приветствия, и от выбранной локали дальше зависит
            // язык всех последующих страниц (см. installerBackend.setField).
            onClicked: pageStack.push(Qt.resolvedUrl("LocalePage.qml"))
        }
    }
}
