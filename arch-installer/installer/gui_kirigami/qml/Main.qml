import QtQuick
import org.kde.kirigami as Kirigami

Kirigami.ApplicationWindow {
    id: root
    title: debugMode ? "Установщик Arch Linux — DEBUG" : "Установщик Arch Linux"
    width: 900
    height: 640

    // pageStack — встроенный в Kirigami.ApplicationWindow стек страниц.
    // По умолчанию Kirigami.PageRow на широких окнах показывает несколько
    // страниц одновременно колонками (это его обычный десктопный режим,
    // удобный для приложений вроде Discover). Для линейного визарда это
    // не нужно и выглядит странно ("шаги открываются сбоку") — поэтому
    // принудительно включаем однoколоночный режим: новая страница ВСЕГДА
    // замещает предыдущую, а не встаёт рядом.
    pageStack.columnView.columnResizeMode: Kirigami.ColumnView.SingleColumn

    // Kirigami сам рисует кнопку "назад" в заголовке, когда depth > 1 —
    // отдельно реализовывать навигацию назад не нужно.
    pageStack.globalToolBar.style: Kirigami.ApplicationHeaderStyle.Breadcrumb

    pageStack.initialPage: Qt.resolvedUrl("WelcomePage.qml")
}
