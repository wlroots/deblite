import QtQuick
import QtQuick.Controls as Controls
import QtQuick.Layouts
import org.kde.kirigami as Kirigami

Kirigami.ScrollablePage {
    title: installerBackend.tr("screen.luks.title")

    ColumnLayout {
        width: parent.width
        spacing: Kirigami.Units.largeSpacing

        Kirigami.FormLayout {
            Layout.fillWidth: true

            Controls.CheckBox {
                text: installerBackend.tr("field.luks.enabled.label")
                onCheckedChanged: installerBackend.setField("luks.enabled", checked)
            }
            Controls.TextField {
                Kirigami.FormData.label: installerBackend.tr("field.luks.passphrase.label") + ":"
                echoMode: TextInput.Password
                onTextChanged: installerBackend.setField("luks.passphrase", text)
            }
        }

        WizardNav {
            stepLabel: installerBackend.tr("nav.step").replace("{index}", "3").replace("{total}", "7")
            nextText: installerBackend.tr("nav.next")
            onNextClicked: pageStack.push(Qt.resolvedUrl("BootloaderPage.qml"))
        }
    }
}
