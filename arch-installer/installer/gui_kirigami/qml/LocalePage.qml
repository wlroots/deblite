import QtQuick
import QtQuick.Controls as Controls
import QtQuick.Layouts
import org.kde.kirigami as Kirigami

Kirigami.ScrollablePage {
    title: installerBackend.tr("screen.locale.title")

    ColumnLayout {
        width: parent.width
        spacing: Kirigami.Units.largeSpacing

        Kirigami.FormLayout {
            Layout.fillWidth: true

            Controls.TextField {
                Kirigami.FormData.label: installerBackend.tr("field.locale.locale.label") + ":"
                text: "en_US.UTF-8"
                // Локаль сразу переключает язык установщика — каждая
                // следующая страница (Disk, Luks, ...) создаётся заново
                // через pageStack.push() и подхватит уже новый язык.
                onTextChanged: installerBackend.setField("locale.locale", text)
            }
            Controls.TextField {
                Kirigami.FormData.label: installerBackend.tr("field.locale.keymap.label") + ":"
                text: "us"
                onTextChanged: installerBackend.setField("locale.keymap", text)
            }
            Controls.TextField {
                Kirigami.FormData.label: installerBackend.tr("field.locale.timezone.label") + ":"
                text: "UTC"
                onTextChanged: installerBackend.setField("locale.timezone", text)
            }
            Controls.TextField {
                Kirigami.FormData.label: installerBackend.tr("field.network.hostname.label") + ":"
                text: "archbox"
                onTextChanged: installerBackend.setField("network.hostname", text)
            }
        }

        WizardNav {
            stepLabel: installerBackend.tr("nav.step").replace("{index}", "1").replace("{total}", "7")
            nextText: installerBackend.tr("nav.next")
            onNextClicked: pageStack.push(Qt.resolvedUrl("DiskPage.qml"))
        }
    }
}
