import QtQuick
import QtQuick.Controls as Controls
import QtQuick.Layouts
import org.kde.kirigami as Kirigami

Kirigami.ScrollablePage {
    title: installerBackend.tr("screen.bootloader.title")

    ColumnLayout {
        width: parent.width
        spacing: Kirigami.Units.largeSpacing

        Kirigami.FormLayout {
            Layout.fillWidth: true

            Controls.ComboBox {
                Kirigami.FormData.label: installerBackend.tr("field.bootloader.kind.label") + ":"
                model: ["grub", "limine", "uki-efistub"]
                onCurrentTextChanged: installerBackend.setField("bootloader.kind", currentText)
            }
        }

        Controls.Label {
            Layout.fillWidth: true
            wrapMode: Text.WordWrap
            color: Kirigami.Theme.disabledTextColor
            text: installerBackend.tr("bootloader.hint")
        }

        WizardNav {
            stepLabel: installerBackend.tr("nav.step").replace("{index}", "4").replace("{total}", "7")
            nextText: installerBackend.tr("nav.next")
            onNextClicked: pageStack.push(Qt.resolvedUrl("DesktopPage.qml"))
        }
    }
}
