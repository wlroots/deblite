import QtQuick
import QtQuick.Controls as Controls
import QtQuick.Layouts
import org.kde.kirigami as Kirigami

Kirigami.ScrollablePage {
    title: installerBackend.tr("screen.desktop.title")

    ColumnLayout {
        width: parent.width
        spacing: Kirigami.Units.largeSpacing

        Kirigami.FormLayout {
            Layout.fillWidth: true

            Controls.ComboBox {
                Kirigami.FormData.label: installerBackend.tr("field.desktop.kind.label") + ":"
                model: ["kde", "gnome", "none"]
                onCurrentTextChanged: installerBackend.setField("desktop.kind", currentText)
            }
        }

        WizardNav {
            stepLabel: installerBackend.tr("nav.step").replace("{index}", "5").replace("{total}", "7")
            nextText: installerBackend.tr("nav.next")
            onNextClicked: pageStack.push(Qt.resolvedUrl("UserPage.qml"))
        }
    }
}
