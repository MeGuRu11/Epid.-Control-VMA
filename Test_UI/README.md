
# EpiSafe — WOW UI demo (Qt Widgets) aligned to context.md

Это **WOW-макет**, который сохраняет "вау эффект" (анимации, toast, плавные переходы, живой мед‑фон),
но придерживается структуры/палитры/разделов из `context.md`. fileciteturn2file6

## Запуск
```bash
pip install -r requirements.txt
python -m app.main
```

## Первый запуск
Если база пустая, появится окно FirstRun и создаст admin:
- login: admin
- password: admin1234

## Что вау
- **Живой медицинский фон** (частицы/клетки + "пульс" + мягкий параллакс) (QGraphicsView + QTimer)
- **Переходы между страницами** (fade + slide) (QPropertyAnimation)
- **Выезжающее меню** (drawer/sidebar) + hover‑микроанимации
- **Toast/Snackbar** по палитре статусов (success/warn/error/info) fileciteturn2file9
- **Скелет‑лоадер** (shimmer) для имитации фоновых операций (в контексте docs это "долгие операции в фоне") fileciteturn2file13

## Разделы
Меню соответствует карте UI из context.md: Главная, ЭМЗ, Форма 100, Поиск и ЭМК, Лаборатория, Санитария, Аналитика, Импорт/Экспорт, Справочники, Администрирование. fileciteturn2file8
