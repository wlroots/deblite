import QtQuick
import QtQuick.Controls as Controls
import QtQuick.Layouts
import org.kde.kirigami as Kirigami

Kirigami.ScrollablePage {
    title: installerBackend.tr("screen.disk.title")

    ColumnLayout {
        width: parent.width
        spacing: Kirigami.Units.largeSpacing

        Kirigami.FormLayout {
            Layout.fillWidth: true

            Controls.TextField {
                Kirigami.FormData.label: installerBackend.tr("field.disk.device.label") + ":"
                text: "/dev/sda"
                onTextChanged: installerBackend.setField("disk.device", text)
            }
            Controls.ComboBox {
                Kirigami.FormData.label: installerBackend.tr("field.disk.filesystem.label") + ":"
                model: ["ext4", "btrfs", "xfs"]
                onCurrentTextChanged: installerBackend.setField("disk.filesystem", currentText)
            }
            Controls.SpinBox {
                Kirigami.FormData.label: installerBackend.tr("field.disk.esp_size_mib.label") + ":"
                from: 128; to: 2048; stepSize: 128; value: 512
                onValueChanged: installerBackend.setField("disk.esp_size_mib", value)
            }
            Controls.SpinBox {
                Kirigami.FormData.label: installerBackend.tr("field.disk.swap_size_mib.label") + ":"
                from: 0; to: 32768; stepSize: 512; value: 0
                onValueChanged: installerBackend.setField("disk.swap_size_mib", value)
            }
        }

        WizardNav {
            stepLabel: installerBackend.tr("nav.step").replace("{index}", "2").replace("{total}", "7")
            nextText: installerBackend.tr("nav.next")
            onNextClicked: pageStack.push(Qt.resolvedUrl("LuksPage.qml"))
        }
    }
}
