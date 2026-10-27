"""Panglica, ca în AutoCAD 2025 (rusă): filele, grupurile și butoanele din capturi.
Fiecare buton trimite o comandă la linia de comandă (ca în AutoCAD); cele care încă nu lucrează spun asta acolo."""
import tkinter as tk
from tkinter import ttk
from stil import *

H_FILE = 26; H_CORP = 92

# ("M", text, icoană, culoare, comandă) = buton mare;  [("m", text, icoană, culoare, comandă), …] = coloană de butoane mici;
# ("c", lățime, cheie) = listă (straturi, culori…)
FILE = {
 "Главная": [
  ("Рисование", [("M", "Отрезок", "╱", "#7fb3ff", "ОТРЕЗОК"), ("M", "Полилиния", "⌇", "#7fb3ff", "ПЛИНИЯ"), ("M", "Круг", "◯", "#7fb3ff", "КРУГ"),
                 ("M", "Дуга", "◠", "#7fb3ff", "ДУГА"), [("m", "", "▭", "#9cc3ff", "ПРЯМОУГ"), ("m", "", "⬭", "#9cc3ff", "ЭЛЛИПС"), ("m", "", "▦", "#9cc3ff", "ШТРИХ")]]),
  ("Редактирование", [[("m", "Перенести", "✥", "#e8ebef", "ПЕРЕНЕСТИ"), ("m", "Копировать", "⧉", "#e8ebef", "КОПИРОВАТЬ"), ("m", "Растянуть", "⇲", "#e8ebef", "РАСТЯНУТЬ")],
                      [("m", "Повернуть", "↻", "#e8ebef", "ПОВЕРНУТЬ"), ("m", "Отразить зеркально", "⧎", "#e8ebef", "ЗЕРКАЛО"), ("m", "Масштаб", "⤢", "#e8ebef", "МАСШТАБ")],
                      [("m", "Обрезать", "✂", "#e8ebef", "ОБРЕЗАТЬ"), ("m", "Сопряжение", "⌒", "#e8ebef", "СОПРЯЖЕНИЕ"), ("m", "Массив", "⣿", "#e8ebef", "МАССИВ")],
                      [("m", "", "✎", "#f0a050", "СТЕРЕТЬ"), ("m", "", "⊡", "#e8ebef", "РАСЧЛЕНИТЬ"), ("m", "", "⫽", "#e8ebef", "ПОДОБИЕ")]]),
  ("Аннотации", [("M", "Текст", "A", "#e8ebef", "МТЕКСТ"), ("M", "Размер", "↔", "#f0c040", "РАЗМЕР"),
                 [("m", "Линейный", "⟷", "#e8ebef", "РАЗМЛИНЕЙНЫЙ"), ("m", "Выноска", "↗", "#e8ebef", "МВЫНОСКА"), ("m", "Таблица", "▦", "#e8ebef", "ТАБЛИЦА")]]),
  ("Слои", [("M", "Свойства\nслоя", "☰", "#f0c040", "СЛОЙ"), [("c", 26, "слой"), [("m", "", "💡", "#f0c040", "СЛОЙ"), ("m", "", "☀", "#f0c040", "СЛОЙ"), ("m", "", "🔒", "#f0c040", "СЛОЙ")], ("m", "", "⇆", "#e8ebef", "СЛОЙТЕК")]]),
  ("Блок", [("M", "Вставка", "⊕", "#7fb3ff", "ВСТАВИТЬ"), ("M", "Обнаружить", "⌕", "#7fb3ff", "НАЙТИ"), [("m", "", "✚", "#f0c040", "БЛОК"), ("m", "", "✎", "#e8ebef", "БЛОКРЕД"), ("m", "", "Ⓐ", "#e8ebef", "АТРРЕД")]]),
  ("Свойства", [("M", "Копирование\nсвойств", "🖌", "#e8ebef", "КОПИРОВАТЬСВ"), [("c", 18, "цвет"), ("c", 18, "тип"), ("c", 18, "вес")]]),
  ("Группы", [("M", "Группа", "▣", "#7fb3ff", "ГРУППА")]),
  ("Утилиты", [("M", "Измерить", "📏", "#f0c040", "ИЗМЕРИТЬ"), [("m", "", "⌖", "#e8ebef", "КООРД"), ("m", "", "▣", "#e8ebef", "БЫСТРВЫБ"), ("m", "", "⊞", "#e8ebef", "КАЛЬК")]]),
  ("Буфер обмена", [("M", "Вставить", "📋", "#f0c040", "ВСТАВИТЬБУФ"), [("m", "", "✂", "#e8ebef", "ВЫРЕЗАТЬ"), ("m", "", "⧉", "#e8ebef", "КОПБУФ")]]),
  ("Вид", [("M", "Базовый", "▱", "#e8ebef", "БАЗОВЫЙ")]),
 ],
 "Вставка": [
  ("Блок", [("M", "Вставка", "⊕", "#7fb3ff", "ВСТАВИТЬ"), ("M", "Обнаружить", "⌕", "#7fb3ff", "НАЙТИ"),
            [("m", "Редактировать атрибут", "✎", "#e8ebef", "АТРРЕД"), ("m", "Сохранить отображение атрибутов", "⧉", "#e8ebef", "АТРОТОБ"), ("m", "Заменить", "⇄", "#e8ebef", "ЗАМЕНИТЬБЛОК")]]),
  ("Определение блока", [("M", "Создать\nблок", "✚", "#f0c040", "БЛОК"), ("M", "Задание\nатрибутов", "🏷", "#e8ebef", "АТРОПР"),
                         ("M", "Управление\nатрибутами", "☷", "#e8ebef", "ДИСПАТР"), ("M", "Редактор\nблоков", "✎", "#e8ebef", "БЛОКРЕД")]),
  ("Ссылка", [("M", "Присоединить", "📎", "#7fb3ff", "ПРИСОЕД"), ("M", "Подрезать", "⬚", "#7fb3ff", "ПОДРЕЗАТЬ"), ("M", "Регулировать", "◐", "#7fb3ff", "РЕГУЛИРОВАТЬ"),
              [("m", "Слои подложки", "☰", "#e8ebef", "СЛОИПОДЛ"), ("m", "*Контуры — различные*", "⬚", "#e8ebef", "КОНТУРЫ"), ("m", "Включить привязку к подложкам", "⌖", "#e8ebef", "ПРИВПОДЛ")]]),
  ("Импорт", [("M", "Импорт\nPDF", "📄", "#e05050", "ИМПОРТPDF"), ("M", "Экспорт\nГИС", "🗺", "#5fd36b", "ЭКСПОРТГИС"), [("m", "Распознавание текста SHX", "Ⓐ", "#e8ebef", "SHX"), ("m", "Параметры распознавания", "⚙", "#e8ebef", "SHXПАР")],
              ("M", "Объединить\nтекст", "A", "#e8ebef", "ОБЪЕДТЕКСТ")]),
  ("Данные", [("M", "Поле", "▤", "#7fb3ff", "ПОЛЕ"), [("m", "Обновление поля", "⟳", "#e8ebef", "ОБНПОЛЕ"), ("m", "OLE-объект", "▣", "#e8ebef", "OLE"), ("m", "Гиперссылка", "🔗", "#e8ebef", "ГИПЕРССЫЛКА")]]),
  ("Связывание и извлечение", [("M", "Связь\nс данными", "⛁", "#f0c040", "СВЯЗЬДАННЫЕ"), [("m", "", "⇩", "#e8ebef", "ИЗВЛЕЧЬ"), ("m", "", "⇧", "#e8ebef", "ЭКСПОРТДАННЫХ"), ("m", "", "⇆", "#e8ebef", "ИМПОРТДАННЫХ")]]),
  ("Местоположение", [("M", "Задать\nместоположение", "🌐", "#7fb3ff", "ГЕОМЕСТО")]),
 ],
 "Аннотации": [
  ("Текст", [("M", "Многострочный\nтекст", "A", "#e8ebef", "МТЕКСТ"), [("c", 24, "стильтекста"), ("e", 24, "Поиск текста"), ("c", 24, "высота")]]),
  ("Размеры", [("M", "Размер", "↔", "#f0c040", "РАЗМЕР"), [("c", 24, "стильразм"), ("m", "Линейный", "⟷", "#e8ebef", "РАЗМЛИНЕЙНЫЙ"), ("m", "Экспресс", "⇹", "#e8ebef", "РАЗМЭКСПРЕСС")],
               [("m", "", "⊤", "#e8ebef", "РАЗМРЕД"), ("m", "", "⊞", "#e8ebef", "РАЗМРЕД"), ("m", "Продолжить", "⇥", "#e8ebef", "РАЗМПРОД")]]),
  ("Осевые линии", [("M", "Маркер\nцентра", "⊕", "#e8ebef", "МАРКЕРЦЕНТРА"), ("M", "Осевая линия", "┅", "#e8ebef", "ОСЕВАЯ")]),
  ("Выноски", [("M", "Мультивыноска", "↗", "#e8ebef", "МВЫНОСКА"), [("c", 24, "стильвыноски"), ("m", "Добавить выноску", "+↗", "#e8ebef", "МВЫНОСКАДОБ"), ("m", "Удалить выноску", "−↗", "#e8ebef", "МВЫНОСКАУД")]]),
  ("Таблицы", [("M", "Таблица", "▦", "#e8ebef", "ТАБЛИЦА"), [("c", 24, "стильтабл"), ("m", "Извлечение данных", "⇩", "#e8ebef", "ИЗВЛЕЧЬ"), ("m", "Связать данные", "⛁", "#e8ebef", "СВЯЗЬДАННЫЕ")]]),
  ("Пометка", [("M", "Маскировка", "▨", "#7fb3ff", "МАСКИРОВКА"), ("M", "Пометочное\nоблако", "☁", "#e8ebef", "ОБЛАКО")]),
  ("Масштабирование аннотаций", [("M", "Добавить\nтекущий масштаб", "✚", "#7fb3ff", "МАСШАННОТ"),
                                 [("m", "Список масштабов", "☰", "#e8ebef", "СПИСОКМАСШ"), ("m", "Добавить/Удалить масштабы", "±", "#e8ebef", "МАСШДОБ"), ("m", "Синх. положения масштабов", "⇅", "#e8ebef", "МАСШСИНХ")]]),
 ],
 "Параметризация": [
  ("Геометрические", [("M", "Автоналожение зависимостей", "⚡", "#f0c040", "АВТОЗАВ"), [("m", "", "∟", "#e8ebef", "ЗАВ"), ("m", "", "∥", "#e8ebef", "ЗАВ"), ("m", "", "⊙", "#e8ebef", "ЗАВ")],
                      [("m", "Показать/Скрыть", "👁", "#e8ebef", "ЗАВПОК"), ("m", "Показать все", "👁", "#e8ebef", "ЗАВПОК"), ("m", "Скрыть все", "◌", "#e8ebef", "ЗАВПОК")]]),
  ("Размерные", [("M", "Линейная", "🔒", "#e8ebef", "РЗАВ"), ("M", "Выравнивание", "🔒", "#e8ebef", "РЗАВ"),
                 [("m", "Показать/Скрыть", "👁", "#e8ebef", "РЗАВПОК"), ("m", "Показать все", "👁", "#e8ebef", "РЗАВПОК"), ("m", "Скрыть все", "◌", "#e8ebef", "РЗАВПОК")]]),
  ("Управление", [("M", "Удалить\nзависимости", "✖", "#e05050", "УДАЛЗАВ"), ("M", "Диспетчер\nпараметров", "ƒ", "#e8ebef", "ПАРАМЕТРЫ")]),
 ],
 "Вид": [
  ("Инструменты видового экрана", [("M", "Знак\nПСК", "⌞", "#7fb3ff", "ЗНАКПСК"), ("M", "View\nCube", "⬢", "#e8ebef", "ВИДКУБ"), ("M", "Панель\nнавигации", "▮", "#e8ebef", "ПАНЕЛЬНАВ")]),
  ("Именованные виды", [[("c", 24, "вид"), ("m", "Новый вид", "✚", "#e8ebef", "ВИД"), ("m", "Диспетчер видов", "☰", "#e8ebef", "ВИД")]]),
  ("Видовые экраны модели", [("M", "Конфигурация\nвидового экрана", "▣", "#e8ebef", "ВЭКРАН"), [("m", "Именованные", "☰", "#e8ebef", "ВЭКРАН"), ("m", "Соединить", "⊞", "#e8ebef", "ВЭКРАН"), ("m", "Восстан", "↺", "#e8ebef", "ВЭКРАН")]]),
  ("Сводка", [("M", "Сравнение файлов\nDWG", "⧉", "#e05050", "СРАВНИТЬ")]),
  ("Журнал", [("M", "Аналитика\nдействий", "⌚", "#f0c040", "ЖУРНАЛ")]),
  ("Палитры", [("M", "Инструментальные\nпалитры", "▦", "#e8ebef", "ПАЛИТРЫ"), ("M", "Свойства", "☰", "#e8ebef", "СВОЙСТВА"), ("M", "Блоки", "⬚", "#7fb3ff", "БЛОКИ"),
               ("M", "Количество", "#", "#7fb3ff", "КОЛИЧЕСТВО"), ("M", "Макросы\nкоманд", "⚡", "#f0a050", "МАКРОСЫ"), ("M", "Диспетчер\nподшивок", "📁", "#e8ebef", "ПОДШИВКИ"),
               [("m", "", ">_", "#e8ebef", "КОМСТРОКА"), ("m", "", "☰", "#e8ebef", "СЛОЙ"), ("m", "", "⊞", "#e8ebef", "КАЛЬК")]]),
  ("Интерфейс", [("M", "Переключить\nокна", "⧉", "#e8ebef", "ОКНА"), ("M", "Вкладки\nфайла", "▭", "#7fb3ff", "ВКЛАДКИФАЙЛА"), ("M", "Вкладки\nлиста", "▭", "#7fb3ff", "ВКЛАДКИЛИСТА"),
                 [("m", "Сверху вниз", "☰", "#e8ebef", "ОКНА"), ("m", "Слева направо", "▥", "#e8ebef", "ОКНА"), ("m", "Каскадом", "⧉", "#e8ebef", "ОКНА")]]),
 ],
 "Управление": [
  ("Рекордер операций", [("M", "Запись", "●", "#e8ebef", "ЗАПИСЬ"), [("m", "Воспроизведение", "▶", "#e8ebef", "ВОСПР"), ("c", 14, "макрос")]]),
  ("Адаптация", [("M", "Пользовательский\nинтерфейс", "CUI", "#e8ebef", "ПИ"), ("M", "Инструментальные\nпалитры", "▦", "#e8ebef", "ПАЛИТРЫ"),
                 [("m", "Импорт", "⇩", "#e8ebef", "ИМПОРТ"), ("m", "Экспорт", "⇧", "#e8ebef", "ЭКСПОРТ"), ("m", "Редактировать псевдонимы", "✎", "#e8ebef", "ПСЕВДОНИМЫ")]]),
  ("Приложения", [("M", "Загрузить\nприложение", "⚙", "#e8ebef", "ЗАГРПРИЛ"), ("M", "Выполнить\nсценарий", ">_", "#e8ebef", "СЦЕНАРИЙ"),
                  [("m", "Редактор Visual Basic", "VB", "#7fb3ff", "VBA"), ("m", "Редактор Visual LISP", "VL", "#7fb3ff", "VLISP"), ("m", "Запустить макрос VBA", "▶", "#7fb3ff", "VBA")]]),
  ("Стандарты оформления", [[("m", "Транслятор слоев", "⇆", "#e8ebef", "ТРАНСЛЯТОР"), ("m", "Проверка", "✔", "#e8ebef", "ПРОВЕРКА"), ("m", "Настройка", "⚙", "#e8ebef", "СТАНДАРТЫ")]]),
  ("Очистка", [("M", "Поиск\nнеудаляемых элементов", "🧹", "#f0c040", "ОЧИСТИТЬ"), [("m", "Очистить", "🧹", "#e8ebef", "ОЧИСТИТЬ"), ("m", "Подчистить", "🧹", "#e8ebef", "ОЧИСТИТЬ"), ("m", "Проверить", "✔", "#e8ebef", "ПРОВЕРИТЬ")]]),
  ("Производительность", [("M", "Анализатор\nпроизводительности", "⏱", "#e8ebef", "ПРОИЗВ")]),
 ],
 "Вывод": [
  ("Печать", [("M", "Печать", "🖶", "#e8ebef", "ПЕЧАТЬ"), ("M", "Пакетная\nпечать", "🖶", "#7fb3ff", "ПАКЕТПЕЧАТЬ"), ("M", "Предварительный просмотр", "🔍", "#e8ebef", "ПРЕДВАР"),
              [("m", "Диспетчер параметров листов", "☰", "#e8ebef", "ПАРАМЛИСТ"), ("m", "Подробности о виде", "ⓘ", "#e8ebef", "ПОДРОБНО"), ("m", "Диспетчер плоттеров", "🖶", "#e8ebef", "ПЛОТТЕРЫ")]]),
  ("Экспорт в DWF/PDF", [("M", "Экспорт", "PDF", "#e05050", "ЭКСПОРТ_PDF"), ("M", "Экспорт\nГИС", "🗺", "#5fd36b", "ЭКСПОРТГИС"), [("c", 26, "экспорт"), ("c", 26, "параметрылиста"), ("m", "", "🔍  ⬇  ⬇", "#e8ebef", "ЭКСПОРТPDF")]]),
 ],
 "Лист": [
  ("Макет", [("M", "Новый\nлист", "▭", "#7fb3ff", "ЛИСТ"), ("M", "Параметры\nлиста", "☰", "#e8ebef", "ПАРАМЛИСТ")]),
  ("Видовые экраны листа", [("M", "Модель", "▣", "#7fb3ff", "МОДЕЛЬ"), [("m", "Развернуть ВЭкран", "⤢", "#e8ebef", "МОДЕЛЬ"), ("m", "Блокировать", "🔒", "#f0c040", "ВЭБЛОК")]]),
  ("Печать и публикация", [("M", "Печать", "🖶", "#e8ebef", "ПЕЧАТЬ"), ("M", "Экспорт\nPDF", "PDF", "#e05050", "ЭКСПОРТPDF"), ("M", "Все листы\nв PDF", "PDF", "#e05050", "ЭКСПОРТВСЕ")]),
 ],
 "Карта": [
  ("Слой", [("M", "Базовая\nкарта", "🗺", "#5fd36b", "БАЗКАРТА"), ("M", "Добавить\nданные", "✚", "#f0c040", "ДОБДАННЫЕ"),
            [("m", "Растр TIFF / GeoTIFF", "🖼", "#e8ebef", "ПРИСОЕД"), ("m", "KML / KMZ / GPX", "🌐", "#7fb3ff", "ГЕОФАЙЛ"), ("m", "Импорт чертежа", "⇩", "#e8ebef", "ИМПОРТЧЕРТ")]]),
  ("Выборка", [("M", "Выбрать", "⬚", "#7fb3ff", "ВЫБРАТЬФОРМА"), ("M", "Выбор по\nатрибутам", "☰", "#7fb3ff", "ВЫБАТР"), ("M", "Выбор по\nрасположению", "◎", "#7fb3ff", "ВЫБРАСП"),
               [("m", "Очистить", "✖", "#e05050", "ОЧИСТВЫБ"), ("m", "Быстрый выбор", "▣", "#e8ebef", "БЫСТРВЫБ"), ("m", "Выбрать подобные", "⧉", "#e8ebef", "ВЫБРАТЬПОДОБНЫЕ")]]),
  ("Экспорт", [("M", "Экспорт\nГИС", "🗺", "#5fd36b", "ЭКСПОРТГИС")]),
 ],
 "Надстройки": [("Приложения", [("M", "Autodesk App\nStore", "⬢", "#e8ebef", "МАГАЗИН")])],
 "Совместная работа": [("Общий доступ", [("M", "Общий\nдоступ", "➤", "#7fb3ff", "ОБЩИЙ")]), ("Сравнение", [("M", "Сравнение файлов\nDWG", "⧉", "#e05050", "СРАВНИТЬ")])],
 "Express Tools": [
  ("Blocks", [("M", "Explode\nAttributes", "⊡", "#7fb3ff", "BURST"), ("M", "Replace\nBlock", "⇄", "#7fb3ff", "BLOCKREPLACE"),
              [("m", "List Properties", "☰", "#e8ebef", "XLIST"), ("m", "Import Attributes", "⇩", "#e8ebef", "ATTIN"), ("m", "Export Attributes", "⇧", "#e8ebef", "ATTOUT")]]),
  ("Text", [("M", "Arc\nAligned", "ᴬᴮᶜ", "#e8ebef", "ARCTEXT"), ("M", "Modify\nText", "A", "#e8ebef", "TXTEDIT"),
            [("m", "Convert to Mtext", "⇄", "#e8ebef", "TXT2MTXT"), ("m", "Auto Number", "¹²³", "#e8ebef", "TCOUNT"), ("m", "Enclose in Object", "Ⓐ", "#e8ebef", "TCIRCLE")]]),
  ("Modify", [[("m", "Move/Copy/Rotate", "✥", "#e8ebef", "MOCORO"), ("m", "Stretch Multiple", "⇲", "#e8ebef", "MSTRETCH")]]),
  ("Layout", [[("m", "Align Space", "⊞", "#e8ebef", "ALIGNSPACE"), ("m", "Synchronize Viewports", "⇆", "#e8ebef", "VPSYNC"), ("m", "Merge Layout", "⧉", "#e8ebef", "LAYOUTMERGE")]]),
  ("Draw", [("M", "Break-line\nSymbol", "⌁", "#e8ebef", "BREAKLINE"), ("M", "Super\nHatch", "▧", "#e8ebef", "SUPERHATCH")]),
  ("Dimension", [("M", "Annotation\nAttachment", "Ⓐ", "#e8ebef", "DIMREASSOC"), [("m", "Reset Text", "↺", "#e8ebef", "DIMREASSOC"), ("m", "Import Style", "⇩", "#e8ebef", "DIMIM"), ("m", "Export Style", "⇧", "#e8ebef", "DIMEX")]]),
  ("Tools", [("M", "Command\nAliases", ">_", "#e8ebef", "ALIASEDIT"), [("m", "Attach Xdata", "⊕", "#e8ebef", "XDATA"), ("m", "List Xdata", "☰", "#e8ebef", "XDLIST"), ("m", "System Variables", "⚙", "#e8ebef", "SYSVDLG")]]),
  ("Web", [("M", "URL\nOptions", "🌐", "#7fb3ff", "URL")]),
 ],
 "Рекомендованные приложения": [("Приложения", [("M", "Рекомендованные\nприложения", "⬢", "#e8ebef", "МАГАЗИН")])],
}


# săgețile ▾ de sub / lângă butoane, ca în AutoCAD: comanda butonului -> [(text, icoană, comandă) sau None = separator]
SUB = {
    "МТЕКСТ": [("Многострочный текст", "A", "МТЕКСТ"), ("Однострочный текст", "A", "ТЕКСТ")],
    "РАЗМЛИНЕЙНЫЙ": [("Линейный", "⟷", "РАЗМЛИНЕЙНЫЙ"), ("Параллельный", "⤡", "РАЗМПАРАЛ"), ("Угловой", "∠", "РАЗМУГЛ"), None,
                     ("Длина дуги", "◠", "РАЗМДУГА"), ("Радиус", "◔", "РАЗМРАДИУС"), ("Диаметр", "⌀", "РАЗМДИАМЕТР"), None,
                     ("Ординатный", "⊥", "РАЗМОРД"), ("С изломом", "⌇", "РАЗМИЗЛОМ")],
    "МВЫНОСКА": [("Выноска", "↗", "МВЫНОСКА"), None, ("Добавить выноску", "+↗", "МВЫНОСКАДОБ"), ("Удалить выноску", "×↗", "МВЫНОСКАУД"), None,
                 ("Выровнять", "⇉", "МВЫНОСКАВЫР"), ("Группировать", "⊞", "МВЫНОСКАГР")],
    "ВСТАВИТЬ": "blocuri",
    "МАССИВ": [("Прямоугольный массив", "⊞", "МАССИВПРЯМ"), ("Массив по траектории", "⋰", "МАССИВТРАЕКТ"), ("Круговой массив", "⁂", "МАССИВКРУГ")],
    "ОБРЕЗАТЬ": [("Обрезать", "✂", "ОБРЕЗАТЬ"), ("Удлинить", "⇥", "УДЛИНИТЬ")],
    "СОПРЯЖЕНИЕ": [("Сопряжение", "⌒", "СОПРЯЖЕНИЕ"), ("Фаска", "⟋", "ФАСКА"), ("Соединение кривых", "∿", "СОЕДИНЕНИЕ")],
    "ВСТАВИТЬБУФ": [("Вставить", "📋", "ВСТАВИТЬБУФ"), ("Вставить как блок", "📋", "ВСТАВИТЬБЛОК"), ("Вставить как гиперссылку", "📋", "ВСТАВИТЬГИПЕР"),
                    ("Вставить с исходными координатами", "📋", "ВСТАВИТЬИСХ"), ("Специальная вставка", "📋", "СПЕЦВСТАВКА")],
    "КРУГ": [("Центр, радиус", "◎", "КРУГ"), ("Центр, диаметр", "⌀", "КРУГЦД"), None, ("2 точки", "◯", "КРУГ2Т"), ("3 точки", "◯", "КРУГ3Т"), None,
             ("2 точки касания, радиус", "◔", "КРУГККР"), ("3 точки касания", "◔", "КРУГ3К")],
    "ДУГА": [("3 точки", "◠", "ДУГА3Т"), None, ("Начало, центр, конец", "◠", "ДУГАНЦК"), ("Начало, центр, угол", "◠", "ДУГАНЦУ"), ("Начало, центр, длина", "◠", "ДУГАНЦД"), None,
             ("Начало, конец, угол", "◠", "ДУГАНКУ"), ("Начало, конец, направление", "◠", "ДУГАНКН"), ("Начало, конец, радиус", "◠", "ДУГАНКР"), None,
             ("Центр, начало, конец", "◠", "ДУГАЦНК"), ("Центр, начало, угол", "◠", "ДУГАЦНУ"), ("Центр, начало, длина", "◠", "ДУГАЦНД"), None, ("Продолжить", "↩", "ДУГАПРОД")],
    "ШТРИХ": [("Штриховка", "▨", "ШТРИХ"), ("Градиент", "▤", "ГРАДИЕНТ"), ("Контур", "▭", "КОНТУР")],
    "ОБЛАКО": [("Прямоугольное", "☁", "ОБЛАКОПРЯМ"), ("Многоугольное", "☁", "ОБЛАКОМНОГ"), ("От руки", "☁", "ОБЛАКОРУКА")],
    "ПОРЯДОК": [("На передний план", "⧉", "ПОРВПЕРЕД"), ("На задний план", "⧉", "ПОРНАЗАД"), ("Перед объектами", "⧉", "ПОРПЕРЕД"), ("За объектами", "⧉", "ПОРЗА"), None,
                ("Текст на передний план", "A", "ТЕКСТВПЕРЕД"), ("Размеры на передний план", "↔", "РАЗМВПЕРЕД"), ("Выноски на передний план", "↗", "ВЫНВПЕРЕД"),
                ("Все аннотации на передний план", "A↔", "АННВПЕРЕД"), ("Штриховку на задний план", "▨", "ШТРИХНАЗАД")],
    "АТРРЕД": [("Один", "✎", "АТРРЕД"), ("Несколько", "✎", "АТРРЕДН")],
    "АТРОТОБ": [("Сохранить отображение атрибутов", "✔", "АТРОТОБН"), ("Показать все атрибуты", "💡", "АТРОТОБВСЕ"), ("Скрыть все атрибуты", "○", "АТРОТОБНЕТ")],
    "ИМПОРТPDF": [("Импорт PDF", "📄", "ИМПОРТPDF"), ("Импорт DGN", "DGN", "ИМПОРТDGN"), ("Импорт", "⇩", "ИМПОРТЧЕРТ")],
    "БЛОК": [("Создать блок", "✚", "БЛОК"), ("Запись блока на диск", "💾", "ПБЛОК")],
    "ГЕОМЕСТО": [("Из карт Esri", "🌐", "ГЕОESRI"), ("Из карт Bing", "🌐", "ГЕОBING"), ("Из файла", "📄", "ГЕОФАЙЛ")],
    "ЭКСПОРТ_PDF": [("DWFx", "DWFx", "ЭКСПОРТDWFX"), ("DWF", "DWF", "ЭКСПОРТDWF"), ("PDF", "PDF", "ЭКСПОРТ_PDF")],
    "ВЫБРАТЬФОРМА": [("Прямоугольник", "▭", "ВЫБПРЯМ"), ("Полигон", "⬠", "ВЫБПОЛИГОН"), ("Лассо", "◌", "ВЫБЛАССО"), ("Круг", "◯", "ВЫБКРУГ"),
                     ("Линия", "╱", "ВЫБЛИНИЯ"), ("Трасса", "⌇", "ВЫБТРАССА")],
    "БАЗКАРТА": "harti",
    "ДОБДАННЫЕ": [("Растр TIFF / GeoTIFF (в координатах)", "🖼", "ПРИСОЕД"), ("KML / KMZ / GPX", "🌐", "ГЕОФАЙЛ"), ("Чертеж DWG / DXF", "⇩", "ИМПОРТЧЕРТ"),
                  ("PDF", "📄", "ИМПОРТPDF"), ("Таблица Excel → TCOUNT / атрибуты", "▦", "ATTIN")],
    "ЭКСПОРТГИС": [("Shapefile (SHP)", "🗺", "ЭКСПОРТSHP"), ("Esri File Geodatabase (GDB)", "🗺", "ЭКСПОРТGDB"), ("Excel (XLSX)", "▦", "ЭКСПОРТXLSX"),
                   ("Excel 97-2003 (XLS)", "▦", "ЭКСПОРТXLS"), ("Google Earth (KML)", "🌐", "ЭКСПОРТKML"), ("Google Earth (KMZ)", "🌐", "ЭКСПОРТKMZ")],
    "БАЗОВЫЙ": [("Из пространства модели", "A", "ВИДМОДЕЛЬ"), ("Из Inventor", "I", "ВИДINVENTOR")],
    "ВЫРЕЗАТЬ": [("Вырезать", "✂", "ВЫРЕЗАТЬ"), ("Вырезать с базовой точкой", "✂", "ВЫРЕЗАТЬБАЗ")],
    "КОПБУФ": [("Копировать в буфер", "⧉", "КОПБУФ"), ("Копировать с базовой точкой", "⧉", "КОПБАЗ")],
    "РАЗМПРОД": [("Продолжить", "⇥", "РАЗМПРОД"), ("Базовый", "⇤", "РАЗМБАЗ")],
    "ПСЕВДОНИМЫ": [("Редактировать псевдонимы", "A", "ПСЕВДОНИМЫ"), ("Редактировать список автоисправления", ">_", "АВТОИСПР"), ("Редактировать список синонимов", ">_", "СИНОНИМЫ")],
    "ИЗМЕРИТЬ": [("Быстрое", "📏", "ИЗМЕРИТЬ"), ("Расстояние", "↔", "ИЗМЕРИТЬ"), ("Радиус", "◔", "РАДИУСИЗМ"), ("Угол", "∠", "УГОЛИЗМ"),
                 ("Площадь", "◺", "ПЛОЩАДЬ"), ("Объем", "⛁", "ОБЪЕМ")],
}

# săgeata ▾ din titlul grupului: instrumentele în plus ale grupului
SUB_GRUP = {
    "Рисование": [("Сплайн", "∿", "СПЛАЙН"), ("Прямая", "⟋", "ПРЯМАЯ"), ("Луч", "↗", "ЛУЧ"), ("Точка", "·", "ТОЧКА"), ("Деление", "⁘", "ДЕЛИТЬ"),
                  ("Разметка", "⁙", "РАЗМЕТИТЬ"), None, ("Область", "▰", "ОБЛАСТЬ"), ("Маскировка", "▨", "МАСКИРОВКА"), ("Облако", "☁", "ОБЛАКО"),
                  ("Спираль", "◎", "СПИРАЛЬ"), ("Кольцо", "◉", "КОЛЬЦО"), ("Контур", "▭", "КОНТУР")],
    "Редактирование": [("Удалить дубликаты", "⧉", "УДАЛИТЬДУБЛ"), ("Разорвать", "⫶", "РАЗОРВАТЬ"), ("Соединить", "⎯", "СОЕДИНИТЬ"), ("Стереть", "✎", "СТЕРЕТЬ"),
                       ("Растянуть", "⇲", "РАСТЯНУТЬ"), ("Расчленить", "⊡", "РАСЧЛЕНИТЬ"), None, ("Порядок прорисовки", "⧈", "ПОРЯДОК"),
                       ("Выровнять", "⇉", "ВЫРОВНЯТЬ"), ("Редактировать полилинию", "⌇", "ПОЛРЕД"), ("Редактировать штриховку", "▦", "ШТРИХРЕД")],
    "Утилиты": [("Координаты", "⌖", "КООРД"), ("Отображение точек...", "⁘", "ДИАЛТОЧ")],
    "Слои": [("Свойства слоя", "☰", "СЛОЙ"), ("Сделать текущим слой объекта", "⇆", "СЛОЙТЕК")],
    "Аннотации": [("Однострочный текст", "A", "ТЕКСТ"), ("Многострочный текст", "A", "МТЕКСТ"), ("Найти и заменить", "🔎", "НАЙТИ"), ("Автонумерация", "¹²³", "TCOUNT")],
    "Блок": [("Вставить блок", "⊕", "ВСТАВИТЬ"), ("Редактировать атрибуты", "Ⓐ", "АТРРЕД"), ("Экспорт атрибутов в Excel", "⇧", "ATTOUT"), ("Импорт атрибутов из Excel", "⇩", "ATTIN")],
}

SFATURI = {
    "ОТРЕЗОК": "Создание прямолинейных сегментов. Каждый сегмент – отдельный объект.", "ПЛИНИЯ": "Создание двумерной полилинии из отрезков.",
    "КРУГ": "Создание круга. ▾ – другие способы построения.", "ДУГА": "Создание дуги. ▾ – 11 способов построения.",
    "ШТРИХ": "Заполнение замкнутой области штриховкой. ▾ – градиент и контур.", "СЛОЙ": "Диспетчер свойств слоев: цвет, вкл/выкл, заморозка, блокировка, печать.",
    "ВСТАВИТЬ": "Вставка блока (символа). ▾ – последние, избранные и блоки из библиотек.", "ТАБЛИЦА": "Вставка таблицы: пустой, из Excel или из атрибутов блоков.",
    "ВЫБРАТЬВСЕ": "Выбор всех объектов, кроме объектов на замороженных или заблокированных слоях (Ctrl+A).", "ЭКСПОРТГИС": "Экспорт в SHP, GDB, XLS, XLSX, KML, KMZ (MOLDREF99).",
    "БАЗКАРТА": "Галерея базовых карт (как в ArcGIS Pro): спутник, улицы, топография, рельеф, серые основы, океаны, OSM. ▾ – быстрый выбор.",
    "ВЫБРАТЬФОРМА": "Выбор объектов формой: прямоугольник, полигон, лассо, круг, линия, трасса (▾).",
    "ВЫБАТР": "Выбор по атрибутам: слой, тип, цвет, блок, текст, длина, площадь, атрибуты блоков; условия И / ИЛИ.",
    "ВЫБРАСП": "Выбор по расположению: пересекаются, в пределах расстояния, полностью внутри, содержат.",
    "ГЕОМЕСТО": "Карта под чертежом (Esri) или точки и линии из KML/KMZ/GPX в координатах MOLDREF99.", "ПРИСОЕД": "Растровое изображение (TIFF/GeoTIFF) в реальных координатах.",
    "ИЗМЕРИТЬ": "Расстояние, радиус, угол, площадь.", "ПЕЧАТЬ": "Печать на принтер или в PDF, форматы A0–A5.",
}

# panourile extinse (săgeata din titlul grupului), ca în AutoCAD: rânduri de iconițe + elemente cu text
# ("r", [(icoană, culoare, comandă, sfat), …]) = rând de iconițe;  ("e", icoană, text, comandă) = element;  "-" = separator
PANOURI = {
    "Рисование": [("r", [("∿", "#7fb3ff", "СПЛАЙН", "Сплайн по определяющим точкам"), ("⟋", "#7fb3ff", "ПРЯМАЯ", "Прямая (бесконечная)"), ("↗", "#7fb3ff", "ЛУЧ", "Луч"),
                         ("·", "#7fb3ff", "ТОЧКА", "Несколько точек"), ("⁘", "#7fb3ff", "ДЕЛИТЬ", "Поделить"), ("⁙", "#7fb3ff", "РАЗМЕТИТЬ", "Разметить")]),
                  ("r", [("▭", "#e8ebef", "КОНТУР", "Контур"), ("▨", "#e8ebef", "ШТРИХ", "Штриховка"), ("◉", "#e8ebef", "КОЛЬЦО", "Кольцо"), ("☁", "#e8ebef", "ОБЛАКО", "Облако для пометок ▾"),
                         ("◎", "#e8ebef", "СПИРАЛЬ", "Спираль"), ("▰", "#e8ebef", "ОБЛАСТЬ", "Область")])],
    "Редактирование": [("r", [("⧉", "#e8ebef", "УДАЛИТЬДУБЛ", "Удалить дубликаты"), ("⫶", "#e8ebef", "РАЗОРВАТЬ", "Разорвать"), ("⎯", "#e8ebef", "СОЕДИНИТЬ", "Соединить"),
                              ("⌇", "#e8ebef", "ПОЛРЕД", "Редактировать полилинию"), ("▦", "#e8ebef", "ШТРИХРЕД", "Редактировать штриховку")]),
                       ("r", [("⇉", "#e8ebef", "ВЫРОВНЯТЬ", "Выровнять"), ("⇄", "#e8ebef", "ОБРАТИТЬ", "Обратить"), ("⊡", "#e8ebef", "РАСЧЛЕНИТЬ", "Расчленить"),
                              ("🧹", "#f0c040", "ОЧИСТИТЬ", "Очистить"), ("⧈", "#7fb3ff", "ПОРЯДОК", "Порядок прорисовки ▾")])],
    "Слои": [("r", [("◐", "#f0c040", "СЛОЙИЗО", "Изолировать слои выбранных объектов"), ("◑", "#f0c040", "СЛОЙНЕИЗО", "Отменить изоляцию слоев"),
                    ("❄", "#7fc8ff", "СЛОЙЗАМ", "Заморозить слой объекта"), ("○", "#f0c040", "СЛОЙОТКЛ", "Отключить слой объекта"), ("⇆", "#e8ebef", "СЛОЙТЕКОБ", "Сделать текущим слой объекта")]),
             ("r", [("💡", "#f0c040", "СЛОЙВКЛ", "Включить все слои"), ("☀", "#f0c040", "СЛОЙРАЗМ", "Разморозить все слои"), ("🔒", "#f0c040", "СЛОЙБЛОК", "Блокировать слой объекта"),
                    ("🔓", "#f0c040", "СЛОЙРАЗБЛОК", "Разблокировать все слои"), ("⇩", "#e8ebef", "СЛОЙНАТЕК", "Перенести на текущий слой")]),
             ("r", [("⧉", "#e8ebef", "СЛОЙОБЪЕД", "Объединить слои"), ("✖", "#e05050", "СЛОЙУДАЛ", "Удалить слой (с объектами)")]), "-",
             ("e", "☰", "Несохраненная конфигурация слоев", "СЛОЙ"), ("e", "◐", "Затенение блокированных слоев: 0 / 30 / 50 / 70 %", "ЗАТЕНЕНИЕ")],
    "Аннотации": [("e", "A", "Текстовый стиль ▾", "СТИЛЬ"), ("e", "↔", "Размерный стиль: Standard", "РЗМСТИЛЬ"), ("e", "↗", "Стиль мультивыноски: Standard", "МЛСТИЛЬ"),
                  ("e", "▦", "Стиль таблиц: Standard", "ТАБЛСТИЛЬ")],
    "Группы": [("e", "▣", "Группа", "ГРУППА"), ("e", "⊡", "Разгруппировать", "РАЗГРУППИРОВАТЬ"), ("e", "✎", "Редактировать группу", "РЕДГРУППА"),
               ("e", "☑", "Выбор группы вкл/выкл", "ВЫБОРГРУППЫ"), "-", ("e", "☰", "Диспетчер групп", "ДИСПГРУПП"), ("e", "⬚", "Ограничивающая рамка группы", "РАМКАГРУППЫ")],
    "Утилиты": [("e", "⌖", "Координаты", "КООРД"), ("e", "⁘", "Отображение точек...", "ДИАЛТОЧ")],
    "Размеры": [("r", [("⟷", "#e8ebef", "РАЗМЛИНЕЙНЫЙ", "Линейный"), ("⤡", "#e8ebef", "РАЗМПАРАЛ", "Параллельный"), ("◔", "#e8ebef", "РАЗМРАДИУС", "Радиус"),
                       ("⌀", "#e8ebef", "РАЗМДИАМЕТР", "Диаметр"), ("⇥", "#e8ebef", "РАЗМПРОД", "Продолжить"), ("⇤", "#e8ebef", "РАЗМБАЗ", "Базовый")])],
    "Определение блока": [("e", "⌖", "Задать базовую точку", "БАЗА"), ("e", "⟳", "Синхронизация", "АТРСИНХР")],
}


class Panglica:
    def __init__(self, app, parinte):
        self.app = app; self.pagini = {}; self.file = {}; self.combo = {}; self.activ = None
        self.grupuri = {}; self.titluri_l = []; self.titluri = True; self.ascunse = {"Лист"}
        bf = tk.Frame(parinte, bg=TITLU, height=H_FILE); bf.pack(fill="x"); bf.pack_propagate(False)
        for n in FILE:
            l = tk.Label(bf, text=n, bg=TITLU, fg=TEXT, font=F_FILA, padx=9); l.pack(side="left", fill="y")
            l.bind("<Button-1>", lambda e, n=n: self.arata(n)); self.file[n] = l
            l.bind("<Enter>", lambda e, n=n: self.file[n].config(bg=HOVER) if n != self.activ else None)
            l.bind("<Leave>", lambda e, n=n: self.file[n].config(bg=TITLU) if n != self.activ else None)
        b = tk.Label(bf, text=" ▭ ▾", bg=TITLU, fg=TEXT, font=F_FILA); b.pack(side="left", padx=8); self.b_comuta = b
        self.file["Лист"].config(bg="#2c5d8a"); self.file["Лист"].pack_forget()
        bf.bind("<Button-3>", lambda e: self.app.mn.context_panglica(e))
        for l in self.file.values(): l.bind("<Button-3>", lambda e: self.app.mn.context_panglica(e))
        b.bind("<Button-1>", lambda e: self.comuta())
        self.corp = tk.Frame(parinte, bg=CORP, height=H_CORP); self.corp.pack(fill="x"); self.corp.pack_propagate(False)
        self.vizibil = True
        for n, grupuri in FILE.items():
            f = tk.Frame(self.corp, bg=CORP); self.pagini[n] = f
            for titlu, coloane in grupuri: self._grup(f, titlu, coloane, n)
            f.bind("<Button-3>", lambda e: self.app.mn.context_panglica(e))
        self.h_corp = H_CORP; self.dx = 0
        self.st = tk.Label(self.corp, text="◀", bg="#2b313a", fg="white", font=(F, -14, "bold"), padx=3)
        self.dr = tk.Label(self.corp, text="▶", bg="#2b313a", fg="white", font=(F, -14, "bold"), padx=3)
        self.st.bind("<Button-1>", lambda e: self._defileaza(+360)); self.dr.bind("<Button-1>", lambda e: self._defileaza(-360))
        self.corp.bind("<Configure>", lambda e: self._defileaza(0))
        self.arata("Главная")
        parinte.after(50, self._ajusteaza)

    def _ajusteaza(self):
        """înălțimea panglicii după conținut (pe Windows cu scară 125–150% textul e mai mare, altfel se tăia)"""
        self.corp.update_idletasks()
        h = max([f.winfo_reqheight() for f in self.pagini.values()] + [H_CORP]) + 2
        if h != self.h_corp:
            self.h_corp = h
            if self.vizibil: self.corp.config(height=h)
        self._defileaza(0)

    def _defileaza(self, d):
        """când filele nu încap pe lățime: săgeți ◀ ▶ (ca în AutoCAD, panourile rămân întregi)"""
        if not self.activ: return
        f = self.pagini[self.activ]; W = self.corp.winfo_width(); w = f.winfo_reqwidth()
        if w <= W: self.dx = 0; self.st.place_forget(); self.dr.place_forget()
        else:
            self.dx = max(min(0, self.dx + d), W - w - 24)
            self.dr.place(relx=1, x=0, y=0, relheight=1, anchor="ne") if self.dx > W - w - 24 else self.dr.place_forget()
            self.st.place(x=0, y=0, relheight=1) if self.dx < 0 else self.st.place_forget()
        f.place(x=self.dx, y=0, width=max(w, W), relheight=1); self.st.lift(); self.dr.lift()

    def comuta(self):
        """ascunde / arată corpul panglicii (ca săgeata din AutoCAD)"""
        self.vizibil = not self.vizibil
        self.corp.config(height=self.h_corp if self.vizibil else 1)

    def arata(self, n):
        if not self.vizibil: self.comuta()
        for k, l in self.file.items(): l.config(bg=CORP if k == n else TITLU, fg="white" if k == n else TEXT)
        for k, f in self.pagini.items():
            if k == n: f.place(x=0, y=0, relwidth=1, relheight=1)
            else: f.place_forget()
        self.activ = n; self.dx = 0
        if hasattr(self, "st"): self.corp.after_idle(lambda: self._defileaza(0))

    # ---------------------------------------------------------------- un grup
    def arata_fila(self, n, da):
        (self.ascunse.discard if da else self.ascunse.add)(n)
        for k, l in self.file.items(): l.pack_forget()
        for k, l in self.file.items():
            if k not in self.ascunse: l.pack(side="left", fill="y", before=self.b_comuta)
        if not da and self.activ == n: self.arata("Главная")

    def arata_grup(self, fr, da):
        if da: fr.pack(side="left", fill="y")
        else: fr.pack_forget()

    def arata_titluri(self, da):
        self.titluri = da
        for l in self.titluri_l: l.pack(side="bottom", fill="x") if da else l.pack_forget()

    def _grup(self, pag, titlu, coloane, fila=None):
        g = tk.Frame(pag, bg=CORP); g.pack(side="left", fill="y"); self.grupuri.setdefault(fila, []).append((titlu, g))
        sus = tk.Frame(g, bg=CORP); sus.pack(side="top", fill="both", expand=True, padx=3, pady=(3, 0))
        are = titlu in SUB_GRUP or titlu in PANOURI
        jos = tk.Label(g, text=titlu + " ▾" if are else titlu, bg=CORP, fg=TEXT, font=F_GRUP); jos.pack(side="bottom", fill="x"); self.titluri_l.append(jos)
        jos.bind("<Button-3>", lambda e: self.app.mn.context_panglica(e))
        if are:
            jos.bind("<Button-1>", lambda e, t=titlu, w=jos: self.submeniu_grup(t, w))
            jos.bind("<Enter>", lambda e, w=jos: w.config(bg=HOVER)); jos.bind("<Leave>", lambda e, w=jos: w.config(bg=CORP))
        for col in coloane:
            if isinstance(col, list):
                c = tk.Frame(sus, bg=CORP); c.pack(side="left", fill="y", padx=2)
                for it in col: self._mic(c, it)
            else: self._mare(sus, col)
        tk.Frame(pag, bg=SEP, width=1).pack(side="left", fill="y", pady=4)

    def _buton(self, w, cmd):
        w.bind("<Enter>", lambda e: self._bg(w, HOVER)); w.bind("<Leave>", lambda e: self._bg(w, CORP))
        w.bind("<Button-1>", lambda e: self.app.executa(cmd))
        for c in w.winfo_children():
            c.bind("<Button-1>", lambda e: self.app.executa(cmd)); c.bind("<Enter>", lambda e: self._bg(w, HOVER)); c.bind("<Leave>", lambda e: self._bg(w, CORP))

    def _sfat(self, w, text, cmd):
        from unelte import Sfat
        t = (text or "").replace("\n", " ").strip() or cmd.capitalize()
        Sfat(w, f"{t}\n\n{SFATURI.get(cmd, 'Щелчок – выполнить команду.')}\n\n>_ {cmd}")

    def _bg(self, w, bg):
        w.config(bg=bg)
        for c in w.winfo_children(): c.config(bg=bg)

    def _mare(self, p, it):
        _, text, ic, cul, cmd = it
        b = tk.Frame(p, bg=CORP); b.pack(side="left", fill="y", padx=1)
        tk.Label(b, text=ic, bg=CORP, fg=cul, font=F_ICON if len(ic) < 3 else (F_ICON[0], -15, "bold"), height=1).pack(side="top", pady=(2, 0))
        tk.Label(b, text=text, bg=CORP, fg=TEXT, font=F_BTN, justify="center").pack(side="top")
        self._buton(b, cmd); self._sfat(b, text, cmd)
        if cmd in SUB:
            s = tk.Label(b, text="▾", bg=CORP, fg=TEXT, font=(F, -10)); s.pack(side="top")
            s.bind("<Button-1>", lambda e, c=cmd, w=b: self.submeniu(c, w)); b.winfo_children()[1].bind("<Button-1>", lambda e, c=cmd, w=b: self.submeniu(c, w))

    def submeniu_grup(self, titlu, w):
        if titlu in PANOURI:
            from unelte import Popup
            p = Popup(self.app, w)
            for el in PANOURI[titlu]:
                if el == "-": p.separator()
                elif el[0] == "r": p.rand_iconite(el[1])
                else: p.element(el[1], el[2], el[3])
            if titlu in SUB_GRUP:
                p.separator()
                for x in SUB_GRUP[titlu]:
                    if x is not None: p.element(x[1], x[0], x[2])
            p.titlu(titlu); return p.arata()
        m = tk.Menu(self.app.root, tearoff=0, bg="#3b4453", fg=TEXT, activebackground=HOVER, activeforeground="white", bd=0, font=(F, -13))
        for x in SUB_GRUP[titlu]:
            if x is None: m.add_separator()
            else: m.add_command(label=f"  {x[1]:<3}  {x[0]}", command=lambda c=x[2]: self.app.executa(c))
        m.tk_popup(w.winfo_rootx(), w.winfo_rooty() + w.winfo_height())

    def submeniu(self, cmd, w):
        m = tk.Menu(self.app.root, tearoff=0, bg="#3b4453", fg=TEXT, activebackground=HOVER, activeforeground="white", bd=0, font=(F, -13))
        el = SUB[cmd]
        if el == "harti":
            import geo
            for n in geo.SURSE: m.add_command(label=("  ✔  " if n == self.app.v.harta.sursa else "      ") + n, command=lambda n=n: self.app.gis.alege_harta(n))
            m.add_separator(); m.add_command(label="      Без базовой карты", command=lambda: self.app.gis.alege_harta(None))
            m.add_command(label="      Галерея базовых карт...", command=self.app.gis.galerie)
            return m.tk_popup(w.winfo_rootx(), w.winfo_rooty() + w.winfo_height())
        if el == "blocuri":
            doc = self.app.doc
            nume = sorted(b.name for b in doc.blocks if not b.name.startswith("*") and not b.is_any_layout) if doc else []
            if not nume: m.add_command(label="      (в чертеже нет блоков)", state="disabled")
            for n in nume[:40]: m.add_command(label="  ⬚   " + n, command=lambda n=n: self.app.executa("ВСТАВИТЬ " + n))
            m.add_separator()
            for t, c in (("Последние блоки...", "БЛОКИПОСЛ"), ("Избранные блоки...", "БЛОКИИЗБР"), ("Блоки из библиотек...", "БЛОКИБИБЛ")): m.add_command(label="      " + t, command=lambda c=c: self.app.executa(c))
        else:
            for x in el:
                if x is None: m.add_separator()
                else: m.add_command(label=f"  {x[1]:<3}  {x[0]}", command=lambda c=x[2]: self.app.executa(c))
        m.tk_popup(w.winfo_rootx(), w.winfo_rooty() + w.winfo_height())

    def _mic(self, p, it):
        if isinstance(it, list):                       # un rând de butoane mici, unul lângă altul
            r = tk.Frame(p, bg=CORP); r.pack(side="top", anchor="w")
            for x in it:
                _, text, ic, cul, cmd = x
                b = tk.Frame(r, bg=CORP); b.pack(side="left")
                tk.Label(b, text=ic, bg=CORP, fg=cul, font=F_ICON_MIC, width=2).pack(side="left"); self._buton(b, cmd); self._sfat(b, text, cmd)
                if cmd in SUB:
                    sg = tk.Label(r, text="▾", bg=CORP, fg=TEXT, font=(F, -9)); sg.pack(side="left")
                    sg.bind("<Button-1>", lambda e, c=cmd, w=b: self.submeniu(c, w))
            return
        if it[0] == "c" and it[2] == "цвет":
            from lista_culori import ListaCulori
            w = ListaCulori(p, self.app, 170); w.pack(side="top", anchor="w", pady=1); self.combo["цвет"] = w; return
        if it[0] == "c" and it[2] == "слой":
            from lista_straturi import ListaStraturi
            w = ListaStraturi(p, self.app, 250); w.pack(side="top", anchor="w", pady=1); self.combo["слой"] = w; return
        if it[0] == "c":
            v = tk.StringVar(); cb = ttk.Combobox(p, textvariable=v, width=it[1], state="readonly", style="Cad.TCombobox")
            cb.pack(side="top", anchor="w", pady=1); self.combo[it[2]] = cb
            cb.bind("<<ComboboxSelected>>", lambda e, k=it[2]: self.app.combo_ales(k, self.combo[k].get()))
            return
        if it[0] == "e":
            e = tk.Entry(p, width=it[1] + 4, bg="#2b313a", fg=GRI, insertbackground=TEXT, relief="flat", font=F_MIC)
            e.insert(0, it[2]); e.pack(side="top", anchor="w", pady=2, ipady=2); self.combo["cauta"] = e
            e.bind("<FocusIn>", lambda ev: (e.delete(0, "end"), e.config(fg=TEXT)) if e.get() == it[2] else None)
            e.bind("<Return>", lambda ev: self.app.executa("НАЙТИТЕКСТ " + e.get()))
            return
        _, text, ic, cul, cmd = it
        b = tk.Frame(p, bg=CORP); b.pack(side="top", anchor="w", fill="x")
        tk.Label(b, text=ic, bg=CORP, fg=cul, font=F_ICON_MIC, width=2 if len(ic) < 3 else len(ic)).pack(side="left")
        if text: tk.Label(b, text=text, bg=CORP, fg=TEXT, font=F_MIC).pack(side="left", padx=(2, 4))
        self._buton(b, cmd); self._sfat(b, text, cmd)
        if cmd in SUB:
            s = tk.Label(b, text="▾", bg=CORP, fg=TEXT, font=(F, -10)); s.pack(side="left")
            s.bind("<Button-1>", lambda e, c=cmd, w=b: self.submeniu(c, w))
