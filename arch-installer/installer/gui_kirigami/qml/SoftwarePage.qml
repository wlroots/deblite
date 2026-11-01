import QtQuick
import QtQuick.Controls as Controls
import QtQuick.Layouts
import org.kde.kirigami as Kirigami

Kirigami.ScrollablePage {
    title: installerBackend.tr("screen.software.title")

    ColumnLayout {
        width: parent.width
        spacing: Kirigami.Units.largeSpacing

        Kirigami.FormLayout {
            Layout.fillWidth: true

            Controls.CheckBox {
                text: installerBackend.tr("field.software.enable_ufw.label")
                checked: true
                onCheckedChanged: installerBackend.setField("software.enable_ufw", checked)
            }
            Controls.CheckBox {
                text: installerBackend.tr("field.software.enable_zram.label")
                checked: true
                onCheckedChanged: installerBackend.setField("software.enable_zram", checked)
            }
            Controls.CheckBox {
                text: installerBackend.tr("field.software.install_flatpak.label")
                checked: true
                onCheckedChanged: installerBackend.setField("software.install_flatpak", checked)
            }
            Controls.CheckBox {
                text: installerBackend.tr("field.software.install_pipewire.label")
                checked: true
                onCheckedChanged: installerBackend.setField("software.install_pipewire", checked)
            }
            Controls.CheckBox {
                text: installerBackend.tr("field.software.enable_bluetooth.label")
                checked: true
                onCheckedChanged: installerBackend.setField("software.enable_bluetooth", checked)
            }
            Controls.CheckBox {
                text: installerBackend.tr("field.software.install_common_apps.label")
                checked: true
                onCheckedChanged: installerBackend.setField("software.install_common_apps", checked)
            }
        }

        WizardNav {
            stepLabel: installerBackend.tr("nav.step").replace("{index}", "7").replace("{total}", "7")
            nextText: installerBackend.tr("nav.review_and_install")
            onNextClicked: pageStack.push(Qt.resolvedUrl("ConfirmPage.qml"))
        }
    }
}
