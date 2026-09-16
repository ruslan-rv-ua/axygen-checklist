# Розробка: середовище та цикл перевірки

Цей файл описує **процес** — як зібрати додаток і як бачити правки в живому NVDA.

Про **поведінку** додатка — [`requirements.md`](requirements.md). Усе, що стосується самого артефакта (структура `addon/`, генерований `manifest.ini`, джерело версії, локалізація), нормативно описано в §6 спеки; тут воно лише використовується.

## 1. Передумови

* **Python 3.13** — версія з `.python-version` шаблону; NVDA `master` вимагає `>=3.13,<3.14`.
* **SCons ≥ 4.10.1** — збірка.
* **GNU gettext** (`msgfmt`, `xgettext`) — компіляція `.po` у `.mo`. Windows-збірки: [gettext-iconv-windows](https://mlocati.github.io/articles/gettext-iconv-windows.html).
* **Markdown ≥ 3.8.2** — генерація HTML з документації.
* **`uv`** — dev-залежності шаблону (Ruff, Pyright, `prek`). `uv run prek install` вмикає ті самі перевірки, що й CI, на кожному коміті; `uv run prek run --all-files` проганяє їх по всьому репозиторію.

## 2. Перша збірка

```
scons
```

Створює:

* `addon/manifest.ini` — з `manifest.ini.tpl` і `buildVars.py`;
* `addon/locale/<lang>/manifest.ini` — з `.po` і `manifest-translated.ini.tpl`;
* `addon/locale/<lang>/LC_MESSAGES/nvda.mo` — компільовані переклади;
* `<addon_name>-<addon_version>.nvda-addon` у корені репозиторію.

Жоден із цих файлів не комітиться — єдине джерело метаданих `buildVars.py` (§6 спеки).

Перед першою збіркою в `buildVars.py` мають бути заповнені `addon_minimumNVDAVersion` і `addon_lastTestedNVDAVersion`: з типовим `None` маніфест не пройде перевірку й NVDA просто не завантажить теку. `addon_lastTestedNVDAVersion` тримай не нижчою за свою версію NVDA — інакше аддон буде позначено несумісним і вимкнено.

## 3. Підключення робочої копії до NVDA

NVDA переглядає `%APPDATA%\nvda\addons\*` і бере кожну теку, у якій читається `manifest.ini` (`addonHandler._getAvailableAddonsFromPath` — звичайні `os.listdir` та `os.path.isdir`). Junction проходить цю перевірку як звичайна тека, тож посилання на `addon/` робить робочу копію встановленим аддоном:

```
powershell -ExecutionPolicy Bypass -File tools\dev-link.ps1
```

Скрипт бере ім'я з `addon_name` у `buildVars.py`, переконується, що `addon/manifest.ini` існує, і створює junction `%APPDATA%\nvda\addons\<addon_name>` → `<репозиторій>\addon`. Junction (`mklink /J`) обрано замість симлінка (`mklink /D`), бо не потребує ані прав адміністратора, ані ввімкненого Режиму розробника Windows.

Після створення посилання **перезапусти NVDA** (`Ctrl+Alt+N`): список аддонів NVDA будує на старті.

Так перевіряється саме той код, що поїде в реліз: працюють `manifest.ini`, перевірка сумісності та `addonHandler.initTranslation()`. Чому не Developer Scratchpad — §8.

### Портативна копія для ризикованих перевірок

*Інструменти → Створити портативну копію* дає NVDA з власною текою конфігурації, тож посилання можна покласти в неї й не чіпати щоденний профіль:

```
powershell -ExecutionPolicy Bypass -File tools\dev-link.ps1 -NvdaConfig D:\nvda-portable\userConfig
```

Дві копії NVDA одночасно не працюють — запуск портативної замінює встановлену, — але експеримент лишається ізольованим від робочого профілю.

## 4. Цикл розробки

* **Код у `addon/globalPlugins/`** — `NVDA+Ctrl+F3` (*Інструменти → Перезавантажити плагіни*). `globalPluginHandler.reloadGlobalPlugins()` викидає з `sys.modules` усе з префіксом `globalPlugins` і імпортує заново; перезапуск NVDA не потрібен.
* **Переклади (`.po`)** — `scons` (перекомпілювати `.mo`), далі перезапуск NVDA.
* **`buildVars.py`, маніфест** — `scons`, далі перезапуск NVDA.
* **Нове посилання, нова тека аддона** — перезапуск NVDA: `addonHandler` будує список аддонів один раз, на старті.

Наслідок для структури коду: **увесь код додатка лежить під `addon/globalPlugins/<пакет>/`**. Модуль поза цим деревом (скажімо, спільна бібліотека в корені `addon/`) не має префікса `globalPlugins`, тому перезавантаження плагінів не викине його з `sys.modules` — у пам'яті лишиться стара версія, і поведінка стане непоясненною.

## 5. Від'єднання

```
powershell -ExecutionPolicy Bypass -File tools\dev-link.ps1 -Remove
```

Скрипт знімає саме посилання й відмовляється працювати, якщо на місці посилання виявилася справжня тека.

**Не видаляй dev-посилання через Add-on Store.** NVDA видаляє аддон так: перейменовує теку, далі `shutil.rmtree` (`addonHandler.Addon.completeRemove`). Python ≥ 3.11 трактує junction як посилання й усередину не заходить, тож файли репозиторію вціліють, але `rmtree` завершиться помилкою, яку `ignore_errors=True` проковтне: посилання лишиться на диску, а стан аддона в NVDA — зіпсованим.

З тієї ж причини не знімай посилання через `Remove-Item` у Windows PowerShell 5.1: там воно заходить у ціль і видаляє вміст. Скрипт видаляє лише точку повторного розбору.

## 6. Коли аддон ламає NVDA

Помилка в глобальному плагіні може лишити машину без озвучення, тож запобіжники варто знати **до** першого запуску:

* `Ctrl+Alt+N` — перезапуск NVDA.
* Меню NVDA → *Вийти* → **«Перезапустити з вимкненими аддонами»**.
* `nvda.exe --disable-addons` — те саме з командного рядка.
* `NVDA+F1` — переглядач логу; повний файл — `%TEMP%\nvda.log`. Рівень *Debug* у *Параметри NVDA → Загальні* показує трасування наших виключень.

## 7. Перед релізом

Dev-посилання перевіряє код, але не перевіряє пакет. Перед злиттям гілки `release/*`:

1. зняти посилання (§5);
2. `scons` — зібрати `.nvda-addon`;
3. встановити зібраний файл (*Інструменти → Add-on Store → Встановити зі стороннього джерела*, або просто відкрити файл) і перезапустити NVDA;
4. перевірити встановлення, оновлення поверх попередньої версії та штатне видалення.

## 8. Відхилені варіанти

**Developer Scratchpad** — `%APPDATA%\nvda\scratchpad\globalPlugins\`, вмикається в *Параметри NVDA → Додатково → «Увімкнути завантаження власного коду з теки Developer Scratchpad»*. Офіційний спосіб швидко перевірити код, сумісний і з посиланням, і з `NVDA+Ctrl+F3`. Відхилено: код у scratchpad не належить жодному аддону, тому `addonHandler.initTranslation()` там завершується помилкою — Developer Guide формулює це прямо. Спека (§6, «Локалізація») вимагає цей виклик у кожному модулі з `_()`, тож у scratchpad додаток або не запуститься, або запуститься лише з тимчасово вирізаною локалізацією — тобто перевірятиметься не той код, що піде в реліз. Додатково scratchpad не бачить `manifest.ini`, теки `addon/locale` і перевірки сумісності.

**Збирати й встановлювати `.nvda-addon` на кожну правку.** Відхилено як щоденний цикл: кожна ітерація коштує перезапуску NVDA. Лишається обов'язковим кроком перед релізом (§7).

## Джерела

* [NVDA Developer Guide](https://download.nvaccess.org/documentation/developerGuide.html)
* [NVDA Add-on Scons Template](https://github.com/nvaccess/AddonTemplate)
* [NVDA Add-on Development Guide](https://github.com/nvdaaddons/DevGuide/wiki/NVDA-Add-on-Development-Guide)
