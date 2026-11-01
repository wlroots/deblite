import QtQuick
import QtQuick.Controls as Controls
import QtQuick.Layouts
import org.kde.kirigami as Kirigami

RowLayout {
    id: nav
    property string stepLabel: ""
    property string nextText: "Далее"
    signal nextClicked()

    Layout.fillWidth: true
    Layout.topMargin: Kirigami.Units.largeSpacing

    Controls.Label {
        text: nav.stepLabel
        color: Kirigami.Theme.disabledTextColor
        Layout.fillWidth: true
    }
    Controls.Button {
        text: nav.nextText
        icon.name: "go-next"
        highlighted: true
        onClicked: nav.nextClicked()
    }
}
