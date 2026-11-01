import QtQuick
import QtQuick.Controls as Controls
import QtQuick.Layouts
import org.kde.kirigami as Kirigami

Kirigami.ScrollablePage {
    title: installerBackend.tr("screen.user.title")

    ColumnLayout {
        width: parent.width
        spacing: Kirigami.Units.largeSpacing

        Kirigami.FormLayout {
            Layout.fillWidth: true

            Controls.TextField {
                Kirigami.FormData.label: installerBackend.tr("field.user.username.label") + ":"
                text: "user"
                onTextChanged: installerBackend.setField("user.username", text)
            }
            Controls.TextField {
                Kirigami.FormData.label: installerBackend.tr("field.user.password.label") + ":"
                echoMode: TextInput.Password
                onTextChanged: installerBackend.setField("user.password", text)
            }
            Controls.CheckBox {
                text: installerBackend.tr("field.user.is_admin.label")
                checked: true
                onCheckedChanged: installerBackend.setField("user.is_admin", checked)
            }
            Controls.TextField {
                Kirigami.FormData.label: installerBackend.tr("field.user.root_password.label") + ":"
                echoMode: TextInput.Password
                onTextChanged: installerBackend.setField("user.root_password", text)
            }
        }

        WizardNav {
            stepLabel: installerBackend.tr("nav.step").replace("{index}", "6").replace("{total}", "7")
            nextText: installerBackend.tr("nav.next")
            onNextClicked: pageStack.push(Qt.resolvedUrl("SoftwarePage.qml"))
        }
    }
}
