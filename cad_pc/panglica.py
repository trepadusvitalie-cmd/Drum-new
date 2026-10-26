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
  ("Вид", [("M", "Базовый", "▱", "#e8ebef", "ВИД")]),
 ],
 "Вставка": [
  ("Блок", [("M", "Вставка", "⊕", "#7fb3ff", "ВСТАВИТЬ"), ("M", "Обнаружить", "⌕", "#7fb3ff", "НАЙТИ"),
            [("m", "Редактировать атрибут", "✎", "#e8ebef", "АТРРЕД"), ("m", "Сохранить отображение атрибутов", "⧉", "#e8ebef", "АТРОТОБ"), ("m", "Заменить", "⇄", "#e8ebef", "ЗАМЕНИТЬБЛОК")]]),
  ("Определение блока", [("M", "Создать\nблок", "✚", "#f0c040", "БЛОК"), ("M", "Задание\nатрибутов", "🏷", "#e8ebef", "АТРОПР"),
                         ("M", "Управление\nатрибутами", "☷", "#e8ebef", "ДИСПАТР"), ("M", "Редактор\nблоков", "✎", "#e8ebef", "БЛОКРЕД")]),
  ("Ссылка", [("M", "Присоединить", "📎", "#7fb3ff", "ПРИСОЕД"), ("M", "Подрезать", "⬚", "#7fb3ff", "ПОДРЕЗАТЬ"), ("M", "Регулировать", "◐", "#7fb3ff", "РЕГУЛИРОВАТЬ"),
              [("m", "Слои подложки", "☰", "#e8ebef", "СЛОИПОДЛ"), ("m", "*Контуры — различные*", "⬚", "#e8ebef", "КОНТУРЫ"), ("m", "Включить привязку к подложкам", "⌖", "#e8ebef", "ПРИВПОДЛ")]]),
  ("Импорт", [("M", "Импорт\nPDF", "📄", "#e05050", "ИМПОРТPDF"), [("m", "Распознавание текста SHX", "Ⓐ", "#e8ebef", "SHX"), ("m", "Параметры распознавания", "⚙", "#e8ebef", "SHXПАР")],
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
  ("Экспорт в DWF/PDF", [("M", "Экспорт", "PDF", "#e05050", "ЭКСПОРТPDF"), [("c", 26, "экспорт"), ("c", 26, "параметрылиста"), ("m", "", "🔍  ⬇  ⬇", "#e8ebef", "ЭКСПОРТPDF")]]),
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
    "СОПРЯЖЕНИЕ": [("Сопряжение", "⌒", "СОПРЯЖЕНИЕ"), ("Фаска", "⟋", "ФАСКА"), ("Плавное соединение", "∿", "СОЕДИНЕНИЕ")],
    "ВСТАВИТЬБУФ": [("Вставить", "📋", "ВСТАВИТЬБУФ"), ("Вставить как блок", "📋", "ВСТАВИТЬБЛОК"), ("Вставить как гиперссылку", "📋", "ВСТАВИТЬГИПЕР"),
                    ("Вставить с исходными координатами", "📋", "ВСТАВИТЬИСХ"), ("Специальная вставка", "📋", "СПЕЦВСТАВКА")],
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


class Panglica:
    def __init__(self, app, parinte):
        self.app = app; self.pagini = {}; self.file = {}; self.combo = {}; self.activ = None
        bf = tk.Frame(parinte, bg=TITLU, height=H_FILE); bf.pack(fill="x"); bf.pack_propagate(False)
        for n in FILE:
            l = tk.Label(bf, text=n, bg=TITLU, fg=TEXT, font=F_FILA, padx=9); l.pack(side="left", fill="y")
            l.bind("<Button-1>", lambda e, n=n: self.arata(n)); self.file[n] = l
            l.bind("<Enter>", lambda e, n=n: self.file[n].config(bg=HOVER) if n != self.activ else None)
            l.bind("<Leave>", lambda e, n=n: self.file[n].config(bg=TITLU) if n != self.activ else None)
        b = tk.Label(bf, text=" ▭ ▾", bg=TITLU, fg=TEXT, font=F_FILA); b.pack(side="left", padx=8)
        b.bind("<Button-1>", lambda e: self.comuta())
        self.corp = tk.Frame(parinte, bg=CORP, height=H_CORP); self.corp.pack(fill="x"); self.corp.pack_propagate(False)
        self.vizibil = True
        for n, grupuri in FILE.items():
            f = tk.Frame(self.corp, bg=CORP); self.pagini[n] = f
            for titlu, coloane in grupuri: self._grup(f, titlu, coloane)
        self.arata("Главная")

    def comuta(self):
        """ascunde / arată corpul panglicii (ca săgeata din AutoCAD)"""
        self.vizibil = not self.vizibil
        self.corp.config(height=H_CORP if self.vizibil else 1)

    def arata(self, n):
        if not self.vizibil: self.comuta()
        for k, l in self.file.items(): l.config(bg=CORP if k == n else TITLU, fg="white" if k == n else TEXT)
        for k, f in self.pagini.items():
            if k == n: f.place(x=0, y=0, relwidth=1, relheight=1)
            else: f.place_forget()
        self.activ = n

    # ---------------------------------------------------------------- un grup
    def _grup(self, pag, titlu, coloane):
        g = tk.Frame(pag, bg=CORP); g.pack(side="left", fill="y")
        sus = tk.Frame(g, bg=CORP); sus.pack(side="top", fill="both", expand=True, padx=3, pady=(3, 0))
        jos = tk.Label(g, text=titlu + " ▾" if len(titlu) < 30 else titlu, bg=CORP, fg=TEXT, font=F_GRUP); jos.pack(side="bottom", fill="x")
        if titlu in SUB_GRUP:
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

    def _bg(self, w, bg):
        w.config(bg=bg)
        for c in w.winfo_children(): c.config(bg=bg)

    def _mare(self, p, it):
        _, text, ic, cul, cmd = it
        b = tk.Frame(p, bg=CORP); b.pack(side="left", fill="y", padx=1)
        tk.Label(b, text=ic, bg=CORP, fg=cul, font=F_ICON if len(ic) < 3 else (F_ICON[0], -15, "bold"), height=1).pack(side="top", pady=(2, 0))
        tk.Label(b, text=text, bg=CORP, fg=TEXT, font=F_BTN, justify="center").pack(side="top")
        self._buton(b, cmd)
        if cmd in SUB:
            s = tk.Label(b, text="▾", bg=CORP, fg=TEXT, font=(F, -10)); s.pack(side="top")
            s.bind("<Button-1>", lambda e, c=cmd, w=b: self.submeniu(c, w)); b.winfo_children()[1].bind("<Button-1>", lambda e, c=cmd, w=b: self.submeniu(c, w))

    def submeniu_grup(self, titlu, w):
        m = tk.Menu(self.app.root, tearoff=0, bg="#3b4453", fg=TEXT, activebackground=HOVER, activeforeground="white", bd=0, font=(F, -13))
        for x in SUB_GRUP[titlu]:
            if x is None: m.add_separator()
            else: m.add_command(label=f"  {x[1]:<3}  {x[0]}", command=lambda c=x[2]: self.app.executa(c))
        m.tk_popup(w.winfo_rootx(), w.winfo_rooty() + w.winfo_height())

    def submeniu(self, cmd, w):
        m = tk.Menu(self.app.root, tearoff=0, bg="#3b4453", fg=TEXT, activebackground=HOVER, activeforeground="white", bd=0, font=(F, -13))
        el = SUB[cmd]
        if el == "blocuri":
            doc = self.app.doc
            nume = sorted(b.name for b in doc.blocks if not b.name.startswith("*") and not b.is_any_layout) if doc else []
            if not nume: m.add_command(label="      (в чертеже нет блоков)", state="disabled")
            for n in nume[:40]: m.add_command(label="  ⬚   " + n, command=lambda n=n: self.app.executa("ВСТАВИТЬ " + n))
            m.add_separator()
            for t in ("Последние блоки...", "Избранные блоки...", "Блоки из библиотек..."): m.add_command(label="      " + t, command=lambda: self.app.executa("ВСТАВИТЬ"))
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
                tk.Label(b, text=ic, bg=CORP, fg=cul, font=F_ICON_MIC, width=2).pack(side="left"); self._buton(b, cmd)
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
        self._buton(b, cmd)
        if cmd in SUB:
            s = tk.Label(b, text="▾", bg=CORP, fg=TEXT, font=(F, -10)); s.pack(side="left")
            s.bind("<Button-1>", lambda e, c=cmd, w=b: self.submeniu(c, w))
